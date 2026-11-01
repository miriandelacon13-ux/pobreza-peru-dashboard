"""Exporta las tablas verificadas al formato que lee el dashboard (web/data/).

El dashboard no recalcula tasas: todas salen de datos/procesados/, que calcula scripts/analizar_datos.py desde los
hogares. Una celda sin hogares en la muestra (Callao rural) se exporta como null, nunca como cero.

Entra: datos/procesados/*.csv, cifras_clave_2024.json y datos/originales/peru_departamental_simple.geojson
Sale:  web/data/pobreza_2024.json y web/data/departamentos.geojson

Uso: uv run scripts/exportar_web.py
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

P = Path("datos/procesados")
O = Path("datos/originales")
WEB = Path("web/data")
TIPOS = {"total": "pobreza", "extrema": "pobreza_extrema", "no_extrema": "pobreza_no_extrema"}
CONTEO = {"total": "pobres_estimados", "extrema": "pobres_extremos_estimados", "no_extrema": "pobres_no_extremos_estimados"}


def num(x, nd=3):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), nd)


def celda(r, sufijo=None):
    """Una estimación (país, área, departamento o departamento × área) con sus tres tipos de pobreza."""
    salida = {"n_hogares": int(r.n_hogares), "poblacion": int(r.poblacion_estimada), "tipos": {}}
    for clave, t in TIPOS.items():
        d = {
            "tasa": num(r[f"tasa_{t}"]), "ic": [num(r[f"ic95_inf_{t}"]), num(r[f"ic95_sup_{t}"])],
            "cv": num(r[f"cv_{t}"], 1), "precision": r[f"precision_{t}"], "personas": int(r[CONTEO[clave]]),
        }
        if sufijo:
            d["dif"] = num(r[f"dif_{sufijo}_{t}"])
            d["dif_ic"] = [num(r[f"ic95_inf_dif_{sufijo}_{t}"]), num(r[f"ic95_sup_dif_{sufijo}_{t}"])]
            d["comparacion"] = r[f"comparacion_{sufijo}_{t}"]
        salida["tipos"][clave] = d
    return salida


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    nac = pd.read_csv(P / "pobreza_nacional_area_2024.csv").set_index("ambito")
    dep = pd.read_csv(P / "pobreza_departamento_2024.csv", dtype={"ccdd": str})
    da = pd.read_csv(P / "pobreza_departamento_area_2024.csv", dtype={"ccdd": str})
    br = pd.read_csv(P / "brecha_urbano_rural_2024.csv", dtype={"ccdd": str})
    cifras = json.loads((P / "cifras_clave_2024.json").read_text(encoding="utf-8"))

    def brechas(ccdd):
        filas = br[br.ccdd == ccdd]
        if filas.empty:
            return None
        inv = {v: k for k, v in TIPOS.items()}
        return {inv[f.tipo]: {"brecha": num(f.brecha_pp), "ic": [num(f.ic95_inf_brecha), num(f.ic95_sup_brecha)],
                              "clara": bool(f.brecha_significativa_95), "urbana": num(f.tasa_urbana),
                              "rural": num(f.tasa_rural)} for f in filas.itertuples()}

    departamentos = []
    for r in dep.itertuples(index=False):
        r = dep[dep.ccdd == r.ccdd].iloc[0]
        areas = {}
        for area in ["Urbana", "Rural"]:
            fila = da[(da.ccdd == r.ccdd) & (da.area == area)]
            areas[area.lower()] = celda(fila.iloc[0], "area_nacional") if len(fila) else None
        departamentos.append({"ccdd": r.ccdd, "nombre": r.departamento, "total": celda(r, "nacional"),
                              **areas, "brecha": brechas(r.ccdd)})

    datos = {
        "meta": {
            "titulo": "Pobreza monetaria en el Perú, 2024",
            "fuente": "INEI, Encuesta Nacional de Hogares (ENAHO) 2024, módulo 34 (Sumaria)",
            "metodo": "Miembros del hogar; cada hogar pesa factor07 × mieperho; una fila por hogar",
            "absolutos": cifras["cifras_absolutas_inei"],
            "mayor_tasa_vs_siguientes": cifras["departamentos"]["mayor_tasa"]["frente_a_los_cuatro_siguientes"],
        },
        "nacional": {"total": celda(nac.loc["Nacional"]), "urbana": celda(nac.loc["Urbana"]),
                     "rural": celda(nac.loc["Rural"]), "brecha": brechas("00")},
        "departamentos": departamentos,
    }
    WEB.mkdir(parents=True, exist_ok=True)
    (WEB / "pobreza_2024.json").write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    geo = json.loads((O / "peru_departamental_simple.geojson").read_text(encoding="utf-8"))
    for f in geo["features"]:
        f["properties"] = {"ccdd": str(f["properties"]["FIRST_IDDP"]).zfill(2), "nombre_geojson": f["properties"]["NOMBDEP"]}
    codigos = sorted(f["properties"]["ccdd"] for f in geo["features"])
    if codigos != sorted(d["ccdd"] for d in departamentos):
        sys.exit("Los códigos del GeoJSON no coinciden con los 25 departamentos de la ENAHO")
    (WEB / "departamentos.geojson").write_text(json.dumps(geo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    sin_dato = [f"{d['nombre']} ({a})" for d in departamentos for a in ("urbana", "rural") if d[a] is None]
    print(f"web/data/pobreza_2024.json: {len(departamentos)} departamentos; celdas sin hogares en la muestra: {sin_dato}")
    print(f"web/data/departamentos.geojson: {len(geo['features'])} polígonos unidos por código (FIRST_IDDP → ccdd)")


if __name__ == "__main__":
    main()
