from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.tenant import require_roles
from app.db import models
from app.db.session import get_db, set_rls_tenant
from app.modules.clientes.schemas import ClienteCreate, ClienteOut
from app.modules.clientes.service import validar_ci_ruc_py

router = APIRouter(prefix="/clientes", tags=["clientes"])


def _out(c: models.Cliente) -> ClienteOut:
    # Oracle convierte '' en NULL: normalizar al responder.
    return ClienteOut(id=c.id, nombre=c.nombre or "", ci_ruc=c.ci_ruc or "", telefono=c.telefono or "",
                      direccion=c.direccion or "", ficha_json=c.ficha_json or "{}", n_visitas=c.n_visitas)


@router.post("", response_model=ClienteOut)
def crear(body: ClienteCreate, db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN", "RECEPCION"))):
    set_rls_tenant(db, ctx["tenant_id"])
    try:
        ci = validar_ci_ruc_py(body.ci_ruc)
    except ValueError as e:
        raise HTTPException(400, str(e))
    c = models.Cliente(tenant_id=ctx["tenant_id"], nombre=body.nombre, ci_ruc=ci,
                       telefono=body.telefono, direccion=body.direccion, ficha_json=body.ficha_json)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _out(c)


@router.get("", response_model=list[ClienteOut])
def listar(db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN", "RECEPCION", "ESTILISTA"))):
    set_rls_tenant(db, ctx["tenant_id"])
    rows = db.query(models.Cliente).filter_by(tenant_id=ctx["tenant_id"]).order_by(models.Cliente.nombre).all()
    return [_out(r) for r in rows]


@router.get("/sin-turno", response_model=list[ClienteOut])
def sin_turno(db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN", "RECEPCION"))):
    """RF09: clientes sin turno futuro agendado (seguimiento)."""
    from datetime import datetime, timezone
    set_rls_tenant(db, ctx["tenant_id"])
    ahora = datetime.now(timezone.utc)
    sub = db.query(models.Turno.cliente_id).filter(
        models.Turno.tenant_id == ctx["tenant_id"],
        models.Turno.inicio >= ahora,
        models.Turno.estado.in_(["RESERVADO", "CONFIRMADO"]),
    ).subquery()
    rows = db.query(models.Cliente).filter(
        models.Cliente.tenant_id == ctx["tenant_id"], ~models.Cliente.id.in_(sub)
    ).all()
    return [_out(r) for r in rows]


@router.put("/{cid}", response_model=ClienteOut)
def actualizar(cid: str, body: ClienteCreate, db: Session = Depends(get_db),
               ctx: dict = Depends(require_roles("ADMIN", "RECEPCION"))):
    set_rls_tenant(db, ctx["tenant_id"])
    c = db.query(models.Cliente).filter_by(id=cid, tenant_id=ctx["tenant_id"]).first()
    if not c:
        raise HTTPException(404, "Cliente no existe")
    try:
        ci = validar_ci_ruc_py(body.ci_ruc)
    except ValueError as e:
        raise HTTPException(400, str(e))
    c.nombre, c.ci_ruc, c.telefono, c.direccion, c.ficha_json = \
        body.nombre, ci, body.telefono, body.direccion, body.ficha_json
    db.commit()
    db.refresh(c)
    return _out(c)


@router.delete("/{cid}")
def eliminar(cid: str, db: Session = Depends(get_db),
             ctx: dict = Depends(require_roles("ADMIN", "RECEPCION"))):
    """Borra solo si no tiene turnos (preserva el historial)."""
    set_rls_tenant(db, ctx["tenant_id"])
    c = db.query(models.Cliente).filter_by(id=cid, tenant_id=ctx["tenant_id"]).first()
    if not c:
        raise HTTPException(404, "Cliente no existe")
    n = db.query(models.Turno).filter_by(cliente_id=cid, tenant_id=ctx["tenant_id"]).count()
    if n:
        raise HTTPException(409, f"No se puede eliminar: tiene {n} turno(s) en el historial")
    db.delete(c)
    db.commit()
    return {"ok": True, "id": cid}
