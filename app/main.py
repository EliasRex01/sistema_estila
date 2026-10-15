from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db.init_db import init_db
from app.modules.auth.router import router as auth_router
from app.modules.chatbot.router import router as chat_router
from app.modules.clientes.router import router as clientes_router
from app.modules.notificaciones.router import router as notif_router
from app.modules.personal.router import router as personal_router
from app.modules.servicios.router import router as servicios_router
from app.modules.tenants.router import router as tenants_router
from app.modules.turnos.router import router as turnos_router
from app.web.router import router as web_router

app = FastAPI(title="Estila SaaS Multitenant - Arselia piloto")

init_db()  # dev; prod usar Alembic + sql/rls.sql
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

app.include_router(web_router)
app.include_router(chat_router)
app.include_router(notif_router)

app.include_router(tenants_router)
app.include_router(auth_router)
app.include_router(personal_router)
app.include_router(clientes_router)
app.include_router(servicios_router)
app.include_router(turnos_router)


@app.get("/health")
def health():
    return {"ok": True, "servicio": "estila-mvp"}
