"""Reglas de agenda: solapamiento y comisiones (RF05/RF17). Puro y testeable sin BD."""

from datetime import datetime, timedelta


def calcular_fin(inicio: datetime, duracion_min: int) -> datetime:
    return inicio + timedelta(minutes=duracion_min)


def _norm(dt: datetime) -> datetime:
    # SQLite devuelve naive y Pydantic aware (Z); normaliza a naive UTC para comparar
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def hay_solapamiento(a_ini: datetime, a_fin: datetime, b_ini: datetime, b_fin: datetime) -> bool:
    a_ini, a_fin, b_ini, b_fin = _norm(a_ini), _norm(a_fin), _norm(b_ini), _norm(b_fin)
    return a_ini < b_fin and b_ini < a_fin


def validar_no_solapamiento(existentes: list[tuple[datetime, datetime]], nuevo_ini: datetime, nuevo_fin: datetime) -> None:
    for e_ini, e_fin in existentes:
        if hay_solapamiento(e_ini, e_fin, nuevo_ini, nuevo_fin):
            raise ValueError("Solapamiento: horario ya ocupado (RF05)")


def calcular_comision(precio_gs: int, pct: float) -> int:
    return int(round(precio_gs * float(pct) / 100))
