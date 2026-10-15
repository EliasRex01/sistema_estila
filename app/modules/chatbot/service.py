"""Asistente conversacional Estila (demo del canal WhatsApp, RF07/RF08).

Motor basado en reglas, sin dependencias externas: la misma logica que usara
el adaptador WhatsApp + LLM mas adelante. Funciones puras (testeables sin BD)
+ `procesar()` que opera contra la BD real (turnos, notificaciones).
"""

import json
import re
from datetime import datetime

from app.modules.turnos.service import calcular_fin, validar_no_solapamiento

FECHA_RE = re.compile(r"(\d{1,2})/(\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?")
NUMERO_RE = re.compile(r"^\d{1,2}$")

MENU = ("Puedo ayudarte con: *ver mis turnos*, *confirmar*, *cancelar* o "
        "*cambiar* un turno. ¿Qué necesitas?")


def normalizar(texto: str) -> str:
    return (texto or "").strip().lower()


def detectar_intencion(texto: str) -> tuple[str, str]:
    """Devuelve (intencion, resto). Pura y testeable."""
    t = normalizar(texto)
    if NUMERO_RE.match(t):
        return ("numero", t)
    resto = ""
    for palabra in ("confirmar", "cancelar", "cambiar", "reprogramar", "mover", "posponer"):
        if palabra in t:
            resto = t.replace(palabra, "").strip()
            return ({"confirmar": "confirmar", "cancelar": "cancelar"}.get(palabra, "cambiar"), resto)
    if any(s in t for s in ("mis turnos", "mi turno", "mis citas", "mi cita", "mi reserva", "mis reservas")):
        return ("listar", "")
    if "turno" in t or "cita" in t or "reserva" in t:
        return ("listar", "")
    if any(s in t for s in ("ayuda", "menu", "menú", "opciones", "que puedes", "qué puedes")):
        return ("ayuda", "")
    if any(s in t for s in ("gracias",)):
        return ("gracias", "")
    if any(s in t for s in ("chau", "adios", "adiós", "salir", "hasta luego", "nos vemos")):
        return ("salir", "")
    if any(s in t for s in ("hola", "buenas", "hey", "buen dia", "buen día")) and len(t) < 30:
        return ("saludo", "")
    return ("no_entendido", "")


def parse_fecha(texto: str, ahora: datetime) -> datetime | None:
    """Entiende 'DD/MM HH:MM' (hora obligatoria). Devuelve naive o None."""
    m = FECHA_RE.search(normalizar(texto))
    if not m:
        return None
    dia, mes = int(m.group(1)), int(m.group(2))
    if m.group(3) is None:
        return None
    try:
        dt = datetime(ahora.year, mes, dia, int(m.group(3)), int(m.group(4)))
    except ValueError:
        return None
    return dt if dt > ahora.replace(tzinfo=None) else None


def fmt_turno(i: int, inicio: datetime, servicio: str, profesional: str, estado: str) -> str:
    ini = inicio.replace(tzinfo=None) if getattr(inicio, "tzinfo", None) else inicio
    return f"{i}) {servicio} — {ini.strftime('%d/%m %H:%M')} con {profesional} ({estado})"


def _ctx(sesion) -> dict:
    try:
        return json.loads(sesion.contexto or "{}")
    except ValueError:
        return {}


def _guardar_ctx(sesion, ctx: dict) -> None:
    sesion.contexto = json.dumps(ctx)


def turnos_proximos(db, models, tid: str, cliente_id: str):
    from datetime import datetime as _dt
    ahora = _dt.now()
    return [t for t in db.query(models.Turno).filter_by(
        tenant_id=tid, cliente_id=cliente_id).order_by(models.Turno.inicio).all()
        if t.estado in ("RESERVADO", "CONFIRMADO") and (t.inicio.replace(tzinfo=None) >= ahora)]


def nombres_turno(db, models, tid: str, t) -> tuple[str, str]:
    cli = db.query(models.Cliente).filter_by(id=t.cliente_id, tenant_id=tid).first()
    prof = db.query(models.UsuarioPersonal).filter_by(id=t.profesional_id, tenant_id=tid).first()
    ser = db.query(models.Servicio).filter_by(id=t.servicio_id, tenant_id=tid).first()
    return ((ser.nombre if ser else "?"), (prof.nombre if prof else "?"), (cli.nombre if cli else "?"))


