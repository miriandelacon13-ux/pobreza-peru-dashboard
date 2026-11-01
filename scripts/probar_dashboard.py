"""Prueba el dashboard en un navegador real (Edge o Chrome sin interfaz) y compara lo que muestra con las tablas CSV.

Para cada combinación de filtros (departamento × área × tipo de pobreza) cambia los controles como lo haría una persona
(eventos change del selector y de los botones) y comprueba:
  - los cuatro KPI (tasa, personas, brecha, comparación) frente a datos/procesados/*.csv;
  - que el mapa, el ranking, la dispersión y la composición reciban las tasas correctas de los 25 departamentos;
  - que una celda sin hogares (Callao rural) aparezca como «sin dato» y nunca como cero;
  - que la URL guarde el estado y que los textos usen «del» y «al» (no «de el», «a el»).
Además prueba el clic en el mapa, el botón Restablecer, la medida «personas», el modo oscuro y una pantalla de celular,
y falla si hay errores de JavaScript o peticiones fallidas.

Uso:  uv run scripts/probar_dashboard.py                       # sirve el repositorio en localhost y prueba web/
      uv run scripts/probar_dashboard.py --url https://…/web/  # prueba el sitio publicado
      … --capturas <carpeta>                                    # guarda capturas de pantalla
"""

import argparse
import functools
import http.server
import json
import re
import sys
import threading
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from navegador import Navegador, puerto_libre  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
P = RAIZ / "datos/procesados"
TIPOS = {"total": "pobreza", "extrema": "pobreza_extrema", "no_extrema": "pobreza_no_extrema"}
CONTEO = {"total": "pobres_estimados", "extrema": "pobres_extremos_estimados", "no_extrema": "pobres_no_extremos_estimados"}
AREA_CSV = {"urbana": "Urbana", "rural": "Rural"}
DEPS = ["00", "15", "07", "06", "11"]  # Perú, Lima, Callao (sin rural), Cajamarca (mayor tasa), Ica (referencial)


class Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class Esperado:
    """Valores esperados leídos de los CSV verificados (no del JSON de la web)."""

    def __init__(self):
        self.nac = pd.read_csv(P / "pobreza_nacional_area_2024.csv").set_index("ambito")
        self.dep = pd.read_csv(P / "pobreza_departamento_2024.csv", dtype={"ccdd": str}).set_index("ccdd")
        self.da = pd.read_csv(P / "pobreza_departamento_area_2024.csv", dtype={"ccdd": str})
        self.br = pd.read_csv(P / "brecha_urbano_rural_2024.csv", dtype={"ccdd": str})

    def fila(self, dep, area):
        if dep == "00":
            return self.nac.loc["Nacional" if area == "total" else AREA_CSV[area]]
        if area == "total":
            return self.dep.loc[dep]
        f = self.da[(self.da.ccdd == dep) & (self.da.area == AREA_CSV[area])]
        return f.iloc[0] if len(f) else None

    def tasas(self, area, tipo):
        col = f"tasa_{TIPOS[tipo]}"
        if area == "total":
            return self.dep[col].to_dict()
        return self.da[self.da.area == AREA_CSV[area]].set_index("ccdd")[col].to_dict()

    def brecha(self, dep, tipo):
        f = self.br[(self.br.ccdd == dep) & (self.br.tipo == TIPOS[tipo])]
        return f.iloc[0] if len(f) else None


def numero(texto):
    m = re.search(r"([−+-]?)(\d[\d,]*\.?\d*)", texto)
    if not m:
        return None
    v = float(m.group(2).replace(",", ""))
    v = -v if m.group(1) in ("−", "-") else v
    if "millones" in texto:
        v *= 1e6
    elif re.search(r"\bmil\b", texto):
        v *= 1e3
    return v


class Prueba:
    def __init__(self):
        self.ok, self.fallas = 0, []

    def check(self, cond, texto):
        if cond:
            self.ok += 1
        else:
            self.fallas.append(texto)


def aplicar(nav, dep, area, tipo, medida="tasa"):
    """Cambia los controles como una persona y espera a que quede dibujado exactamente ese estado."""
    errores_antes = len(nav.errores)
    nav.evaluar(f"""(() => {{
        let n = 0;
        const s = document.getElementById('f-dep');
        if (s.value !== '{dep}') {{ s.value = '{dep}'; s.dispatchEvent(new Event('change')); n++; }}
        for (const [k, v] of [['area', '{area}'], ['tipo', '{tipo}'], ['medida', '{medida}']]) {{
            const i = document.querySelector(`input[name="${{k}}"][value="${{v}}"]`);
            if (!i.checked) {{ i.checked = true; i.dispatchEvent(new Event('change')); n++; }}
        }}
        return n;
    }})()""")
    esperar_estado(nav, dep, area, tipo, medida)
    nav.evaluar("1")  # vacía los eventos pendientes (errores de consola)
    if len(nav.errores) > errores_antes:
        raise RuntimeError(f"error de JavaScript con dep={dep} área={area} tipo={tipo}: {nav.errores[errores_antes:]}")


