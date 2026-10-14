"""Interfaz web Estila: login + menu por rol + paginas (RF02: acceso segun rol)."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db import models
from app.db.session import auth_mode, get_db, set_rls_tenant
from app.modules.clientes.service import validar_ci_ruc_py
from app.modules.turnos.service import calcular_fin, validar_no_solapamiento
from app.web.deps import menu_para, ui_ctx

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def shell(db: Session, ctx: dict) -> dict:
    u = db.query(models.UsuarioPersonal).filter_by(id=ctx["user_id"]).first()
    t = db.query(models.Tenant).filter_by(id=ctx["tenant_id"]).first()
    return {
        "ctx": ctx,
        "usuario": u,
        "tenant_nombre": t.razon_social if t else "",
        "menu": menu_para(ctx["rol"]),
    }


def exigir(request: Request, *roles: str):
    ctx = ui_ctx(request)
    if not ctx:
        return None, RedirectResponse("/login", status_code=302)
    if roles and ctx["rol"] not in roles:
        return None, RedirectResponse("/panel", status_code=302)
    return ctx, None


@router.get("/")
def raiz(request: Request):
    return RedirectResponse("/panel" if ui_ctx(request) else "/login", status_code=302)


@router.get("/login")
def login_get(request: Request, error: str = ""):
    if ui_ctx(request):
        return RedirectResponse("/panel", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": error, "tenant_nombre": "Arselia", "menu": [], "usuario": None, "ctx": {}})


@router.post("/login")
def login_post(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    with auth_mode(db):
        u = db.query(models.UsuarioPersonal).filter_by(email=email.strip(), activo=1).first()
    if not u or not verify_password(password, u.password_hash):
        return RedirectResponse("/login?error=Correo+o+contrase%C3%B1a+inv%C3%A1lidos", status_code=302)
    r = RedirectResponse("/panel", status_code=302)
    r.set_cookie("estila_token", create_access_token(sub=u.id, tenant_id=u.tenant_id, rol=u.rol), httponly=True, path="/")
    return r


@router.get("/logout")
def logout():
    r = RedirectResponse("/login", status_code=302)
    r.delete_cookie("estila_token", path="/")
    return r


@router.get("/panel")
def panel(request: Request, db: Session = Depends(get_db)):
    ctx, red = exigir(request)
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    return templates.TemplateResponse(request, "panel.html", shell(db, ctx))


# --- Personal (ADMIN) ---
@router.get("/ui/personal")
def personal_get(request: Request, db: Session = Depends(get_db), error: str = ""):
    ctx, red = exigir(request, "ADMIN")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    filas = db.query(models.UsuarioPersonal).filter_by(tenant_id=ctx["tenant_id"]).all()
    return templates.TemplateResponse(request, "personal.html", {**shell(db, ctx), "filas": filas, "error": error})


@router.post("/ui/personal")
def personal_post(
    request: Request, nombre: str = Form(...), email: str = Form(...), password: str = Form(...),
    rol: str = Form(...), comision_default_pct: float = Form(0), db: Session = Depends(get_db),
):
    ctx, red = exigir(request, "ADMIN")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    if rol not in ("ADMIN", "RECEPCION", "ESTILISTA") or len(password) < 8:
        return RedirectResponse("/ui/personal?error=Datos+inv%C3%A1lidos+(rol+o+clave+corta)", status_code=302)
    if db.query(models.UsuarioPersonal).filter_by(email=email.strip()).first():
        return RedirectResponse("/ui/personal?error=Correo+ya+existe", status_code=302)
    db.add(models.UsuarioPersonal(tenant_id=ctx["tenant_id"], nombre=nombre.strip(), email=email.strip(),
                                  password_hash=hash_password(password), rol=rol, comision_default_pct=comision_default_pct))
    db.commit()
    return RedirectResponse("/ui/personal", status_code=302)


# --- Clientes ---
@router.get("/ui/clientes")
def clientes_get(request: Request, db: Session = Depends(get_db), error: str = ""):
    ctx, red = exigir(request, "ADMIN", "RECEPCION")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    filas = db.query(models.Cliente).filter_by(tenant_id=ctx["tenant_id"]).order_by(models.Cliente.nombre).all()
    return templates.TemplateResponse(request, "clientes.html",
                                      {**shell(db, ctx), "filas": filas, "titulo": "Clientes", "puede_crear": True, "error": error})


@router.post("/ui/clientes")
def clientes_post(request: Request, nombre: str = Form(...), ci_ruc: str = Form(""), telefono: str = Form(""),
                  direccion: str = Form(""), db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN", "RECEPCION")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    try:
        ci = validar_ci_ruc_py(ci_ruc)
    except ValueError as e:
        return RedirectResponse(f"/ui/clientes?error={e}", status_code=302)
    db.add(models.Cliente(tenant_id=ctx["tenant_id"], nombre=nombre.strip(), ci_ruc=ci, telefono=telefono.strip(), direccion=direccion.strip()))
    db.commit()
    return RedirectResponse("/ui/clientes", status_code=302)


@router.get("/ui/clientes/sin-turno")
def sin_turno(request: Request, db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN", "RECEPCION")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    ahora = datetime.now()
    sub = db.query(models.Turno.cliente_id).filter(
        models.Turno.tenant_id == ctx["tenant_id"], models.Turno.inicio >= ahora,
        models.Turno.estado.in_(["RESERVADO", "CONFIRMADO"])).subquery()
    filas = db.query(models.Cliente).filter(models.Cliente.tenant_id == ctx["tenant_id"], ~models.Cliente.id.in_(sub)).all()
    return templates.TemplateResponse(request, "clientes.html",
                                      {**shell(db, ctx), "filas": filas, "titulo": "Clientes sin turno (seguimiento)", "puede_crear": False, "error": ""})


# --- Servicios ---
@router.get("/ui/servicios")
def servicios_get(request: Request, db: Session = Depends(get_db), error: str = ""):
    ctx, red = exigir(request, "ADMIN", "RECEPCION", "ESTILISTA")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    filas = db.query(models.Servicio).filter_by(tenant_id=ctx["tenant_id"]).all()
    return templates.TemplateResponse(request, "servicios.html",
                                      {**shell(db, ctx), "filas": filas, "puede_crear": ctx["rol"] == "ADMIN", "error": error})


@router.post("/ui/servicios")
def servicios_post(request: Request, nombre: str = Form(...), duracion_min: int = Form(30),
                   precio_gs: int = Form(0), comision_pct: float = Form(0), db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    db.add(models.Servicio(tenant_id=ctx["tenant_id"], nombre=nombre.strip(), duracion_min=duracion_min,
                           precio_gs=precio_gs, comision_pct=comision_pct))
    db.commit()
    return RedirectResponse("/ui/servicios", status_code=302)


# --- Turnos ---
def _turnos_filas(db: Session, ctx: dict):
    q = db.query(models.Turno).filter_by(tenant_id=ctx["tenant_id"]).order_by(models.Turno.inicio)
    if ctx["rol"] == "ESTILISTA":
        q = q.filter_by(profesional_id=ctx["user_id"])
    nombres_c = {c.id: c.nombre for c in db.query(models.Cliente).filter_by(tenant_id=ctx["tenant_id"]).all()}
    nombres_p = {p.id: p.nombre for p in db.query(models.UsuarioPersonal).filter_by(tenant_id=ctx["tenant_id"]).all()}
    nombres_s = {s.id: s.nombre for s in db.query(models.Servicio).filter_by(tenant_id=ctx["tenant_id"]).all()}
    return [{"id": t.id, "inicio": t.inicio.strftime("%d/%m/%Y %H:%M"), "cliente": nombres_c.get(t.cliente_id, "?"),
             "profesional": nombres_p.get(t.profesional_id, "?"), "servicio": nombres_s.get(t.servicio_id, "?"),
             "estado": t.estado} for t in q.all()]


@router.get("/ui/turnos")
def turnos_get(request: Request, db: Session = Depends(get_db), error: str = ""):
    ctx, red = exigir(request, "ADMIN", "RECEPCION", "ESTILISTA")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    base = {**shell(db, ctx), "filas": _turnos_filas(db, ctx), "error": error,
            "titulo": "Mi agenda" if ctx["rol"] == "ESTILISTA" else "Turnos",
            "puede_gestionar": ctx["rol"] in ("ADMIN", "RECEPCION")}
    if base["puede_gestionar"]:
        base.update({
            "clientes": db.query(models.Cliente).filter_by(tenant_id=ctx["tenant_id"]).all(),
            "profesionales": db.query(models.UsuarioPersonal).filter_by(tenant_id=ctx["tenant_id"]).all(),
            "servicios": db.query(models.Servicio).filter_by(tenant_id=ctx["tenant_id"]).all(),
        })
    return templates.TemplateResponse(request, "turnos.html", base)


@router.post("/ui/turnos")
def turnos_post(request: Request, cliente_id: str = Form(...), profesional_id: str = Form(...),
                servicio_id: str = Form(...), inicio: str = Form(...), db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN", "RECEPCION")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    tid = ctx["tenant_id"]
    try:
        ini = datetime.fromisoformat(inicio)
    except ValueError:
        return RedirectResponse("/ui/turnos?error=Fecha+inv%C3%A1lida", status_code=302)
    serv = db.query(models.Servicio).filter_by(id=servicio_id, tenant_id=tid).first()
    if not serv or not db.query(models.Cliente).filter_by(id=cliente_id, tenant_id=tid).first() \
            or not db.query(models.UsuarioPersonal).filter_by(id=profesional_id, tenant_id=tid).first():
        return RedirectResponse("/ui/turnos?error=Cliente,+profesional+o+servicio+inv%C3%A1lido", status_code=302)
    fin = calcular_fin(ini, serv.duracion_min)
    ocupados = db.query(models.Turno.inicio, models.Turno.fin).filter(
        models.Turno.tenant_id == tid, models.Turno.profesional_id == profesional_id,
        models.Turno.estado.in_(["RESERVADO", "CONFIRMADO", "BLOQUEADO"])).all()
    try:
        validar_no_solapamiento([(i, f) for i, f in ocupados], ini, fin)
    except ValueError as e:
        return RedirectResponse(f"/ui/turnos?error={e}", status_code=302)
    db.add(models.Turno(tenant_id=tid, cliente_id=cliente_id, profesional_id=profesional_id,
                        servicio_id=servicio_id, inicio=ini, fin=fin, canal="MOSTRADOR"))
    db.commit()
    return RedirectResponse("/ui/turnos", status_code=302)


@router.post("/ui/turnos/{turno_id}/cancelar")
def turno_cancelar(request: Request, turno_id: str, motivo: str = Form(...), db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN", "RECEPCION")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    t = db.query(models.Turno).filter_by(id=turno_id, tenant_id=ctx["tenant_id"]).first()
    if not t:
        return RedirectResponse("/ui/turnos?error=Turno+no+existe", status_code=302)
    t.estado = "CANCELADO"
    t.motivo_cancelacion = motivo.strip()
    db.commit()
    return RedirectResponse("/ui/turnos", status_code=302)
