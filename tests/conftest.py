"""Общие pytest-фикстуры."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from etl.load import load_validation_results
from etl.schemas import init_core_schema, init_dq_schema
from etl.staging import extract_and_stage_window

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    """Подключение к тестовой БД из TEST_DATABASE_URL."""
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL не задан")

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            if conn.execute(text("SELECT to_regclass('public.prices')")).scalar() is None:
                pytest.skip("В тестовой БД нет public.prices")
            rows = conn.execute(text("SELECT count(*) FROM public.prices")).scalar()
            if not rows:
                pytest.skip("public.prices пуст")
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def prepared_core(test_engine: Engine) -> None:
    """Один раз заливает полный ETL в тестовую БД."""
    init_dq_schema(test_engine)
    init_core_schema(test_engine)
    extract_and_stage_window("2023-01-01", "2027-12-31", test_engine)
    load_validation_results(test_engine, run_id="test-prepare-core")


@pytest.fixture(scope="session")
def model_path() -> Path:
    """Путь к обученной модели для теста batch inference."""
    path = PROJECT_ROOT.joinpath("ml", "artifacts", "catboost_v1.cbm")
    if not path.exists():
        pytest.skip("Нет ml/artifacts/catboost_v1.cbm")
    return path
