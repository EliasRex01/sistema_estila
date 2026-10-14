"""Validacion CI/RUC Paraguay (RNF11) y normalizacion."""

import re

CI_RUC_RE = re.compile(r"^(\d{5,9})(-(\d))?$")


def validar_ci_ruc_py(valor: str) -> str:
    v = (valor or "").strip()
    if v == "":
        return ""  # opcional en ficha rapida
    m = CI_RUC_RE.match(v)
    if not m:
        raise ValueError("CI/RUC invalido (ej. 1234567 o 80012345-6)")
    return v
