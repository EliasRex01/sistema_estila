"""Prueba de solo lectura contra Oracle: conexion, VPD instalado y aislamiento.

Uso (con variables de entorno del .env de Oracle):
  $env:DATABASE_URL="oracle+oracledb://ESTILA_APP:clave@alias"  # + TNS_ADMIN=./wallet
  # o ORACLE_USER / ORACLE_PASSWORD / ORACLE_DSN (TLS sin wallet)
  py scripts/probar_oracle.py

Verifica:
1. Dialecto oracle y conexion viva.
2. Politicas VPD presentes en las 10 tablas operativas.
3. Sin contexto: clientes devuelve 0 filas (denegacion por defecto).
4. Con tenant fijado: solo filas de ese tenant.
"""

import sys

from sqlalchemy import text

from app.db.session import SessionLocal, engine


def check(nombre, cond):
    print(("PASS " if cond else "FAIL ") + nombre)
    if not cond:
        raise SystemExit(1)


print("dialecto:", engine.dialect.name)
if engine.dialect.name != "oracle":
    print("Apunta DATABASE_URL u ORACLE_DSN a Oracle para esta prueba.")
    raise SystemExit(2)

db = SessionLocal()
try:
    check("conexion", db.execute(text("SELECT 1 FROM DUAL")).scalar() == 1)

    esperadas = {"usuarios_personal", "clientes", "servicios", "productos", "turnos",
                 "ventas_cabecera", "ventas_detalle", "cajas", "comisiones", "auditoria"}
    con_politica = {r[0].lower() for r in
                    db.execute(text("SELECT object_name FROM user_policies WHERE policy_name = 'TENANT_P'"))}
    faltan = esperadas - con_politica
    check(f"vpd-10-tablas (faltan: {sorted(faltan) or 'ninguna'})", not faltan)

    n_sin = db.execute(text("SELECT COUNT(*) FROM clientes")).scalar()
    check(f"sin-contexto-cero (n={n_sin})", n_sin == 0)

    tenants = [r[0] for r in db.execute(text("SELECT id FROM tenants"))]
    if not tenants:
        print("AVISO: sin tenants; crea uno con POST /tenants y repite.")
        raise SystemExit(0)
    tid = tenants[0]
    db.execute(text("BEGIN estila_ctx_pkg.set_tenant(:t); END;"), {"t": tid})
    distintos = db.execute(text("SELECT COUNT(DISTINCT tenant_id) FROM clientes")).scalar() or 0
    check(f"tenant-aislado (tenants distintos visibles: {distintos})", distintos <= 1)
    db.execute(text("BEGIN estila_ctx_pkg.clear_all; END;"))
    n_despues = db.execute(text("SELECT COUNT(*) FROM clientes")).scalar()
    check(f"contexto-limpio (n={n_despues})", n_despues == 0)
finally:
    db.close()

print("ALL ORACLE OK")
