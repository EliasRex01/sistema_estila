"""Recordatorios de turnos (RF08). Se programan al reservar/reprogramar."""

from datetime import datetime, timedelta


def _ahora():
    return datetime.now()


def programar_recordatorio(db, turno) -> None:
    """Crea o actualiza el RECORDATORIO PENDIENTE 24 h antes del turno."""
    from app.db import models
    ini = turno.inicio.replace(tzinfo=None) if getattr(turno.inicio, "tzinfo", None) else turno.inicio
    prog = ini - timedelta(hours=24)
    ahora = _ahora()
    if prog < ahora:
        prog = ahora
    n = db.query(models.Notificacion).filter_by(turno_id=turno.id, estado="PENDIENTE").first()
    if n:
        n.programada_para = prog
    else:
        db.add(models.Notificacion(tenant_id=turno.tenant_id, turno_id=turno.id,
                                   tipo="RECORDATORIO", programada_para=prog, canal="WEB-DEMO",
                                   detalle="Aviso automatico de turno agendado"))


def cancelar_recordatorios(db, turno, detalle: str = "") -> None:
    from app.db import models
    for n in db.query(models.Notificacion).filter_by(turno_id=turno.id, estado="PENDIENTE").all():
        n.estado = "CANCELADA"
        n.detalle = detalle[:255]
