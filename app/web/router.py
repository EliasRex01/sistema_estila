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
    with auth_mode(db):
        if db.query(models.UsuarioPersonal).filter_by(email=email.strip()).first():
            return RedirectResponse("/ui/personal?error=Correo+ya+existe", status_code=302)
    db.add(models.UsuarioPersonal(tenant_id=ctx["tenant_id"], nombre=nombre.strip(), email=email.strip(),
                                  password_hash=hash_password(password), rol=rol, comision_default_pct=comision_default_pct))
    db.commit()
    return RedirectResponse("/ui/personal", status_code=302)


def _ultimo_admin(db: Session, tid: str, target: models.UsuarioPersonal) -> bool:
    if target.rol != "ADMIN" or not target.activo:
        return False
    otros = db.query(models.UsuarioPersonal).filter(
        models.UsuarioPersonal.tenant_id == tid, models.UsuarioPersonal.rol == "ADMIN",
        models.UsuarioPersonal.activo == 1, models.UsuarioPersonal.id != target.id).count()
    return otros == 0


@router.get("/ui/personal/{uid}/editar")
def personal_editar(request: Request, uid: str, db: Session = Depends(get_db), error: str = ""):
    ctx, red = exigir(request, "ADMIN")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    u = db.query(models.UsuarioPersonal).filter_by(id=uid, tenant_id=ctx["tenant_id"]).first()
    if not u:
        return RedirectResponse("/ui/personal?error=Personal+no+existe", status_code=302)
    return templates.TemplateResponse(request, "editar_personal.html", {**shell(db, ctx), "u": u, "error": error})


@router.post("/ui/personal/{uid}/guardar")
def personal_guardar(
    request: Request, uid: str, nombre: str = Form(...), email: str = Form(...), rol: str = Form(...),
    comision_default_pct: float = Form(0), activo: int = Form(1), password: str = Form(""),
    db: Session = Depends(get_db),
):
    ctx, red = exigir(request, "ADMIN")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    u = db.query(models.UsuarioPersonal).filter_by(id=uid, tenant_id=ctx["tenant_id"]).first()
    if not u:
        return RedirectResponse("/ui/personal?error=Personal+no+existe", status_code=302)
    if rol not in ("ADMIN", "RECEPCION", "ESTILISTA"):
        return RedirectResponse(f"/ui/personal/{uid}/editar?error=Rol+inv%C3%A1lido", status_code=302)
    if email.strip() != u.email:
        with auth_mode(db):
            if db.query(models.UsuarioPersonal).filter_by(email=email.strip()).first():
                return RedirectResponse(f"/ui/personal/{uid}/editar?error=Correo+ya+existe", status_code=302)
    if u.rol == "ADMIN" and (rol != "ADMIN" or activo == 0) and _ultimo_admin(db, ctx["tenant_id"], u):
        return RedirectResponse(f"/ui/personal/{uid}/editar?error=No+se+puede+quitar+el+ultimo+ADMIN", status_code=302)
    if u.id == ctx["user_id"] and activo == 0:
        return RedirectResponse(f"/ui/personal/{uid}/editar?error=No+puedes+desactivar+tu+propio+usuario", status_code=302)
    if password:
        if len(password) < 8:
            return RedirectResponse(f"/ui/personal/{uid}/editar?error=Clave+minima+de+8", status_code=302)
        u.password_hash = hash_password(password)
    u.nombre, u.email, u.rol = nombre.strip(), email.strip(), rol
    u.comision_default_pct, u.activo = comision_default_pct, activo
    db.commit()
    return RedirectResponse("/ui/personal", status_code=302)


