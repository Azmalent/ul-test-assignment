-- Схема для ML: признаки, модели и прогнозы.
CREATE SCHEMA IF NOT EXISTS ml;

-- Материализованные признаки для обучения и скоринга.
CREATE TABLE IF NOT EXISTS ml.price_features (
    price_id bigint PRIMARY KEY,
    loading_date date NOT NULL,

    loading_city_gcid integer NOT NULL,
    unloading_city_gcid integer NOT NULL,

    origin_city text NOT NULL,
    origin_region text,
    origin_lat double precision,
    origin_lon double precision,

    destination_city text NOT NULL,
    destination_region text,
    destination_lat double precision,
    destination_lon double precision,

    distance double precision NOT NULL,
    total_weight double precision NOT NULL,
    total_volume double precision NOT NULL,

    body_type integer,
    body_group varchar(32) NOT NULL,
    weight_category varchar(4) NOT NULL,
    volume_category varchar(4) NOT NULL,

    loading_year integer NOT NULL,
    loading_month integer NOT NULL,
    loading_dow integer NOT NULL,
    loading_doy integer NOT NULL,

    month_sin double precision NOT NULL,
    month_cos double precision NOT NULL,
    dow_sin double precision NOT NULL,
    dow_cos double precision NOT NULL,
    doy_sin double precision NOT NULL,
    doy_cos double precision NOT NULL,

    target numeric(14, 2) NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ml_price_features_loading_date_idx
    ON ml.price_features (loading_date);

CREATE INDEX IF NOT EXISTS ml_price_features_route_idx
    ON ml.price_features (loading_city_gcid, unloading_city_gcid);

CREATE INDEX IF NOT EXISTS ml_price_features_body_idx
    ON ml.price_features (body_group, weight_category);
