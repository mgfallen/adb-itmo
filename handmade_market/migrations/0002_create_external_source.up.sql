-- Задание 2. Схема external_source — внешние данные, подключённые к хранилищу.
-- Целевые колонки таблиц — по заданию. Остальные колонки исходных CSV
-- (uniq_id, city_id, city_name, first_name, last_name, item_*, action_id)
-- сохранены для трассировки исходной строки.

CREATE SCHEMA IF NOT EXISTS external_source;

-- user_order_log.csv -> user_order_log: Date_time, Customer_id, Quantity, Payment_amount
CREATE TABLE IF NOT EXISTS external_source.user_order_log (
    id             BIGSERIAL PRIMARY KEY,
    uniq_id        TEXT,
    date_time      TIMESTAMP,
    city_id        BIGINT,
    city_name      TEXT,
    customer_id    BIGINT,
    first_name     TEXT,
    last_name      TEXT,
    item_id        BIGINT,
    item_name      TEXT,
    quantity       BIGINT,
    payment_amount NUMERIC(12, 2)
);

-- user_activity_log.csv -> user_activity_log: Date_time, Customer_id
CREATE TABLE IF NOT EXISTS external_source.user_activity_log (
    id          BIGSERIAL PRIMARY KEY,
    uniq_id     TEXT,
    date_time   TIMESTAMP,
    action_id   BIGINT,
    customer_id BIGINT,
    quantity    BIGINT
);

-- customer_research.csv -> customer_research: Date_id, Geo_id, Sales_qty, Sales_amt
CREATE TABLE IF NOT EXISTS external_source.customer_research (
    id          BIGSERIAL PRIMARY KEY,
    date_id     BIGINT,
    category_id BIGINT,
    geo_id      BIGINT,
    sales_qty   BIGINT,
    sales_amt   NUMERIC(12, 2)
);
