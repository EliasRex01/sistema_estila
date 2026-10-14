"""Verifica CRUD API: PUT/DELETE + reglas (ultimo admin, referenciados, solape, atender)."""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8001"


def api(method, path, body=None, token=None, tenant=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    if tenant:
        req.add_header("X-Tenant-ID", tenant)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data) as x:
            raw = x.read().decode()
            return x.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:160]


def check(nombre, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + nombre, extra)
    if not cond:
        raise SystemExit(1)


s, b = api("POST", "/auth/login", {"email": "admin@arselia.py", "password": "Segura123!"})
check("login", s == 200)
tok, tid = b["access_token"], b["tenant_id"]
A = dict(token=tok, tenant=tid)

import time
TAG = str(int(time.time()) % 100000)
EMAIL_T = f"crudt{TAG}@arselia.py"

# --- personal: editar ---
s, u = api("POST", "/personal", {"nombre": "Crud T", "email": EMAIL_T,
                                 "password": "Segura123!", "rol": "ESTILISTA",
                                 "comision_default_pct": 5}, **A)
check("personal-crear", s == 200, u["id"] if s == 200 else u)
uid = u["id"]
s, u2 = api("PUT", f"/personal/{uid}", {"nombre": "Crud T2", "email": EMAIL_T,
                                        "rol": "RECEPCION", "comision_default_pct": 15,
                                        "activo": 1, "password": ""}, **A)
check("personal-editar", s == 200 and u2["nombre"] == "Crud T2" and u2["rol"] == "RECEPCION", u2 if s != 200 else "")
s, b = api("PUT", f"/personal/{uid}", {"nombre": "Otro Nombre", "email": "admin@arselia.py",
                                        "rol": "RECEPCION", "comision_default_pct": 0,
                                        "activo": 1, "password": ""}, **A)
check("personal-email-dup-409", s == 409, b)
# ultimo admin protegido
s, yo = api("GET", "/personal", **A)
admin_id = [x for x in yo if x["rol"] == "ADMIN" and x["activo"] == 1][0]["id"]
s, b = api("DELETE", f"/personal/{admin_id}", **A)
check("ultimo-admin-bloqueado", s == 409, b)
s, b = api("PUT", f"/personal/{admin_id}", {"nombre": "Arselia", "email": "admin@arselia.py",
                                            "rol": "ADMIN", "comision_default_pct": 0,
                                            "activo": 0, "password": ""}, **A)
check("autodesactivar-bloqueado", s == 409, b)
s, u3 = api("DELETE", f"/personal/{uid}", **A)
check("personal-baja-suave", s == 200 and u3["activo"] == 0)

# --- servicio + cliente: editar y borrado bloqueado por referencia ---
s, cli = api("POST", "/clientes", {"nombre": "Crud Cli", "ci_ruc": "9999999"}, **A)
s, ser = api("POST", "/servicios", {"nombre": "Crud Serv", "duracion_min": 30,
                                    "precio_gs": 50000, "comision_pct": 10}, **A)
check("base-creada", s == 200)
cid, sid = cli["id"], ser["id"]
s, c2 = api("PUT", f"/clientes/{cid}", {"nombre": "Crud Cli2", "ci_ruc": "9999999",
                                        "telefono": "0981", "direccion": "d", "ficha_json": "{}"}, **A)
check("cliente-editar", s == 200 and c2["nombre"] == "Crud Cli2" and c2["telefono"] == "0981")
s, s2 = api("PUT", f"/servicios/{sid}", {"nombre": "Crud Serv2", "duracion_min": 45,
                                         "precio_gs": 60000, "comision_pct": 20}, **A)
check("servicio-editar", s == 200 and s2["duracion_min"] == 45)
s, pers = api("GET", "/personal", **A)
prof = [x for x in pers if x["activo"] == 1 and x["rol"] in ("ADMIN", "ESTILISTA")][0]["id"]
s, t1 = api("POST", "/turnos", {"cliente_id": cid, "profesional_id": prof, "servicio_id": sid,
                                "inicio": "2026-11-02T10:00:00"}, **A)
check("turno-crear", s == 200, t1["id"])
t1id = t1["id"]
s, b = api("DELETE", f"/clientes/{cid}", **A)
check("cliente-referenciado-409", s == 409, b)
s, b = api("DELETE", f"/servicios/{sid}", **A)
check("servicio-referenciado-409", s == 409, b)

# --- reprogramar: solape bloqueado, libre ok ---
s, b = api("PUT", f"/turnos/{t1id}", {"cliente_id": cid, "profesional_id": prof,
                                      "servicio_id": sid, "inicio": "2026-11-02T10:15:00"}, **A)
check("reprogramar-mismo-ok", s == 200)
s, t2 = api("POST", "/turnos", {"cliente_id": cid, "profesional_id": prof, "servicio_id": sid,
                                "inicio": "2026-11-02T12:00:00"}, **A)
check("turno2-crear", s == 200)
s, b = api("PUT", f"/turnos/{t2['id']}", {"cliente_id": cid, "profesional_id": prof,
                                          "servicio_id": sid, "inicio": "2026-11-02T10:10:00"}, **A)
check("reprogramar-solape-409", s == 409, b)

# --- atender suma visita; luego borrados ---
s, ta = api("POST", f"/turnos/{t1id}/atender", {}, **A)
check("atender", s == 200 and ta["estado"] == "ATENDIDO")
s, cl = api("GET", "/clientes", **A)
nv = [x for x in cl if x["id"] == cid][0]["n_visitas"]
check("visita-sumada", nv >= 1, f"n={nv}")
s, b = api("DELETE", f"/turnos/{t1id}", **A)
check("eliminar-atendido-409", s == 409, b)
s, b = api("DELETE", f"/turnos/{t2['id']}", **A)
check("eliminar-reservado-200", s == 200, b)
s, b = api("DELETE", f"/turnos/{t1id}", **A)
check("eliminar-atendido-sigue-409", s == 409, b)

# --- profesional inactivo no recibe turnos ---
s, b = api("POST", "/turnos", {"cliente_id": cid, "profesional_id": uid, "servicio_id": sid,
                               "inicio": "2026-11-03T10:00:00"}, **A)
check("turno-profesional-inactivo-409", s == 409, b)

# --- limpieza: el atendido ya no se puede cancelar ---
s, b = api("POST", f"/turnos/{t1id}/cancelar", {"motivo": "prueba limpieza"}, **A)
check("cancelar-atendido-409", s == 409, b)
print("ALL CRUD OK")
