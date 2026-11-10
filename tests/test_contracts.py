"""Контрактные тесты без БД и обучения."""

import pandas as pd
import pendulum
import pytest

from etl.models import Window
from ml.dataset import (
    CATEGORICAL_FEATURES,
    FEATURES,
    LEAKAGE_COLUMNS,
    NUMERIC_FEATURES,
    prepare_xy,
)
from ml.split import split_train_test


def test_window_requires_start_before_end():
    window = Window(start_date="2026-10-01", end_date="2026-11-01")

    assert window.start_date == pendulum.Date(2026, 10, 1)
    assert window.end_date == pendulum.Date(2026, 11, 1)

    with pytest.raises(ValueError, match="start_date"):
        Window(start_date="2026-10-01", end_date="2026-10-01")


def test_time_split_boundaries():
    data = pd.DataFrame(
        {
            "loading_date": pd.to_datetime(
                [
                    "2026-07-25",
                    "2026-07-26",
                    "2026-10-04",
                    "2026-10-05",
                    "2026-10-26",
                    "2026-10-27",
                ]
            )
        }
    )

    split = split_train_test(data, as_of="2026-10-26")

    assert len(split.train) == 2
    assert len(split.test) == 2
    assert split.train["loading_date"].min() == pd.Timestamp("2026-07-26")
    assert split.train["loading_date"].max() == pd.Timestamp("2026-10-04")
    assert split.test["loading_date"].min() == pd.Timestamp("2026-10-05")
    assert split.test["loading_date"].max() == pd.Timestamp("2026-10-26")


def test_prepare_xy_excludes_target_and_ids():
    row = dict.fromkeys(NUMERIC_FEATURES, 1.0)
    row.update(dict.fromkeys(CATEGORICAL_FEATURES, "test"))
    row["target"] = 100.0
    row["price_id"] = 1
    row["loading_date"] = pd.Timestamp("2026-10-01")

    features, target = prepare_xy(pd.DataFrame([row]))

    assert list(features.columns) == list(FEATURES)
    assert "target" not in features.columns
    assert "price_id" not in features.columns
    assert target.iloc[0] == 100.0
    assert not set(FEATURES) & LEAKAGE_COLUMNS
