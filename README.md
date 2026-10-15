# Estila — SaaS Multitenant Peluquerias/Barberias (MVP base)

Piloto: Arselia Beauty Center. Alcance MVP: RF01 tenants + RF02 auth/roles + VPD + CRUD personal/clientes/servicios/turnos.

Stack: FastAPI + **Oracle** (ADB Always Free en nube / SQLite en dev) + Jinja2.
Despliegue: ver `DEPLOY_ORACLE.md` (producción) y `DEPLOY_VERCEL.md` (pruebas).
Docs internas: `AGENTS.md` (agentes), `HUMAN.md` (tu rol), `PLAN.md` (ruta), `STRATEGY.md` (estrategia).

## Arranque dev (PowerShell)

```powershell
cd sistema_estila
py -m venv .venv; .\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
copy .env.example .env
py -m app.db.init_db
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Oracle local: `docker compose up -d db` luego `DATABASE_URL=oracle+oracledb://system:EstilaLocal123@localhost:1521/FREEPDB1`
(tras `init_db`, aplicar `sql/vpd_oracle.sql` como SYSTEM). Nube: ver `DEPLOY_ORACLE.md`.

## Interfaz web

Entrar en http://127.0.0.1:8001 con correo + contraseña. El menú se adapta al rol
(ADMIN todo, RECEPCION turnos/clientes/sin-turno/notificaciones,
ESTILISTA su agenda + servicios). El panel muestra la agenda del día y
contadores. Burbuja 💬 abajo a la derecha: asistente demo que avisa los turnos
agendados al cliente (por teléfono o nombre) y permite confirmar, cancelar con
motivo o reprogramar. Los recordatorios se programan solos al reservar
(24 h antes) y se ven en Notificaciones.

## Flujo piloto (API)

1. `POST /tenants` {ruc, razon_social, admin_nombre, admin_email, admin_password} -> crea tenant + ADMIN.
2. `POST /auth/login` {email, password} -> JWT con tenant_id + rol. Usar header `Authorization: Bearer` + `X-Tenant-ID`.
3. `POST /personal`, `/clientes`, `/servicios`, `/turnos`. Solapamiento da 409. Cancelar pide motivo. `GET /clientes/sin-turno` para RF09.

## Aislamiento por tenant (RNF02)

Toda tabla operativa tiene `tenant_id`. `session.set_rls_tenant` fija el contexto
(VPD en Oracle, RLS legado en Postgres). En SQLite dev el aislamiento es por
`filter_by(tenant_id)` en routers + check header-vs-token en `core/tenant.py`.
En Oracle además: login/alta usan `auth_mode()` y el pool limpia el contexto.

## Roadmap (anteproyecto)

Siguiente: POS/ventas + kárdex (RF13/RF14), caja (RF16), comisiones (RF17), SIFEN XAdES (RF15), IA WhatsApp (RF07/RF08), vitrina (RF19), reportes (RF18), auditoria (RF20).
