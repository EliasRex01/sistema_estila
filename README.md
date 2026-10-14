# Estila — SaaS Multitenant Peluquerias/Barberias (MVP base)

Piloto: Arselia Beauty Center. Alcance MVP: RF01 tenants + RF02 auth/roles + RLS + CRUD personal/clientes/servicios/turnos.

## Arranque dev (PowerShell)

```powershell
cd sistema_estila
py -m venv .venv; .\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
copy .env.example .env
py -m app.db.init_db
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Prod Postgres: `docker compose up -d db` luego `DATABASE_URL=postgresql+psycopg2://estila:estila@localhost:5433/estila`
y aplicar `sql/rls.sql` con psql tras el primer arranque.

## Interfaz web

Entrar en http://127.0.0.1:8001 con correo + contraseña. El menú se adapta al rol:

- ADMIN: Personal, Clientes, Servicios, Turnos, Sin turno (+ tarjetas de POS/Caja/Comisiones/Inventario/Reportes como próximos módulos).
- RECEPCION: Turnos, Clientes, Sin turno.
- ESTILISTA: Mi agenda (solo sus turnos), Servicios.

Páginas en `/ui/...` (el API JSON sigue en `/personal`, `/clientes`, etc. y en `/docs`).

## Flujo piloto (API)

1. `POST /tenants` {ruc, razon_social, admin_nombre, admin_email, admin_password} -> crea tenant + ADMIN.
2. `POST /auth/login` {email, password} -> JWT con tenant_id + rol. Usar header `Authorization: Bearer` + `X-Tenant-ID`.
3. `POST /personal`, `/clientes`, `/servicios`, `/turnos`. Solapamiento da 409. Cancelar pide motivo. `GET /clientes/sin-turno` para RF09.

## RLS (RNF02)

Toda tabla operativa tiene `tenant_id`. `session.set_rls_tenant` fija `SET LOCAL app.tenant_id` y `sql/rls.sql` crea politicas. En SQLite dev el aislamiento es por `filter_by(tenant_id)` en routers + check header-vs-token en `core/tenant.py`.

## Roadmap (anteproyecto)

Siguiente: POS/ventas + kárdex (RF13/RF14), caja (RF16), comisiones (RF17), SIFEN XAdES (RF15), IA WhatsApp (RF07/RF08), vitrina (RF19), reportes (RF18), auditoria (RF20).
