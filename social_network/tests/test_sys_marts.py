from datetime import datetime, timedelta

from src.config import load_settings
from src.sys_marts import (
    build_schedule_rows,
    build_task_run_rows,
    evaluate_schedule,
    save_schedule_rows,
    save_task_run_rows,
)
from tests.fakes import FakeConnection

CHECKED_AT = datetime(2024, 6, 1, 12, 0, 0)


def test_evaluate_schedule_valid_cron():
    evaluation = evaluate_schedule("*/5 * * * *", CHECKED_AT)

    assert evaluation.has_schedule is True
    assert evaluation.is_valid_cron is True
    assert evaluation.next_fire_time is not None
    assert evaluation.prev_fire_time is not None


def test_evaluate_schedule_daily_preset():
    evaluation = evaluate_schedule("@daily", CHECKED_AT)

    assert evaluation.is_valid_cron is True


def test_evaluate_schedule_none():
    evaluation = evaluate_schedule(None, CHECKED_AT)

    assert evaluation.has_schedule is False
    assert evaluation.is_valid_cron is False


def test_evaluate_schedule_once():
    evaluation = evaluate_schedule("@once", CHECKED_AT)

    assert evaluation.has_schedule is False


def test_evaluate_schedule_invalid_cron():
    evaluation = evaluate_schedule("not a cron", CHECKED_AT)

    assert evaluation.has_schedule is True
    assert evaluation.is_valid_cron is False
    assert evaluation.next_fire_time is None


def test_evaluate_schedule_timedelta():
    evaluation = evaluate_schedule(timedelta(minutes=30), CHECKED_AT)

    assert evaluation.has_schedule is True
    assert evaluation.is_valid_cron is False


def test_build_schedule_rows():
    task_schedules = [
        ("build_marts", "build", "0 4 * * *"),
        ("load_dv", "load", None),
        ("broken", "task", "bad cron"),
    ]

    rows = build_schedule_rows(task_schedules, CHECKED_AT)

    assert len(rows) == 3
    assert rows[0]["is_valid_cron"] is True
    assert rows[0]["next_fire_time"] is not None
    assert rows[1]["has_schedule"] is False
    assert rows[1]["cron_expression"] is None
    assert rows[2]["is_valid_cron"] is False
    assert rows[2]["checked_at"] == CHECKED_AT


def test_build_task_run_rows_computes_duration():
    start = datetime(2024, 6, 1, 12, 0, 0)
    end = datetime(2024, 6, 1, 12, 0, 30)
    run_rows = [
        ("dag1", "task1", "run1", "success", start, end, 0),
        ("dag1", "task2", "run1", "running", start, None, 0),
    ]

    rows = build_task_run_rows(run_rows)

    assert rows[0]["duration_sec"] == 30.0
    assert rows[1]["duration_sec"] is None


def test_save_schedule_rows():
    connection = FakeConnection()
    settings = load_settings()
    rows = build_schedule_rows([("build_marts", "build", "0 4 * * *")], CHECKED_AT)

    save_schedule_rows(connection, settings, rows)

    truncate_sql = connection._cursor.executed[0][0]
    insert_sql, insert_params = connection._cursor.executed[1]
    assert truncate_sql == "TRUNCATE TABLE sys_marts.sys_cron_schedule"
    assert "INSERT INTO sys_marts.sys_cron_schedule" in insert_sql
    assert insert_params["dag_id"] == "build_marts"
    assert connection.commits == 1


def test_save_task_run_rows_empty():
    connection = FakeConnection()

    save_task_run_rows(connection, load_settings(), [])

    assert connection._cursor.executed == []
    assert connection.commits == 0
