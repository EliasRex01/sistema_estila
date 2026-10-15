# AGENTS.md — Estila SaaS Multitenant (Arselia piloto)

> Instrucciones operativas para agentes de código (humanos y IA).
> Stack: FastAPI + SQLAlchemy 2 + Oracle (ADB/XE, SQLite en dev) + Jinja2.
> Shell: **Windows PowerShell**, launcher `py`. Python 3.11+.
> Docs: `HUMAN.md` (rol del humano), `PLAN.md` (hoja de ruta),
> `STRATEGY.md` (estrategia). Leerlos antes de cambios grandes.

## 1. Mapa del repo

```text
app/main.py                        FastAPI, monta API + web, GET /health
app/core/config.py                 Settings (.env): DATABASE_URL, ORACLE_*, JWT_*, MASTER_KEY
app/core/security.py               bcrypt + JWT(tenant_id, rol) + Fernet (secretos SIFEN)
app/core/tenant.py                 Bearer + X-Tenant-ID deben coincidir (RNF02)
app/db/session.py                  engine mult dialecto, set_rls_tenant, auth_mode, limpieza pool Oracle
app/db/models.py                   Tenant + 10 tablas con tenant_id (diccionario §8 anteproyecto)
app/db/init_db.py                  create_all (solo dev; prod = scripts SQL + futuro Alembic)
app/modules/tenants|auth/          RF01 alta tenant+admin, RF02 login JWT
app/modules/personal/              RF03 ABM + baja logica + guardias (ultimo ADMIN, auto-baja, email global)
app/modules/clientes/              RF09/10/11 ABM + sin-turno; borrado solo sin turnos
app/modules/servicios/             RF12 ABM; borrado solo sin referencias
app/modules/turnos/                RF05/06: alta con antisolape, reprogramar, cancelar con motivo,
                                   atender (+1 visita), eliminar solo RESERVADO
app/modules/chatbot/               asistente demo (RF07/08): reglas ES, identifica cliente,
                                   avisa turnos, confirma/cancela/reprograma (service+router)
app/modules/notificaciones/        RF08: RECORDATORIO auto al reservar (24 h antes), centro /ui
app/web/router.py + deps.py        UI cookie (login/panel//ui/*). Las paginas viven en /ui (ver §8.3)
app/web/templates/                 base/panel/login/listados/editar_*
app/web/static/style.css           tema empresarial (sidebar marino)
api/index.py + vercel.json         adaptador Mangum para Vercel (pruebas)
sql/adb_setup_admin.sql            usuario ESTILA_APP + CONTEXT (como ADMIN de ADB)
sql/vpd_oracle.sql                 paquete ctx + funcion + 10 politicas TENANT_P (como ESTILA_APP)
sql/rls.sql                        LEGADO Postgres, sin mantenimiento
scripts/check_ui_roles.py          18 controles de menu por rol (vivo)
scripts/check_tema.py              9 controles de tema (vivo)
scripts/check_crud.py              23 controles CRUD + reglas (vivo)
scripts/check_abm_ui.py            formato ABM en clientes/servicios/turnos/sin-turno (vivo)
scripts/check_personal_ui.py       formato ABM personal + paginacion (vivo)
scripts/check_turno_iconos.py      iconos con turno RESERVADO temporal (vivo, lo borra)
scripts/check_panel_chat.py        panel + chatbot demo + notificaciones (vivo)
tests/test_chatbot.py              11 tests puros del asistente (intenciones, fechas, formato)
scripts/probar_oracle.py           conexion + VPD + aislamiento (solo lectura, contra Oracle real)
scripts/dev.ps1                    arranque dev
tests/test_multitenant.py          9 tests sin BD ni red (solape, RUC/CI, comision, fin)
```

## 2. Setup y arranque (PowerShell)

```powershell
cd C:\Users\Desarrollo\sistema_estila
py -m venv .venv; .\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
copy .env.example .env          # dev: sqlite; ver DEPLOY_ORACLE.md para Oracle
py -m app.db.init_db
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001   # SIN --reload (ver §8.2)
```

Docs API: `/docs`. Web: `/` → `/login` → `/panel`. Usuarios de prueba en
`DEPLOY_VERCEL.md` (solo dev local).

## 3. Verificacion obligatoria antes de entregar

```powershell
.\.venv\Scripts\python.exe -m py_compile $(Get-ChildItem -Recurse -Filter *.py -Path app,api,tests,scripts | ForEach-Object FullName)
.\.venv\Scripts\python.exe tests\test_multitenant.py
.\.venv\Scripts\python.exe scripts\check_ui_roles.py
.\.venv\Scripts\python.exe scripts\check_tema.py
.\.venv\Scripts\python.exe scripts\check_crud.py
# Contra Oracle real: scripts\probar_oracle.py (ver DEPLOY_ORACLE.md)
```

Toda tarea termina con: compile OK + suites OK + prueba viva del endpoint o
pagina tocada. Nota: compilar **excluyendo `.venv`** (ruta demasiado larga en
Windows). Los datos de prueba se crean con marcas claras (`Crud`, `crudt*`) y
se borra lo borrable; lo desactivado (`activo=0`) se deja identificado.

## 4. Convenciones de codigo

- **Routers**: un `APIRouter` por modulo; `main.py` solo monta. API en
  `/personal`, `/clientes`...; web en `/ui/...`, login/panel en raiz (§8.3).
