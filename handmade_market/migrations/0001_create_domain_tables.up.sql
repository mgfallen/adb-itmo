-- Задание 1. Доменные таблицы магазина изделий ручной работы (схема public).
-- Структура повторяет схему, на которой строится отчёт из repo.go.

CREATE TABLE IF NOT EXISTS client (
    client_id BIGINT PRIMARY KEY,
    name      TEXT NOT NULL,
    address   TEXT,
    birthday  DATE,
    email     TEXT
);

CREATE TABLE IF NOT EXISTS product (
    product_id BIGINT PRIMARY KEY,
    type       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS master (
    master_id BIGINT PRIMARY KEY,
    name      TEXT NOT NULL
);

-- Таблица «мастера и товары»: мастер продаёт товар по своей цене.
CREATE TABLE IF NOT EXISTS master_product (
    master_id  BIGINT NOT NULL REFERENCES master (master_id),
    product_id BIGINT NOT NULL REFERENCES product (product_id),
    price      NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (master_id, product_id)
);

CREATE TABLE IF NOT EXISTS "order" (
    order_id      BIGINT PRIMARY KEY,
    client_id     BIGINT NOT NULL REFERENCES client (client_id),
    master_id     BIGINT NOT NULL REFERENCES master (master_id),
    product_id    BIGINT NOT NULL REFERENCES product (product_id),
    order_date    DATE NOT NULL,
    delivery_date DATE,
    status        TEXT NOT NULL
);

-- Индексы под отчёт: группировка по клиенту за период, фильтр по статусу.
CREATE INDEX IF NOT EXISTS idx_order_client_date ON "order" (client_id, order_date);
CREATE INDEX IF NOT EXISTS idx_order_status ON "order" (status);
