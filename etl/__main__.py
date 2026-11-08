"""Точка входа пайплайна ETL для CLI."""

from __future__ import annotations

import argparse
import logging
from datetime import date

from dotenv import load_dotenv

from etl.core import init_core_schema
from etl.db import create_db_engine
from etl.dq import init_dq_schema
from etl.load import load_validation_results
from etl.staging import extract_and_stage_window

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="etl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "init-dq",
        help="Создать схему dq, справочник причин и таблицу карантина",
    )
    subparsers.add_parser(
        "init-core",
        help="Создать core.prices и ML-вьюху",
    )
    subparsers.add_parser(
        "load-validation",
        help="Загрузить staging в core.prices и карантин",
    )
    stage_parser = subparsers.add_parser(
        "stage-validation",
        help="Сохранить результат DQ-валидации в stg.price_validation",
    )
    stage_parser.add_argument(
        "--start-date",
        required=True,
        type=date.fromisoformat,
        help="Начало окна, включительно (YYYY-MM-DD)",
    )
    stage_parser.add_argument(
        "--end-date",
        required=True,
        type=date.fromisoformat,
        help="Конец окна, включительно (YYYY-MM-DD)",
    )
    return parser


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = _build_parser().parse_args()

    if args.command == "init-dq":
        init_dq_schema(create_db_engine())
        logger.info("Схема dq инициализирована")
    elif args.command == "init-core":
        init_core_schema(create_db_engine())
        logger.info("Схема core инициализирована")
    elif args.command == "stage-validation":
        table = extract_and_stage_window(args.start_date, args.end_date)
        logger.info("Результат валидации сохранён в %s", table)
    elif args.command == "load-validation":
        result = load_validation_results(create_db_engine())
        logger.info(
            "Загрузка завершена: run_id=%s, valid=%s, quarantine=%s, удалено из core=%s, удалено из карантина=%s",
            result.run_id,
            result.valid_rows,
            result.quarantined_rows,
            result.core_deleted,
            result.quarantine_deleted,
        )


if __name__ == "__main__":
    main()
