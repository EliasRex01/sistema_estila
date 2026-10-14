"""Entrada serverless para Vercel: adapta la app FastAPI a la funcion Python."""

from mangum import Mangum

from app.main import app

# lifespan off: en serverless no hay arranque persistente; init_db() ya corre al importar.
handler = Mangum(app, lifespan="off")