def esperar_estado(nav, dep, area, tipo, medida="tasa"):
    objetivo = json.dumps({"dep": dep, "area": area, "tipo": tipo, "medida": medida}, separators=(",", ":"))
    nav.esperar(f"window.tablero.dibujado === {json.dumps(objetivo)}", segundos=30)


def leer(nav):
    return nav.evaluar("""(() => {
        const k = (id) => ({etiqueta: document.querySelector(`#${id} .kpi-etiqueta`).textContent,
                            valor: document.querySelector(`#${id} .kpi-valor`).textContent,
                            detalle: document.querySelector(`#${id} .kpi-detalle`).textContent});
        const g = (id) => document.getElementById(id).data.map(t => ({name: t.name, x: t.x, y: t.y, z: t.z, locations: t.locations,
                                                                    customdata: t.customdata}));
        return {kpi: {tasa: k('kpi-tasa'), personas: k('kpi-personas'), brecha: k('kpi-brecha'), comparacion: k('kpi-comparacion')},
                mapa: g('g-mapa'), ranking: g('g-ranking'), dispersion: g('g-dispersion'), composicion: g('g-composicion'),
                filas_tabla: document.querySelectorAll('#tabla tbody tr').length, url: location.search,
                titulo_mapa: document.getElementById('t-mapa').textContent};
    })()""")


