# Smart Logistics Data & ML Platform

Тестовое задание на позицию **Middle Data Engineer**: сквозной прототип
`ETL → Core DWH → Mart → ML` для аналитики и прогнозирования тарифов
грузоперевозок.

## Содержание

- [Архитектура](#архитектура)
- [Стек](#стек)
- [Быстрый старт](#быстрый-старт)
- [Структура репозитория](#структура-репозитория)
- [Слои данных](#слои-данных)
- [Вопрос 1. ETL и DQ](#вопрос-1-etl-и-dq)
- [Вопрос 2. Mart Layer](#вопрос-2-mart-layer)
- [Вопрос 3. ML и batch inference](#вопрос-3-ml-и-batch-inference)
- [Airflow](#airflow)
- [Тесты](#тесты)
- [Проверочные SQL-запросы](#проверочные-sql-запросы)
- [Решения и ограничения](#решения-и-ограничения)
- [Чек-лист сдачи](#чек-лист-сдачи)

## Архитектура

```mermaid
flowchart LR
    SRC["public.prices + справочники"] --> STG["stg.price_validation"]
    STG --> DQ["dq.dq_quarantine_prices"]
    STG --> CORE["core.prices"]
    CORE --> MART["mart.mart_route_card"]
    CORE --> FEATURES["ml.price_features"]
    FEATURES --> MODEL["CatBoost + baseline"]
    MODEL --> PRED["mart.ml_price_predictions"]
```

Пайплайн:

1. **ETL** читает окно `[start_date, end_date)` из `public.prices`.
2. Выполняет DQ-валидацию, конвертацию валют, обогащение категорий.
3. Валидные строки пишет в `core.prices`, отбракованные — в карантин.
4. Собирает аналитическую витрину `mart.mart_route_card`.
5. Материализует ML-признаки в `ml.price_features`.
6. Обучает CatBoost и пишет прогнозы в `mart.ml_price_predictions`.

## Стек

- **PostgreSQL 17** — источник, Core DWH, Mart и ML-таблицы.
- **Python 3.11+** — ETL, ML, CLI.
- **SQLAlchemy + psycopg2** — работа с БД.
- **Pydantic** — валидация конфигов и результатов.
- **pandas / numpy** — подготовка ML-данных.
- **scikit-learn / CatBoost** — baseline и основная модель.
- **Apache Airflow 2.10.5** — оркестрация ETL и ML.
- **Docker Compose** — локальный запуск всего стека.

## Быстрый старт

### Docker

```bash
cp .env.example .env
docker compose up --build
```

- Airflow UI: <http://localhost:8080>
  - Логин/пароль: `airflow` / `airflow`
- PostgreSQL: `localhost:5432`, БД `deals_bigdata`
  - Логин/пароль: `postgres` / `postgres`

При первом старте PostgreSQL применяет `sql/schema.sql` и
`sql/synthetic.sql`. Если база уже создана, init-скрипты повторно не
выполняются. Для полного пересоздания:

```bash
docker compose down -v
docker compose up --build
```

Airflow-образ собирается из `docker/airflow/Dockerfile`: в него добавлены
`catboost` и `scikit-learn` для ML.

ETL DAG `run_etl_pipeline` запускается по расписанию (ежедневно в 7:00 по МСК)
и триггерит `ml_pipeline` после успешного завершения.

### CLI

```bash
pip install -e '.[dev]'
```

или:

```bash
pip install -r requirements.txt
pip install pytest
```

ETL:

```bash
python -m etl --start-date 2023-01-01 --end-date 2027-12-31
```

Окно право-исключающее: `[start_date, end_date)`.

ML:

```bash
python -m ml --as-of 2026-10-26
```

Без `--as-of` берётся `AS_OF_DATE` или дефолт `2026-10-26`.

## Структура репозитория

```text
docker/airflow/Dockerfile   # Airflow + CatBoost/sklearn
etl/                        # ETL-библиотека
  db.py                     # engine, выполнение SQL
  schemas.py                # инициализация схем
  staging.py                # DQ-валидация и stg
  load.py                   # загрузка core/quarantine
  mart.py                   # сборка mart_route_card
  models.py                 # Pydantic-модели
  config.py                 # AS_OF_DATE
  __main__.py               # CLI etl
ml/                         # ML-пайплайн
  features.py               # материализация признаков
  split.py                  # time-split
  dataset.py                # X/y, категориальные признаки
  metrics.py                # метрики
  train.py                  # baseline + CatBoost
  predict.py                # batch inference
  pipeline.py               # полный ML-пайплайн
  models.py                 # Pydantic-модели ML
  __main__.py               # CLI ml
dags/
  etl_pipeline.py           # ETL DAG + TriggerDagRunOperator
  ml_pipeline.py            # отдельный ML DAG
sql/
  schema.sql                # DDL источника
  synthetic.sql             # генератор данных
  migrations/               # DQ, core, mart, ml
  transforms/               # DQ, загрузка core/quarantine
  marts/build_mart_route_card.sql
  ml/features.sql
tests/                      # контрактные и интеграционные тесты
```

## Слои данных

| Слой | Объект | Назначение |
| --- | --- | --- |
| Staging | `stg.price_validation` | Результат DQ-валидации окна |
| DQ | `dq.dq_quarantine_prices` | Отбракованные сделки и причины |
| Core | `core.prices` | Очищенные факты сделок |
| Mart | `mart.mart_route_card` | Месячные коридоры ставок |
| ML | `ml.price_features` | Материализованные признаки |
| Prediction | `mart.ml_price_predictions` | Факт vs прогноз |

## Вопрос 1. ETL и DQ

### Окно и идемпотентность

- Окно: `[start_date, end_date)`, правая граница не включается.
- Повторный запуск за тот же период безопасен: из `core.prices` и карантина
  удаляются только `price_id`, попавшие в staging, затем данные вставляются
  заново.
- `etl_run_id` — `text`: в CLI пишется UUID, в Airflow — `run_id` запуска DAG.

### DQ-правила

| Причина | Условие |
| --- | --- |
| `1. Некорректная цена` | `price <= 0` |
| `2. Слишком низкая цена` | RUB и `0 < price <= 1000` |
| `3. Некорректная дистанция` | `distance <= 0` |
| `4. Некорректный вес` | `total_weight < 0` |
| `5. Некорректный объём` | `total_volume < 0` |
| `6. Неизвестный город` | города нет в `cities` |
| `7. Нет курса валюты` | нет точного курса для `840/978` |

Важно:

- RUB (`643`) всегда имеет курс `1.0`; `nearest_rate_date IS NULL` для RUB
  не является ошибкой.
- Иностранная валюта конвертируется по точному курсу
  `exchange_rates.setting_date = prices.nearest_rate_date`.
- Fallback по `loading_date` не используется.
- `outlier_mark` не отбраковывается в Core: это флаг для витрины и ML.
- Ноль в весе/объёме допустим; отрицательные значения — нет.

Результат на текущем датасете:

```text
источник:        300 000
core.prices:     299 797
карантин:            203
  причина 1:         164
  причина 7:          39
```

### Обогащение

- `weight_category` заполняется по весу с округлением до `0.1` т.
- `volume_category`: `0 < V <= 120` → `FTL`, иначе `OTH`.
- Пропуски категорий заполняются, существующие значения сохраняются.

## Вопрос 2. Mart Layer

### `mart.mart_route_card`

Grain:

```text
month × loading_city_gcid × unloading_city_gcid × body_group × weight_category
```

`volume_category` — атрибут, не входит в grain. Также хранится
`volume_categories text[]` со всеми встреченными значениями.

### Правила

- Месяц берётся из `price_dates.price_date`, а не из `loading_date`.
- Только `is_fact = true`, `NOT complex`, `NOT outlier_mark`.
- `price_rub > 0`, `distance > 0`.
- Будущие месяцы `price_date > as_of` исключаются.
- Дубли `cities.gc_id` устраняются минимальным `cities.id`.
- Кузова маппятся в группы: `Тент`, `Рефрижератор`, `Изотерм`, `Борт`,
  `Прочие`, `Не указан`.

### Метрики

- `p25_trip`, `median_trip`, `p75_trip`, `avg_trip`;
- `p25_km`, `median_km`, `p75_km`;
- `trips_count`, `carriers_count`, `cv_rate`;
- `mom_pct`, `yoy_pct`;
- `reliability_level`.

`MoM`/`YoY` считаются только к ровно предыдущему календарному
месяцу/году; при отсутствии ячейки — `NULL`.

`reliability_level`:

- `HIGH` — `trips_count >= 30`, `carriers_count >= 5` и конец месяца не
  старше 30 дней от `as_of`;
- `MEDIUM` — `trips_count >= 10`;
- иначе `LOW_DATA`.

Результат текущего прогона:

```text
mart.mart_route_card: 203 644 строки
HIGH:                       10
MEDIUM:                    924
LOW_DATA:              202 710
```

Сборка полного mart занимает около 14 секунд.

## Вопрос 3. ML и batch inference

### Данные и target

- Источник: `core.prices`.
- Target: `price_rub`.
- Только `is_fact`, `NOT complex`, `NOT outlier_mark`, `price_rub > 0`,
  `distance > 0`.
- `outlier_mark` — фильтр, не признак.

### Time split

```text
as_of       = 2026-10-26
train_start = 2026-07-26
test_start  = 2026-10-05

train: [2026-07-26, 2026-10-05)
test:  [2026-10-05, 2026-10-26]
```

Случайный shuffle не используется.

### Признаки

22 базовых признака:

- `distance`, `total_weight`, `total_volume`;
- координаты отправления/назначения;
- `loading_year`, `loading_month`, `loading_dow`, `loading_doy`;
- `month_sin/cos`, `dow_sin/cos`, `doy_sin/cos`;
- регионы отправления/назначения;
- `body_group`, `weight_category`, `volume_category`.

Названия городов и `body_type` остаются в `ml.price_features` как резерв,
но в базовую модель не входят из-за высокой кардинальности/дублирования.

### Защита от утечек

Исключены:

- `price`, `price_rub`, `price_with_vat`;
- `price / distance`, `price / total_weight`;
- `price_group_id`, `price_group_stats`;
- `outlier_mark`, `is_fact`, `complex`, `price_type`;
- `organization_id`, `subscriber_id`;
- `created_at`, `updated_at`, `currency_code`, `nearest_rate_date`.

`SimpleImputer`, `StandardScaler`, `OneHotEncoder` обучаются только на train.

### Модели и метрики

Baseline: `Ridge` с one-hot и масштабированием.

Основная модель: `CatBoostRegressor` с дефолтными параметрами,
`random_seed=42`, `cat_features` для категориальных признаков.

Метрики на test:

| Модель | R² | MAPE | RMSE, ₽ | MAE, ₽ |
| --- | ---: | ---: | ---: | ---: |
| Ridge baseline | 0.8401 | 49.50% | 76 489.86 | 48 408.82 |
| **CatBoost** | **0.9146** | **16.38%** | **55 913.81** | **28 922.18** |

Артефакты:

```text
ml/artifacts/catboost_v1.cbm
ml/artifacts/catboost_v1_metadata.json
```

Метаданные содержат метрики, границы split, список признаков, категориальные
признаки и `random_seed`.

### Batch inference

- test: `actual_price_rub = target`, считаются `abs_error_rub` и `ape_pct`;
- future (`loading_date > as_of`): `actual_price_rub`, `abs_error_rub`,
  `ape_pct` = `NULL`, даже если в источнике заполнено `price`;
- запись идемпотентна: удаление по `model_name` + batch insert через
  `execute_values`.

Результат текущего прогона:

```text
ml.price_features:            37 034
train:                        24 226
test:                         12 808
mart.ml_price_predictions:   18 625
  test с фактом:             12 808
  future без факта:           5 817
```

## Airflow

### ETL DAG `run_etl_pipeline`

Задачи:

```text
init_dq_schema
  >> init_core_schema
  >> init_mart_schema
  >> init_ml_schema
  >> extract_and_stage_window
  >> load_validation_results
  >> refresh_mart_route_card
  >> trigger_ml_pipeline
```

- Расписание: `0 7 * * *`.
- Окно берётся из `data_interval_start` / `data_interval_end`.
- `load_validation_results` получает Airflow `run_id`.
- В конце — `TriggerDagRunOperator` для `ml_pipeline`.

### ML DAG `ml_pipeline`

- `schedule=None`, запускается только триггером.
- Одна задача `run_ml_pipeline`, которая вызывает общий `run_ml_pipeline()`.
- Тот же код, что и `python -m ml`.

`TriggerDagRunOperator` не ждёт завершения ML DAG. Если нужно, чтобы ETL
ждал ML, установи `wait_for_completion=True`.

## Тесты

```bash
pip install -e '.[dev]'
```

Без БД:

```bash
pytest -q -m 'not integration'
```

Проверяются:

- `Window`: `start_date < end_date`;
- границы time-split;
- отсутствие target/id в `X`;
- отсутствие leakage-колонок в признаках.

Интеграционные тесты требуют отдельную БД. Создание:

```bash
docker exec -i ul_postgres psql -U postgres -d postgres \
  -c "DROP DATABASE IF EXISTS deals_bigdata_test;" \
  -c "CREATE DATABASE deals_bigdata_test;"

docker exec -i ul_postgres psql -U postgres -d deals_bigdata_test \
  -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/01_schema.sql

docker exec -i ul_postgres psql -U postgres -d deals_bigdata_test \
  -v ON_ERROR_STOP=1 -v n_prices=300000 \
  -f /docker-entrypoint-initdb.d/02_synthetic.sql
```

Запуск:

```bash
TEST_DATABASE_URL='postgresql+psycopg2://postgres:postgres@localhost:5432/deals_bigdata_test' \
  pytest -q
```

Интеграционные тесты проверяют:

- повторный ETL не меняет количество строк и сумму `price_rub`;
- повторная материализация признаков не меняет count/sum `target`;
- повторный batch inference не меняет count/sum прогнозов;
- нет дублей `(price_id, model_name)`;
- у future-строк `actual_price_rub IS NULL`.

Результат:

```text
6 passed
```

## Проверочные SQL-запросы

Коридор по маршрутам с достаточной выборкой:

```sql
SELECT
    month,
    loading_city_name,
    unloading_city_name,
    body_group,
    weight_category,
    trips_count,
    p25_trip,
    median_trip,
    p75_trip,
    reliability_level
FROM mart.mart_route_card
WHERE trips_count >= 30
ORDER BY month DESC, trips_count DESC
LIMIT 20;
```

Факт vs прогноз:

```sql
SELECT
    loading_date,
    loading_city_gcid,
    unloading_city_gcid,
    body_group,
    actual_price_rub,
    predicted_price_rub,
    abs_error_rub,
    ape_pct
FROM mart.ml_price_predictions
WHERE model_name = 'catboost_v1'
ORDER BY loading_date DESC
LIMIT 20;
```

Карантин по причинам:

```sql
SELECT
    r.description,
    count(*) AS rows
FROM dq.dq_quarantine_prices q
JOIN dq.dq_quarantine_reasons r ON r.id = q.reason_id
GROUP BY r.description
ORDER BY rows DESC;
```

## Решения и ограничения

- `as_of = 2026-10-26` задаётся через `AS_OF_DATE`; системная дата не
  используется.
- `outlier_mark` для самых свежих сделок `2026-10-26` может быть `false`,
  потому что ночной job разметки ещё не отработал. Это ограничение
  исходных данных.
- Для RUB `nearest_rate_date IS NULL` допустим: курс рубля равен `1.0`.
- В ML одна сделка получает одну primary-группу кузова по приоритету
  `Тент → Рефрижератор → Изотерм → Борт → Прочие`; для витрины допустимо
  несколько групп.
- `volume_category` в витрине — представительный атрибут (`MIN`), а
  `volume_categories` хранит все значения.
- `reliability_level = HIGH` считается по концу месяца.
- Для future-скоринга используется `require_fact = false`, чтобы оценивать
  плановые заявки независимо от `is_fact`.
- Airflow worker использует кастомный образ с CatBoost; без пересборки
  `docker compose up --build` ML DAG не запустится.