- **Logica** en `service.py` pura y testeable sin BD (solape, comisiones,
  validadores RUC/CI); routers validan y persisten.
- **Schemas** Pydantic v2 (`pattern=`, opcionales con default).
- **Modelos**: solo SQLAlchemy 2 (`Mapped`/`mapped_column`). Fechas default
  con `func.current_timestamp()` (portable Oracle/PG/SQLite, nunca `func.now()`).
- **Respuestas**: normalizar `or ""` en strings (Oracle guarda `''` como NULL)
  y `float()` en `Numeric` (llega `Decimal`).
- **Fechas**: normalizar naive UTC antes de comparar (SQLite/Oracle devuelven
  naive, Pydantic aware) — ver `turnos/service.py:_norm`.
- **Tenant**: `set_rls_tenant()` al inicio de cada endpoint con tenant;
  `auth_mode()` solo para consultas globales (login, alta tenant, email unico).
- **Borrados**: personal = baja logica; clientes/servicios = borrado solo sin
  referencias (409 si hay); turnos = eliminar solo RESERVADO, resto cancelar.
- **Maquina de estados turno**: RESERVADO/CONFIRMADO/BLOQUEADO → ATENDIDO
  (suma visita) o CANCELADO (con motivo, terminal). Nada sale de terminales.
- **UI**: Jinja sin `{{` dentro de `<script>`; formularios POST + redirect
  (PRG); errores por `?error=`. Sin JS salvo `confirm()` en bajas.
- **ABM empresarial**: alta tras boton "+ Incluir" (form oculto, pie del
  reporte); 1ra columna lapiz amarillo, 2da basurero rojo (solo iconos SVG);
  helper `pagina()` (10 filas, rango "X a Y de Z", sin numero actual).
- Comentarios en español, concisos. Referencias como `ruta:línea`.

## 5. Reglas de dominio (no relajar sin pedir)

- **Antisolape RF05**: mismo profesional + estados activos + `hay_solapamiento`;
  reprogramar excluye el propio turno. 409 con mensaje, nunca silencioso.
- **Profesional inactivo** no recibe turnos nuevos (pero conserva historial).
- **Email unico global** (el login no conoce el tenant).
- **Ultimo ADMIN** no se quita ni se autodesactiva (409).
- **VPD Oracle**: predicado `tenant_id = SYS_CONTEXT(...)`, `AUTH_MODE='1'`
  solo en login/alta, limpieza en `checkin` del pool. Verificar con
  `probar_oracle.py` contra ADB real antes de declarar listo.

## 6. Seguridad y secretos

- `.env`, `*.db`, `.venv/`, `wallet/` jamas se commitean (ver `.gitignore`).
- Claves: bcrypt; JWT con `tenant_id`+`rol` y expiracion; `JWT_SECRET` 32+ en
  nube (el default corto dispara warning, solo dev).
- Certificados SIFEN por tenant cifrados con Fernet (`MASTER_KEY` en entorno).
- Nada sensible en logs ni respuestas API (nunca `password_hash`).

## 7. Prohibido para agentes

- No registrar rutas web y API con el mismo path (la primera opaca a la otra).
- No usar `shell` para I/O de archivos (usar herramientas de ficheros).
- No `&&`, heredoc `<<`, `grep`, `head`, `tail` en PowerShell (usar `;`,
  `Select-Object`, `Select-String`). Python inline con comillas solo para
  one-liners simples; si lleva comillas anidadas → script en `scripts/`.
- No "adivinar" endpoints SIFEN/WhatsApp: marcar `TODO` y pedir el manual o
  captura del portal vigente.
- **No tocar ediciones del usuario en archivos sin preguntar** (ej. sus notas
  en `DEPLOY_VERCEL.md`): avisar y proponer, el humano decide.
- No exponer endpoints sin validacion Pydantic ni estados fuera de la maquina
  definida en §4.

## 8. Comportamientos aprendidos (obligatorios)

1. **Evidencia antes que sintesis**: leer el archivo/log real antes de afirmar.
   Ante un error "imposible", sospechar codigo viejo en memoria y reiniciar.
2. **Puerto unico, un solo servidor**: sin `--reload`; matar por dueño del
   puerto y confirmar libre antes de levantar (huerfanos sirven codigo viejo).
3. **Web vs API**: paginas en `/ui/...`, API en raiz. La colision
   `POST /personal` (web primero) dio 422 silencioso al API — asi se detecto.
4. **Fechas mixtas naive/aware** dan 500 en el 2do turno: normalizar siempre.
5. **Oracle no es Postgres**: `''→NULL`, `NUMBER→Decimal`, VPD≠RLS,
   `update_check` exige `tenant_id` en inserts, tablas en minusculas
   entrecomilladas en `user_tables`.
6. **Fallo honesto y tipificado**: 404 no existe, 409 regla de negocio con
   mensaje claro, 401/403 auth. Nunca datos inventados.
7. **Scripts de verificacion versionados** (`check_*.py`, `probar_oracle.py`):
   un bug verificado una vez queda cubierto para siempre.
8. **Limpieza y secretos**: borrar debug (`dbg_*.py`), revisar `git status`
   antes de commitear; un `git diff` del archivo del usuario antes de tocarlo.
