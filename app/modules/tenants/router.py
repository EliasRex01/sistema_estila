from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db import models
from app.db.session import get_db
from app.modules.tenants.schemas import TenantCreate, TenantOut
from app.modules.tenants.service import validar_ruc_py

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantOut)
def crear_tenant(body: TenantCreate, db: Session = Depends(get_db)):
    try:
        ruc = validar_ruc_py(body.ruc)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if db.query(models.Tenant).filter_by(ruc=ruc).first():
        raise HTTPException(409, "RUC ya registrado")
    t = models.Tenant(ruc=ruc, razon_social=body.razon_social, timbrado=body.timbrado)
    db.add(t)
    db.flush()  # obtiene t.id
    if db.query(models.UsuarioPersonal).filter_by(email=body.admin_email).first():
        db.rollback()
        raise HTTPException(409, "Email admin ya existe")
    admin = models.UsuarioPersonal(
        tenant_id=t.id,
        nombre=body.admin_nombre,
        email=body.admin_email,
        password_hash=hash_password(body.admin_password),
        rol="ADMIN",
    )
    db.add(admin)
    db.commit()
    db.refresh(t)
    return TenantOut(id=t.id, ruc=t.ruc, razon_social=t.razon_social, estado=t.estado)


@router.get("", response_model=list[TenantOut])
def listar(db: Session = Depends(get_db)):
    # TODO: restringir a superadmin cuando exista ese rol
    rows = db.query(models.Tenant).all()
    return [TenantOut(id=r.id, ruc=r.ruc, razon_social=r.razon_social, estado=r.estado) for r in rows]
