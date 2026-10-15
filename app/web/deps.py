"""Sesion web por cookie (el API sigue con Bearer). Lee el mismo JWT."""

from fastapi import Request

from app.core.security import decode_access_token


def ui_ctx(request: Request) -> dict | None:
    token = request.cookies.get("estila_token")
    if not token:
        return None
    try:
        p = decode_access_token(token)
        return {"user_id": p.get("sub"), "tenant_id": p.get("tenant_id"), "rol": p.get("rol")}
    except Exception:
        return None


def menu_para(rol: str) -> list[tuple[str, str]]:
    if rol == "ADMIN":
        return [
            ("Personal", "/ui/personal"),
            ("Clientes", "/ui/clientes"),
            ("Servicios", "/ui/servicios"),
            ("Turnos", "/ui/turnos"),
            ("Sin turno", "/ui/clientes/sin-turno"),
            ("Notificaciones", "/ui/notificaciones"),
        ]
    if rol == "RECEPCION":
        return [("Turnos", "/ui/turnos"), ("Clientes", "/ui/clientes"), ("Sin turno", "/ui/clientes/sin-turno"),
                ("Notificaciones", "/ui/notificaciones")]
    return [("Mi agenda", "/ui/turnos"), ("Servicios", "/ui/servicios")]
