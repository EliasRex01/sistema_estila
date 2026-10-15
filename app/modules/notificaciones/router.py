from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.tenant import require_roles
from app.db import models
from app.db.session import get_db, set_rls_tenant

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


def _fila(n: models.Notificacion, db: Session, tid: str) -> dict:
    t = db.query(models.Turno).filter_by(id=n.turno_id, tenant_id=tid).first()
    cli = db.query(models.Cliente).filter_by(id=t.cliente_id, tenant_id=tid).first() if t else None
    ini = t.inicio.replace(tzinfo=None).strftime("%d/%m %H:%M") if t and t.inicio else "?"
    prog = n.programada_para.replace(tzinfo=None).strftime("%d/%m %H:%M") if n.programada_para else "?"
    return {"id": n.id, "cliente": cli.nombre if cli else "?", "turno": ini,
            "programada": prog, "estado": n.estado, "canal": n.canal, "detalle": n.detalle}


@router.get("")
def listar(db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN", "RECEPCION"))):
    set_rls_tenant(db, ctx["tenant_id"])
    rows = db.query(models.Notificacion).filter_by(tenant_id=ctx["tenant_id"]).order_by(
        models.Notificacion.programada_para).all()
    return [_fila(n, db, ctx["tenant_id"]) for n in rows]


@router.post("/{nid}/enviar")
def enviar(nid: str, db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN", "RECEPCION"))):
    set_rls_tenant(db, ctx["tenant_id"])
    n = db.query(models.Notificacion).filter_by(id=nid, tenant_id=ctx["tenant_id"]).first()
    if not n:
        raise HTTPException(404, "Notificacion no existe")
    if n.estado != "PENDIENTE":
        raise HTTPException(409, f"Ya esta {n.estado}")
    n.estado = "ENVIADA"
    n.detalle = (n.detalle + " | Enviada desde el centro (demo)").strip(" |")[:255]
    db.commit()
    return {"ok": True, "id": nid}
