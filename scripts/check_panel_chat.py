"""Verifica panel real + chatbot demo + notificaciones (vivo, con limpieza)."""
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
        return e.code, e.read().decode()[:160]


def wlogin(email, pw):
    data = urllib.parse.urlencode({"email": email, "password": pw}).encode()
    req = urllib.request.Request(BASE + "/login", data=data, method="POST")
    try:
        OP.open(req)
        return ""
    except urllib.error.HTTPError as e:
        return (e.headers.get("Set-Cookie") or "").split(";")[0]


def wget(path, cookie):
    req = urllib.request.Request(BASE + path)
    req.add_header("Cookie", cookie)
    with OP.open(req) as x:
        return x.status, x.read().decode()


def chat(cookie, cid, texto):
    data = json.dumps({"cid": cid, "texto": texto}).encode()
    req = urllib.request.Request(BASE + "/chat/mensaje", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Cookie", cookie)
    with OP.open(req) as x:
        return json.loads(x.read().decode())["respuesta"]


def check(nombre, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + nombre, extra)
    if not cond:
        raise SystemExit(1)


import time
TAG = str(int(time.time()) % 100000)
ca = wlogin("admin@arselia.py", "Segura123!")

s, b = wget("/panel", ca)
check("panel-200", s == 200)
for txt in ["Agenda de hoy", "Próximo turno", "Recordatorios pendientes", "chat-burbuja", "Asistente Estila"]:
    check(f"panel-{txt[:12]}", txt in b)

# cliente temporal con telefono unico
s, b = api("POST", "/auth/login", {"email": "admin@arselia.py", "password": "Segura123!"})
tok, tid = b["access_token"], b["tenant_id"]
A = dict(token=tok, tenant=tid)
s, cli = api("POST", "/clientes", {"nombre": "Chat Demo", "ci_ruc": "1122334",
                                   "telefono": f"0991{TAG}"}, **A)
check("cli-temporal", s == 200)
s, se = api("GET", "/servicios", **A)
s, pe = api("GET", "/personal", **A)
prof = [x for x in pe if x["activo"] == 1][0]["id"]
s, t = api("POST", "/turnos", {"cliente_id": cli["id"], "profesional_id": prof,
                               "servicio_id": se[0]["id"], "inicio": "2026-12-05T10:00:00"}, **A)
check("turno-temporal", s == 200)
s, nn = api("GET", "/notificaciones", **A)
check("notif-auto", s == 200 and any(n["estado"] == "PENDIENTE" for n in nn))

CID = f"demo{TAG}"
r = chat(ca, CID, "hola")
check("chat-saluda-pide-datos", "teléfono" in r or "nombre" in r, r[:80])
r = chat(ca, CID, f"0991{TAG}")
check("chat-avisa-turnos", "turnos agendados" in r and "05/12" in r, r[:100])
r = chat(ca, CID, "confirmar 1")
check("chat-confirma", "confirmado" in r, r[:80])
s, tt = api("GET", "/turnos", **A)
est = [x for x in tt if x["id"] == t["id"]][0]["estado"]
check("turno-confirmado-bd", est == "CONFIRMADO", est)
r = chat(ca, CID, "cancelar 1")
check("chat-pide-motivo", "motivo" in r, r[:80])
r = chat(ca, CID, "ya me corte en otro lado")
check("chat-cancela", "cancelado" in r, r[:80])
s, tt = api("GET", "/turnos", **A)
est = [x for x in tt if x["id"] == t["id"]][0]["estado"]
check("turno-cancelado-bd", est == "CANCELADO", est)
s, h = api("GET", "/turnos", **A)
r = chat(ca, CID, "mis turnos")
check("chat-sin-turnos", "No tienes turnos" in r, r[:80])

s, b = wget("/ui/notificaciones", ca)
check("notif-pagina-200", s == 200 and "Notificaciones" in b)

# marcar enviada sobre otra pendiente (si existe)
s, nn = api("GET", "/notificaciones", **A)
pend = [n for n in nn if n["estado"] == "PENDIENTE"]
if pend:
    s, _ = api("POST", f"/notificaciones/{pend[0]['id']}/enviar", {}, **A)
    check("notif-enviar", s == 200)
else:
    print("SKIP notif-enviar (sin pendientes)")

print("ALL PANEL+CHAT OK")
