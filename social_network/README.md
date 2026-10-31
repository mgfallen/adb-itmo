# social_network — хранилище Data Vault на Vertica

Лабораторная работа 2 (АБД, ИТМО): Data Vault 2.0 в Vertica + Airflow + Apache Superset.

## Структура

```
data/csv/       исходные CSV (Windows-1251)
config/         параметры прогонов (settings.yml)
sql/            DDL Vertica (схемы, staging, Data Vault, витрины)
src/            модули: конфиг, очистка CSV, загрузчики, витрины
dags/           Airflow: load_social_dv, build_marts, sys_marts_refresh
tests/          pytest
docs/           ТЗ, архитектура, план разработки
```

## Запуск

```bash
cp .env.example .env
docker compose up --build -d
```

Порты: Airflow `8081` (admin/admin), Superset `8088` (admin/admin), Vertica `5433`.

Пайплайн:

1. В Airflow запустить DAG `load_social_dv` (DDL → staging → хабы → линки → спутники).
2. Даг `build_marts` пересобирает аналитические витрины (расписание в `config/settings.yml`).
3. Даг `sys_marts_refresh` обновляет системные витрины `sys_cron_schedule` и `sys_task_runs`.

В Superset подключить Vertica (SQLAlchemy URI `vertica+vertica_python://dbadmin@vertica:5433/social`)
и построить дашборды над схемами `marts` и `sys_marts`.

Секреты и персональные переопределения — в `.env.local` (в git не попадает).

## Разработка

```bash
pip install -r requirements-dev.txt
pytest
ruff check .
```
