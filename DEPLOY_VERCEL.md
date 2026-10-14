# BASE
Admin: admin@arselia.py / Segura123! → menú completo (Personal, Clientes, Servicios, Turnos, Sin turno)
Recepción: recep@arselia.py / Segura123! → Turnos, Clientes, Sin turno
Estilista: esti@arselia.py / Segura123! → solo Mi agenda y Servicios

# Despliegue en Vercel (entorno de pruebas)
La app corre en Vercel como función serverless (`api/index.py` + `vercel.json`).
Ojo: en serverless **no se puede usar SQLite** (el disco es efímero y los datos
se pierden) → se usa **Oracle Autonomous DB** (Always Free).

## 1. Base de datos
Seguir `DEPLOY_ORACLE.md` pasos 1–5: crear el ADB, usuario `estila_app`,
esquema (`init_db`), VPD (`vpd_oracle.sql`) y verificación
(`scripts/probar_oracle.py`).

Para Vercel **sin wallet**: en la consola ADB desactivar
"Require mutual TLS authentication" y usar conexión TLS con usuario/clave
(formato `ORACLE_DSN` en `.env.example`).

## 2. Importar en Vercel
1. Entrar a https://vercel.com → Add New → Project → importar
   `EliasRex01/sistema_estila`.
2. Framework Preset: Other. Root Directory: `./`.
3. Variables de entorno (Settings → Environment Variables):
   - `ORACLE_USER` / `ORACLE_PASSWORD` / `ORACLE_DSN` (mismas del paso 1)
   - `JWT_SECRET` = clave de 32+ caracteres (¡no usar la de ejemplo!)
   - `MASTER_KEY` = otra clave larga para cifrado de secretos SIFEN
4. Deploy. La URL queda tipo `https://sistema-estila.vercel.app`.

## 3. Probar
Abrir la URL → login → panel. Primer paso: `POST /tenants` en
`/docs` para crear el tenant piloto.

## Límites conocidos (plan Hobby, solo pruebas)
- Arranque en frío: la primera petición tarda unos segundos.
- Timeout 10 s por petición (suficiente para el MVP actual).
- Sin tareas de fondo: recordatorios WhatsApp/SIFEN futuros van en otro servicio.
- SQLite local (`estila.db`) sigue valiendo solo para desarrollo en tu PC.

# Nuevas cosas 
- Driver oracledb (reemplaza psycopg2); Postgres queda solo como legado.
- VPD en vez de RLS: sql/vpd_oracle.sql crea el paquete estila_ctx_pkg, la función tenant_policy 
y 10 políticas TENANT_P. Sin contexto, las tablas devuelven 0 filas por defecto.
- session.py ahora es mult dialecto: fija tenant en Oracle, y limpia el contexto al devolver cada 
conexión al pool (anti-fuga entre tenants).
- auth_mode() para consultas globales (login, alta de tenant, unicidad de email) — además corregí 
un detalle real: el email debe ser único global porque el login no conoce el tenant.
- Peculiaridades Oracle cubiertas: ''→NULL (normalizado con or ""), NUMBER→Decimal, 
CURRENT_TIMESTAMP portable.
- Conexión flexible: wallet/mTLS con DATABASE_URL + TNS_ADMIN (VM prod), o TLS sin wallet 
con ORACLE_USER/PASSWORD/DSN (Vercel/pruebas), o SQLite (dev), u Oracle local con el compose (imagen oracle-free).
Nuevos archivos: sql/adb_setup_admin.sql (usuario + contexto, como ADMIN), scripts/probar_oracle.py 
(verifica conexión, VPD y aislamiento), DEPLOY_ORACLE.md (guía completa Always Free), DEPLOY_VERCEL.md 
reescrito a ADB. También limpié ese archivo: tenía credenciales de prueba y notas pegadas.
Lo que hacés vos en OCI (pasos 1–5 de la guía): crear el ADB Always Free, bajar el wallet a wallet/, 
correr los 2 scripts SQL, init_db y probar_oracle.py — ese script te tiene que dar ALL ORACLE OK.
Nota honesta: el flujo Oracle está completo en código pero verificado en vivo solo contra SQLite 
(no tengo ADB). Por eso dejé el verificador: si algo del VPD rechina en tu instancia real, lo ajustamos con su salida.