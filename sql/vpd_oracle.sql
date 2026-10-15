-- ============================================================
-- Estila en Oracle — Paso 2 (ejecutar como ESTILA_APP, salvo nota)
-- Paquete de contexto + funcion de politica + VPD por tabla.
-- Equivale al RLS de Postgres (sql/rls.sql): cada tenant solo ve sus filas.
--
-- Requisito: el esquema ya creado (init_db / create_all) y el CONTEXT
-- creado por el ADMIN (sql/adb_setup_admin.sql).
-- Nombres de tabla en MINUSCULAS: SQLAlchemy las crea entrecomilladas.
-- ============================================================

-- Paquete de confianza: unico medio para fijar el contexto de la sesion.
CREATE OR REPLACE PACKAGE estila_ctx_pkg AS
  PROCEDURE set_tenant(p_tid IN VARCHAR2);
  PROCEDURE set_auth(p_on IN NUMBER);
  PROCEDURE clear_all;
END estila_ctx_pkg;
/

CREATE OR REPLACE PACKAGE BODY estila_ctx_pkg AS
  PROCEDURE set_tenant(p_tid IN VARCHAR2) IS
  BEGIN
    DBMS_SESSION.SET_CONTEXT('APP_CTX', 'TENANT_ID', p_tid);
  END;
  PROCEDURE set_auth(p_on IN NUMBER) IS
  BEGIN
    DBMS_SESSION.SET_CONTEXT('APP_CTX', 'AUTH_MODE', TO_CHAR(p_on));
  END;
  PROCEDURE clear_all IS
  BEGIN
    DBMS_SESSION.CLEAR_CONTEXT('APP_CTX');
  END;
END estila_ctx_pkg;
/

-- Funcion de politica: modo auth (login/alta) ve todo; si no, solo su tenant.
-- Sin contexto fijado el predicado es 'tenant_id = NULL' -> no devuelve filas.
CREATE OR REPLACE FUNCTION tenant_policy(p_schema IN VARCHAR2, p_objeto IN VARCHAR2)
RETURN VARCHAR2 IS
BEGIN
  IF SYS_CONTEXT('APP_CTX', 'AUTH_MODE') = '1' THEN
    RETURN '1=1';
  END IF;
  RETURN 'tenant_id = SYS_CONTEXT(''APP_CTX'',''TENANT_ID'')';
END tenant_policy;
/

-- Una politica por tabla operativa (la tabla tenants queda sin politica: solo la usa el bootstrap).
BEGIN
  FOR t IN (SELECT table_name FROM user_tables WHERE table_name IN (
    'usuarios_personal', 'clientes', 'servicios', 'productos', 'turnos',
    'ventas_cabecera', 'ventas_detalle', 'cajas', 'comisiones', 'auditoria',
    'notificaciones', 'chat_sesiones', 'chat_mensajes'
  )) LOOP
    BEGIN
      DBMS_RLS.DROP_POLICY(USER, t.table_name, 'TENANT_P');
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
    DBMS_RLS.ADD_POLICY(
      object_schema   => USER,
      object_name     => t.table_name,
      policy_name     => 'TENANT_P',
      function_schema => USER,
      policy_function => 'TENANT_POLICY',
      statement_types => 'SELECT,INSERT,UPDATE,DELETE',
      update_check    => TRUE,
      enable          => TRUE
    );
  END LOOP;
END;
/

-- Verificacion (como ESTILA_APP):
--   SELECT object_name, policy_name, enable FROM user_policies;
--   SELECT COUNT(*) FROM clientes;  -- sin contexto debe dar 0
