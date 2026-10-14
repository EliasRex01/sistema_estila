from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.tenant import require_roles
from app.db import models
from app.db.session import auth_mode, get_db, set_rls_tenant
from app.modules.personal.schemas import PersonalCreate, PersonalOut, PersonalUpdate

router = APIRouter(prefix="/personal", tags=["personal"])


def _out(u: models.UsuarioPersonal) -> PersonalOut:
    return PersonalOut(
        id=u.id, nombre=u.nombre, email=u.email, rol=u.rol,
        comision_default_pct=float(u.comision_default_pct), activo=u.activo,
    )


def _es_ultimo_admin(db: Session, tid: str, target: models.UsuarioPersonal) -> bool:
    """El tenant no puede quedarse sin ADMIN activo."""
    if target.rol != "ADMIN" or not target.activo:
        return False
    otros = db.query(models.UsuarioPersonal).filter(
        models.UsuarioPersonal.tenant_id == tid, models.UsuarioPersonal.rol == "ADMIN",
        models.UsuarioPersonal.activo == 1, models.UsuarioPersonal.id != target.id).count()
    return otros == 0


@router.post("", response_model=PersonalOut)
def crear(
    body: PersonalCreate,
    db: Session = Depends(get_db),
    ctx: dict = Depends(require_roles("ADMIN")),
):
    set_rls_tenant(db, ctx["tenant_id"])
    # Unicidad global de email (el login no conoce el tenant todavia).
    with auth_mode(db):
        if db.query(models.UsuarioPersonal).filter_by(email=body.email).first():
            raise HTTPException(409, "Email ya existe")
    u = models.UsuarioPersonal(
        tenant_id=ctx["tenant_id"], nombre=body.nombre, email=body.email,
        password_hash=hash_password(body.password), rol=body.rol,
        comision_default_pct=body.comision_default_pct,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return _out(u)


@router.get("", response_model=list[PersonalOut])
def listar(db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN", "RECEPCION"))):
    set_rls_tenant(db, ctx["tenant_id"])
    rows = db.query(models.UsuarioPersonal).filter_by(tenant_id=ctx["tenant_id"]).all()
    return [_out(r) for r in rows]


@router.put("/{uid}", response_model=PersonalOut)
def actualizar(uid: str, body: PersonalUpdate, db: Session = Depends(get_db),
               ctx: dict = Depends(require_roles("ADMIN"))):
    set_rls_tenant(db, ctx["tenant_id"])
    u = db.query(models.UsuarioPersonal).filter_by(id=uid, tenant_id=ctx["tenant_id"]).first()
    if not u:
        raise HTTPException(404, "Personal no existe")
    if body.email != u.email:
        with auth_mode(db):
            if db.query(models.UsuarioPersonal).filter_by(email=body.email).first():
                raise HTTPException(409, "Email ya existe")
    pierde_admin = (u.rol == "ADMIN" and (body.rol != "ADMIN" or body.activo == 0))
    if pierde_admin and _es_ultimo_admin(db, ctx["tenant_id"], u):
        raise HTTPException(409, "No se puede quitar el ultimo ADMIN del negocio")
    if u.id == ctx["user_id"] and body.activo == 0:
        raise HTTPException(409, "No puedes desactivar tu propio usuario")
    if body.password:
        if len(body.password) < 8:
            raise HTTPException(400, "Clave minima de 8 caracteres")
        u.password_hash = hash_password(body.password)
    u.nombre, u.email, u.rol = body.nombre, body.email, body.rol
    u.comision_default_pct, u.activo = body.comision_default_pct, body.activo
    db.commit()
    db.refresh(u)
    return _out(u)


@router.delete("/{uid}", response_model=PersonalOut)
def eliminar(uid: str, db: Session = Depends(get_db), ctx: dict = Depends(require_roles("ADMIN"))):
    """Baja logica (activo=0): preserva el historial de turnos."""
    set_rls_tenant(db, ctx["tenant_id"])
    u = db.query(models.UsuarioPersonal).filter_by(id=uid, tenant_id=ctx["tenant_id"]).first()
    if not u:
        raise HTTPException(404, "Personal no existe")
    if _es_ultimo_admin(db, ctx["tenant_id"], u):
        raise HTTPException(409, "No se puede quitar el ultimo ADMIN del negocio")
    if u.id == ctx["user_id"]:
        raise HTTPException(409, "No puedes desactivar tu propio usuario")
    u.activo = 0
    db.commit()
    db.refresh(u)
    return _out(u)
