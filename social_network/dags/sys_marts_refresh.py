from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.config import load_settings
from src.db import connect
from src.sys_marts import build_schedule_rows, build_task_run_rows, save_schedule_rows, save_task_run_rows

TASK_RUN_QUERY = """
    SELECT dag_id, task_id, run_id, state, start_date, end_date, try_number
    FROM task_instance
"""

DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


def extract_airflow_metadata():
    from airflow import settings
    from airflow.configuration import conf
    from airflow.models import DagBag
    from sqlalchemy import text

    bag = DagBag(dag_folder=conf.get("core", "dags_folder"), include_examples=False)
    task_schedules = [
        (dag_id, task.task_id, dag.schedule_interval)
        for dag_id, dag in bag.dags.items()
        for task in dag.tasks
    ]
    session = settings.Session()
    try:
        task_runs = session.execute(text(TASK_RUN_QUERY)).all()
    finally:
        session.close()
    return task_schedules, task_runs


def run_refresh():
    settings = load_settings()
    checked_at = datetime.now()
    task_schedules, task_runs = extract_airflow_metadata()
    schedule_rows = build_schedule_rows(task_schedules, checked_at)
    run_rows = build_task_run_rows(task_runs)
    with connect() as connection:
        save_schedule_rows(connection, settings, schedule_rows)
        save_task_run_rows(connection, settings, run_rows)
    print(len(schedule_rows), len(run_rows))


with DAG(
    dag_id="sys_marts_refresh",
    default_args=DEFAULT_ARGS,
    schedule=load_settings().schedules.sys_marts_refresh,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["social", "sys_marts"],
) as dag:
    refresh_task = PythonOperator(task_id="refresh_sys_marts", python_callable=run_refresh)
