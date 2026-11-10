-- Инициализация основной схемы DWH.
CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.prices (
    price_id bigint PRIMARY KEY,
    loading_date date NOT NULL,
    created_at timestamp(0),
    updated_at timestamp(0),
    loading_city_gcid integer NOT NULL,
    unloading_city_gcid integer NOT NULL,
    distance double precision NOT NULL,
    total_weight double precision NOT NULL,
    total_volume double precision NOT NULL,
    body_type integer,
    price double precision NOT NULL,
    currency_code varchar(3) NOT NULL,
    nearest_rate_date date,
    price_rub numeric(14, 2) NOT NULL,
    complex boolean NOT NULL,
    price_type smallint NOT NULL,
    is_fact boolean NOT NULL,
    outlier_mark boolean NOT NULL,
    weight_category varchar(4) NOT NULL,
    volume_category varchar(4) NOT NULL,
    organization_id integer,
    subscriber_id integer,
    end_loading_date date,
    source varchar(255),
    meta_item_id bigint,
    etl_run_id text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS core_prices_loading_date_idx ON core.prices (loading_date);

CREATE INDEX IF NOT EXISTS core_prices_route_idx ON core.prices (loading_city_gcid, unloading_city_gcid);

CREATE INDEX IF NOT EXISTS core_prices_fact_outlier_idx ON core.prices (is_fact, outlier_mark);

CREATE INDEX IF NOT EXISTS core_prices_currency_idx ON core.prices (currency_code);
