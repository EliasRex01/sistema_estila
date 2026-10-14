"""Verifica menu web por rol: ADMIN ve todo, RECEPCION sin Personal, ESTILISTA solo agenda+servicios."""
import urllib.request, urllib.error, urllib.parse

BASE = "http://127.0.0.1:8001"


class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None


OP = urllib.request.build_opener(NoRedir)


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
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        x = OP.open(req)
        return x.status, x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location") or ""


def check(nombre, cond):
    print(("PASS " if cond else "FAIL ") + nombre)
    if not cond:
        raise SystemExit(1)


ca = wlogin("admin@arselia.py", "Segura123!")
cr = wlogin("recep@arselia.py", "Segura123!")
ce = wlogin("esti@arselia.py", "Segura123!")
check("cookies", bool(ca and cr and ce))

s, b = wget("/panel", ca)
check("admin-panel-200", s == 200)
check("admin-ve-personal", "/ui/personal" in b)
check("admin-ve-clientes", "/ui/clientes" in b)
check("admin-ve-turnos", "/ui/turnos" in b)

s, b = wget("/ui/personal", ca)
check("admin-ui-personal-200", s == 200 and "Alta de personal" in b)

s, b = wget("/panel", cr)
check("recep-panel-200", s == 200)
check("recep-ve-turnos", "/ui/turnos" in b)
check("recep-no-ve-personal", "/ui/personal" not in b)

s, b = wget("/ui/personal", cr)
check("recep-ui-personal-bloqueado", s == 302 and b == "/panel")

s, b = wget("/ui/clientes", cr)
check("recep-ui-clientes-200", s == 200)

s, b = wget("/panel", ce)
check("esti-panel-200", s == 200)
check("esti-ve-agenda", "Mi agenda" in b)
check("esti-no-ve-clientes", "/ui/clientes" not in b)
check("esti-no-ve-personal", "/ui/personal" not in b)

s, b = wget("/ui/turnos", ce)
check("esti-agenda-propia", s == 200 and "Mi agenda" in b)

s, b = wget("/ui/clientes", ce)
check("esti-ui-clientes-bloqueado", s == 302 and b == "/panel")

s, b = wget("/panel", "")
check("sin-cookie-va-login", s == 302 and b == "/login")

print("ALL UI OK")
