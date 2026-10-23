"""Задание 3. DAG синхронизирует доменные таблицы PostgreSQL в MongoDB (upsert).

Коллекции (БД handmade_market):
  - clients  <- client
  - orders   <- "order"
  - masters  <- master
  - logs     <- logs (аудит изменений доменных таблиц, пишется триггерами)

Все задачи независимы, поэтому выполняются параллельно.
"""
from datetime import datetime

import psycopg2
from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from pymongo import MongoClient

PG_DSN = "postgresql://postgres:postgres@db:5432/handmade_market"
MONGO_URI = "mongodb://mongo:27017"
MONGO_DB = "handmade_market"


def _pg_conn():
    return psycopg2.connect(PG_DSN)


def _mongo_db():
    return MongoClient(MONGO_URI)[MONGO_DB]


def _update_time():
    return datetime.utcnow().isoformat()


def sync_clients() -> None:
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT client_id, name, address, birthday, email FROM client ORDER BY client_id"
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    coll = _mongo_db()["clients"]
    for client_id, name, address, birthday, email in rows:
        coll.replace_one(
            {"_id": client_id},
            {
                "name": name,
                "address": address,
                "birthday": birthday.isoformat() if birthday else None,
                "email": email,
                "update_time": _update_time(),
            },
            upsert=True,
        )


def sync_masters() -> None:
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT master_id, name FROM master ORDER BY master_id")
            rows = cur.fetchall()
    finally:
        conn.close()

    coll = _mongo_db()["masters"]
    for master_id, name in rows:
        coll.replace_one(
            {"_id": master_id},
            {
                "name": name,
                "update_time": _update_time(),
            },
            upsert=True,
        )


def sync_orders() -> None:
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT order_id, client_id, master_id, product_id, '
                'order_date, delivery_date, status FROM "order" ORDER BY order_id'
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    coll = _mongo_db()["orders"]
    for (order_id, client_id, master_id, product_id,
         order_date, delivery_date, status) in rows:
        coll.replace_one(
            {"_id": order_id},
            {
                "client_id": client_id,
                "master_id": master_id,
                "product_id": product_id,
                "order_date": order_date.isoformat() if order_date else None,
                "delivery_date": delivery_date.isoformat() if delivery_date else None,
                "status": status,
                "update_time": _update_time(),
            },
            upsert=True,
        )


def sync_logs() -> None:
    """Копирует журнал изменений PostgreSQL в коллекцию logs MongoDB."""
    conn = _pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT log_id, table_name, operation, payload::text, changed_at "
                "FROM logs ORDER BY log_id"
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    coll = _mongo_db()["logs"]
    for log_id, table_name, operation, payload, changed_at in rows:
        coll.replace_one(
            {"_id": log_id},
            {
                "table_name": table_name,
                "operation": operation,
                "payload": payload,
                "changed_at": changed_at.isoformat() if changed_at else None,
            },
            upsert=True,
        )


default_args = {
    "owner": "handmade_market",
    "start_date": days_ago(1),
    "retries": 1,
}

with DAG(
    dag_id="sync_mongo",
    default_args=default_args,
    schedule="@daily",
    catchup=False,
    description="Синхронизация доменных таблиц PostgreSQL в MongoDB",
    tags=["mongo", "sync"],
) as dag:
    start = DummyOperator(task_id="start")

    t_clients = PythonOperator(task_id="sync_clients", python_callable=sync_clients)
    t_masters = PythonOperator(task_id="sync_masters", python_callable=sync_masters)
    t_orders = PythonOperator(task_id="sync_orders", python_callable=sync_orders)
    t_logs = PythonOperator(task_id="sync_logs", python_callable=sync_logs)

    end = DummyOperator(task_id="end")

    start >> [t_clients, t_masters, t_orders, t_logs] >> end
