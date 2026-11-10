"""Baseline, CatBoost и сохранение модели."""

import json
import logging
from pathlib import Path

from catboost import CatBoostRegressor
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.dataset import CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES, prepare_xy
from ml.metrics import compute_metrics
from ml.models import Metrics, TrainResult
from ml.split import TimeSplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = PROJECT_ROOT.joinpath("ml", "artifacts")

MODEL_NAME = "catboost_v1"
RANDOM_SEED = 42

logger = logging.getLogger(__name__)


def build_baseline() -> Pipeline:
    """Ridge с one-hot для категорий и масштабированием числовых."""
    numeric_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("num", numeric_pipeline, list(NUMERIC_FEATURES)),
            ("cat", categorical_pipeline, list(CATEGORICAL_FEATURES)),
        ]
    )
    return Pipeline(
        [
            ("preprocessor", preprocessor),
            ("model", Ridge()),
        ]
    )


def build_catboost() -> CatBoostRegressor:
    """CatBoost с дефолтными настройками и фиксированным seed."""
    return CatBoostRegressor(
        loss_function="RMSE",
        random_seed=RANDOM_SEED,
        verbose=False,
        allow_writing_files=False,
    )


def train_and_evaluate(split: TimeSplit) -> TrainResult:
    """Обучает baseline и CatBoost, считает метрики и сохраняет артефакт."""
    x_train, y_train = prepare_xy(split.train)
    x_test, y_test = prepare_xy(split.test)

    baseline = build_baseline()
    baseline.fit(x_train, y_train)
    baseline_metrics: Metrics = compute_metrics(y_test, baseline.predict(x_test))

    catboost_model = build_catboost()
    catboost_model.fit(
        x_train,
        y_train,
        cat_features=list(CATEGORICAL_FEATURES),
    )
    catboost_metrics: Metrics = compute_metrics(
        y_test,
        catboost_model.predict(x_test),
    )

    logger.info("Baseline Ridge: %s", baseline_metrics.model_dump())
    logger.info("CatBoost: %s", catboost_metrics.model_dump())

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = ARTIFACTS_DIR.joinpath(f"{MODEL_NAME}.cbm")
    metadata_path = ARTIFACTS_DIR.joinpath(f"{MODEL_NAME}_metadata.json")

    catboost_model.save_model(str(model_path))

    metadata = {
        "model_name": MODEL_NAME,
        "metrics": catboost_metrics.model_dump(),
        "baseline_metrics": baseline_metrics.model_dump(),
        "train_rows": len(split.train),
        "test_rows": len(split.test),
        "train_start": str(split.train_start),
        "test_start": str(split.test_start),
        "test_end": str(split.test_end),
        "features": list(FEATURES),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "random_seed": RANDOM_SEED,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Модель сохранена: %s", model_path)
    logger.info("Метаданные сохранены: %s", metadata_path)

    return TrainResult(
        model_name=MODEL_NAME,
        model_path=str(model_path),
        metadata_path=str(metadata_path),
        metrics=catboost_metrics,
        baseline_metrics=baseline_metrics,
        train_rows=len(split.train),
        test_rows=len(split.test),
        train_start=split.train_start,
        test_start=split.test_start,
        test_end=split.test_end,
        features=list(FEATURES),
        categorical_features=list(CATEGORICAL_FEATURES),
        random_seed=RANDOM_SEED,
    )
