"""Crea turno RESERVADO temporal, verifica iconos en /ui/turnos y lo borra."""
import json
import urllib.request, urllib.error, urllib.parse

BASE = "http://127.0.0.1:8001"


class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None


OP = urllib.request.build_opener(NoRedir)


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
        return e.code, e.read().decode()[:120]


def wlogin(email, pw):
    data = urllib.parse.urlencode({"email": email, "password": pw}).encode()
    req = urllib.request.Request(BASE + "/login", data=data, method="POST")
    try:
        OP.open(req)
        return ""
    except urllib.error.HTTPError as e:
        return (e.headers.get("Set-Cookie") or "").split(";")[0]


s, b = api("POST", "/auth/login", {"email": "admin@arselia.py", "password": "Segura123!"})
tok, tid = b["access_token"], b["tenant_id"]
s, cl = api("GET", "/clientes", token=tok, tenant=tid)
s, se = api("GET", "/servicios", token=tok, tenant=tid)
s, pe = api("GET", "/personal", token=tok, tenant=tid)
prof = [x for x in pe if x["activo"] == 1][0]["id"]
s, t = api("POST", "/turnos", {"cliente_id": cl[0]["id"], "profesional_id": prof,
                               "servicio_id": se[0]["id"], "inicio": "2026-12-01T10:00:00"},
           token=tok, tenant=tid)
assert s == 200, t
ck = wlogin("admin@arselia.py", "Segura123!")
req = urllib.request.Request(BASE + "/ui/turnos")
req.add_header("Cookie", ck)
html = OP.open(req).read().decode()
ok1 = 'stroke="#d9a400"' in html
ok2 = 'stroke="#b3261e"' in html
print(("PASS " if ok1 else "FAIL ") + "turnos-lapiz-reservado")
print(("PASS " if ok2 else "FAIL ") + "turnos-basura-reservado")
s, _ = api("DELETE", f"/turnos/{t['id']}", token=tok, tenant=tid)
print(("PASS " if s == 200 else "FAIL ") + "turno-temporal-borrado")
if not (ok1 and ok2 and s == 200):
    raise SystemExit(1)
print("OK TURNO ICONOS")
