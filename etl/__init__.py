"""Общая библиотека ETL-пайплайна."""

from etl.db import create_db_engine, execute_sql_script
from etl.load import load_validation_results
from etl.models import DqReason, LoadResult, Window
from etl.schemas import CORE_SCHEMA_SQL, DQ_SCHEMA_SQL, init_core_schema, init_dq_schema
from etl.staging import extract_and_stage_window

__all__ = [
    "CORE_SCHEMA_SQL",
    "DQ_SCHEMA_SQL",
    "DqReason",
    "LoadResult",
    "Window",
    "create_db_engine",
    "execute_sql_script",
    "init_core_schema",
    "init_dq_schema",
    "load_validation_results",
    "extract_and_stage_window",
]
