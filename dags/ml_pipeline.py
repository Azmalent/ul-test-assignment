import logging

import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator

from ml.pipeline import run_ml_pipeline

logger = logging.getLogger(__name__)

default_args = {
    "owner": "Дмитрий Съестов",
}


def run_ml_task() -> None:
    """Запускает полный ML-пайплайн и логирует метрики."""
    result = run_ml_pipeline()
    logger.info(
        "ML DAG: as_of=%s, R2=%.4f, MAPE=%.2f%%, predictions=%s",
        result.as_of,
        result.train.metrics.r2,
        result.train.metrics.mape_pct,
        result.prediction_rows,
    )


with DAG(
    dag_id="ml_pipeline",
    schedule=None,
    default_args=default_args,
    catchup=False,
    start_date=pendulum.datetime(2026, 11, 8, tz=pendulum.timezone("Europe/Moscow")),
    tags=["ML"],
    max_active_runs=1,
) as dag:
    t_run_ml_pipeline = PythonOperator(
        task_id="run_ml_pipeline",
        python_callable=run_ml_task,
        dag=dag,
    )
