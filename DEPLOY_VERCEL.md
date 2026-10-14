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

## Por qué no GitHub Pages

Pages solo publica archivos estáticos (HTML/CSS/JS): no ejecuta Python ni
bases de datos, así que este sistema no puede correr ahí. Si algún día se
quiere una portada estática en Pages, el API igual debe vivir en Vercel/VM.

# Bases, por definir y hacer despues 
api/index.py (adaptador Mangum), vercel.json (todas las rutas → la app), 
.vercelignore. 
Lo que falta:
Crear DB gratis en Neon y correr el esquema una vez desde una PC 
(comando arriba) + aplicar sql/rls.sql.
En Vercel: importar EliasRex01/sistema_estila,      -> de github de elias 
cargar DATABASE_URL, JWT_SECRET (32+ caracteres) y MASTER_KEY, Deploy.
Condiciones: en Vercel no vale SQLite (los datos se perderían, 
por eso el Postgres externo); plan Hobby con arranque en frío de unos segundos 
y timeout de 10 s — bien para desarrollo/pruebas, no para producción final.

# Lo que sí podés hacer gratis para producción piloto:
- Servidor: VM Ampere (Ubuntu) en Oracle Free Tier + tu docker-compose (app + Postgres). 
O mejor: Oracle Autonomous Database gratis (2 bases de 20 GB, con respaldo incluido) + la app en la VM.
- HTTPS sin pagar dominio: subdominio gratuito tipo estila-piloto.duckdns.org (DuckDNS) 
+ Caddy como proxy (certificado Let's Encrypt automático). Funciona para probar, incluida 
la futura conexión con WhatsApp Cloud/SIFEN que exige HTTPS pública.
- Dominio propio (recomendado al salir a clientes reales, ~USD 12/año un .com 
o el .com.py en NIC-PY): lo apuntás a la VM y Caddy hace el resto.
- Respaldos (RNF08): pg_dump diario por cron hacia Object Storage de Oracle (10 GB gratis).
