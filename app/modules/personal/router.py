from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.tenant import require_roles
from app.db import models
from app.db.session import auth_mode, get_db, set_rls_tenant
from app.modules.personal.schemas import PersonalCreate, PersonalOut

router = APIRouter(prefix="/personal", tags=["personal"])


def _out(u: models.UsuarioPersonal) -> PersonalOut:
    return PersonalOut(
        id=u.id, nombre=u.nombre, email=u.email, rol=u.rol,
        comision_default_pct=float(u.comision_default_pct),
    )


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
