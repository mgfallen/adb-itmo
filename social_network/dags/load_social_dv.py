from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.config import PROJECT_ROOT, load_settings
from src.db import connect, execute_script
from src.load import load_hubs, load_links, load_satellites, load_staging

DDL_FILES = (
    "00_schemas.sql",
    "01_staging_ddl.sql",
    "02_dv_ddl.sql",
    "03_marts_ddl.sql",
    "04_sys_marts_ddl.sql",
)
SQL_DIR = PROJECT_ROOT / "sql"

DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


def run_ddl():
    load_settings()
    with connect() as connection:
        for name in DDL_FILES:
            execute_script(connection, SQL_DIR / name)
        connection.commit()


def run_load_staging():
    settings = load_settings()
    with connect() as connection:
        counts = load_staging(connection, settings)
    print(counts)


def run_load_hubs():
    with connect() as connection:
        load_hubs(connection, load_settings(), datetime.now())


def run_load_links():
    with connect() as connection:
        load_links(connection, load_settings(), datetime.now())


def run_load_satellites():
    with connect() as connection:
        load_satellites(connection, load_settings(), datetime.now())


with DAG(
    dag_id="load_social_dv",
    default_args=DEFAULT_ARGS,
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["social", "dwh"],
) as dag:
    create_ddl = PythonOperator(task_id="create_ddl", python_callable=run_ddl)
    staging_task = PythonOperator(task_id="load_staging", python_callable=run_load_staging)
    hubs_task = PythonOperator(task_id="load_hubs", python_callable=run_load_hubs)
    links_task = PythonOperator(task_id="load_links", python_callable=run_load_links)
    satellites_task = PythonOperator(task_id="load_satellites", python_callable=run_load_satellites)

    create_ddl >> staging_task >> hubs_task >> links_task >> satellites_task
