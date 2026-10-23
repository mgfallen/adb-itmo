-- Откат демо-данных: удаляет только строки из 0004_seed_demo_data.up.sql.
DELETE FROM "order" WHERE order_id IN (1, 2, 3, 4, 5, 6);
DELETE FROM master_product WHERE master_id IN (1, 2) AND product_id IN (1, 2);
DELETE FROM master WHERE master_id IN (1, 2);
DELETE FROM product WHERE product_id IN (1, 2);
DELETE FROM client WHERE client_id IN (1, 2);
