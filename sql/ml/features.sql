-- Дедупликация городов по gc_id
WITH cities_dedup AS MATERIALIZED (
    SELECT
        DISTINCT ON (gc_id) gc_id,
        id,
        name,
        split_part(full_name_local, ', ', 2) as region_name,
        latitude,
        longitude
    FROM
        cities
    ORDER BY
        gc_id,
        id
),
-- Выборка подходящих сделок
filtered_prices AS (
    SELECT
        *
    FROM
        core.prices
    WHERE
        (:require_fact = false OR is_fact)
        AND NOT complex
        AND NOT outlier_mark
        AND price_rub > 0
        AND distance > 0
        AND loading_date >= :start_date
        AND loading_date < :end_date
),
-- Маппинг кодов кузова в бизнес-группы + приоритет для выбора одной группы
body_map AS (
    SELECT
        bt.id AS body_type_id,
        CASE
            WHEN bt.id IN (56, 57, 58, 59, 60, 61) THEN 'Тент'
            WHEN bt.id IN (4, 46, 47, 48) THEN 'Рефрижератор'
            WHEN bt.id = 2 THEN 'Изотерм'
            WHEN bt.id IN (1, 15) THEN 'Борт'
            ELSE 'Прочие'
        END AS body_group,
        CASE
            WHEN bt.id IN (56, 57, 58, 59, 60, 61) THEN 1
            WHEN bt.id IN (4, 46, 47, 48) THEN 2
            WHEN bt.id = 2 THEN 3
            WHEN bt.id IN (1, 15) THEN 4
            ELSE 5
        END AS body_group_priority
    FROM
        body_types bt
),
-- Одна группа кузова на сделку, выбираем по приоритету
price_body_primary AS (
    SELECT
        DISTINCT ON (pbt.price_id) pbt.price_id,
        bm.body_group
    FROM
        price_body_types pbt
        JOIN body_map bm ON bm.body_type_id = pbt.body_type_id
    ORDER BY
        pbt.price_id,
        bm.body_group_priority,
        pbt.body_type_id
),
-- Фоллбек на prices.body_type
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
        filtered_prices p
    WHERE NOT EXISTS (
        SELECT 1 FROM price_body_primary b WHERE b.price_id = p.price_id
    )
),
price_body AS (
    SELECT price_id, body_group
    FROM price_body_primary
    
    UNION ALL -- заведомо не пересекаются - UNION ALL будет быстрее
    
    SELECT price_id, body_group FROM price_body_fallback
)
SELECT
    p.price_id,
    p.loading_date,
    p.loading_city_gcid,
    p.unloading_city_gcid,
    origin.name AS origin_city,
    origin.region_name AS origin_region,
    origin.latitude AS origin_lat,
    origin.longitude AS origin_lon,
    dest.name AS destination_city,
    dest.region_name AS destination_region,
    dest.latitude AS destination_lat,
    dest.longitude AS destination_lon,
    p.distance,
    p.total_weight,
    p.total_volume,
    p.body_type,
    b.body_group,
    p.weight_category,
    p.volume_category,
    
    EXTRACT(YEAR FROM p.loading_date)::int AS loading_year,
    EXTRACT(MONTH FROM p.loading_date)::int AS loading_month,
    EXTRACT(ISODOW FROM p.loading_date)::int AS loading_dow,
    EXTRACT(DOY FROM p.loading_date)::int AS loading_doy,
    
    -- Циклические признаки - мапим месяц, день недели и день года на окружность
    sin(2 * pi() * EXTRACT(MONTH FROM p.loading_date) / 12) AS month_sin,
    cos(2 * pi() * EXTRACT(MONTH FROM p.loading_date) / 12) AS month_cos,
    sin(2 * pi() * EXTRACT(ISODOW FROM p.loading_date) / 7) AS dow_sin,
    cos(2 * pi() * EXTRACT(ISODOW FROM p.loading_date) / 7) AS dow_cos,
    sin(2 * pi() * EXTRACT(DOY FROM p.loading_date) / 365.25) AS doy_sin,
    cos(2 * pi() * EXTRACT(DOY FROM p.loading_date) / 365.25) AS doy_cos,

    p.price_rub AS target
FROM
    filtered_prices p
    JOIN cities_dedup origin ON origin.gc_id = p.loading_city_gcid
    JOIN cities_dedup dest ON dest.gc_id = p.unloading_city_gcid
    JOIN price_body b ON b.price_id = p.price_id;
