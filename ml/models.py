"""Pydantic-модели результатов обучения."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class Metrics(BaseModel):
    """Метрики качества регрессии."""

    model_config = ConfigDict(frozen=True)

    r2: float
    mape_pct: float
    rmse_rub: float
    mae_rub: float


class TrainResult(BaseModel):
    """Результат обучения и сохранения модели."""

    model_config = ConfigDict(frozen=True)

    model_name: str
    model_path: str
    metadata_path: str
    metrics: Metrics
    baseline_metrics: Metrics
    train_rows: int
    test_rows: int
    train_start: date
    test_start: date
    test_end: date
    features: list[str]
    categorical_features: list[str]
    random_seed: int


class MLRunResult(BaseModel):
    """Результат полного ML-пайплайна."""

    model_config = ConfigDict(frozen=True)

    as_of: date
    train: TrainResult
    prediction_rows: int
