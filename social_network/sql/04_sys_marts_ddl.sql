CREATE TABLE IF NOT EXISTS sys_marts.sys_cron_schedule (
    dag_id VARCHAR(250),
    task_id VARCHAR(250),
    cron_expression VARCHAR(64),
    is_valid_cron BOOLEAN,
    has_schedule BOOLEAN,
    next_fire_time TIMESTAMP,
    prev_fire_time TIMESTAMP,
    checked_at TIMESTAMP
) ORDER BY dag_id, task_id;

CREATE TABLE IF NOT EXISTS sys_marts.sys_task_runs (
    dag_id VARCHAR(250),
    task_id VARCHAR(250),
    run_id VARCHAR(250),
    state VARCHAR(32),
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    duration_sec NUMERIC(12, 3),
    try_number INT
) ORDER BY dag_id, start_date;
