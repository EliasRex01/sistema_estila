"""Verifica el tema empresarial: sidebar en panel, login centrado, CSS nuevo."""
import urllib.request, urllib.error, urllib.parse

BASE = "http://127.0.0.1:8001"


class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None


OP = urllib.request.build_opener(NoRedir)


def get(path, cookie=""):
    req = urllib.request.Request(BASE + path)
    if cookie:
        req.add_header("Cookie", cookie)
    with OP.open(req) as x:
        return x.status, x.read().decode()


def check(nombre, cond):
    print(("PASS " if cond else "FAIL ") + nombre)
    if not cond:
        raise SystemExit(1)


s, css = get("/static/style.css")
check("css-200", s == 200)
check("css-marino", "--marino" in css)
check("css-sin-violeta", "#6d28d9" not in css)

s, login = get("/login")
check("login-200", s == 200)
check("login-centrado", "login-fondo" in login and "login-marca" in login)
check("login-sin-sidebar", "lateral" not in login)

data = urllib.parse.urlencode({"email": "admin@arselia.py", "password": "Segura123!"}).encode()
req = urllib.request.Request(BASE + "/login", data=data, method="POST")
try:
    OP.open(req)
    ck = ""
except urllib.error.HTTPError as e:
    ck = (e.headers.get("Set-Cookie") or "").split(";")[0]
s, panel = get("/panel", ck)
check("panel-200", s == 200)
check("panel-sidebar", 'class="lateral"' in panel and 'class="barra"' in panel)
check("panel-modulos", "etiqueta" in panel and "Cerrar sesi" in panel)

print("ALL TEMA OK")
