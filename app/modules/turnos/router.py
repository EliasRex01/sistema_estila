from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.tenant import require_roles
from app.db import models
from app.db.session import get_db, set_rls_tenant
from app.modules.turnos.schemas import TurnoCancelar, TurnoCreate, TurnoOut
from app.modules.turnos.service import calcular_fin, validar_no_solapamiento

router = APIRouter(prefix="/turnos", tags=["turnos"])
ESTADOS_ACTIVOS = ["RESERVADO", "CONFIRMADO", "BLOQUEADO"]


def _out(t: models.Turno) -> TurnoOut:
    return TurnoOut(id=t.id, cliente_id=t.cliente_id, profesional_id=t.profesional_id,
                    servicio_id=t.servicio_id, inicio=t.inicio, fin=t.fin,
                    estado=t.estado, motivo_cancelacion=t.motivo_cancelacion, canal=t.canal)


@router.post("", response_model=TurnoOut)
def crear(body: TurnoCreate, db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN", "RECEPCION"))):
    set_rls_tenant(db, ctx["tenant_id"])
    tid = ctx["tenant_id"]
    # FKs del mismo tenant
    if not db.query(models.Cliente).filter_by(id=body.cliente_id, tenant_id=tid).first():
        raise HTTPException(404, "Cliente no existe en tenant")
    prof = db.query(models.UsuarioPersonal).filter_by(id=body.profesional_id, tenant_id=tid).first()
    if not prof:
        raise HTTPException(404, "Profesional no existe en tenant")
    serv = db.query(models.Servicio).filter_by(id=body.servicio_id, tenant_id=tid).first()
    if not serv:
        raise HTTPException(404, "Servicio no existe en tenant")
    fin = calcular_fin(body.inicio, serv.duracion_min)
    ocupados = db.query(models.Turno.inicio, models.Turno.fin).filter(
        models.Turno.tenant_id == tid, models.Turno.profesional_id == body.profesional_id,
        models.Turno.estado.in_(ESTADOS_ACTIVOS),
    ).all()
    try:
        validar_no_solapamiento([(i, f) for i, f in ocupados], body.inicio, fin)
    except ValueError as e:
        raise HTTPException(409, str(e))
    t = models.Turno(tenant_id=tid, cliente_id=body.cliente_id, profesional_id=body.profesional_id,
                     servicio_id=body.servicio_id, inicio=body.inicio, fin=fin, canal=body.canal)
    db.add(t)
    db.commit()
    db.refresh(t)
    return _out(t)


@router.get("", response_model=list[TurnoOut])
def listar(db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN", "RECEPCION", "ESTILISTA"))):
    set_rls_tenant(db, ctx["tenant_id"])
    rows = db.query(models.Turno).filter_by(tenant_id=ctx["tenant_id"]).order_by(models.Turno.inicio).all()
    # Estilista solo ve su agenda
    if ctx["rol"] == "ESTILISTA":
        rows = [r for r in rows if r.profesional_id == ctx["user_id"]]
    return [_out(r) for r in rows]


@router.post("/{turno_id}/cancelar", response_model=TurnoOut)
def cancelar(turno_id: str, body: TurnoCancelar, db: Session = Depends(get_db),
             ctx: dict = Depends(require_roles("ADMIN", "RECEPCION"))):
    set_rls_tenant(db, ctx["tenant_id"])
    t = db.query(models.Turno).filter_by(id=turno_id, tenant_id=ctx["tenant_id"]).first()
    if not t:
        raise HTTPException(404, "Turno no existe")
    t.estado = "CANCELADO"
    t.motivo_cancelacion = body.motivo
    db.commit()
    db.refresh(t)
    return _out(t)


@router.post("/bloqueo", response_model=TurnoOut)
def bloquear(body: TurnoCreate, db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN", "RECEPCION"))):
    """RF06: bloquea franja (descanso/no disponible) como turno BLOQUEADO sin cliente real."""
    set_rls_tenant(db, ctx["tenant_id"])
    serv = db.query(models.Servicio).filter_by(id=body.servicio_id, tenant_id=ctx["tenant_id"]).first()
    if not serv:
        raise HTTPException(404, "Servicio no existe")
    fin = calcular_fin(body.inicio, serv.duracion_min)
    ocupados = db.query(models.Turno.inicio, models.Turno.fin).filter(
        models.Turno.tenant_id == ctx["tenant_id"], models.Turno.profesional_id == body.profesional_id,
        models.Turno.estado.in_(ESTADOS_ACTIVOS),
    ).all()
    try:
        validar_no_solapamiento([(i, f) for i, f in ocupados], body.inicio, fin)
    except ValueError as e:
        raise HTTPException(409, str(e))
    t = models.Turno(tenant_id=ctx["tenant_id"], cliente_id=body.cliente_id, profesional_id=body.profesional_id,
                     servicio_id=body.servicio_id, inicio=body.inicio, fin=fin, estado="BLOQUEADO", canal=body.canal)
    db.add(t)
    db.commit()
    db.refresh(t)
    return _out(t)