@router.post("/ui/personal/{uid}/eliminar")
def personal_eliminar(request: Request, uid: str, db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    u = db.query(models.UsuarioPersonal).filter_by(id=uid, tenant_id=ctx["tenant_id"]).first()
    if not u:
        return RedirectResponse("/ui/personal?error=Personal+no+existe", status_code=302)
    if _ultimo_admin(db, ctx["tenant_id"], u):
        return RedirectResponse("/ui/personal?error=No+se+puede+quitar+el+ultimo+ADMIN", status_code=302)
    if u.id == ctx["user_id"]:
        return RedirectResponse("/ui/personal?error=No+puedes+desactivar+tu+propio+usuario", status_code=302)
    u.activo = 0
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
                                      {**shell(db, ctx), "filas": filas, "titulo": "Clientes", "puede_crear": True, "puede_editar": True, "error": error})


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
                                      {**shell(db, ctx), "filas": filas, "titulo": "Clientes sin turno (seguimiento)", "puede_crear": False, "puede_editar": True, "error": ""})


@router.get("/ui/clientes/{cid}/editar")
def cliente_editar(request: Request, cid: str, db: Session = Depends(get_db), error: str = ""):
    ctx, red = exigir(request, "ADMIN", "RECEPCION")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    c = db.query(models.Cliente).filter_by(id=cid, tenant_id=ctx["tenant_id"]).first()
    if not c:
        return RedirectResponse("/ui/clientes?error=Cliente+no+existe", status_code=302)
    return templates.TemplateResponse(request, "editar_cliente.html", {**shell(db, ctx), "c": c, "error": error})


