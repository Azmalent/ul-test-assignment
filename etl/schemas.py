"""Инициализация схем БД."""

import logging
from pathlib import Path

from sqlalchemy.engine import Engine

from etl.db import create_db_engine, execute_sql_script

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DQ_SCHEMA_SQL = PROJECT_ROOT.joinpath("sql/migrations/001_dq_schema.sql")
CORE_SCHEMA_SQL = PROJECT_ROOT.joinpath("sql/migrations/002_core_schema.sql")
MART_SCHEMA_SQL = PROJECT_ROOT.joinpath("sql/migrations/003_mart_schema.sql")
ML_SCHEMA_SQL = PROJECT_ROOT.joinpath("sql/migrations/004_ml_schema.sql")

logger = logging.getLogger(__name__)


def init_dq_schema(engine: Engine | None = None) -> None:
    """Создаёт схему DQ."""
    logger.info("Инициализация схемы DQ...")
    execute_sql_script(engine or create_db_engine(), DQ_SCHEMA_SQL)
    logger.info("Схема DQ инициализирована")


def init_core_schema(engine: Engine | None = None) -> None:
    """Создаёт схему core."""
    logger.info("Инициализация схемы core...")
    execute_sql_script(engine or create_db_engine(), CORE_SCHEMA_SQL)
    logger.info("Схема core инициализирована")


def init_mart_schema(engine: Engine | None = None) -> None:
    """Создаёт схему mart и витрину mart_route_card."""
    logger.info("Инициализация схемы mart...")
    execute_sql_script(engine or create_db_engine(), MART_SCHEMA_SQL)
    logger.info("Схема mart инициализирована")


def init_ml_schema(engine: Engine | None = None) -> None:
    """Создаёт схему ml и таблицу признаков."""
    engine = engine or create_db_engine()
    logger.info("Инициализация схемы ml...")
    execute_sql_script(engine, ML_SCHEMA_SQL)
    logger.info("Схема ml инициализирована")
