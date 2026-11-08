-- Схема карантина DQ: справочник причин отсева и таблица отбракованных сделок.
-- Миграция идемпотентна: повторный запуск не ломает существующие объекты,
-- а описания причин обновляет через ON CONFLICT.

CREATE SCHEMA IF NOT EXISTS dq;

-- Справочник причин отсева
CREATE TABLE IF NOT EXISTS dq.dq_quarantine_reasons (
    id          smallint PRIMARY KEY,
    description text     NOT NULL
);

INSERT INTO dq.dq_quarantine_reasons (id, description) VALUES
    (1, 'Некорректная цена'),
    (2, 'Слишком низкая цена'),
    (3, 'Некорректная дистанция'),
    (4, 'Некорректный вес'),
    (5, 'Некорректный объём'),
    (6, 'Неизвестный город'),
    (7, 'Нет курса валюты')
ON CONFLICT (id) DO UPDATE
SET description = EXCLUDED.description;

-- Отбракованные сделки.
-- Одна сделка может попасть в карантин по нескольким причинам,
-- поэтому первичный ключ составной: (price_id, reason_id).
CREATE TABLE IF NOT EXISTS dq.dq_quarantine_prices (
    price_id      bigint      NOT NULL,
    reason_id     smallint    NOT NULL
                  REFERENCES dq.dq_quarantine_reasons (id),
    detected_at   timestamptz NOT NULL DEFAULT now(),
    etl_run_id    uuid,
    loading_date  date,
    currency_code varchar(3),
    price         double precision,
    distance      double precision,
    raw_row       jsonb       NOT NULL,

    PRIMARY KEY (price_id, reason_id)
);

CREATE INDEX IF NOT EXISTS dq_quarantine_prices_reason_idx
    ON dq.dq_quarantine_prices (reason_id);

CREATE INDEX IF NOT EXISTS dq_quarantine_prices_detected_at_idx
    ON dq.dq_quarantine_prices (detected_at);
