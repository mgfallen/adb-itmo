from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.config import load_settings
from src.db import connect
from src.marts import build_marts

DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


def run_build_marts():
    with connect() as connection:
        build_marts(connection, load_settings())


with DAG(
    dag_id="build_marts",
    default_args=DEFAULT_ARGS,
    schedule=load_settings().schedules.build_marts,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["social", "marts"],
) as dag:
    build_task = PythonOperator(task_id="build_all_marts", python_callable=run_build_marts)
