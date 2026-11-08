"""Подключение к БД и выполнение SQL-файлов через SQLAlchemy."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_database_url() -> str:
    """Возвращает DSN из окружения.

    Приоритет:
    1. DATABASE_URL — для CLI и локальных запусков;
    2. AIRFLOW_CONN_DEALS_BIGDATA — уже задан в docker-compose для Airflow.
    """
    url = os.getenv("DATABASE_URL") or os.getenv("AIRFLOW_CONN_DEALS_BIGDATA")
    if not url:
        raise RuntimeError(
            "Не задан DATABASE_URL (или AIRFLOW_CONN_DEALS_BIGDATA). "
            "Пример: postgresql+psycopg2://postgres:postgres@localhost:5432/deals_bigdata"
        )
    return url


def create_db_engine(url: str | None = None) -> Engine:
    """Создаёт SQLAlchemy Engine с проверкой живости соединения."""
    return create_engine(url or get_database_url(), pool_pre_ping=True)


def execute_sql_file(engine: Engine, path: Path) -> None:
    """Выполняет SQL-файл целиком в одной транзакции.

    exec_driver_sql передаёт скрипт драйверу как есть, поэтому несколько
    statement'ов, разделённых ';', выполняются за один вызов.
    """
    sql = path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
