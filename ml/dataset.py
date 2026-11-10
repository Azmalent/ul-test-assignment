"""Подготовка X/y для ML-модели."""

from __future__ import annotations

import pandas as pd

TARGET = "target"
DATE_COLUMN = "loading_date"
ID_COLUMN = "price_id"

# Базовая модель: регионы + координаты, без названий городов
NUMERIC_FEATURES = (
    "distance",
    "total_weight",
    "total_volume",
    "origin_lat",
    "origin_lon",
    "destination_lat",
    "destination_lon",
    "loading_year",
    "loading_month",
    "loading_dow",
    "loading_doy",
    "month_sin",
    "month_cos",
    "dow_sin",
    "dow_cos",
    "doy_sin",
    "doy_cos",
)

CATEGORICAL_FEATURES = (
    "origin_region",
    "destination_region",
    "body_group",
    "weight_category",
    "volume_category",
)

FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

LEAKAGE_COLUMNS = {
    "target",
    "price",
    "price_rub",
    "price_with_vat",
    "price_group_id",
    "price_group_stats",
    "outlier_mark",
    "is_fact",
    "complex",
    "currency_code",
    "nearest_rate_date",
    "organization_id",
    "subscriber_id",
    "created_at",
    "updated_at",
    "price_type",
    "carrier_cost",
    "customer_cost",
    "profit",
}


def validate_feature_frame(data: pd.DataFrame) -> None:
    """Проверяет наличие нужных колонок и отсутствие утечек."""
    required = set(FEATURES) | {TARGET}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Нет обязательных колонок: {sorted(missing)}")

    leaked = set(FEATURES) & LEAKAGE_COLUMNS
    if leaked:
        raise ValueError(f"Leakage-колонки попали в признаки: {sorted(leaked)}")

    if data.columns.duplicated().any():
        duplicated = sorted(set(data.columns[data.columns.duplicated()]))
        raise ValueError(f"Дублирующиеся колонки: {duplicated}")


def prepare_xy(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Возвращает матрицу признаков X и target y."""
    validate_feature_frame(data)

    features = data[list(FEATURES)].copy()
    target = data[TARGET].copy()

    for column in CATEGORICAL_FEATURES:
        features[column] = features[column].fillna("unknown").replace("", "unknown").astype(str)

    return features, target
