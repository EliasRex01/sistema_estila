# Despliegue en Vercel (entorno de pruebas)

La app corre en Vercel como función serverless (`api/index.py` + `vercel.json`).
Ojo: en serverless **no se puede usar SQLite** (el disco es efímero y los datos
se pierden) → se usa Postgres externo (Neon, capa gratuita).

## 1. Crear la base de datos (Neon, gratis)

1. Entrar a https://neon.tech y crear proyecto `estila`.
2. Copiar la cadena de conexión (termina en `?sslmode=require`).

## 2. Crear el esquema una sola vez (desde tu PC)

```powershell
cd C:\Users\Desarrollo\sistema_estila
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL="postgresql+psycopg2://USUARIO:CLAVE@HOST/estila?sslmode=require"
.\.venv\Scripts\python.exe -c "from app.db.init_db import init_db; init_db()"
```

Luego aplicar `sql/rls.sql` con cualquier cliente Postgres (psql, DBeaver)
conectado a Neon. Esto activa el aislamiento por tenant (RNF02).

## 3. Importar en Vercel

1. Entrar a https://vercel.com → Add New → Project → importar
   `EliasRex01/sistema_estila`.
2. Framework Preset: Other. Root Directory: `./`.
3. Variables de entorno (Settings → Environment Variables):
   - `DATABASE_URL` = la cadena de Neon (misma del paso 2)
   - `JWT_SECRET` = una clave larga de 32+ caracteres (¡no usar la de ejemplo!)
   - `MASTER_KEY` = otra clave larga para cifrado de secretos SIFEN
4. Deploy. La URL queda tipo `https://sistema-estila.vercel.app`.

## 4. Probar

Abrir la URL → login → panel. Primer paso: `POST /tenants` en
`/docs` para crear el tenant piloto (o pedirlo al admin).

## Límites conocidos (plan Hobby, solo pruebas)

- Arranque en frío: la primera petición tarda unos segundos.
- Timeout 10 s por petición (suficiente para el MVP actual).
- Sin tareas de fondo: recordatorios WhatsApp/SIFEN futuros van en otro servicio.
- SQLite local (`estila.db`) sigue valiendo solo para desarrollo en tu PC.

## Por qué no GitHub Pages

Pages solo publica archivos estáticos (HTML/CSS/JS): no ejecuta Python ni
bases de datos, así que este sistema no puede correr ahí. Si algún día se
quiere una portada estática en Pages, el API igual debe vivir en Vercel/Render.
