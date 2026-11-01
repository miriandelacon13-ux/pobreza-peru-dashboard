"""Captura las tarjetas del tablero publicado que usa el reel (reel/recursos/capturas/*.png).

Abre el tablero en un navegador sin interfaz con ancho de celular (540 px CSS a doble densidad = 1080 px de ancho),
pone cada combinación de filtros por la URL, espera a que quede dibujada y fotografía solo la tarjeta pedida.

Uso: uv run scripts/capturas_reel.py [--url https://…/web/]
"""

import argparse
import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from navegador import Navegador  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "reel/recursos/capturas"
URL = "https://miriandelacon13-ux.github.io/pobreza-peru-dashboard/web/"

TARJETA = "document.getElementById('{}').closest('.tarjeta')"
# nombre: (consulta de la URL, expresión JS del elemento a capturar)
CAPTURAS = {
    "portada": ("", "document.querySelector('header.portada')"),
    "mapa_total": ("", TARJETA.format("g-mapa")),
    "mapa_cajamarca": ("?dep=06", TARJETA.format("g-mapa")),
    "mapa_ica": ("?dep=11", TARJETA.format("g-mapa")),
    "ranking_total": ("", TARJETA.format("g-ranking")),
    "mapa_personas": ("?medida=personas", TARJETA.format("g-mapa")),
    "dispersion_lima": ("?dep=15", TARJETA.format("g-dispersion")),
    "brecha_total": ("", TARJETA.format("g-brecha")),
    "mapa_urbana": ("?area=urbana", TARJETA.format("g-mapa")),
    "mapa_rural": ("?area=rural", TARJETA.format("g-mapa")),
    "composicion_extrema": ("?tipo=extrema", TARJETA.format("g-composicion")),
    "mapa_rural_extrema": ("?area=rural&tipo=extrema", TARJETA.format("g-mapa")),
    "filtros_kpis_cusco": ("?dep=08", "document.querySelector('nav.filtros')"),
    "kpis_cusco_rural": ("?dep=08&area=rural", "document.querySelector('.kpis')"),
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=URL)
    args = ap.parse_args()
    SALIDA.mkdir(parents=True, exist_ok=True)

    nav = Navegador(ancho=540, alto=1000)
    nav.enviar("Emulation.setDeviceMetricsOverride", width=540, height=1000, deviceScaleFactor=2, mobile=True)
    nav.enviar("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])
    try:
        for nombre, (consulta, elemento) in CAPTURAS.items():
            nav.ir(args.url + consulta, "window.tablero && window.tablero.listo", segundos=90)
            time.sleep(0.8)  # transiciones de Plotly
            caja = nav.evaluar(f"""(() => {{ const e = {elemento}; e.scrollIntoView(); const r = e.getBoundingClientRect();
                return {{x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height}}; }})()""")
            r = nav.enviar("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                           clip={"x": caja["x"], "y": caja["y"], "width": caja["w"], "height": caja["h"], "scale": 1})
            (SALIDA / f"{nombre}.png").write_bytes(base64.b64decode(r["data"]))
            print(f"{nombre}: {int(caja['w'] * 2)}×{int(caja['h'] * 2)} px  ({consulta or 'sin filtros'})")
        if nav.errores or nav.fallos_red:
            sys.exit(f"Errores en la página: {nav.errores} {nav.fallos_red}")
    finally:
        nav.cerrar()
    (SALIDA / "LEEME.md").write_text(
        "Capturas del tablero publicado, hechas con `scripts/capturas_reel.py` (obra propia).\n\n"
        + "\n".join(f"- `{n}.png`: {URL}{c}" for n, (c, _) in CAPTURAS.items()) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
