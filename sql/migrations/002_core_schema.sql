-- Core DWH: очищенные сделки и ML-вьюха.
-- Миграция идемпотентна: повторный запуск не ломает существующие объекты.

CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.prices (
    price_id             bigint PRIMARY KEY,
    loading_date         date NOT NULL,
    created_at           timestamp(0),
    updated_at           timestamp(0),

    loading_city_gcid    integer NOT NULL,
    unloading_city_gcid  integer NOT NULL,
    distance             double precision NOT NULL,
    total_weight         double precision NOT NULL,
    total_volume         double precision NOT NULL,
    body_type            integer,

    price                double precision NOT NULL,
    currency_code        varchar(3) NOT NULL,
    nearest_rate_date    date,
    price_rub            numeric(14, 2) NOT NULL,

    complex              boolean NOT NULL,
    price_type           smallint NOT NULL,
    is_fact              boolean NOT NULL,
    outlier_mark         boolean NOT NULL,

    weight_category      varchar(4) NOT NULL,
    volume_category      varchar(4) NOT NULL,

    organization_id      integer,
    subscriber_id        integer,
    end_loading_date     date,
    source               varchar(255),
    meta_item_id         bigint,

    etl_run_id           uuid NOT NULL,
    loaded_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS core_prices_loading_date_idx
    ON core.prices (loading_date);

CREATE INDEX IF NOT EXISTS core_prices_route_idx
    ON core.prices (loading_city_gcid, unloading_city_gcid);

CREATE INDEX IF NOT EXISTS core_prices_fact_outlier_idx
    ON core.prices (is_fact, outlier_mark);

CREATE INDEX IF NOT EXISTS core_prices_currency_idx
    ON core.prices (currency_code);

-- История для обучения ML.
-- as_of = 2026-10-26 — дата снимка задания.
-- Выбросы, не-факты и составные маршруты отфильтрованы здесь,
-- чтобы ML-код не повторял эти условия и не использовал outlier_mark как признак.
CREATE OR REPLACE VIEW core.ml_training_rows AS
SELECT
    price_id,
    loading_date,
    loading_city_gcid,
    unloading_city_gcid,
    distance,
    total_weight,
    total_volume,
    body_type,
    price_rub,
    weight_category,
    volume_category
FROM core.prices
WHERE is_fact
  AND NOT complex
  AND NOT outlier_mark
  AND loading_date <= DATE '2026-10-26';

COMMENT ON VIEW core.ml_training_rows IS
    'Исторические факты для обучения ML: is_fact, без complex и outlier_mark, loading_date <= as_of.';