def procesar(db, models, sesion, texto: str) -> str:
    """Un mensaje del cliente -> respuesta del bot (persiste estado y mensajes)."""
    from app.db.session import set_rls_tenant
    set_rls_tenant(db, sesion.tenant_id)
    tid = sesion.tenant_id
    ctx = _ctx(sesion)

    def decir(msg: str) -> str:
        db.add(models.ChatMensaje(tenant_id=tid, sesion_id=sesion.id, rol="bot", texto=msg))
        db.commit()
        return msg

    db.add(models.ChatMensaje(tenant_id=tid, sesion_id=sesion.id, rol="cliente", texto=texto))
    t = normalizar(texto)

    # --- identificacion del cliente ---
    if not sesion.cliente_id:
        if sesion.esperando == "identificacion" or True:
            digitos = re.sub(r"\D", "", t)
            cli = None
            if len(digitos) >= 6:
                cli = db.query(models.Cliente).filter_by(telefono=digitos, tenant_id=tid).first()
                if not cli:
                    cli = db.query(models.Cliente).filter(
                        models.Cliente.tenant_id == tid,
                        models.Cliente.telefono.like(f"%{digitos}%")).first()
            if not cli and len(t) >= 3 and not digitos == t.replace(" ", ""):
                cands = db.query(models.Cliente).filter_by(tenant_id=tid).all()
                cands = [c for c in cands if t in (c.nombre or "").lower()]
                if len(cands) == 1:
                    cli = cands[0]
                elif len(cands) > 1:
                    sesion.esperando = "elegir_cliente"
                    _guardar_ctx(sesion, {"candidatos": [{"id": c.id, "nombre": c.nombre} for c in cands[:5]]})
                    db.commit()
                    ops = ", ".join(f"{i + 1}) {c.nombre}" for i, c in enumerate(cands[:5]))
                    return decir(f"Encontré varios clientes: {ops}. Respondé con el número.")
            if cli:
                sesion.cliente_id = cli.id
                sesion.esperando = ""
                db.commit()
                return decir(_bienvenida(db, models, sesion, cli))
            sesion.esperando = "identificacion"
            db.commit()
            return decir("Hola, soy el asistente de Estila. Para ver tus turnos agendados, "
                         "decime tu número de teléfono o tu nombre y apellido.")

    # --- elegir entre homonimos ---
    if sesion.esperando == "elegir_cliente":
        cands = ctx.get("candidatos", [])
        if t.isdigit() and 1 <= int(t) <= len(cands):
            cli = db.query(models.Cliente).filter_by(id=cands[int(t) - 1]["id"], tenant_id=tid).first()
            if cli:
                sesion.cliente_id = cli.id
                sesion.esperando = ""
                db.commit()
                return decir(_bienvenida(db, models, sesion, cli))
        sesion.esperando = ""
        db.commit()
        return decir("No te encontré. Escribí tu teléfono o avisá en recepción para registrarte. " + MENU)

    # --- cliente ya identificado: flujos con numero o motivo/fecha pendiente ---
    if sesion.esperando in ("elegir_confirmar", "elegir_cancelar", "elegir_cambiar"):
        prox = turnos_proximos(db, models, tid, sesion.cliente_id)
        if t.isdigit() and 1 <= int(t) <= len(prox):
            objetivo = prox[int(t) - 1]
            if sesion.esperando == "elegir_confirmar":
                objetivo.estado = "CONFIRMADO"
                sesion.esperando = ""
                db.commit()
                return decir("Listo, tu turno quedó confirmado. Te esperamos.")
            if sesion.esperando == "elegir_cancelar":
                sesion.esperando = "motivo_cancel"
                _guardar_ctx(sesion, {"turno_id": objetivo.id})
                db.commit()
                return decir("¿Cuál es el motivo de la cancelación? (se registra para mejorar el servicio)")
            sesion.esperando = "nueva_fecha"
            _guardar_ctx(sesion, {"turno_id": objetivo.id})
            db.commit()
            return decir("Escribí la nueva fecha y hora como DD/MM HH:MM (ej. 25/10 15:30).")
        sesion.esperando = ""
        db.commit()
        return decir("Número inválido. " + MENU)

    if sesion.esperando == "motivo_cancel":
        objetivo = db.query(models.Turno).filter_by(id=ctx.get("turno_id"), tenant_id=tid).first()
        if objetivo and objetivo.estado in ("RESERVADO", "CONFIRMADO"):
            objetivo.estado = "CANCELADO"
            objetivo.motivo_cancelacion = f"Chat: {texto.strip()[:200]}"
            from app.modules.notificaciones.service import cancelar_recordatorios
            cancelar_recordatorios(db, objetivo, "Cancelado por el cliente (chat)")
            sesion.esperando = ""
            db.commit()
            return decir("Turno cancelado y motivo registrado. ¡Te esperamos la próxima!")
        sesion.esperando = ""
        db.commit()
        return decir("Ese turno ya no se puede cancelar. " + MENU)

    if sesion.esperando == "nueva_fecha":
        objetivo = db.query(models.Turno).filter_by(id=ctx.get("turno_id"), tenant_id=tid).first()
        ahora = datetime.now()
        nueva = parse_fecha(texto, ahora)
        if not objetivo or not nueva:
            sesion.esperando = ""
            db.commit()
            return decir("Fecha inválida o pasada. Usá el formato DD/MM HH:MM. " + MENU)
        ser = db.query(models.Servicio).filter_by(id=objetivo.servicio_id, tenant_id=tid).first()
        fin = calcular_fin(nueva, ser.duracion_min if ser else 30)
        ocupados = db.query(models.Turno.id, models.Turno.inicio, models.Turno.fin).filter(
            models.Turno.tenant_id == tid, models.Turno.profesional_id == objetivo.profesional_id,
            models.Turno.estado.in_(["RESERVADO", "CONFIRMADO", "BLOQUEADO"]),
            models.Turno.id != objetivo.id).all()
        try:
            validar_no_solapamiento([(i, f) for _, i, f in ocupados], nueva, fin)
        except ValueError:
            db.commit()
            return decir("Ese horario ya está ocupado. Probá con otro DD/MM HH:MM.")
        objetivo.inicio, objetivo.fin = nueva, fin
        from app.modules.notificaciones.service import programar_recordatorio
        programar_recordatorio(db, objetivo)
        sesion.esperando = ""
        db.commit()
        return decir(f"Listo, tu turno pasó al {nueva.strftime('%d/%m %H:%M')}. Te avisaremos un día antes.")

    # --- intenciones generales ---
    inten, resto = detectar_intencion(texto)
    prox = turnos_proximos(db, models, tid, sesion.cliente_id)

    if inten == "saludo":
        cli = db.query(models.Cliente).filter_by(id=sesion.cliente_id, tenant_id=tid).first()
        return decir(_bienvenida(db, models, sesion, cli))
    if inten == "listar":
        if not prox:
            return decir("No tienes turnos agendados por ahora. Escribí *cambiar* si querías mover alguno, o avisá en recepción para reservar.")
        return decir("Tus turnos agendados:\n" + "\n".join(
            fmt_turno(i + 1, t.inicio, *nombres_turno(db, models, tid, t)[:2], t.estado)
            for i, t in enumerate(prox)) + "\nRespondé *confirmar N*, *cancelar N* o *cambiar N*.")
    if inten in ("confirmar", "cancelar", "cambiar"):
        n = re.search(r"(\d{1,2})", resto)
        if n and prox and 1 <= int(n.group(1)) <= len(prox):
            objetivo = prox[int(n.group(1)) - 1]
            if inten == "confirmar":
                objetivo.estado = "CONFIRMADO"
                db.commit()
                return decir("Listo, tu turno quedó confirmado. Te esperamos.")
            if inten == "cancelar":
                sesion.esperando = "motivo_cancel"
                _guardar_ctx(sesion, {"turno_id": objetivo.id})
                db.commit()
                return decir("¿Cuál es el motivo de la cancelación?")
            sesion.esperando = "nueva_fecha"
            _guardar_ctx(sesion, {"turno_id": objetivo.id})
            db.commit()
            return decir("Escribí la nueva fecha y hora como DD/MM HH:MM.")
        if not prox:
            return decir("No tienes turnos agendados para esa acción.")
        if len(prox) == 1 and inten == "confirmar":
            prox[0].estado = "CONFIRMADO"
            db.commit()
            return decir("Listo, tu turno quedó confirmado. Te esperamos.")
        sesion.esperando = {"confirmar": "elegir_confirmar", "cancelar": "elegir_cancelar",
                            "cambiar": "elegir_cambiar"}[inten]
        db.commit()
        return decir("¿Cuál? Respondé con el número:\n" + "\n".join(
            fmt_turno(i + 1, t.inicio, *nombres_turno(db, models, tid, t)[:2], t.estado)
            for i, t in enumerate(prox)))
    if inten == "gracias":
        return decir("¡Un placer! Quedo atento a tus turnos.")
    if inten == "salir":
        sesion.esperando = ""
        db.commit()
        return decir("¡Hasta luego! Cuando quieras consultar tus turnos, escribime.")
    if inten == "ayuda":
        return decir(MENU)
    return decir("No entendí bien. " + MENU)


def _bienvenida(db, models, sesion, cli) -> str:
    nombre = (cli.nombre if cli else "hola").split()[0] if cli and cli.nombre else "hola"
    prox = turnos_proximos(db, models, sesion.tenant_id, sesion.cliente_id) if cli else []
    base = f"Hola {nombre}, soy el asistente de Estila."
    if not prox:
        return base + " No tienes turnos agendados por ahora."
    lineas = "\n".join(fmt_turno(i + 1, t.inicio, *nombres_turno(db, models, sesion.tenant_id, t)[:2], t.estado)
                        for i, t in enumerate(prox))
    return base + " Tus turnos agendados:\n" + lineas + "\nRespondé *confirmar N*, *cancelar N* o *cambiar N*."
