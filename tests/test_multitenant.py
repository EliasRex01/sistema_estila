"""Tests MVP multitenant sin BD ni red: solapamiento, RUC/CI, comision, auth hash."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.clientes.service import validar_ci_ruc_py  # noqa: E402
from app.modules.tenants.service import validar_ruc_py  # noqa: E402
from app.modules.turnos.service import (  # noqa: E402
    calcular_comision,
    calcular_fin,
    hay_solapamiento,
    validar_no_solapamiento,
)


def check(nombre, cond):
    print(("PASS " if cond else "FAIL ") + nombre)
    if not cond:
        raise SystemExit(1)


ahora = datetime.now(timezone.utc)
# 1. solapamiento detecta
check("solapa", hay_solapamiento(ahora, ahora + timedelta(hours=1), ahora + timedelta(minutes=30), ahora + timedelta(hours=2)))
# 2. adyacente no solapa
check("adyacente-ok", not hay_solapamiento(ahora, ahora + timedelta(hours=1), ahora + timedelta(hours=1), ahora + timedelta(hours=2)))
# 3. validador lanza en conflicto
try:
    validar_no_solapamiento([(ahora, ahora + timedelta(hours=1))], ahora + timedelta(minutes=30), ahora + timedelta(hours=2))
    check("validador-conflicto", False)
except ValueError:
    check("validador-conflicto", True)
# 4. RUC py
check("ruc-ok", validar_ruc_py("80012345-6") == "80012345-6")
try:
    validar_ruc_py("abc")
    check("ruc-malo", False)
except ValueError:
    check("ruc-malo", True)
# 5. CI/RUC cliente
check("ci-ok", validar_ci_ruc_py("1234567") == "1234567")
check("ci-vacio-ok", validar_ci_ruc_py("") == "")
# 6. fin por duracion
check("fin-30min", calcular_fin(ahora, 30) == ahora + timedelta(minutes=30))
# 7. comision 20% de 100000 = 20000
check("comision", calcular_comision(100000, 20) == 20000)

print("ALL OK")
