from dataclasses import dataclass
from datetime import datetime, timedelta

from croniter import CroniterBadCronError, croniter

from src.config import Settings

CRON_PRESETS = {
    "@hourly": "0 * * * *",
    "@daily": "0 0 * * *",
    "@weekly": "0 0 * * 0",
    "@monthly": "0 0 1 * *",
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
}
NO_SCHEDULE_VALUES = (None, "", "@once")


@dataclass(frozen=True)
class ScheduleEvaluation:
    has_schedule: bool
    is_valid_cron: bool
    next_fire_time: datetime | None
    prev_fire_time: datetime | None


def evaluate_schedule(expression, checked_at: datetime) -> ScheduleEvaluation:
    if isinstance(expression, timedelta):
        return ScheduleEvaluation(has_schedule=True, is_valid_cron=False, next_fire_time=None, prev_fire_time=None)
    if expression in NO_SCHEDULE_VALUES:
        return ScheduleEvaluation(has_schedule=False, is_valid_cron=False, next_fire_time=None, prev_fire_time=None)
    cron = CRON_PRESETS.get(expression, expression)
    try:
        iterator = croniter(cron, checked_at)
    except (CroniterBadCronError, ValueError):
        return ScheduleEvaluation(has_schedule=True, is_valid_cron=False, next_fire_time=None, prev_fire_time=None)
    return ScheduleEvaluation(
        has_schedule=True,
        is_valid_cron=True,
        next_fire_time=iterator.get_next(datetime),
        prev_fire_time=iterator.get_prev(datetime),
    )


def build_schedule_rows(task_schedules: list[tuple], checked_at: datetime) -> list[dict]:
    rows = []
    for dag_id, task_id, expression in task_schedules:
        evaluation = evaluate_schedule(expression, checked_at)
        rows.append(
            {
                "dag_id": dag_id,
                "task_id": task_id,
                "cron_expression": str(expression) if expression is not None else None,
                "is_valid_cron": evaluation.is_valid_cron,
                "has_schedule": evaluation.has_schedule,
                "next_fire_time": evaluation.next_fire_time,
                "prev_fire_time": evaluation.prev_fire_time,
                "checked_at": checked_at,
            }
        )
    return rows


def build_task_run_rows(run_rows: list[tuple]) -> list[dict]:
    rows = []
    for dag_id, task_id, run_id, state, start_date, end_date, try_number in run_rows:
        duration_sec = (end_date - start_date).total_seconds() if start_date and end_date else None
        rows.append(
            {
                "dag_id": dag_id,
                "task_id": task_id,
                "run_id": run_id,
                "state": state,
                "start_date": start_date,
                "end_date": end_date,
                "duration_sec": duration_sec,
                "try_number": try_number,
            }
        )
    return rows


def _save_rows(connection, table: str, columns: tuple[str, ...], rows: list[dict]) -> None:
    if not rows:
        return
    placeholders = ", ".join(f":{column}" for column in columns)
    insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    with connection.cursor() as cursor:
        cursor.execute(f"TRUNCATE TABLE {table}")
        for row in rows:
            cursor.execute(insert_sql, row)
    connection.commit()


def save_schedule_rows(connection, settings: Settings, rows: list[dict]) -> None:
    table = f"{settings.dwh.sys_marts_schema}.sys_cron_schedule"
    columns = (
        "dag_id",
        "task_id",
        "cron_expression",
        "is_valid_cron",
        "has_schedule",
        "next_fire_time",
        "prev_fire_time",
        "checked_at",
    )
    _save_rows(connection, table, columns, rows)


def save_task_run_rows(connection, settings: Settings, rows: list[dict]) -> None:
    table = f"{settings.dwh.sys_marts_schema}.sys_task_runs"
    columns = (
        "dag_id",
        "task_id",
        "run_id",
        "state",
        "start_date",
        "end_date",
        "duration_sec",
        "try_number",
    )
    _save_rows(connection, table, columns, rows)
