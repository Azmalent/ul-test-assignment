"""CLI ML-пайплайна."""

import argparse
import logging

import pendulum
from dotenv import load_dotenv

from ml.pipeline import run_ml_pipeline

logger = logging.getLogger(__name__)


def _parse_date(value: str) -> pendulum.Date:
    """Парсит дату CLI в pendulum.Date."""
    return pendulum.parse(value).date()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ml",
        description="ML-пайплайн: признаки -> обучение CatBoost -> batch inference.",
    )
    parser.add_argument(
        "--as-of",
        type=_parse_date,
        default=None,
        help="Дата снимка (YYYY-MM-DD). По умолчанию AS_OF_DATE или 2026-10-26.",
    )
    return parser


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = _build_parser().parse_args()
    logger.info("Запуск ML-пайплайна, as_of=%s", args.as_of or "из AS_OF_DATE")

    try:
        result = run_ml_pipeline(as_of=args.as_of)
    except Exception:
        logger.exception("ML-пайплайн завершился с ошибкой")
        raise

    logger.info(
        "ML-пайплайн завершён: as_of=%s, R2=%.4f, MAPE=%.2f%%, "
        "RMSE=%.2f, MAE=%.2f, predictions=%s",
        result.as_of,
        result.train.metrics.r2,
        result.train.metrics.mape_pct,
        result.train.metrics.rmse_rub,
        result.train.metrics.mae_rub,
        result.prediction_rows,
    )


if __name__ == "__main__":
    main()
