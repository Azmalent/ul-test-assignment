FROM apache/airflow:2.10.5

USER airflow

RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt" \
    "catboost>=1.2,<2" \
    "scikit-learn>=1.4,<2"
