# Producción y pruebas en Oracle Autonomous DB (Always Free)

Motor oficial del proyecto: **Oracle**. SQLite queda solo para desarrollo rápido
en PC; Postgres quedó como legado (`sql/rls.sql`, sin mantenimiento).
El aislamiento por tenant en Oracle se hace con **VPD** (`sql/vpd_oracle.sql`).

## 1. Crear la base Always Free (consola OCI)

1. Oracle Cloud → Oracle Database → Autonomous Database → Create.
2. Workload: **Transaction Processing**, activar **Always Free**.
3. Usuario ADMIN + clave (guardarla en un gestor de claves).
4. Red: dejar mTLS activado (recomendado prod). Para pruebas sin wallet
   (Vercel) se puede desactivar "Require mutual TLS authentication" después.

## 2. Wallet (conexión con mTLS: PC y VM)

1. En la ficha de la base → DB Connection → Download Wallet (clave del wallet).
2. Descomprimir en `C:\Users\Desarrollo\sistema_estila\wallet\`
   (carpeta ignorada por git: `tnsnames.ora`, `sqlnet.ora`, `ewallet.pem`).
3. Ver el alias en `tnsnames.ora` (ej. `estila_high`).

## 3. Usuario y contexto (una vez)

Conectado como **ADMIN** (Database Actions → SQL): ejecutar
`sql/adb_setup_admin.sql` (cambiar la clave de `estila_app`).

## 4. Esquema + VPD (una vez)

Desde el PC, con el entorno del proyecto:

```powershell
cd C:\Users\Desarrollo\sistema_estila
.\.venv\Scripts\Activate.ps1
$env:TNS_ADMIN="C:\Users\Desarrollo\sistema_estila\wallet"
$env:DATABASE_URL="oracle+oracledb://ESTILA_APP:TuClave@estila_high"
.\.venv\Scripts\python.exe -c "from app.db.init_db import init_db; init_db()"
```

Luego, conectado como **ESTILA_APP**, ejecutar `sql/vpd_oracle.sql`
(paquete `estila_ctx_pkg`, función `tenant_policy` y 10 políticas TENANT_P).

## 5. Verificar aislamiento

```powershell
$env:TNS_ADMIN="C:\Users\Desarrollo\sistema_estila\wallet"
$env:DATABASE_URL="oracle+oracledb://ESTILA_APP:TuClave@estila_high"
.\.venv\Scripts\python.exe scripts\probar_oracle.py
```

Debe dar `ALL ORACLE OK`: sin contexto 0 filas, con tenant solo sus filas.

## 6. VM de producción (Oracle Always Free)

1. Crear instancia Ampere (Ubuntu) en OCI, abrir puertos 80/443.
2. Instalar Docker, clonar el repo, poner `wallet/` + `.env` (alias + claves
   fuertes de 32+ para `JWT_SECRET` y `MASTER_KEY`).
3. `docker compose` con `DATABASE_URL` Oracle (perfil prod: ver guía de Caddy
   cuando se sume el proxy HTTPS).
4. Respaldo diario (RNF08): cron con Data Pump o `expdp` hacia un bucket de
   Object Storage (10 GB Always Free).

## 7. Vercel (pruebas) contra ADB

Sin wallet: desactivar mTLS en la consola ADB y usar las variables
`ORACLE_USER` / `ORACLE_PASSWORD` / `ORACLE_DSN` (formato en `.env.example`).
Detalle en `DEPLOY_VERCEL.md`.

## Notas Oracle a tener en cuenta

- `''` se guarda como `NULL`: el código normaliza con `or ""` al responder.
- `NUMBER` llega como `Decimal`: los esquemas convierten a `float`/`int`.
- Fechas con zona horaria: se normalizan a naive UTC al comparar turnos.
- El pool limpia el contexto tenant al devolver cada conexión (anti-fuga).
