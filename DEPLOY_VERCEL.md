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
