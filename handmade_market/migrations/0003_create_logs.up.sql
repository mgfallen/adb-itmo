-- Задание 3. Таблица logs хранит все изменения, внесённые в другие таблицы БД.
-- Формат записи близок к примеру из задания:
--   id, дата/время, имя таблицы, JSON со «снимком» изменённой строки.

CREATE TABLE IF NOT EXISTS logs (
    log_id     BIGSERIAL PRIMARY KEY,
    table_name TEXT        NOT NULL,
    operation  TEXT        NOT NULL,
    payload    JSONB       NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE'))
);

-- Универсальная функция аудита: пишет снимок NEW после INSERT/UPDATE
-- и снимок OLD после DELETE.
CREATE OR REPLACE FUNCTION log_table_change() RETURNS trigger AS $$
BEGIN
    INSERT INTO logs (table_name, operation, payload)
    VALUES (TG_TABLE_NAME, TG_OP, to_jsonb(COALESCE(NEW, OLD)));
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Аудит изменений доменных таблиц (задание 1).
CREATE TRIGGER trg_client_audit
    AFTER INSERT OR UPDATE OR DELETE ON client
    FOR EACH ROW EXECUTE FUNCTION log_table_change();

CREATE TRIGGER trg_product_audit
    AFTER INSERT OR UPDATE OR DELETE ON product
    FOR EACH ROW EXECUTE FUNCTION log_table_change();

CREATE TRIGGER trg_master_audit
    AFTER INSERT OR UPDATE OR DELETE ON master
    FOR EACH ROW EXECUTE FUNCTION log_table_change();

CREATE TRIGGER trg_master_product_audit
    AFTER INSERT OR UPDATE OR DELETE ON master_product
    FOR EACH ROW EXECUTE FUNCTION log_table_change();

CREATE TRIGGER trg_order_audit
    AFTER INSERT OR UPDATE OR DELETE ON "order"
    FOR EACH ROW EXECUTE FUNCTION log_table_change();

-- При необходимости аудит можно распространить и на staging-таблицы
-- external_source (задание 2), раскомментировав блок ниже:
-- CREATE TRIGGER trg_user_order_log_audit
--     AFTER INSERT OR UPDATE OR DELETE ON external_source.user_order_log
--     FOR EACH ROW EXECUTE FUNCTION log_table_change();
-- CREATE TRIGGER trg_user_activity_log_audit
--     AFTER INSERT OR UPDATE OR DELETE ON external_source.user_activity_log
--     FOR EACH ROW EXECUTE FUNCTION log_table_change();
-- CREATE TRIGGER trg_customer_research_audit
--     AFTER INSERT OR UPDATE OR DELETE ON external_source.customer_research
--     FOR EACH ROW EXECUTE FUNCTION log_table_change();
