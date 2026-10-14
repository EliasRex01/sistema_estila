from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.tenant import require_roles
from app.db import models
from app.db.session import get_db, set_rls_tenant
from app.modules.servicios.schemas import ServicioCreate, ServicioOut

router = APIRouter(prefix="/servicios", tags=["servicios"])


@router.post("", response_model=ServicioOut)
def crear(body: ServicioCreate, db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN"))):
    set_rls_tenant(db, ctx["tenant_id"])
    s = models.Servicio(tenant_id=ctx["tenant_id"], nombre=body.nombre, duracion_min=body.duracion_min,
                        precio_gs=body.precio_gs, comision_pct=body.comision_pct)
    db.add(s)
    db.commit()
    db.refresh(s)
    return ServicioOut(id=s.id, nombre=s.nombre, duracion_min=s.duracion_min,
                       precio_gs=s.precio_gs, comision_pct=float(s.comision_pct))


@router.get("", response_model=list[ServicioOut])
def listar(db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN", "RECEPCION", "ESTILISTA"))):
    set_rls_tenant(db, ctx["tenant_id"])
    rows = db.query(models.Servicio).filter_by(tenant_id=ctx["tenant_id"]).all()
    return [ServicioOut(id=r.id, nombre=r.nombre, duracion_min=r.duracion_min,
                        precio_gs=r.precio_gs, comision_pct=float(r.comision_pct)) for r in rows]


@router.put("/{sid}", response_model=ServicioOut)
def actualizar(sid: str, body: ServicioCreate, db: Session = Depends(get_db),
               ctx: dict = Depends(require_roles("ADMIN"))):
    set_rls_tenant(db, ctx["tenant_id"])
    s = db.query(models.Servicio).filter_by(id=sid, tenant_id=ctx["tenant_id"]).first()
    if not s:
        raise HTTPException(404, "Servicio no existe")
    s.nombre, s.duracion_min, s.precio_gs, s.comision_pct = \
        body.nombre, body.duracion_min, body.precio_gs, body.comision_pct
    db.commit()
    db.refresh(s)
    return ServicioOut(id=s.id, nombre=s.nombre, duracion_min=s.duracion_min,
                       precio_gs=s.precio_gs, comision_pct=float(s.comision_pct))


@router.delete("/{sid}")
def eliminar(sid: str, db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN"))):
    """Borra solo si no esta referenciado (preserva el historial)."""
    set_rls_tenant(db, ctx["tenant_id"])
    tid = ctx["tenant_id"]
    s = db.query(models.Servicio).filter_by(id=sid, tenant_id=tid).first()
    if not s:
        raise HTTPException(404, "Servicio no existe")
    n_turnos = db.query(models.Turno).filter_by(servicio_id=sid, tenant_id=tid).count()
    n_ventas = db.query(models.VentaDetalle).filter_by(tipo="SERVICIO", ref_id=sid, tenant_id=tid).count()
    if n_turnos or n_ventas:
        raise HTTPException(409, "No se puede eliminar: referenciado en turnos o ventas")
    db.delete(s)
    db.commit()
    return {"ok": True, "id": sid}
