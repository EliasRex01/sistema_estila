"""Verifica pagina personal: boton Incluir, iconos, paginacion 10 por pagina."""
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
s, b = wget("/ui/personal", ca)
check("personal-200", s == 200)
s, css = wget("/static/style.css", ca)
check("basura-sin-caja", ".btn-icono:hover" in css and "background-color: transparent" in css)
check("boton-incluir", 'id="btn-incluir"' in b and "+ Incluir" in b)
check("incluir-abajo", b.find('id="btn-incluir"') > b.find("</table>"))
check("lapiz-amarillo", 'stroke="#d9a400"' in b and 'stroke="#1f5fa8"' not in b)
check("sin-num-pagina-actual", "<b>" not in b.split('class="pags"')[1].split("</div>")[0])
check("form-oculto", 'id="form-alta" style="display:none"' in b)
check("icono-lapiz", "M17 3a2.8" in b and ">Editar<" not in b)
check("icono-basurero", "M3 6h18M8 6V4" in b and ">Desactivar<" not in b and ">Eliminar<" not in b)
check("rango-pie", " de " in b and 'class="rango"' in b)
import re
m = re.search(r'class="rango">(\d+) a (\d+) de (\d+)<', b)
check("rango-formato", bool(m), m.group(0) if m else "")
if m:
    d, h, t = int(m.group(1)), int(m.group(2)), int(m.group(3))
    check("rango-max10", h - d + 1 <= 10 if t else True, f"{d} a {h} de {t}")

s, b2 = wget("/ui/personal?pag=99", ca)
check("pag-fuera-rango-200", s == 200)
m2 = re.search(r'class="rango">(\d+) a (\d+) de (\d+)<', b2)
check("pag-sujeta-ultima", bool(m2) and int(m2.group(2)) == int(m2.group(3)), m2.group(0) if m2 else "")

print("ALL PERSONAL UI OK")
