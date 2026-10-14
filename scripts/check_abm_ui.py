"""Verifica formato ABM empresarial en clientes, servicios, turnos y sin-turno."""
import re
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
    req.add_header("Cookie", cookie)
    with OP.open(req) as x:
        return x.status, x.read().decode()


def check(nombre, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + nombre, extra)
    if not cond:
        raise SystemExit(1)


ca = wlogin("admin@arselia.py", "Segura123!")
ce = wlogin("esti@arselia.py", "Segura123!")

for nombre, url, con_alta in [("clientes", "/ui/clientes", True), ("servicios", "/ui/servicios", True),
                              ("turnos", "/ui/turnos", True), ("sin-turno", "/ui/clientes/sin-turno", False)]:
    s, b = wget(url, ca)
    check(f"{nombre}-200", s == 200)
    hay_iconos = url != "/ui/turnos" or "RESERVADO" in b
    if hay_iconos:
        check(f"{nombre}-lapiz-amarillo", 'stroke="#d9a400"' in b)
        check(f"{nombre}-basurero-rojo", 'stroke="#b3261e"' in b)
    else:
        print("SKIP turnos-iconos (sin reservas pendientes; ver check_turno_iconos.py)")
    check(f"{nombre}-sin-texto-editar", ">Editar<" not in b and ">Reprogramar<" not in b)
    m = re.search(r'class="rango">(\d+) a (\d+) de (\d+)<', b)
    check(f"{nombre}-rango", bool(m), m.group(0) if m else "")
    if m:
        d, h, t = int(m.group(1)), int(m.group(2)), int(m.group(3))
        check(f"{nombre}-max10", (h - d + 1) <= 10 if t else True, f"{d} a {h} de {t}")
    if con_alta:
        check(f"{nombre}-incluir-abajo", 'id="btn-incluir"' in b and b.find('id="btn-incluir"') > b.find("</table>"))
    else:
        check(f"{nombre}-sin-incluir", 'id="btn-incluir"' not in b)

s, b = wget("/ui/clientes/sin-turno?pag=99", ca)
import re as _re
_m = _re.search(r'class="rango">\d+ a \d+ de (\d+)<', b)
_tot = int(_m.group(1)) if _m else 0
check("sinturno-pag-propia", s == 200 and (_tot <= 10 or "sin-turno?pag=" in b))

s, b = wget("/ui/turnos", ce)
check("esti-sin-incluir", 'id="btn-incluir"' not in b)
check("esti-sin-lapiz", 'stroke="#d9a400"' not in b)

s, b = wget("/ui/servicios", ce)
check("esti-servicios-sin-acciones", 'stroke="#d9a400"' not in b and 'stroke="#b3261e"' not in b)

print("ALL ABM UI OK")
