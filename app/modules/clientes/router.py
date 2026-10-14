from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.tenant import require_roles
from app.db import models
from app.db.session import get_db, set_rls_tenant
from app.modules.clientes.schemas import ClienteCreate, ClienteOut
from app.modules.clientes.service import validar_ci_ruc_py

router = APIRouter(prefix="/clientes", tags=["clientes"])


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
    return ClienteOut(id=c.id, nombre=c.nombre, ci_ruc=c.ci_ruc, telefono=c.telefono,
                      direccion=c.direccion, ficha_json=c.ficha_json, n_visitas=c.n_visitas)


@router.get("", response_model=list[ClienteOut])
def listar(db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN", "RECEPCION", "ESTILISTA"))):
    set_rls_tenant(db, ctx["tenant_id"])
    rows = db.query(models.Cliente).filter_by(tenant_id=ctx["tenant_id"]).order_by(models.Cliente.nombre).all()
    return [ClienteOut(id=r.id, nombre=r.nombre, ci_ruc=r.ci_ruc, telefono=r.telefono,
                       direccion=r.direccion, ficha_json=r.ficha_json, n_visitas=r.n_visitas) for r in rows]


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
    return [ClienteOut(id=r.id, nombre=r.nombre, ci_ruc=r.ci_ruc, telefono=r.telefono,
                       direccion=r.direccion, ficha_json=r.ficha_json, n_visitas=r.n_visitas) for r in rows]
