"""Tasas de pobreza monetaria 2024 por departamento y área, con población estimada y error de muestreo.

Cada tasa es un cociente ponderado calculado desde los hogares: suma de factor07 × mieperho de los hogares pobres
entre la suma de factor07 × mieperho de todos los hogares del grupo. Nunca se promedian porcentajes.

El error estándar usa linealización de Taylor para un cociente, con el conglomerado como unidad primaria de muestreo,
como el do-file oficial del INEI (`svyset [pweight = factor07*mieperho], psu(conglome)`). No usa estratos, igual que ese
do-file. Los dominios (departamento, área) se estiman sobre la muestra completa, con ceros fuera del dominio.

Las comparaciones (departamento frente al país, rural frente a urbano) se hacen sobre la DIFERENCIA de tasas, con el
error estándar de esa diferencia, que incluye la covarianza: un departamento forma parte del total nacional. Una
diferencia es «clara» (estadísticamente significativa al 95 %) cuando su intervalo de confianza no incluye el cero.

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
TIPOS = {"pobreza": "pobre", "pobreza_extrema": "pobre_extremo", "pobreza_no_extrema": "pobre_no_extremo"}
# INEI, «Una mirada al Perú en cifras» Nº 7, julio 2024: población total proyectada al 2024
POBLACION_PROYECTADA_INEI_2024 = 34_038_457


class Diseno:
    """Muestra de hogares con su unidad primaria de muestreo (conglomerado)."""

    def __init__(self, h):
        self.h = h
        psu = h.conglome.astype("category")
        self.psu = psu.cat.codes.to_numpy()
        self.n_psu = len(psu.cat.categories)
        self.peso = h.peso.to_numpy()

    def linealizar(self, dominio, y):
        """Tasa (%) del dominio y contribución de cada conglomerado a su varianza."""
        w = np.where(dominio, self.peso, 0.0)
        valores = self.h[y].to_numpy(dtype=float)
        total = w.sum()
        tasa = (w * valores).sum() / total
        z = np.bincount(self.psu, weights=w * (valores - tasa) / total, minlength=self.n_psu)
        return 100 * tasa, 100 * z

    def error_estandar(self, z):
        return float(np.sqrt(self.n_psu / (self.n_psu - 1) * ((z - z.mean()) ** 2).sum()))

    def diferencia(self, dom_a, dom_b, y):
        """Tasa(a) - tasa(b) en puntos, con su error estándar e IC 95 % (incluye la covarianza)."""
        ta, za = self.linealizar(dom_a, y)
        tb, zb = self.linealizar(dom_b, y)
        d, ee = ta - tb, self.error_estandar(za - zb)
        return d, ee, d - Z95 * ee, d + Z95 * ee


def clasificar(inf, sup):
    return "mayor" if inf > 0 else "menor" if sup < 0 else "no distinguible"


def estimar(dis, dominio):
    d = dis.h[dominio]
    fila = {
        "n_hogares": len(d),
        "n_conglomerados": d.conglome.nunique(),
        "n_personas_muestra": int(d.mieperho.sum()),
        "poblacion_estimada": round(d.peso.sum()),
        "pobres_estimados": round((d.peso * d.pobre).sum()),
        "pobres_extremos_estimados": round((d.peso * d.pobre_extremo).sum()),
        "pobres_no_extremos_estimados": round((d.peso * d.pobre_no_extremo).sum()),
    }
    for nombre, y in TIPOS.items():
        tasa, z = dis.linealizar(dominio, y)
        ee = dis.error_estandar(z)
        fila[f"tasa_{nombre}"] = tasa
        fila[f"ee_{nombre}"] = ee
        fila[f"ic95_inf_{nombre}"] = max(0.0, tasa - Z95 * ee)
        fila[f"ic95_sup_{nombre}"] = tasa + Z95 * ee
        fila[f"cv_{nombre}"] = 100 * ee / tasa if tasa > 0 else np.nan
        fila[f"precision_{nombre}"] = "adecuada" if fila[f"cv_{nombre}"] <= CV_MAXIMO else "referencial"
    return fila


def comparar(dis, dominio, referencia, sufijo):
    """Diferencia del dominio frente a una referencia (el país o la misma área en el país), por tipo de pobreza."""
    fila = {}
    for nombre, y in TIPOS.items():
        d, ee, inf, sup = dis.diferencia(dominio, referencia, y)
        fila[f"dif_{sufijo}_{nombre}"] = d
        fila[f"ic95_inf_dif_{sufijo}_{nombre}"] = inf
        fila[f"ic95_sup_dif_{sufijo}_{nombre}"] = sup
        fila[f"comparacion_{sufijo}_{nombre}"] = clasificar(inf, sup)
    return fila


def brechas(dis, ccdd, nombre, rural, urbano):
    filas = []
    for tipo, y in TIPOS.items():
        tr, _ = dis.linealizar(rural, y)
        tu, _ = dis.linealizar(urbano, y)
        b, ee, inf, sup = dis.diferencia(rural, urbano, y)
        filas.append({
            "ccdd": ccdd, "departamento": nombre, "tipo": tipo, "tasa_urbana": tu, "tasa_rural": tr,
            "brecha_pp": b, "ee_brecha": ee, "ic95_inf_brecha": inf, "ic95_sup_brecha": sup,
            "brecha_significativa_95": bool(inf > 0 or sup < 0),
            "razon_rural_urbana": tr / tu if tu > 0 else np.nan,
        })
    return filas


def redondear(df):
    prefijos = ("tasa_", "ee_", "ic95_", "cv_", "brecha_pp", "participacion", "razon", "dif_")
    return df.round({c: 3 for c in df.columns if c.startswith(prefijos)})


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if not BASE.exists():
        sys.exit(f"Falta {BASE}. Corre antes: uv run scripts/procesar_datos.py")
    h = pd.read_parquet(BASE)
    dis = Diseno(h)
    pais = np.ones(len(h), dtype=bool)
    urbano, rural = (h.area == "Urbana").to_numpy(), (h.area == "Rural").to_numpy()
    area_dom = {"Urbana": urbano, "Rural": rural}

    # Nacional y por área
    nacional = pd.DataFrame([{"ambito": n, **estimar(dis, d)} for n, d in [("Nacional", pais), ("Urbana", urbano), ("Rural", rural)]])
    pobres_pais = nacional.loc[0, "pobres_estimados"]
    nacional["participacion_en_pobres_pct"] = 100 * nacional.pobres_estimados / pobres_pais

    # Por departamento, comparado con el país
    deps = h[["departamento", "nombre_departamento"]].drop_duplicates().sort_values("departamento")
    filas = []
    for c, n in deps.itertuples(index=False):
        dom = (h.departamento == c).to_numpy()
        filas.append({"ccdd": c, "departamento": n, **estimar(dis, dom), **comparar(dis, dom, pais, "nacional")})
    departamento = pd.DataFrame(filas)
    departamento["participacion_en_pobres_pct"] = 100 * departamento.pobres_estimados / pobres_pais

    # ¿El departamento con la tasa más alta se distingue de los cuatro siguientes?
    top = departamento.sort_values("tasa_pobreza", ascending=False).head(5)
    lider = (h.departamento == top.iloc[0].ccdd).to_numpy()
    comparacion_top = []
    for r in top.iloc[1:].itertuples():
        d, _, i, s = dis.diferencia(lider, (h.departamento == r.ccdd).to_numpy(), "pobre")
        comparacion_top.append({"frente_a": r.departamento, "dif_pp": d, "ic95": [i, s], "comparacion": clasificar(i, s)})

    # Por departamento y área, comparado con la misma área en el país (Callao no tiene hogares rurales en la muestra)
    filas = []
    for c, n in deps.itertuples(index=False):
        es_dep = (h.departamento == c).to_numpy()
        for area, dom_area in area_dom.items():
            dom = es_dep & dom_area
            if dom.any():
                filas.append({"ccdd": c, "departamento": n, "area": area, **estimar(dis, dom),
                              **comparar(dis, dom, dom_area, "area_nacional")})
    dep_area = pd.DataFrame(filas)
    dep_area["participacion_en_pobres_del_departamento_pct"] = 100 * dep_area.pobres_estimados / dep_area.ccdd.map(
        departamento.set_index("ccdd").pobres_estimados)

    # Brecha rural - urbana por tipo de pobreza: país y cada departamento con ambas áreas
    filas = brechas(dis, "00", "Perú", rural, urbano)
    for c, n in deps.itertuples(index=False):
        es_dep = (h.departamento == c).to_numpy()
        if (es_dep & rural).any() and (es_dep & urbano).any():
            filas += brechas(dis, c, n, es_dep & rural, es_dep & urbano)
    brecha_df = pd.DataFrame(filas)

    PROCESADOS.mkdir(parents=True, exist_ok=True)
    redondear(nacional).to_csv(PROCESADOS / "pobreza_nacional_area_2024.csv", index=False, encoding="utf-8")
    redondear(departamento).to_csv(PROCESADOS / "pobreza_departamento_2024.csv", index=False, encoding="utf-8")
    redondear(dep_area).to_csv(PROCESADOS / "pobreza_departamento_area_2024.csv", index=False, encoding="utf-8")
    redondear(brecha_df).to_csv(PROCESADOS / "brecha_urbano_rural_2024.csv", index=False, encoding="utf-8")

    # Cifras clave para los hallazgos y el dashboard
    n = nacional.set_index("ambito")
    dep = departamento.set_index("departamento")
    mayor, menor = dep.tasa_pobreza.idxmax(), dep.tasa_pobreza.idxmin()
    top5 = dep.sort_values("pobres_estimados", ascending=False).head(5)
    bt = brecha_df[brecha_df.tipo == "pobreza"].set_index("departamento")
    bt_dep = bt.drop(index="Perú")
    lima = dep.loc["Lima"]
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
        "cifras_absolutas_inei": {
            "nota": "El INEI difundió 9 395 000 pobres y 1 872 000 pobres extremos (prensa, mayo 2025). Equivalen a la tasa "
                    "publicada (27.6 % y 5.5 %) × la población proyectada al 2024. Las cifras absolutas de este proyecto son "
                    "estimaciones propias: expanden la muestra con factor07 × mieperho.",
            "poblacion_proyectada_2024": POBLACION_PROYECTADA_INEI_2024,
            "fuente_poblacion": "INEI, Una mirada al Perú en cifras, Nº 7, julio 2024",
            "pobres_difundidos": 9_395_000,
            "pobres_extremos_difundidos": 1_872_000,
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
        "brecha_nacional": {
            fila.tipo: {"brecha_pp": fila.brecha_pp, "ic95": [fila.ic95_inf_brecha, fila.ic95_sup_brecha],
                        "razon_rural_urbana": fila.razon_rural_urbana}
            for fila in brecha_df[brecha_df.ccdd == "00"].itertuples()
        },
        "departamentos": {
            "mayor_tasa": {"departamento": mayor, "tasa": dep.loc[mayor, "tasa_pobreza"],
                           "ic95": [dep.loc[mayor, "ic95_inf_pobreza"], dep.loc[mayor, "ic95_sup_pobreza"]],
                           "frente_a_los_cuatro_siguientes": comparacion_top},
            "menor_tasa": {"departamento": menor, "tasa": dep.loc[menor, "tasa_pobreza"],
                           "ic95": [dep.loc[menor, "ic95_inf_pobreza"], dep.loc[menor, "ic95_sup_pobreza"]]},
            "mayor_que_el_nacional": dep[dep.comparacion_nacional_pobreza == "mayor"].index.tolist(),
            "menor_que_el_nacional": dep[dep.comparacion_nacional_pobreza == "menor"].index.tolist(),
            "no_distinguible_del_nacional": dep[dep.comparacion_nacional_pobreza == "no distinguible"].index.tolist(),
            "lima": {"tasa": lima.tasa_pobreza, "dif_vs_nacional_pp": lima.dif_nacional_pobreza,
                     "ic95_dif": [lima.ic95_inf_dif_nacional_pobreza, lima.ic95_sup_dif_nacional_pobreza],
                     "comparacion": lima.comparacion_nacional_pobreza, "pobres_estimados": int(lima.pobres_estimados),
                     "participacion_en_pobres_pct": lima.participacion_en_pobres_pct},
            "mas_pobres_en_numero": [{"departamento": d, "pobres": int(r.pobres_estimados), "tasa": r.tasa_pobreza,
                                      "participacion_pct": r.participacion_en_pobres_pct} for d, r in top5.iterrows()],
            "promedio_simple_de_tasas": float(dep.tasa_pobreza.mean()),
            "referenciales_cv_mayor_15": dep[dep.precision_pobreza == "referencial"].index.tolist(),
        },
        "brecha_por_departamento": {
            "mayor": {"departamento": bt_dep.brecha_pp.idxmax(), "brecha_pp": bt_dep.brecha_pp.max()},
            "rural_mayor_significativa": bt_dep[bt_dep.ic95_inf_brecha > 0].index.tolist(),
            "rural_menor_significativa": bt_dep[bt_dep.ic95_sup_brecha < 0].index.tolist(),
            "no_significativa": bt_dep[~bt_dep.brecha_significativa_95].index.tolist(),
            "con_ambas_areas": len(bt_dep),
        },
    }
    (PROCESADOS / "cifras_clave_2024.json").write_text(
        json.dumps(cifras, ensure_ascii=False, indent=2, default=float), encoding="utf-8")

    cols = ["tasa_pobreza", "ic95_inf_pobreza", "ic95_sup_pobreza", "dif_nacional_pobreza", "comparacion_nacional_pobreza",
            "pobres_estimados", "participacion_en_pobres_pct"]
    print(nacional.set_index("ambito")[["tasa_pobreza", "ic95_inf_pobreza", "ic95_sup_pobreza", "tasa_pobreza_extrema",
                                        "poblacion_estimada", "pobres_estimados"]].round(2).to_string())
    print()
    print(dep[cols].sort_values("tasa_pobreza", ascending=False).round(2).to_string())
    print()
    print(brecha_df.pivot(index="departamento", columns="tipo", values="brecha_pp").round(2).to_string())
    print(f"\nTablas y cifras clave en {PROCESADOS}/")


if __name__ == "__main__":
    main()
