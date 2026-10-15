"""Tests puros del asistente (sin BD ni red): intenciones, fechas y formato."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.chatbot.service import (  # noqa: E402
    detectar_intencion,
    fmt_turno,
    normalizar,
    parse_fecha,
)


def check(nombre, cond):
    print(("PASS " if cond else "FAIL ") + nombre)
    if not cond:
        raise SystemExit(1)


check("norm", normalizar("  Hola  ") == "hola")
check("int-numero", detectar_intencion("2") == ("numero", "2"))
check("int-confirmar", detectar_intencion("confirmar 1") == ("confirmar", "1"))
check("int-cancelar", detectar_intencion("quiero cancelar mi turno")[0] == "cancelar")
check("int-cancelar-num", detectar_intencion("cancelar 2") == ("cancelar", "2"))
check("int-cambiar", detectar_intencion("cambiar 2") == ("cambiar", "2"))
check("int-listar", detectar_intencion("ver mis turnos")[0] == "listar")
check("int-ayuda", detectar_intencion("menu")[0] == "ayuda")
check("int-gracias", detectar_intencion("muchas gracias")[0] == "gracias")
check("int-salir", detectar_intencion("chau")[0] == "salir")
check("int-saludo", detectar_intencion("hola")[0] == "saludo")
check("int-fallback", detectar_intencion("xyz123")[0] == "no_entendido")

ahora = datetime(2026, 10, 15, 12, 0)
check("fecha-ok", parse_fecha("25/10 15:30", ahora) == datetime(2026, 10, 25, 15, 30))
check("fecha-pasada-no", parse_fecha("10/10 10:00", ahora) is None)
check("fecha-sin-hora-no", parse_fecha("25/10", ahora) is None)
check("fecha-basura-no", parse_fecha("mañana", ahora) is None)

check("fmt", fmt_turno(1, datetime(2026, 10, 20, 14, 0), "Corte", "Arselia", "RESERVADO")
      == "1) Corte — 20/10 14:00 con Arselia (RESERVADO)")

print("ALL CHATBOT OK")
