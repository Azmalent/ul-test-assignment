"""Общие функции для работы с БД."""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_database_url() -> str:
    """Возвращает строку подключения к БД, задаваемую переменной окружения DATABASE_URL."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Не задана строка подключения к БД.")

    return url


def create_db_engine(url: str | None = None) -> Engine:
    """Создаёт SQLAlchemy Engine."""
    return create_engine(url or get_database_url(), pool_pre_ping=True)


def execute_sql_script(engine: Engine, path: Path) -> None:
    """Выполняет SQL-скрипт целиком в одной транзакции."""
    sql = path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
