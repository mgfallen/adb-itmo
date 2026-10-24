-- Демо-данные: базовый набор для отчёта (Задание 1) и Mongo-синка (Задание 3).
-- Идемпотентно: повторное выполнение ничего не ломает.

INSERT INTO client (client_id, name, address, birthday, email) VALUES
    (1, 'Иван Иванов',   'Москва', '1995-03-15', 'ivan@example.com'),
    (2, 'Пётр Петров',   'Казань', '1990-01-01', 'petr@example.com')
ON CONFLICT (client_id) DO NOTHING;

INSERT INTO product (product_id, type) VALUES
    (1, 'украшения'),
    (2, 'керамика')
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO master (master_id, name) VALUES
    (1, 'Мария'),
    (2, 'Анна')
ON CONFLICT (master_id) DO NOTHING;

INSERT INTO master_product (master_id, product_id, price) VALUES
    (1, 1, 1000),
    (2, 1, 1200),
    (1, 2, 800),
    (2, 2, 900)
ON CONFLICT (master_id, product_id) DO NOTHING;

INSERT INTO "order" (order_id, client_id, master_id, product_id, order_date, delivery_date, status) VALUES
    (1, 1, 1, 1, '2026-10-01', '2026-10-03', 'paid'),
    (2, 1, 1, 2, '2026-10-05', '2026-10-09', 'paid'),
    (3, 1, 2, 1, '2026-10-10', '2026-10-11', 'completed'),
    (4, 2, 1, 1, '2026-09-02', '2026-09-03', 'paid'),
    (5, 2, 2, 2, '2026-09-06', NULL,        'created'),
    (6, 2, 2, 1, '2026-09-09', '2026-09-09', 'in_progress')
ON CONFLICT (order_id) DO NOTHING;
