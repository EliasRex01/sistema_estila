from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db, set_rls_tenant
from app.modules.chatbot import service as chat
from app.web.deps import ui_ctx

router = APIRouter(tags=["chat"])


class ChatIn(BaseModel):
    cid: str = Field(min_length=3, max_length=100)
    texto: str = Field(min_length=1, max_length=500)


class ChatOut(BaseModel):
    respuesta: str


@router.post("/chat/mensaje", response_model=ChatOut)
def mensaje(body: ChatIn, request: Request, db: Session = Depends(get_db)):
    # Demo del canal cliente: usa el tenant del personal logueado.
    ctx = ui_ctx(request)
    if not ctx:
        from fastapi import HTTPException
        raise HTTPException(401, "Inicia sesion para usar el asistente demo")
    set_rls_tenant(db, ctx["tenant_id"])
    s = db.query(models.ChatSesion).filter_by(tenant_id=ctx["tenant_id"], identificador=body.cid).first()
    if not s:
        s = models.ChatSesion(tenant_id=ctx["tenant_id"], identificador=body.cid)
        db.add(s)
        db.commit()
        db.refresh(s)
    return ChatOut(respuesta=chat.procesar(db, models, s, body.texto))


@router.get("/chat/historial")
def historial(cid: str, request: Request, db: Session = Depends(get_db)):
    ctx = ui_ctx(request)
    if not ctx:
        from fastapi import HTTPException
        raise HTTPException(401, "Inicia sesion para usar el asistente demo")
    set_rls_tenant(db, ctx["tenant_id"])
    s = db.query(models.ChatSesion).filter_by(tenant_id=ctx["tenant_id"], identificador=cid).first()
    if not s:
        return {"mensajes": []}
    msgs = db.query(models.ChatMensaje).filter_by(sesion_id=s.id).order_by(models.ChatMensaje.created_at).all()[-20:]
    return {"mensajes": [{"rol": m.rol, "texto": m.texto} for m in msgs]}
