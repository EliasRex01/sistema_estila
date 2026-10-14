from fastapi import APIRouter, Depends
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
