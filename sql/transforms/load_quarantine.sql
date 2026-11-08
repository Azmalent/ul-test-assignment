-- Загрузка отбракованных сделок из staging в карантин.
-- Одна сделка может иметь несколько причин, поэтому массив разворачивается.
-- Delete старого состояния выполняется в etl.load перед этим запросом.
-- raw_row — только для отладки и аудита; price_group_id из него нельзя
-- использовать как признак ML.

INSERT INTO dq.dq_quarantine_prices (
    price_id,
    reason_id,
    etl_run_id,
    loading_date,
    currency_code,
    price,
    distance,
    raw_row
)
SELECT
    s.id,
    r.reason_id::smallint,
    :etl_run_id,
    s.loading_date,
    s.currency_code,
    s.price,
    s.distance,
    to_jsonb(s)
FROM stg.price_validation s
CROSS JOIN LATERAL unnest(s.dq_reason_ids) AS r(reason_id)
WHERE cardinality(s.dq_reason_ids) > 0;
