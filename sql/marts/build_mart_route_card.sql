-- Сборка витрины mart.mart_route_card.
-- Очистка таблицы выполняется в refresh_mart_route_card.
-- as_of передаётся параметром :as_of.

-- Дедупликация городов по gc_id
WITH cities_dedup AS MATERIALIZED (
    SELECT DISTINCT ON (gc_id) 
        gc_id,
        id,
        name,
        full_name_local,
        latitude,
        longitude
    FROM
        cities
    ORDER BY
        gc_id,
        id
),
-- Преобразование price_body_types в бизнес-группы с дедупликацией по группе
price_body_groups AS MATERIALIZED (
    SELECT
        DISTINCT pbt.price_id,
        CASE
            WHEN pbt.body_type_id IN (56, 57, 58, 59, 60, 61) THEN 'Тент'
            WHEN pbt.body_type_id IN (4, 46, 47, 48) THEN 'Рефрижератор'
            WHEN pbt.body_type_id = 2 THEN 'Изотерм'
            WHEN pbt.body_type_id IN (1, 15) THEN 'Борт'
            ELSE 'Прочие'
        END AS body_group
    FROM
        price_body_types pbt
),
-- Фоллбек для цен, у которых нет соответствия в price_body_types
-- Для них берём prices.body_type
price_body_fallback AS (
    SELECT
        p.price_id,
        CASE
            WHEN p.body_type IS NULL THEN 'Не указан'
            WHEN p.body_type IN (56, 57, 58, 59, 60, 61) THEN 'Тент'
            WHEN p.body_type IN (4, 46, 47, 48) THEN 'Рефрижератор'
            WHEN p.body_type = 2 THEN 'Изотерм'
            WHEN p.body_type IN (1, 15) THEN 'Борт'
            ELSE 'Прочие'
        END AS body_group
    FROM
        core.prices p
    WHERE NOT EXISTS (
        SELECT 1 FROM price_body_groups g WHERE g.price_id = p.price_id
    )
),
-- Объединяем два предыдущих запроса
price_groups AS MATERIALIZED (
    SELECT price_id, body_group
    FROM price_body_groups
    
    UNION

    SELECT price_id, body_group
    FROM price_body_fallback
),
-- В одной сделке может быть несколько дат ПРМ с разными месяцами,
-- поэтому переводим даты в месяцы и группируем, чтобы убрать дубли
price_months AS MATERIALIZED (
    SELECT
        pd.price_id,
        date_trunc('month', pd.price_date)::date AS month
    FROM
        price_dates pd
    WHERE
        pd.price_date <= :as_of
    GROUP BY
        pd.price_id,
        date_trunc('month', pd.price_date)::date
),
-- Джойним и делаем выборку цен, которые нужны в нашей витрине
filtered AS (
    SELECT
        pm.month,
        p.price_id,
        p.loading_city_gcid,
        p.unloading_city_gcid,
        g.body_group,
        p.weight_category,
        p.volume_category,
        p.price_rub,
        p.distance,
        p.organization_id,
        p.price_type
    FROM
        core.prices p
        JOIN price_months pm ON pm.price_id = p.price_id
        JOIN price_groups g ON g.price_id = p.price_id
    WHERE
        p.is_fact
        AND NOT p.complex
        AND NOT p.outlier_mark
        AND p.price > 0
        AND p.distance > 0
        AND p.price_rub IS NOT NULL
),
-- Группируем по grain и считаем метрики для витрины
aggregated AS MATERIALIZED (
    SELECT
        month,
        loading_city_gcid,
        unloading_city_gcid,
        body_group,
        weight_category,
        count(DISTINCT price_id) AS trips_count,
        count(DISTINCT organization_id) FILTER (
            WHERE price_type IN (3, 9)
        ) AS carriers_count,

        round(percentile_cont(0.25) WITHIN GROUP (ORDER BY price_rub)::numeric, 2) AS p25_trip,
        round(percentile_cont(0.50) WITHIN GROUP (ORDER BY price_rub)::numeric, 2) AS median_trip,
        round(percentile_cont(0.75) WITHIN GROUP (ORDER BY price_rub)::numeric, 2) AS p75_trip,
        round(avg(price_rub)::numeric, 2) AS avg_trip,
        
        round(percentile_cont(0.25) WITHIN GROUP (
            ORDER BY price_rub::numeric / NULLIF(distance, 0)::numeric
        )::numeric, 2) AS p25_km,
        round(percentile_cont(0.50) WITHIN GROUP (
            ORDER BY price_rub::numeric / NULLIF(distance, 0)::numeric
        )::numeric, 2) AS median_km,
        round(percentile_cont(0.75) WITHIN GROUP (
            ORDER BY price_rub::numeric / NULLIF(distance, 0)::numeric
        )::numeric, 2) AS p75_km,

        CASE WHEN count(*) >= 2 THEN round(
            stddev_samp(price_rub)::numeric / NULLIF(avg(price_rub), 0)::numeric, 6
        ) END AS cv_rate,

        -- Может получиться несколько категорий объёма,
        -- поэтому сохраняем минимум и массив
        min(volume_category) AS volume_category,
        array_agg(
            DISTINCT volume_category::text
            ORDER BY volume_category::text
        ) AS volume_categories
    FROM
        filtered
    GROUP BY
        month,
        loading_city_gcid,
        unloading_city_gcid,
        body_group,
        weight_category
),
-- Вычисляем динамику месяц к месяцу и год к году
-- Для этого делаем самоджойн два раза
with_dynamics AS (
    SELECT
        a.*,
        CASE
            WHEN (
                prev.median_trip IS NOT NULL
                AND prev.median_trip != 0
            ) THEN round((a.median_trip - prev.median_trip) / prev.median_trip * 100, 2)
        END AS mom_pct,

        CASE
            WHEN (
                yoy.median_trip IS NOT NULL
                AND yoy.median_trip != 0
            ) THEN round((a.median_trip - yoy.median_trip) / yoy.median_trip * 100, 2)
        END AS yoy_pct
    FROM
        aggregated a

        LEFT JOIN aggregated prev 
            ON prev.month = (a.month - INTERVAL '1 month')::date
            AND prev.loading_city_gcid = a.loading_city_gcid
            AND prev.unloading_city_gcid = a.unloading_city_gcid
            AND prev.body_group = a.body_group
            AND prev.weight_category = a.weight_category

        LEFT JOIN aggregated yoy ON yoy.month = (a.month - INTERVAL '1 year')::date
            AND yoy.loading_city_gcid = a.loading_city_gcid
            AND yoy.unloading_city_gcid = a.unloading_city_gcid
            AND yoy.body_group = a.body_group
            AND yoy.weight_category = a.weight_category
),
-- Вычисляем reliability_level по ТЗ
with_reliability_level AS (
    SELECT
        w.*,
        CASE
            WHEN (
                w.trips_count >= 30
                AND w.carriers_count >= 5
                AND (:as_of - (w.month + INTERVAL '1 month - 1 day')::date) <= 30 
            ) THEN 'HIGH'
            WHEN w.trips_count >= 10 THEN 'MEDIUM'
            ELSE 'LOW_DATA'
        END AS reliability_level
    FROM
        with_dynamics w
)
INSERT INTO
    mart.mart_route_card (
        month,
        loading_city_gcid,
        unloading_city_gcid,
        loading_city_name,
        unloading_city_name,
        body_group,
        weight_category,
        volume_category,
        volume_categories,
        p25_trip,
        median_trip,
        p75_trip,
        avg_trip,
        p25_km,
        median_km,
        p75_km,
        trips_count,
        carriers_count,
        cv_rate,
        mom_pct,
        yoy_pct,
        reliability_level
    )
SELECT
    s.month,
    s.loading_city_gcid,
    s.unloading_city_gcid,
    lc.name AS loading_city_name,
    uc.name AS unloading_city_name,
    s.body_group,
    s.weight_category,
    s.volume_category,
    s.volume_categories,
    s.p25_trip,
    s.median_trip,
    s.p75_trip,
    s.avg_trip,
    s.p25_km,
    s.median_km,
    s.p75_km,
    s.trips_count,
    s.carriers_count,
    s.cv_rate,
    s.mom_pct,
    s.yoy_pct,
    s.reliability_level
FROM
    with_reliability_level s
    JOIN cities_dedup lc ON lc.gc_id = s.loading_city_gcid
    JOIN cities_dedup uc ON uc.gc_id = s.unloading_city_gcid;
