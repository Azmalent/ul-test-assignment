"""Настройки ETL-пайплайна."""

import os

import pendulum

from etl.models import to_pendulum_date

DEFAULT_AS_OF_DATE = pendulum.date(2026, 10, 26)


def get_as_of_date() -> pendulum.Date:
    """Возвращает as_of из AS_OF_DATE или значение по умолчанию."""
    raw = os.getenv("AS_OF_DATE")
    return to_pendulum_date(raw) if raw else DEFAULT_AS_OF_DATE
