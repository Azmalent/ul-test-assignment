import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from etl.config import get_as_of_date
from etl.load import load_validation_results
from etl.mart import refresh_mart_route_card
from etl.schemas import init_core_schema, init_dq_schema, init_mart_schema, init_ml_schema
from etl.staging import extract_and_stage_window


def extract_window_task(**context) -> None:
    """Берёт окно из интервала Airflow и запускает staging."""
    start_date = context["data_interval_start"].date()
    end_date = context["data_interval_end"].date()
    extract_and_stage_window(start_date, end_date)


def load_validation_task(**context) -> None:
    """Передаёт Airflow run_id в загрузку core/карантина."""
    load_validation_results(run_id=context["run_id"])


def refresh_mart_task() -> None:
    """Пересобирает витрину mart.mart_route_card."""
    refresh_mart_route_card(as_of=get_as_of_date())


default_args = {
    "owner": "Дмитрий Съестов",
}

with DAG(
    dag_id="run_etl_pipeline",
    schedule="0 7 * * *",  # 07:00 daily # type: ignore
    default_args=default_args,
    catchup=False,
    start_date=pendulum.datetime(2026, 11, 8, tz=pendulum.timezone("Europe/Moscow")),  # type: ignore
    tags=["ETL"],
    max_active_runs=1,
) as dag:
    t_init_dq_schema = PythonOperator(
        task_id="init_dq_schema",
        python_callable=init_dq_schema,
        dag=dag,
    )

    t_init_core_schema = PythonOperator(
        task_id="init_core_schema",
        python_callable=init_core_schema,
        dag=dag,
    )

    t_init_mart_schema = PythonOperator(
        task_id="init_mart_schema",
        python_callable=init_mart_schema,
        dag=dag,
    )

    t_init_ml_schema = PythonOperator(
        task_id="init_ml_schema",
        python_callable=init_ml_schema,
        dag=dag,
    )

    t_extract_and_stage_window = PythonOperator(
        task_id="extract_and_stage_window",
        python_callable=extract_window_task,
        dag=dag,
    )

    t_load_validation_results = PythonOperator(
        task_id="load_validation_results",
        python_callable=load_validation_task,
        dag=dag,
    )

    t_refresh_mart_route_card = PythonOperator(
        task_id="refresh_mart_route_card",
        python_callable=refresh_mart_task,
        dag=dag,
    )

    t_trigger_ml_pipeline = TriggerDagRunOperator(
        task_id="trigger_ml_pipeline",
        trigger_dag_id="ml_pipeline",
        dag=dag,
    )

    (  # type: ignore # noqa: B018
        t_init_dq_schema
        >> t_init_core_schema
        >> t_init_mart_schema
        >> t_init_ml_schema
        >> t_extract_and_stage_window
        >> t_load_validation_results
        >> t_refresh_mart_route_card
        >> t_trigger_ml_pipeline
    )
