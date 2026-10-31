from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy import text

from src.config import load_settings
from src.db import connect
from src.sys_marts import build_schedule_rows, build_task_run_rows, save_schedule_rows, save_task_run_rows

SCHEDULE_QUERY = "SELECT dag_id, schedule_interval FROM dag"
TASK_QUERY = "SELECT dag_id, task_id FROM task"
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
    from airflow.settings import Session

    session = Session()
    try:
        schedules = session.execute(text(SCHEDULE_QUERY)).all()
        tasks = session.execute(text(TASK_QUERY)).all()
        task_runs = session.execute(text(TASK_RUN_QUERY)).all()
    finally:
        session.close()
    schedule_by_dag = {dag_id: schedule for dag_id, schedule in schedules}
    task_schedules = [
        (dag_id, task_id, schedule_by_dag.get(dag_id)) for dag_id, task_id in tasks
    ]
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
