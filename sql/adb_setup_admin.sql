-- ============================================================
-- Estila en Oracle Autonomous DB — Paso 1 (ejecutar como ADMIN)
-- Crea el usuario de la app y el espacio de nombres de contexto VPD.
-- ============================================================

-- 1) Usuario de aplicacion (cambiar la clave; debe cumplir la politica de ADB)
CREATE USER estila_app IDENTIFIED BY "CambiarEstaClave123#";
GRANT CREATE SESSION TO estila_app;
GRANT CREATE TABLE, CREATE VIEW, CREATE SEQUENCE, CREATE PROCEDURE TO estila_app;
ALTER USER estila_app QUOTA UNLIMITED ON DATA;
GRANT EXECUTE ON DBMS_RLS TO estila_app;

-- 2) Espacio de nombres del contexto (requiere privilegio DBA).
--    El paquete estila_ctx_pkg se crea en el Paso 2 (sql/vpd_oracle.sql).
CREATE OR REPLACE CONTEXT app_ctx USING estila_app.estila_ctx_pkg;

-- Verificacion:
--   SELECT username, account_status FROM all_users WHERE username = 'ESTILA_APP';
