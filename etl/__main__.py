"""Точка входа пайплайна ETL для CLI."""

import argparse
import logging
import time
from uuid import uuid4

import pendulum
from dotenv import load_dotenv
from sqlalchemy.engine import Engine

from etl.config import get_as_of_date
from etl.db import create_db_engine
from etl.load import load_validation_results
from etl.mart import refresh_mart_route_card
from etl.models import LoadResult, Window
from etl.schemas import init_core_schema, init_dq_schema, init_mart_schema
from etl.staging import STAGING_TABLE, extract_and_stage_window

logger = logging.getLogger(__name__)


def _parse_date(value: str) -> pendulum.Date:
    """Парсит дату CLI в pendulum.Date."""
    return pendulum.parse(value).date()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="etl",
        description="Полный ETL-пайплайн: схемы, DQ-валидация, core и карантин.",
    )
    parser.add_argument(
        "--start-date",
        required=True,
        type=_parse_date,
        help="Начало окна, включительно (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        type=_parse_date,
        help="Конец окна, не включается (YYYY-MM-DD)",
    )
    return parser


def _run_pipeline(
    start_date: pendulum.Date | pendulum.DateTime | str,
    end_date: pendulum.Date | pendulum.DateTime | str,
    engine: Engine | None = None,
) -> LoadResult:
    """Выполняет полный ETL пайплайн за окно [start_date, end_date)."""
    window = Window(start_date=start_date, end_date=end_date)
    engine = engine or create_db_engine()
    as_of = get_as_of_date()
    run_id = uuid4()

    logger.info(
        "Старт ETL-пайплайна: окно [%s, %s), as_of=%s, run_id=%s",
        window.start_date,
        window.end_date,
        as_of,
        run_id,
    )
    started_at = time.perf_counter()

    init_dq_schema(engine)
    init_core_schema(engine)
    init_mart_schema(engine)
    extract_and_stage_window(window.start_date, window.end_date, engine)
    result = load_validation_results(engine, run_id=run_id)
    mart_rows = refresh_mart_route_card(engine, as_of=as_of)

    logger.info(
        "ETL-пайплайн завершён: staging=%s, run_id=%s, valid=%s, "
        "quarantine=%s, mart_rows=%s, %.2f c",
        STAGING_TABLE,
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
        "ETL-пайплайн завершён: run_id=%s, valid=%s, quarantine=%s, "
        "удалено из core=%s, удалено из карантина=%s",
        result.run_id,
        result.valid_rows,
        result.quarantined_rows,
        result.core_deleted,
        result.quarantine_deleted,
    )


if __name__ == "__main__":
    main()
