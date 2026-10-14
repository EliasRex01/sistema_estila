-- RLS Estila (RNF02): ejecutar en Postgres prod tras create_all.
-- Cada tabla operativa aisla por app.tenant_id (text). Tenants sin RLS (superadmin).
DO $$ BEGIN
  IF current_setting('server_version_num')::int < 150000 THEN RAISE NOTICE 'requiere PG15+'; END IF;
END $$;

-- Limpia politicas previas para re-ejecucion idempotente
DROP POLICY IF EXISTS p_usuarios ON usuarios_personal;
DROP POLICY IF EXISTS p_clientes ON clientes;
DROP POLICY IF EXISTS p_servicios ON servicios;
DROP POLICY IF EXISTS p_productos ON productos;
DROP POLICY IF EXISTS p_turnos ON turnos;
DROP POLICY IF EXISTS p_ventas_cab ON ventas_cabecera;
DROP POLICY IF EXISTS p_ventas_det ON ventas_detalle;
DROP POLICY IF EXISTS p_cajas ON cajas;
DROP POLICY IF EXISTS p_comisiones ON comisiones;
DROP POLICY IF EXISTS p_auditoria ON auditoria;

ALTER TABLE usuarios_personal ENABLE ROW LEVEL SECURITY;
ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE servicios ENABLE ROW LEVEL SECURITY;
ALTER TABLE productos ENABLE ROW LEVEL SECURITY;
ALTER TABLE turnos ENABLE ROW LEVEL SECURITY;
ALTER TABLE ventas_cabecera ENABLE ROW LEVEL SECURITY;
ALTER TABLE ventas_detalle ENABLE ROW LEVEL SECURITY;
ALTER TABLE cajas ENABLE ROW LEVEL SECURITY;
ALTER TABLE comisiones ENABLE ROW LEVEL SECURITY;
ALTER TABLE auditoria ENABLE ROW LEVEL SECURITY;

-- La app fija SET LOCAL app.tenant_id = '<uuid>' por request (ver session.set_rls_tenant).
CREATE POLICY p_usuarios ON usuarios_personal USING (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY p_clientes ON clientes USING (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY p_servicios ON servicios USING (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY p_productos ON productos USING (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY p_turnos ON turnos USING (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY p_ventas_cab ON ventas_cabecera USING (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY p_ventas_det ON ventas_detalle USING (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY p_cajas ON cajas USING (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY p_comisiones ON comisiones USING (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY p_auditoria ON auditoria USING (tenant_id = current_setting('app.tenant_id', true));
