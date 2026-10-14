from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db import models
from app.db.session import auth_mode, get_db
from app.modules.auth.schemas import LoginIn, LoginOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    with auth_mode(db):
        u = db.query(models.UsuarioPersonal).filter_by(email=body.email, activo=1).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Credenciales invalidas")
    token = create_access_token(sub=u.id, tenant_id=u.tenant_id, rol=u.rol)
    return LoginOut(access_token=token, tenant_id=u.tenant_id, rol=u.rol)
