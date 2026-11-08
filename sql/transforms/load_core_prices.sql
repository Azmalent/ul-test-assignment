-- Загрузка валидных сделок из staging в core.prices.
-- Delete старого состояния выполняется в etl.load перед этим запросом.

INSERT INTO core.prices (
    price_id,
    loading_date,
    created_at,
    updated_at,
    loading_city_gcid,
    unloading_city_gcid,
    distance,
    total_weight,
    total_volume,
    body_type,
    price,
    currency_code,
    nearest_rate_date,
    price_rub,
    complex,
    price_type,
    is_fact,
    outlier_mark,
    weight_category,
    volume_category,
    organization_id,
    subscriber_id,
    end_loading_date,
    source,
    meta_item_id,
    etl_run_id
)
SELECT
    s.id,
    s.loading_date,
    s.created_at,
    s.updated_at,
    s.loading_city_gcid,
    s.unloading_city_gcid,
    s.distance,
    s.total_weight,
    s.total_volume,
    s.body_type,
    s.price,
    s.currency_code,
    s.nearest_rate_date,
    s.price_rub,
    s.complex,
    s.price_type,
    s.is_fact,
    s.outlier_mark,

    COALESCE(s.weight_category, CASE
        WHEN round(s.total_weight::numeric, 1) >= 30  THEN 'G20T'
        WHEN round(s.total_weight::numeric, 1) >= 10  THEN 'FTL'
        WHEN round(s.total_weight::numeric, 1) >= 5   THEN '10T'
        WHEN round(s.total_weight::numeric, 1) >= 2.5 THEN '5T'
        WHEN round(s.total_weight::numeric, 1) >= 0.5 THEN 'L5T'
        ELSE 'OTH'
    END),

    COALESCE(s.volume_category, CASE
        WHEN s.total_volume > 0 AND s.total_volume <= 120 THEN 'FTL'
        ELSE 'OTH'
    END),

    s.organization_id,
    s.subscriber_id,
    s.end_loading_date,
    s.source,
    s.meta_item_id,
    :etl_run_id
FROM stg.price_validation s
WHERE cardinality(s.dq_reason_ids) = 0;