def probar_combinacion(nav, esp, pr, dep, area, tipo):
    aplicar(nav, dep, area, tipo)
    r = leer(nav)
    nombre = f"[dep={dep} área={area} tipo={tipo}]"
    t, col = TIPOS[tipo], f"tasa_{TIPOS[tipo]}"
    fila = esp.fila(dep, area)

    # KPI 1 y 2
    if fila is None:
        pr.check(r["kpi"]["tasa"]["valor"] == "Sin dato" and r["kpi"]["personas"]["valor"] == "Sin dato",
                 f"{nombre} sin hogares debe mostrar «Sin dato»: {r['kpi']['tasa']['valor']}")
    else:
        pr.check(abs(numero(r["kpi"]["tasa"]["valor"]) - fila[col]) <= 0.0501,
                 f"{nombre} KPI tasa {r['kpi']['tasa']['valor']} ≠ {fila[col]:.3f}")
        esperado = fila[CONTEO[tipo]]
        tol = 5_000 if esperado >= 1e6 else 500
        pr.check(abs(numero(r["kpi"]["personas"]["valor"]) - esperado) <= tol,
                 f"{nombre} KPI personas {r['kpi']['personas']['valor']} ≠ {esperado:,}")
        pr.check(("pobreza extrema" in r["kpi"]["tasa"]["etiqueta"]) == (tipo == "extrema")
                 and ("no extrema" in r["kpi"]["tasa"]["etiqueta"]) == (tipo == "no_extrema"),
                 f"{nombre} la etiqueta del KPI no nombra el tipo elegido: {r['kpi']['tasa']['etiqueta']}")

    # KPI 3: brecha (no depende del área)
    b = esp.brecha(dep, tipo)
    if b is None:
        pr.check(r["kpi"]["brecha"]["valor"] == "No disponible", f"{nombre} brecha de Callao debe ser «No disponible»")
    else:
        pr.check(abs(numero(r["kpi"]["brecha"]["valor"]) - b.brecha_pp) <= 0.0501,
                 f"{nombre} KPI brecha {r['kpi']['brecha']['valor']} ≠ {b.brecha_pp:.3f}")

    # KPI 4: comparación con el país, o mayor tasa
    if dep != "00":
        if fila is None:
            pr.check(r["kpi"]["comparacion"]["valor"] == "Sin dato", f"{nombre} comparación sin hogares debe ser «Sin dato»")
        else:
            dif = fila[f"dif_nacional_{t}"] if area == "total" else fila[f"dif_area_nacional_{t}"]
            pr.check(abs(numero(r["kpi"]["comparacion"]["valor"]) - dif) <= 0.0501,
                     f"{nombre} KPI comparación {r['kpi']['comparacion']['valor']} ≠ {dif:.3f}")
    else:
        tasas = esp.tasas(area, tipo)
        mayor = max(tasas, key=tasas.get)
        nombre_mayor = esp.dep.loc[mayor, "departamento"]
        pr.check(r["kpi"]["comparacion"]["valor"].startswith(nombre_mayor)
                 and abs(numero(r["kpi"]["comparacion"]["valor"]) - tasas[mayor]) <= 0.0501,
                 f"{nombre} mayor tasa {r['kpi']['comparacion']['valor']} ≠ {nombre_mayor} {tasas[mayor]:.3f}")

    # Mapa: tasas correctas y celdas sin hogares en la traza «sin dato», nunca con cero
    tasas = esp.tasas(area, tipo)
    datos_mapa = next(tr for tr in r["mapa"] if tr["name"] == "datos")
    en_mapa = dict(zip(datos_mapa["locations"], datos_mapa["z"]))
    pr.check(set(en_mapa) == set(tasas) and all(abs(en_mapa[c] - tasas[c]) < 1e-6 for c in tasas),
             f"{nombre} el mapa no tiene las tasas de los departamentos con dato")
    faltan = sorted(set(esp.dep.index) - set(tasas))
    sin = next((tr for tr in r["mapa"] if tr["name"] == "sin dato"), None)
    pr.check((sorted(sin["locations"]) if sin else []) == faltan, f"{nombre} traza «sin dato» ≠ {faltan}")
    pr.check(not set(faltan) & set(en_mapa), f"{nombre} una celda sin hogares aparece con valor en el mapa")
    pr.check(len(set(en_mapa) | set(faltan)) == 25, f"{nombre} el mapa no cubre los 25 departamentos")

    # Ranking y dispersión: mismas tasas, sin celdas inexistentes
    rk = r["ranking"][0]
    pr.check(sorted(round(x, 6) for x in rk["x"]) == sorted(round(v, 6) for v in tasas.values()),
             f"{nombre} el ranking no coincide con las tasas")
    pr.check(rk["x"] == sorted(rk["x"]), f"{nombre} el ranking no está ordenado")
    ds = r["dispersion"][0]
    pr.check(sorted(round(x, 6) for x in ds["x"]) == sorted(round(v, 6) for v in tasas.values()),
             f"{nombre} la dispersión no coincide con las tasas")

    # Composición: extrema + no extrema + no pobre = 100 en cada área con datos; null sin hogares
    comp = {tr["name"]: tr["x"] for tr in r["composicion"]}
    for i, a in enumerate(["total", "urbana", "rural"]):
        f = esp.fila(dep, a)
        valores = [comp[n][i] for n in ["Pobreza extrema", "Pobreza no extrema", "No pobre"]]
        if f is None:
            pr.check(all(v is None for v in valores), f"{nombre} composición {a} sin hogares debe ser vacía")
        else:
            pr.check(abs(valores[0] - f.tasa_pobreza_extrema) < 1e-6 and abs(valores[1] - f.tasa_pobreza_no_extrema) < 1e-6
                     and abs(sum(valores) - 100) < 0.01, f"{nombre} composición {a} no cuadra")

    pr.check(r["filas_tabla"] == 26, f"{nombre} la tabla tiene {r['filas_tabla']} filas, no 26")
    texto = nav.evaluar("document.body.innerText")
    contracciones = re.findall(r"(?:de|a) el.{0,25}", texto)
    pr.check(not contracciones, f"{nombre} faltan contracciones («del», «al»): {contracciones[:3]}")
    esperado_url = {k: v for k, v in [("dep", dep), ("area", area), ("tipo", tipo)] if v not in ("00", "total")}
    pr.check(dict(re.findall(r"(\w+)=(\w+)", r["url"])) == esperado_url, f"{nombre} la URL no guarda el estado: {r['url']}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", help="URL del dashboard publicado; si falta, se sirve web/ en localhost")
    ap.add_argument("--capturas", type=Path, help="carpeta donde guardar capturas de pantalla")
    args = ap.parse_args()

    servidor = None
    url = args.url
    if not url:
        puerto = puerto_libre()
        servidor = http.server.ThreadingHTTPServer(("127.0.0.1", puerto), functools.partial(Silencioso, directory=str(RAIZ)))
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{puerto}/web/"
    if args.capturas:
        args.capturas.mkdir(parents=True, exist_ok=True)

    esp, pr = Esperado(), Prueba()
    nav = Navegador()
    try:
        nav.ir(url, "window.tablero && (window.tablero.listo || window.tablero.error)", segundos=90)
        pr.check(nav.evaluar("window.tablero.error") is None, f"error al cargar: {nav.evaluar('window.tablero.error')}")
        pr.check(nav.evaluar("document.title") == "Pobreza monetaria en el Perú, 2024", "título de la página")
        if args.capturas:
            nav.captura(args.capturas / "01_inicio.png")

        for dep in DEPS:
            for area in ["total", "urbana", "rural"]:
                for tipo in TIPOS:
                    probar_combinacion(nav, esp, pr, dep, area, tipo)

        # Medida «personas» en el mapa
        aplicar(nav, "00", "rural", "extrema", "personas")
        r = leer(nav)
        datos_mapa = next(tr for tr in r["mapa"] if tr["name"] == "datos")
        conteos = esp.da[esp.da.area == "Rural"].set_index("ccdd")["pobres_extremos_estimados"] / 1e6
        pr.check(all(abs(z - conteos[c]) < 1e-6 for c, z in zip(datos_mapa["locations"], datos_mapa["z"])),
                 "medida personas: el mapa no muestra los conteos (millones)")
        pr.check("estimación propia" in r["titulo_mapa"], "medida personas: el título no dice «estimación propia»")
        if args.capturas:
            nav.captura(args.capturas / "02_rural_extrema_personas.png")

        # Clic en el mapa (evento de Plotly) selecciona el departamento; el botón Restablecer vuelve al inicio
        aplicar(nav, "00", "total", "total")
        nav.evaluar("document.getElementById('g-mapa').emit('plotly_click', {points: [{location: '08'}]})")
        esperar_estado(nav, "08", "total", "total")
        pr.check(nav.evaluar("document.getElementById('f-dep').value") == "08", "clic en el mapa no seleccionó Cusco")
        pr.check("Cusco" in leer(nav)["kpi"]["tasa"]["etiqueta"], "clic en el mapa no actualizó el KPI")
        if args.capturas:
            nav.captura(args.capturas / "03_cusco.png")
        aplicar(nav, "08", "rural", "extrema", "personas")
        nav.evaluar("document.getElementById('f-reiniciar').click()")
        esperar_estado(nav, "00", "total", "total")
        pr.check(nav.evaluar("document.getElementById('f-dep').value") == "00" and nav.evaluar("location.search") == "",
                 "Restablecer no volvió al estado inicial")

        # Estado desde la URL
        nav.ir(url + "?dep=07&area=rural&tipo=extrema", "window.tablero && window.tablero.listo")
        r = leer(nav)
        pr.check(r["kpi"]["tasa"]["valor"] == "Sin dato" and r["kpi"]["brecha"]["valor"] == "No disponible",
                 "abrir ?dep=07&area=rural no muestra «Sin dato»")
        if args.capturas:
            nav.captura(args.capturas / "04_callao_rural.png")

        # Modo oscuro: cambia la superficie y vuelve a dibujar
        antes = nav.evaluar("window.tablero.dibujos")
        nav.enviar("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
        nav.esperar(f"window.tablero.dibujos > {antes}")
        fondo = nav.evaluar("getComputedStyle(document.body).backgroundColor")
        papel = nav.evaluar("document.getElementById('g-mapa').layout.paper_bgcolor")
        pr.check(fondo == "rgb(13, 13, 13)" and papel == "#1a1a19", f"modo oscuro: fondo {fondo}, gráfico {papel}")
        if args.capturas:
            nav.ir(url, "window.tablero && window.tablero.listo")
            nav.captura(args.capturas / "05_oscuro.png")
        nav.enviar("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])

        # Celular: sin desplazamiento horizontal
        nav.enviar("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=True)
        nav.ir(url, "window.tablero && window.tablero.listo")
        nav.evaluar("new Promise(r => setTimeout(r, 800))")
        ancho = nav.evaluar("[document.documentElement.scrollWidth, window.innerWidth]")
        pr.check(ancho[0] <= ancho[1], f"celular: la página se desborda ({ancho[0]} > {ancho[1]} px)")
        if args.capturas:
            nav.captura(args.capturas / "06_celular.png")

        pr.check(not nav.errores, f"errores de JavaScript: {nav.errores}")
        pr.check(not nav.fallos_red, f"peticiones fallidas: {nav.fallos_red}")
    finally:
        nav.cerrar()
        if servidor:
            servidor.shutdown()

    print(f"Dashboard probado en {url}")
    print(f"Comprobaciones: {pr.ok} OK, {len(pr.fallas)} con falla ({len(DEPS) * 9} combinaciones de filtros)")
    for f in pr.fallas[:40]:
        print("  FALLA", f)
    sys.exit(1 if pr.fallas else 0)


if __name__ == "__main__":
    main()
