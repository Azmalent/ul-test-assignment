"""Метрики качества регрессии."""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

from ml.models import Metrics


def compute_metrics(y_true: pd.Series, y_pred: np.ndarray) -> Metrics:
    """Считает R², MAPE, RMSE и MAE."""
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)

    mask = actual != 0
    if mask.any():
        mape = float(
            np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100
        )
    else:
        mape = float("nan")

    return Metrics(
        r2=float(r2_score(actual, predicted)),
        mape_pct=mape,
        rmse_rub=float(root_mean_squared_error(actual, predicted)),
        mae_rub=float(mean_absolute_error(actual, predicted)),
    )
