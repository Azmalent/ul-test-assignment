import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator

from etl.core import init_core_schema
from etl.dq import init_dq_schema
from etl.load import load_validation_results
from etl.staging import extract_and_stage_window

default_args = {
    "owner": "Дмитрий Съестов",
}

with DAG(
    dag_id="run_etl_pipeline",  # type: ignore
    schedule=None,
    default_args=default_args,
    catchup=False,
    start_date=pendulum.datetime(2026, 11, 8, tzinfo=pendulum.timezone("Europe/Moscow")),  # type: ignore
    tags=["VRP"],
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

    t_extract_and_stage_window = PythonOperator(
        task_id="extract_and_stage_window",
        python_callable=extract_and_stage_window,
        dag=dag,
    )

    t_load_validation_results = PythonOperator(
        task_id="load_validation_results",
        python_callable=load_validation_results,
        dag=dag,
    )

    (  # type: ignore # noqa: B018
        t_init_dq_schema >> t_init_core_schema >> t_extract_and_stage_window >> t_load_validation_results
    )
