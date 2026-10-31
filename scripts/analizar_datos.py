"""Tasas de pobreza monetaria 2024 por departamento y área, con población estimada y error de muestreo.

Cada tasa es un cociente ponderado calculado desde los hogares: suma de factor07 × mieperho de los hogares pobres
entre la suma de factor07 × mieperho de todos los hogares del grupo. Nunca se promedian porcentajes.

El error estándar usa linealización de Taylor para un cociente, con el conglomerado como unidad primaria de muestreo,
como el do-file oficial del INEI (`svyset [pweight = factor07*mieperho], psu(conglome)`). No usa estratos, igual que ese
do-file. Los dominios (departamento, área) se estiman sobre la muestra completa, con ceros fuera del dominio.

Entra: datos/procesados/hogares_2024.parquet (corre antes scripts/procesar_datos.py)
Sale:  datos/procesados/pobreza_nacional_area_2024.csv
       datos/procesados/pobreza_departamento_2024.csv
       datos/procesados/pobreza_departamento_area_2024.csv
       datos/procesados/brecha_urbano_rural_2024.csv
       datos/procesados/cifras_clave_2024.json

Uso: uv run scripts/analizar_datos.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("datos/procesados/hogares_2024.parquet")
PROCESADOS = Path("datos/procesados")
Z95 = 1.959964
CV_MAXIMO = 15.0  # % : por encima, la estimación se marca como referencial en este proyecto


def linealizar(h, dominio, y):
    """Tasa (%) del dominio y contribución de cada conglomerado a su varianza."""
    w = h.peso.where(dominio, 0.0)
    total = w.sum()
    tasa = (w * h[y]).sum() / total
    z = (w * (h[y] - tasa) / total).groupby(h.conglome).sum()  # incluye conglomerados fuera del dominio con 0
    return 100 * tasa, 100 * z


def error_estandar(z):
    n = len(z)
    return float(np.sqrt(n / (n - 1) * ((z - z.mean()) ** 2).sum()))


def estimar(h, dominio):
    d = h[dominio]
    fila = {
        "n_hogares": len(d),
        "n_conglomerados": d.conglome.nunique(),
        "n_personas_muestra": int(d.mieperho.sum()),
        "poblacion_estimada": round(d.peso.sum()),
        "pobres_estimados": round((d.peso * d.pobre).sum()),
        "pobres_extremos_estimados": round((d.peso * d.pobre_extremo).sum()),
        "pobres_no_extremos_estimados": round((d.peso * d.pobre_no_extremo).sum()),
    }
    for nombre, y in [("pobreza", "pobre"), ("pobreza_extrema", "pobre_extremo"), ("pobreza_no_extrema", "pobre_no_extremo")]:
        tasa, z = linealizar(h, dominio, y)
        ee = error_estandar(z)
        fila[f"tasa_{nombre}"] = tasa
        fila[f"ee_{nombre}"] = ee
        fila[f"ic95_inf_{nombre}"] = max(0.0, tasa - Z95 * ee)
        fila[f"ic95_sup_{nombre}"] = tasa + Z95 * ee
        fila[f"cv_{nombre}"] = 100 * ee / tasa if tasa > 0 else np.nan
    fila["precision_pobreza"] = "adecuada" if fila["cv_pobreza"] <= CV_MAXIMO else "referencial"
    return fila


def brecha(h, dominio_rural, dominio_urbano):
    """Brecha rural - urbana en puntos porcentuales, con su error estándar (incluye la covarianza)."""
    tr, zr = linealizar(h, dominio_rural, "pobre")
    tu, zu = linealizar(h, dominio_urbano, "pobre")
    ee = error_estandar(zr - zu)
    b = tr - tu
    return {
        "tasa_urbana": tu, "tasa_rural": tr, "brecha_pp": b, "ee_brecha": ee,
        "ic95_inf_brecha": b - Z95 * ee, "ic95_sup_brecha": b + Z95 * ee,
        "brecha_significativa_95": bool(abs(b) > Z95 * ee),
        "razon_rural_urbana": tr / tu,
    }


def redondear(df):
    tasas = [c for c in df.columns if c.startswith(("tasa_", "ee_", "ic95_", "cv_", "brecha_pp", "participacion", "razon"))]
    return df.round({c: 3 for c in tasas})


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if not BASE.exists():
        sys.exit(f"Falta {BASE}. Corre antes: uv run scripts/procesar_datos.py")
    h = pd.read_parquet(BASE)
    todos = pd.Series(True, index=h.index)
    urbano, rural = h.area == "Urbana", h.area == "Rural"

    # Nacional y por área
    nacional = pd.DataFrame([{"ambito": nombre, **estimar(h, dom)}
                             for nombre, dom in [("Nacional", todos), ("Urbana", urbano), ("Rural", rural)]])
    pobres_pais = nacional.loc[0, "pobres_estimados"]
    nacional["participacion_en_pobres_pct"] = 100 * nacional.pobres_estimados / pobres_pais

    # Por departamento
    deps = h[["departamento", "nombre_departamento"]].drop_duplicates().sort_values("departamento")
    departamento = pd.DataFrame([
        {"ccdd": c, "departamento": n, **estimar(h, h.departamento == c)} for c, n in deps.itertuples(index=False)
    ])
    departamento["participacion_en_pobres_pct"] = 100 * departamento.pobres_estimados / pobres_pais

    # Por departamento y área (Callao no tiene hogares rurales en la muestra)
    filas = []
    for c, n in deps.itertuples(index=False):
        for area, dom_area in [("Urbana", urbano), ("Rural", rural)]:
            dom = (h.departamento == c) & dom_area
            if dom.any():
                filas.append({"ccdd": c, "departamento": n, "area": area, **estimar(h, dom)})
    dep_area = pd.DataFrame(filas)
    dep_area["participacion_en_pobres_del_departamento_pct"] = 100 * dep_area.pobres_estimados / dep_area.ccdd.map(
        departamento.set_index("ccdd").pobres_estimados)

    # Brecha rural - urbana: país y cada departamento con ambas áreas
    brechas = [{"ccdd": "00", "departamento": "Perú", **brecha(h, rural, urbano)}]
    for c, n in deps.itertuples(index=False):
        es_dep = h.departamento == c
        if (es_dep & rural).any() and (es_dep & urbano).any():
            brechas.append({"ccdd": c, "departamento": n, **brecha(h, es_dep & rural, es_dep & urbano)})
    brecha_df = pd.DataFrame(brechas)

    PROCESADOS.mkdir(parents=True, exist_ok=True)
    redondear(nacional).to_csv(PROCESADOS / "pobreza_nacional_area_2024.csv", index=False, encoding="utf-8")
    redondear(departamento).to_csv(PROCESADOS / "pobreza_departamento_2024.csv", index=False, encoding="utf-8")
    redondear(dep_area).to_csv(PROCESADOS / "pobreza_departamento_area_2024.csv", index=False, encoding="utf-8")
    redondear(brecha_df).to_csv(PROCESADOS / "brecha_urbano_rural_2024.csv", index=False, encoding="utf-8")

    # Cifras clave para los hallazgos y el dashboard
    n = nacional.set_index("ambito")
    dep = departamento.set_index("departamento")
    mayor, menor = dep.tasa_pobreza.idxmax(), dep.tasa_pobreza.idxmin()
    sobre_nacional = dep[dep.ic95_inf_pobreza > n.loc["Nacional", "tasa_pobreza"]].index.tolist()
    bajo_nacional = dep[dep.ic95_sup_pobreza < n.loc["Nacional", "tasa_pobreza"]].index.tolist()
    top5 = dep.sort_values("pobres_estimados", ascending=False).head(5)
    b = brecha_df.set_index("departamento")
    b_dep = b.drop(index="Perú")
    cifras = {
        "fuente": "INEI, ENAHO 2024 (módulo 34, Sumaria); cálculo propio con factor07 × mieperho",
        "nacional": {
            "tasa_pobreza": n.loc["Nacional", "tasa_pobreza"],
            "ic95_pobreza": [n.loc["Nacional", "ic95_inf_pobreza"], n.loc["Nacional", "ic95_sup_pobreza"]],
            "tasa_pobreza_extrema": n.loc["Nacional", "tasa_pobreza_extrema"],
            "tasa_pobreza_no_extrema": n.loc["Nacional", "tasa_pobreza_no_extrema"],
            "poblacion_estimada": int(n.loc["Nacional", "poblacion_estimada"]),
            "pobres_estimados": int(n.loc["Nacional", "pobres_estimados"]),
            "pobres_extremos_estimados": int(n.loc["Nacional", "pobres_extremos_estimados"]),
            "hogares_muestra": int(n.loc["Nacional", "n_hogares"]),
        },
        "area": {
            a: {
                "tasa_pobreza": n.loc[a, "tasa_pobreza"],
                "tasa_pobreza_extrema": n.loc[a, "tasa_pobreza_extrema"],
                "pobres_estimados": int(n.loc[a, "pobres_estimados"]),
                "pobres_extremos_estimados": int(n.loc[a, "pobres_extremos_estimados"]),
                "participacion_en_pobres_pct": n.loc[a, "participacion_en_pobres_pct"],
                "participacion_en_pobres_extremos_pct": 100 * n.loc[a, "pobres_extremos_estimados"] / n.loc["Nacional", "pobres_extremos_estimados"],
                "participacion_en_poblacion_pct": 100 * n.loc[a, "poblacion_estimada"] / n.loc["Nacional", "poblacion_estimada"],
            } for a in ["Urbana", "Rural"]
        },
        "brecha_nacional": {k: (float(v) if not isinstance(v, (bool, np.bool_)) else bool(v)) for k, v in b.loc["Perú"].drop("ccdd").items()},
        "departamentos": {
            "mayor_tasa": {"departamento": mayor, "tasa": dep.loc[mayor, "tasa_pobreza"],
                           "ic95": [dep.loc[mayor, "ic95_inf_pobreza"], dep.loc[mayor, "ic95_sup_pobreza"]]},
            "menor_tasa": {"departamento": menor, "tasa": dep.loc[menor, "tasa_pobreza"],
                           "ic95": [dep.loc[menor, "ic95_inf_pobreza"], dep.loc[menor, "ic95_sup_pobreza"]]},
            "por_encima_del_nacional_con_ic95": sobre_nacional,
            "por_debajo_del_nacional_con_ic95": bajo_nacional,
            "mas_pobres_en_numero": [{"departamento": d, "pobres": int(r.pobres_estimados), "tasa": r.tasa_pobreza,
                                      "participacion_pct": r.participacion_en_pobres_pct} for d, r in top5.iterrows()],
            "promedio_simple_de_tasas": float(dep.tasa_pobreza.mean()),
            "referenciales_cv_mayor_15": dep[dep.precision_pobreza == "referencial"].index.tolist(),
        },
        "brecha_por_departamento": {
            "mayor": {"departamento": b_dep.brecha_pp.idxmax(), "brecha_pp": b_dep.brecha_pp.max()},
            "menor": {"departamento": b_dep.brecha_pp.idxmin(), "brecha_pp": b_dep.brecha_pp.min()},
            "significativas_95": int(b_dep.brecha_significativa_95.sum()),
            "con_ambas_areas": len(b_dep),
            "rural_menor_que_urbana": b_dep[b_dep.brecha_pp < 0].index.tolist(),
        },
    }
    (PROCESADOS / "cifras_clave_2024.json").write_text(
        json.dumps(cifras, ensure_ascii=False, indent=2, default=float), encoding="utf-8")

    cols = ["tasa_pobreza", "ic95_inf_pobreza", "ic95_sup_pobreza", "tasa_pobreza_extrema", "poblacion_estimada", "pobres_estimados"]
    print(nacional.set_index("ambito")[cols + ["participacion_en_pobres_pct"]].round(2).to_string())
    print()
    print(departamento.set_index("departamento")[cols + ["cv_pobreza", "participacion_en_pobres_pct"]]
          .sort_values("tasa_pobreza", ascending=False).round(2).to_string())
    print()
    print(brecha_df.set_index("departamento")[["tasa_urbana", "tasa_rural", "brecha_pp", "ic95_inf_brecha", "ic95_sup_brecha",
                                                "brecha_significativa_95"]].sort_values("brecha_pp", ascending=False).round(2).to_string())
    print(f"\nTablas y cifras clave en {PROCESADOS}/")


if __name__ == "__main__":
    main()