@router.post("/ui/clientes/{cid}/guardar")
def cliente_guardar(request: Request, cid: str, nombre: str = Form(...), ci_ruc: str = Form(""),
                    telefono: str = Form(""), direccion: str = Form(""), ficha_json: str = Form("{}"),
                    db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN", "RECEPCION")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    c = db.query(models.Cliente).filter_by(id=cid, tenant_id=ctx["tenant_id"]).first()
    if not c:
        return RedirectResponse("/ui/clientes?error=Cliente+no+existe", status_code=302)
    try:
        ci = validar_ci_ruc_py(ci_ruc)
    except ValueError as e:
        return RedirectResponse(f"/ui/clientes/{cid}/editar?error={e}", status_code=302)
    c.nombre, c.ci_ruc, c.telefono, c.direccion, c.ficha_json = nombre.strip(), ci, telefono.strip(), direccion.strip(), ficha_json
    db.commit()
    return RedirectResponse("/ui/clientes", status_code=302)


@router.post("/ui/clientes/{cid}/eliminar")
def cliente_eliminar(request: Request, cid: str, db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN", "RECEPCION")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    c = db.query(models.Cliente).filter_by(id=cid, tenant_id=ctx["tenant_id"]).first()
    if not c:
        return RedirectResponse("/ui/clientes?error=Cliente+no+existe", status_code=302)
    n = db.query(models.Turno).filter_by(cliente_id=cid, tenant_id=ctx["tenant_id"]).count()
    if n:
        return RedirectResponse(f"/ui/clientes?error=Tiene+{n}+turno(s)+en+el+historial", status_code=302)
    db.delete(c)
    db.commit()
    return RedirectResponse("/ui/clientes", status_code=302)


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


@router.get("/ui/servicios/{sid}/editar")
def servicio_editar(request: Request, sid: str, db: Session = Depends(get_db), error: str = ""):
    ctx, red = exigir(request, "ADMIN")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    s = db.query(models.Servicio).filter_by(id=sid, tenant_id=ctx["tenant_id"]).first()
    if not s:
        return RedirectResponse("/ui/servicios?error=Servicio+no+existe", status_code=302)
    return templates.TemplateResponse(request, "editar_servicio.html", {**shell(db, ctx), "s": s, "error": error})


@router.post("/ui/servicios/{sid}/guardar")
def servicio_guardar(request: Request, sid: str, nombre: str = Form(...), duracion_min: int = Form(30),
                     precio_gs: int = Form(0), comision_pct: float = Form(0), db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    s = db.query(models.Servicio).filter_by(id=sid, tenant_id=ctx["tenant_id"]).first()
    if not s:
        return RedirectResponse("/ui/servicios?error=Servicio+no+existe", status_code=302)
    s.nombre, s.duracion_min, s.precio_gs, s.comision_pct = nombre.strip(), duracion_min, precio_gs, comision_pct
    db.commit()
    return RedirectResponse("/ui/servicios", status_code=302)


@router.post("/ui/servicios/{sid}/eliminar")
def servicio_eliminar(request: Request, sid: str, db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    tid = ctx["tenant_id"]
    s = db.query(models.Servicio).filter_by(id=sid, tenant_id=tid).first()
    if not s:
        return RedirectResponse("/ui/servicios?error=Servicio+no+existe", status_code=302)
    n = db.query(models.Turno).filter_by(servicio_id=sid, tenant_id=tid).count()
    n += db.query(models.VentaDetalle).filter_by(tipo="SERVICIO", ref_id=sid, tenant_id=tid).count()
    if n:
        return RedirectResponse("/ui/servicios?error=Referenciado+en+turnos+o+ventas", status_code=302)
    db.delete(s)
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
            "profesionales": db.query(models.UsuarioPersonal).filter_by(tenant_id=ctx["tenant_id"], activo=1).all(),
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
    cli = db.query(models.Cliente).filter_by(id=cliente_id, tenant_id=tid).first()
    prof = db.query(models.UsuarioPersonal).filter_by(id=profesional_id, tenant_id=tid).first()
    if not serv or not cli or not prof:
        return RedirectResponse("/ui/turnos?error=Cliente,+profesional+o+servicio+inv%C3%A1lido", status_code=302)
    if not prof.activo:
        return RedirectResponse("/ui/turnos?error=Profesional+inactivo", status_code=302)
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
    if t.estado not in ("RESERVADO", "CONFIRMADO", "BLOQUEADO"):
        return RedirectResponse(f"/ui/turnos?error=No+se+puede+cancelar+un+turno+{t.estado}", status_code=302)
    t.estado = "CANCELADO"
    t.motivo_cancelacion = motivo.strip()
    db.commit()
    return RedirectResponse("/ui/turnos", status_code=302)


@router.get("/ui/turnos/{turno_id}/editar")
def turno_editar(request: Request, turno_id: str, db: Session = Depends(get_db), error: str = ""):
    ctx, red = exigir(request, "ADMIN", "RECEPCION")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    tid = ctx["tenant_id"]
    t = db.query(models.Turno).filter_by(id=turno_id, tenant_id=tid).first()
    if not t:
        return RedirectResponse("/ui/turnos?error=Turno+no+existe", status_code=302)
    if t.estado not in ("RESERVADO", "CONFIRMADO", "BLOQUEADO"):
        return RedirectResponse(f"/ui/turnos?error=No+se+puede+reprogramar+un+turno+{t.estado}", status_code=302)
    ini_local = t.inicio.replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M") if t.inicio else ""
    return templates.TemplateResponse(request, "editar_turno.html", {
        **shell(db, ctx), "t": t, "ini_local": ini_local, "error": error,
        "clientes": db.query(models.Cliente).filter_by(tenant_id=tid).all(),
        "profesionales": db.query(models.UsuarioPersonal).filter_by(tenant_id=tid, activo=1).all(),
        "servicios": db.query(models.Servicio).filter_by(tenant_id=tid).all(),
    })


@router.post("/ui/turnos/{turno_id}/guardar")
def turno_guardar(request: Request, turno_id: str, cliente_id: str = Form(...), profesional_id: str = Form(...),
                  servicio_id: str = Form(...), inicio: str = Form(...), db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN", "RECEPCION")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    tid = ctx["tenant_id"]
    err = f"/ui/turnos/{turno_id}/editar?error="
    t = db.query(models.Turno).filter_by(id=turno_id, tenant_id=tid).first()
    if not t:
        return RedirectResponse("/ui/turnos?error=Turno+no+existe", status_code=302)
    if t.estado not in ("RESERVADO", "CONFIRMADO", "BLOQUEADO"):
        return RedirectResponse(f"/ui/turnos?error=No+se+puede+reprogramar+un+turno+{t.estado}", status_code=302)
    try:
        ini = datetime.fromisoformat(inicio)
    except ValueError:
        return RedirectResponse(err + "Fecha+inv%C3%A1lida", status_code=302)
    serv = db.query(models.Servicio).filter_by(id=servicio_id, tenant_id=tid).first()
    cli = db.query(models.Cliente).filter_by(id=cliente_id, tenant_id=tid).first()
    prof = db.query(models.UsuarioPersonal).filter_by(id=profesional_id, tenant_id=tid).first()
    if not serv or not cli or not prof:
        return RedirectResponse(err + "Cliente,+profesional+o+servicio+inv%C3%A1lido", status_code=302)
    if not prof.activo:
        return RedirectResponse(err + "Profesional+inactivo", status_code=302)
    fin = calcular_fin(ini, serv.duracion_min)
    ocupados = db.query(models.Turno.id, models.Turno.inicio, models.Turno.fin).filter(
        models.Turno.tenant_id == tid, models.Turno.profesional_id == profesional_id,
        models.Turno.estado.in_(["RESERVADO", "CONFIRMADO", "BLOQUEADO"]),
        models.Turno.id != turno_id).all()
    try:
        validar_no_solapamiento([(i, f) for _, i, f in ocupados], ini, fin)
    except ValueError as e:
        return RedirectResponse(err + str(e), status_code=302)
    t.cliente_id, t.profesional_id, t.servicio_id = cliente_id, profesional_id, servicio_id
    t.inicio, t.fin = ini, fin
    db.commit()
    return RedirectResponse("/ui/turnos", status_code=302)


@router.post("/ui/turnos/{turno_id}/atender")
def turno_atender(request: Request, turno_id: str, db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN", "RECEPCION", "ESTILISTA")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    t = db.query(models.Turno).filter_by(id=turno_id, tenant_id=ctx["tenant_id"]).first()
    if not t:
        return RedirectResponse("/ui/turnos?error=Turno+no+existe", status_code=302)
    if ctx["rol"] == "ESTILISTA" and t.profesional_id != ctx["user_id"]:
        return RedirectResponse("/ui/turnos?error=Solo+tu+propia+agenda", status_code=302)
    if t.estado not in ("RESERVADO", "CONFIRMADO"):
        return RedirectResponse(f"/ui/turnos?error=No+se+puede+atender+un+turno+{t.estado}", status_code=302)
    t.estado = "ATENDIDO"
    cli = db.query(models.Cliente).filter_by(id=t.cliente_id, tenant_id=ctx["tenant_id"]).first()
    if cli:
        cli.n_visitas = (cli.n_visitas or 0) + 1
    db.commit()
    return RedirectResponse("/ui/turnos", status_code=302)


@router.post("/ui/turnos/{turno_id}/eliminar")
def turno_eliminar(request: Request, turno_id: str, db: Session = Depends(get_db)):
    ctx, red = exigir(request, "ADMIN", "RECEPCION")
    if red:
        return red
    set_rls_tenant(db, ctx["tenant_id"])
    t = db.query(models.Turno).filter_by(id=turno_id, tenant_id=ctx["tenant_id"]).first()
    if not t:
        return RedirectResponse("/ui/turnos?error=Turno+no+existe", status_code=302)
    if t.estado != "RESERVADO":
        return RedirectResponse("/ui/turnos?error=Solo+se+elimina+un+RESERVADO;+usa+cancelar", status_code=302)
    db.delete(t)
    db.commit()
    return RedirectResponse("/ui/turnos", status_code=302)
