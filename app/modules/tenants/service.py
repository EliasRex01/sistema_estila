"""Alta de tenant + admin inicial (RF01). Valida RUC py."""

import re

RUC_RE = re.compile(r"^\d{6,9}-\d$")


def validar_ruc_py(ruc: str) -> str:
    ruc = ruc.strip()
    if not RUC_RE.match(ruc):
        raise ValueError("RUC invalido (formato 80012345-6)")
    return ruc
