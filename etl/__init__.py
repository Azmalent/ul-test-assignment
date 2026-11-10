"""Общая библиотека ETL-пайплайна."""

from etl.db import create_db_engine, execute_sql_script
from etl.load import load_validation_results
from etl.mart import refresh_mart_route_card
from etl.models import LoadResult, Window
from etl.schemas import (
    CORE_SCHEMA_SQL,
    DQ_SCHEMA_SQL,
    MART_SCHEMA_SQL,
    init_core_schema,
    init_dq_schema,
    init_mart_schema,
)
from etl.staging import extract_and_stage_window

__all__ = [
    "CORE_SCHEMA_SQL",
    "DQ_SCHEMA_SQL",
    "MART_SCHEMA_SQL",
    "LoadResult",
    "Window",
    "create_db_engine",
    "execute_sql_script",
    "extract_and_stage_window",
    "init_core_schema",
    "init_dq_schema",
    "init_mart_schema",
    "load_validation_results",
    "refresh_mart_route_card",
]
