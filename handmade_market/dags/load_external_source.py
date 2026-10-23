"""Задание 2. DAG загружает три CSV-файла в схему external_source PostgreSQL.

Файлы (data/csv):
  - user_order_log.csv  -> external_source.user_order_log  (Date_time, Customer_id, Quantity, Payment_amount + raw-колонки)
  - user_activity_log.csv -> external_source.user_activity_log (Date_time, Customer_id + raw-колонки)
  - customer_research.csv -> external_source.customer_research (Date_id, Geo_id, Sales_qty, Sales_amt + raw-колонки)

Загрузка выполняется командой COPY ... FROM STDIN с заголовком CSV.
Перед загрузкой таблица очищается (TRUNCATE), чтобы DAG был идемпотентным.
"""
import os
from functools import partial

import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

PG_DSN = "postgresql://postgres:postgres@db:5432/handmade_market"
CSV_DIR = "/opt/airflow/data/csv"


def copy_csv_to_pg(filename: str, table: str, columns: list[str]) -> None:
    """Очищает целевую таблицу и копирует CSV по указанным колонкам."""
    conn = psycopg2.connect(PG_DSN)
    try:
        with conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {table}")
            with open(os.path.join(CSV_DIR, filename), "rb") as csv_file:
                cur.copy_expert(
                    "COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true)".format(
                        table=table, cols=", ".join(columns)
                    ),
                    csv_file,
                )
        conn.commit()
    finally:
        conn.close()


default_args = {
    "owner": "handmade_market",
    "start_date": days_ago(1),
    "retries": 1,
}

with DAG(
    dag_id="load_external_source",
    default_args=default_args,
    schedule="@daily",
    catchup=False,
    description="Загрузка CSV из data/csv в схему external_source",
    tags=["external_source", "csv"],
) as dag:
    load_user_order_log = PythonOperator(
        task_id="load_user_order_log",
        python_callable=partial(
            copy_csv_to_pg,
            filename="user_order_log.csv",
            table="external_source.user_order_log",
            columns=[
                "uniq_id", "date_time", "city_id", "city_name",
                "customer_id", "first_name", "last_name",
                "item_id", "item_name", "quantity", "payment_amount",
            ],
        ),
    )

    load_user_activity_log = PythonOperator(
        task_id="load_user_activity_log",
        python_callable=partial(
            copy_csv_to_pg,
            filename="user_activity_log.csv",
            table="external_source.user_activity_log",
            columns=["uniq_id", "date_time", "action_id", "customer_id", "quantity"],
        ),
    )

    load_customer_research = PythonOperator(
        task_id="load_customer_research",
        python_callable=partial(
            copy_csv_to_pg,
            filename="customer_research.csv",
            table="external_source.customer_research",
            columns=["date_id", "category_id", "geo_id", "sales_qty", "sales_amt"],
        ),
    )

    [load_user_order_log, load_user_activity_log, load_customer_research]
