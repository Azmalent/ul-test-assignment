"""Точка входа пайплайна ETL для CLI."""

import argparse
import logging
from datetime import date, datetime, time

from dotenv import load_dotenv
from sqlalchemy import Engine

from etl.db import create_db_engine
from etl.load import load_validation_results
from etl.mart import refresh_mart_route_card
from etl.models import LoadResult, Window
from etl.schemas import init_core_schema, init_dq_schema, init_mart_schema
from etl.staging import extract_and_stage_window

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="etl",
        description="Полный ETL-пайплайн: схемы, DQ-валидация, core и карантин.",
    )
    parser.add_argument(
        "--start-date",
        required=True,
        type=date.fromisoformat,
        help="Начало окна, включительно (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        type=date.fromisoformat,
        help="Конец окна, не включается (YYYY-MM-DD)",
    )
    return parser


def _run_pipeline(
    start_date: date | datetime | str,
    end_date: date | datetime | str,
    engine: Engine | None = None,
) -> LoadResult:
    """Выполняет полный ETL пайплайн за окно [start_date, end_date)."""
    window = Window(start_date=start_date, end_date=end_date)
    engine = engine or create_db_engine()

    logger.info("Старт ETL-пайплайна: окно [%s, %s)", window.start_date, window.end_date)
    started_at = time.perf_counter()

    init_dq_schema(engine)
    init_core_schema(engine)
    init_mart_schema(engine)
    staging_table = extract_and_stage_window(window.start_date, window.end_date, engine)
    result = load_validation_results(engine)
    mart_rows = refresh_mart_route_card(engine)

    logger.info(
        "ETL-пайплайн завершён: staging=%s, run_id=%s, valid=%s, quarantine=%s, mart_rows=%s, %.2f c",
        staging_table,
        result.run_id,
        result.valid_rows,
        result.quarantined_rows,
        mart_rows,
        time.perf_counter() - started_at,
    )

    return result


def main() -> None:
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = _build_parser().parse_args()
    logger.info("Запуск ETL-пайплайна из CLI: окно [%s, %s)", args.start_date, args.end_date)

    try:
        result = _run_pipeline(args.start_date, args.end_date)
    except Exception:
        logger.exception("ETL-пайплайн завершился с ошибкой")
        raise

    logger.info(
        "ETL-пайплайн завершён: run_id=%s, valid=%s, quarantine=%s, удалено из core=%s, удалено из карантина=%s",
        result.run_id,
        result.valid_rows,
        result.quarantined_rows,
        result.core_deleted,
        result.quarantine_deleted,
    )


if __name__ == "__main__":
    main()
