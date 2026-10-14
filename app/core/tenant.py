"""Contexto multitenant: extrae tenant_id y rol desde JWT + header (RF01/RF02/RNF02)."""

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_tenant_context(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> dict:
    """Devuelve {"user_id","tenant_id","rol"}. Exige JWT; si hay header debe coincidir."""
    if cred is None:
        raise HTTPException(status_code=401, detail="Falta token Bearer")
    try:
        payload = decode_access_token(cred.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")
    tenant_jwt = payload.get("tenant_id")
    if x_tenant_id and tenant_jwt != x_tenant_id:
        raise HTTPException(status_code=403, detail="Tenant del header no coincide con token (RNF02)")
    return {"user_id": payload.get("sub"), "tenant_id": tenant_jwt, "rol": payload.get("rol")}


def require_roles(*roles: str):
    def _check(ctx: dict = Depends(get_tenant_context)) -> dict:
        if ctx["rol"] not in roles:
            raise HTTPException(status_code=403, detail="Rol sin permiso")
        return ctx

    return _check
