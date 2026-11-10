"""Интеграционные тесты идемпотентности."""

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.load import load_validation_results
from etl.schemas import init_mart_schema, init_ml_schema
from etl.staging import extract_and_stage_window
from ml.features import refresh_price_features
from ml.predict import run_batch_inference
from ml.split import load_price_features, split_train_test

pytestmark = pytest.mark.integration

FEATURES_START = "2026-07-26"
FEATURES_END = "2026-10-27"
AS_OF = "2026-10-26"
MODEL_NAME = "catboost_v1"


def _core_totals(engine: Engine):
    with engine.connect() as conn:
        core = conn.execute(
            text(
                """
                SELECT count(*) AS rows, coalesce(sum(price_rub), 0) AS total
                FROM core.prices
                """
            )
        ).one()
        quarantine = conn.execute(
            text("SELECT count(*) AS rows FROM dq.dq_quarantine_prices")
        ).one()
    return core.rows, core.total, quarantine.rows


def test_etl_idempotent(test_engine: Engine, prepared_core):
    before = _core_totals(test_engine)

    extract_and_stage_window("2023-01-01", "2027-12-31", test_engine)
    load_validation_results(test_engine, run_id="test-etl-idempotent")

    after = _core_totals(test_engine)

    assert before == after


def test_features_idempotent(test_engine: Engine, prepared_core):
    init_ml_schema(test_engine)

    refresh_price_features(FEATURES_START, FEATURES_END, test_engine, require_fact=True)
    with test_engine.connect() as conn:
        first = conn.execute(
            text(
                """
                SELECT count(*) AS rows, coalesce(sum(target), 0) AS total
                FROM ml.price_features
                """
            )
        ).one()

    refresh_price_features(FEATURES_START, FEATURES_END, test_engine, require_fact=True)
    with test_engine.connect() as conn:
        second = conn.execute(
            text(
                """
                SELECT count(*) AS rows, coalesce(sum(target), 0) AS total
                FROM ml.price_features
                """
            )
        ).one()

    assert (first.rows, first.total) == (second.rows, second.total)


def test_predictions_idempotent(test_engine: Engine, prepared_core, model_path):
    init_ml_schema(test_engine)
    init_mart_schema(test_engine)

    with test_engine.connect() as conn:
        feature_rows = conn.execute(text("SELECT count(*) FROM ml.price_features")).scalar()

    if not feature_rows:
        refresh_price_features(FEATURES_START, FEATURES_END, test_engine, require_fact=True)

    data = load_price_features(test_engine)
    split = split_train_test(data, as_of=AS_OF)

    def snapshot():
        with test_engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                        count(*) AS rows,
                        count(*) FILTER (WHERE actual_price_rub IS NULL) AS future_rows,
                        coalesce(sum(predicted_price_rub), 0) AS total,
                        count(*) FILTER (
                            WHERE loading_date > DATE '2026-10-26'
                                AND actual_price_rub IS NOT NULL
                        ) AS future_with_actual
                    FROM mart.ml_price_predictions
                    WHERE model_name = :model_name
                    """
                ),
                {"model_name": MODEL_NAME},
            ).one()
            duplicates = conn.execute(
                text(
                    """
                    SELECT count(*)
                    FROM (
                        SELECT price_id, model_name
                        FROM mart.ml_price_predictions
                        GROUP BY 1, 2
                        HAVING count(*) > 1
                    ) t
                    """
                )
            ).scalar()
        return row, duplicates

    run_batch_inference(
        split,
        as_of=AS_OF,
        engine=test_engine,
        model_path=model_path,
    )
    first, first_duplicates = snapshot()

    run_batch_inference(
        split,
        as_of=AS_OF,
        engine=test_engine,
        model_path=model_path,
    )
    second, second_duplicates = snapshot()

    assert (first.rows, first.future_rows, first.total) == (
        second.rows,
        second.future_rows,
        second.total,
    )
    assert first_duplicates == 0
    assert second_duplicates == 0
    assert first.future_rows > 0
    assert first.future_with_actual == 0
