-- Результат DQ-валидации сделок за окно [start_date, end_date] (обе границы включительно).
-- Это SELECT-запрос: etl.staging оборачивает его в CREATE UNLOGGED TABLE.
WITH rate AS (
    SELECT
        DISTINCT ON (num_code, setting_date) num_code,
        setting_date,
        value :: numeric AS value
    FROM
        exchange_rates
    ORDER BY
        num_code,
        setting_date,
        id DESC
),
normalized AS (
    SELECT
        p.*,
        CASE
            WHEN p.currency_code = '643' THEN 1.0 :: numeric
            ELSE r.value
        END AS exchange_rate,
        (
            p.currency_code = '643'
            OR r.value IS NOT NULL
        ) AS rate_found
    FROM
        prices p
        LEFT JOIN rate r ON r.num_code = p.currency_code
        AND r.setting_date = p.nearest_rate_date
    WHERE
        p.loading_date BETWEEN :start_date
        AND :end_date
),
validated AS (
    SELECT
        n.*,
        round(n.price :: numeric * n.exchange_rate, 2) AS price_rub,
        -- Порядок проверок совпадает с порядком причин в задании.
        (n.price <= 0) AS dq_invalid_price,
        (
            n.currency_code = '643'
            AND n.price > 0
            AND n.price <= 1000
        ) AS dq_low_price,
        (n.distance <= 0) AS dq_invalid_distance,
        (n.total_weight < 0) AS dq_invalid_weight,
        (n.total_volume < 0) AS dq_invalid_volume,
        (
            NOT EXISTS (
                SELECT
                    1
                FROM
                    cities c
                WHERE
                    c.gc_id = n.loading_city_gcid
            )
            OR NOT EXISTS (
                SELECT
                    1
                FROM
                    cities c
                WHERE
                    c.gc_id = n.unloading_city_gcid
            )
        ) AS dq_unknown_city,
        (NOT n.rate_found) AS dq_missing_exchange_rate
    FROM
        normalized n
)
SELECT
    v.*,
    ARRAY_REMOVE(
        ARRAY [
        CASE WHEN v.dq_invalid_price THEN 1 END,
        CASE WHEN v.dq_low_price THEN 2 END,
        CASE WHEN v.dq_invalid_distance THEN 3 END,
        CASE WHEN v.dq_invalid_weight THEN 4 END,
        CASE WHEN v.dq_invalid_volume THEN 5 END,
        CASE WHEN v.dq_unknown_city THEN 6 END,
        CASE WHEN v.dq_missing_exchange_rate THEN 7 END
    ],
        NULL
    ) AS dq_reason_ids
FROM
    validated v;
