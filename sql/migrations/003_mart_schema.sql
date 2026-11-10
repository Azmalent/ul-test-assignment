-- Mart Layer: карточка маршрута и рыночный коридор ставок.
-- Гранулярность: month × loading_city × unloading_city × body_group × weight_category.
-- volume_category — атрибут, в grain не входит.

CREATE SCHEMA IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS mart.mart_route_card (
    month                 date NOT NULL,
    loading_city_gcid     integer NOT NULL,
    unloading_city_gcid   integer NOT NULL,
    loading_city_name     text NOT NULL,
    unloading_city_name   text NOT NULL,
    body_group            varchar(32) NOT NULL,
    weight_category       varchar(4) NOT NULL,

    volume_category       varchar(4),
    volume_categories     text[],

    p25_trip              numeric(14, 2),
    median_trip           numeric(14, 2),
    p75_trip              numeric(14, 2),
    avg_trip              numeric(14, 2),

    p25_km                numeric(14, 2),
    median_km             numeric(14, 2),
    p75_km                numeric(14, 2),

    trips_count           integer NOT NULL,
    carriers_count        integer NOT NULL,
    cv_rate               numeric(14, 6),

    mom_pct               numeric(10, 2),
    yoy_pct               numeric(10, 2),

    reliability_level     varchar(16) NOT NULL,
    updated_at            timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT mart_route_card_pkey PRIMARY KEY (
        month,
        loading_city_gcid,
        unloading_city_gcid,
        body_group,
        weight_category
    )
);

CREATE INDEX IF NOT EXISTS mart_route_card_route_idx
    ON mart.mart_route_card (loading_city_gcid, unloading_city_gcid, month);

CREATE INDEX IF NOT EXISTS mart_route_card_month_idx
    ON mart.mart_route_card (month);

CREATE INDEX IF NOT EXISTS mart_route_card_reliability_idx
    ON mart.mart_route_card (reliability_level);
