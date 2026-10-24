DROP TRIGGER IF EXISTS trg_order_audit ON "order";
DROP TRIGGER IF EXISTS trg_master_product_audit ON master_product;
DROP TRIGGER IF EXISTS trg_master_audit ON master;
DROP TRIGGER IF EXISTS trg_product_audit ON product;
DROP TRIGGER IF EXISTS trg_client_audit ON client;

DROP FUNCTION IF EXISTS log_table_change();

DROP TABLE IF EXISTS logs;
