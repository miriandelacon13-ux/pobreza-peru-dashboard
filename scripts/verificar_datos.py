"""Verifica las tablas de pobreza 2024 y escribe datos/procesados/verificacion.txt.

1. Integridad: el zip coincide con el manifiesto; 33,691 hogares; cada conglomerado está en un solo departamento y área.
2. Cifras externas: la pobreza nacional, extrema, urbana y rural frente a las publicadas por el INEI, los 25
   departamentos frente a la referencia del curso, y la explicación de las cifras absolutas del INEI.
3. Coherencia interna: los departamentos y las áreas suman el total nacional; pobreza total = extrema + no extrema;
   la tasa nacional es el cociente de los totales, no el promedio de las tasas departamentales; las diferencias y
   brechas cuadran con las tasas.
4. Error de muestreo: compara el error estándar linealizado (de tasas y de diferencias) con un bootstrap de
   conglomerados.

Termina con error si alguna comprobación falla.

Uso: uv run scripts/verificar_datos.py
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

P = Path("datos/procesados")
O = Path("datos/originales")
# INEI, «Perú: Evolución de la pobreza monetaria 2015-2024», según la cobertura de prensa del 8-9 may. 2025
# (el informe en gob.pe no permite la descarga automática). Coinciden con el README de la Sesión 16 del curso.
OFICIAL = {"Nacional": 27.6, "extrema": 5.5, "Urbana": 24.8, "Rural": 39.3}
POBRES_DIFUNDIDOS, EXTREMOS_DIFUNDIDOS = 9_395_000, 1_872_000  # «9 millones 395 mil» y «1 millón 872 mil», misma fuente
POBLACION_PROYECTADA_2024 = 34_038_457  # INEI, «Una mirada al Perú en cifras» Nº 7, julio 2024
TOLERANCIA_OFICIAL = 0.1  # puntos
TOLERANCIA_REFERENCIA = 0.05  # la referencia del curso viene redondeada a un decimal
Z95 = 1.959964
REPLICAS, SEMILLA = 500, 20241031


class Informe:
    def __init__(self):
        self.lineas, self.fallas = [], 0

    def seccion(self, t):
        self.lineas.append(f"\n## {t}")

    def check(self, ok, t):
        self.fallas += not ok
        self.lineas.append(f"[{'OK' if ok else 'FALLA'}] {t}")

    def info(self, t):
        self.lineas.append(f"[INFO] {t}")


class Bootstrap:
    """Réplicas de la muestra que remuestrean conglomerados con reemplazo (sin estratos)."""

    def __init__(self, h):
        psu = h.conglome.astype("category")
        self.codigos, n = psu.cat.codes.to_numpy(), len(psu.cat.categories)
        self.n, self.h = n, h
        rng = np.random.default_rng(SEMILLA)
        self.conteos = rng.multinomial(n, np.full(n, 1 / n), size=REPLICAS)  # veces que sale cada conglomerado

    def tasas(self, dominio, y="pobre"):
        w = np.where(dominio, self.h.peso.to_numpy(), 0.0)
        num = np.bincount(self.codigos, weights=w * self.h[y].to_numpy(), minlength=self.n)
        den = np.bincount(self.codigos, weights=w, minlength=self.n)
        return 100 * (self.conteos @ num) / (self.conteos @ den)


def ee_de_ic(inf, sup):
    return (sup - inf) / (2 * Z95)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    inf = Informe()
    h = pd.read_parquet(P / "hogares_2024.parquet")
    nac = pd.read_csv(P / "pobreza_nacional_area_2024.csv").set_index("ambito")
    dep = pd.read_csv(P / "pobreza_departamento_2024.csv", dtype={"ccdd": str})
    da = pd.read_csv(P / "pobreza_departamento_area_2024.csv", dtype={"ccdd": str})
    br = pd.read_csv(P / "brecha_urbano_rural_2024.csv", dtype={"ccdd": str})

    inf.seccion("1. Integridad de los datos")
    manifiesto = json.loads((O / "manifiesto.json").read_text(encoding="utf-8"))
    huella = hashlib.sha256((O / "966-Modulo34.zip").read_bytes()).hexdigest()
    inf.check(huella == manifiesto["966-Modulo34.zip"]["sha256"], f"966-Modulo34.zip coincide con el manifiesto (sha256 {huella[:16]}…)")
    inf.check(len(h) == 33_691 and not h.duplicated(["conglome", "vivienda", "hogar"]).any(), f"{len(h):,} hogares, sin duplicados")
    g = h.groupby("conglome")
    inf.check((g.departamento.nunique() == 1).all() and (g.area.nunique() == 1).all(),
              f"cada uno de los {h.conglome.nunique():,} conglomerados pertenece a un solo departamento y una sola área")
    inf.check(int(nac.loc["Nacional", "n_personas_muestra"]) == 109_842, "personas en la muestra (suma de mieperho): 109,842")

    inf.seccion("2. Cifras externas")
    for ambito in ["Nacional", "Urbana", "Rural"]:
        t = nac.loc[ambito, "tasa_pobreza"]
        inf.check(abs(t - OFICIAL[ambito]) < TOLERANCIA_OFICIAL and round(t, 1) == OFICIAL[ambito],
                  f"pobreza {ambito.lower()}: {t:.2f} % (INEI, cifra difundida por la prensa: {OFICIAL[ambito]} %)")
    t = nac.loc["Nacional", "tasa_pobreza_extrema"]
    inf.check(round(t, 1) == OFICIAL["extrema"], f"pobreza extrema nacional: {t:.2f} % (INEI, según la prensa: {OFICIAL['extrema']} %)")
    ref = pd.read_csv(O / "referencia_curso_pobreza_departamento_2024.csv", dtype={"ccdd": str}).set_index("ccdd").pobreza_pct
    dif = (dep.set_index("ccdd").tasa_pobreza - ref).abs()
    inf.check(len(dif) == 25 and dif.max() <= TOLERANCIA_REFERENCIA,
              f"25 departamentos frente a la referencia del curso: diferencia máxima {dif.max():.3f} puntos ({dif.idxmax()})")
    inei_pobres = round(OFICIAL["Nacional"] / 100 * POBLACION_PROYECTADA_2024, -3)
    inei_extremos = round(OFICIAL["extrema"] / 100 * POBLACION_PROYECTADA_2024, -3)
    inf.check(inei_pobres == POBRES_DIFUNDIDOS and inei_extremos == EXTREMOS_DIFUNDIDOS,
              f"cifras absolutas del INEI = tasa publicada × población proyectada 2024 ({POBLACION_PROYECTADA_2024:,}): "
              f"{OFICIAL['Nacional']} % → {inei_pobres:,.0f} y {OFICIAL['extrema']} % → {inei_extremos:,.0f}, iguales a las difundidas")
    pobres, poblacion = int(nac.loc["Nacional", "pobres_estimados"]), int(nac.loc["Nacional", "poblacion_estimada"])
    inf.info(f"estimación propia: {pobres:,} pobres sobre {poblacion:,} personas que expande la sumaria (factor07 × mieperho); "
             f"{pobres - POBRES_DIFUNDIDOS:+,} ({100 * (pobres / POBRES_DIFUNDIDOS - 1):+.1f} %) frente a la cifra del INEI, porque "
             f"la población de la expansión es {poblacion - POBLACION_PROYECTADA_2024:+,} mayor que la proyectada")

    inf.seccion("3. Coherencia interna")
    for col in ["poblacion_estimada", "pobres_estimados", "pobres_extremos_estimados"]:
        total = nac.loc["Nacional", col]
        inf.check(abs(dep[col].sum() - total) <= 25, f"suma de departamentos = nacional en {col} ({dep[col].sum():,} frente a {total:,})")
        inf.check(abs(nac.loc["Urbana", col] + nac.loc["Rural", col] - total) <= 2, f"urbana + rural = nacional en {col}")
        suma_da = da.groupby("ccdd")[col].sum()
        inf.check((suma_da - dep.set_index("ccdd")[col]).abs().max() <= 2, f"departamento × área suma al departamento en {col}")
    for nombre, t in [("nacional y áreas", nac), ("departamentos", dep), ("departamento × área", da)]:
        inf.check(((t.tasa_pobreza - t.tasa_pobreza_extrema - t.tasa_pobreza_no_extrema).abs() < 0.002).all()
                  and ((t.pobres_estimados - t.pobres_extremos_estimados - t.pobres_no_extremos_estimados).abs() <= 2).all(),
                  f"pobreza total = extrema + no extrema ({nombre})")
        inf.check(t.tasa_pobreza.between(0, 100).all() and (t.ic95_inf_pobreza <= t.tasa_pobreza).all()
                  and (t.tasa_pobreza <= t.ic95_sup_pobreza).all(), f"tasas entre 0 y 100 y dentro de su IC 95 % ({nombre})")
    desde_totales = 100 * dep.pobres_estimados.sum() / dep.poblacion_estimada.sum()
    inf.check(abs(desde_totales - nac.loc["Nacional", "tasa_pobreza"]) < 0.001,
              f"tasa nacional = pobres / población sumados por departamento ({desde_totales:.3f} %)")
    inf.info(f"el promedio simple de las 25 tasas departamentales sería {dep.tasa_pobreza.mean():.2f} %, no "
             f"{nac.loc['Nacional', 'tasa_pobreza']:.2f} %: promediar porcentajes ignora el tamaño de cada departamento")
    inf.check(len(da) == 49 and not ((da.ccdd == "07") & (da.area == "Rural")).any(),
              "departamento × área: 49 celdas (Callao no tiene hogares rurales en la muestra)")
    for tipo in ["pobreza", "pobreza_extrema", "pobreza_no_extrema"]:
        d = dep[f"tasa_{tipo}"] - nac.loc["Nacional", f"tasa_{tipo}"]
        cls = np.where(dep[f"ic95_inf_dif_nacional_{tipo}"] > 0, "mayor",
                       np.where(dep[f"ic95_sup_dif_nacional_{tipo}"] < 0, "menor", "no distinguible"))
        inf.check(((d - dep[f"dif_nacional_{tipo}"]).abs() < 0.002).all() and (cls == dep[f"comparacion_nacional_{tipo}"]).all(),
                  f"{tipo}: diferencia departamento − país = resta de tasas y clasificación coherente con su IC 95 %")
        b = br[br.tipo == tipo].set_index("ccdd")
        u = da[da.area == "Urbana"].set_index("ccdd")[f"tasa_{tipo}"]
        r = da[da.area == "Rural"].set_index("ccdd")[f"tasa_{tipo}"]
        bd = b.drop(index="00")
        inf.check(len(b) == 25 and ((bd.brecha_pp - (r - u).reindex(bd.index)).abs() < 0.002).all()
                  and abs(b.loc["00", "brecha_pp"] - (nac.loc["Rural", f"tasa_{tipo}"] - nac.loc["Urbana", f"tasa_{tipo}"])) < 0.002,
                  f"{tipo}: brecha = tasa rural − tasa urbana en el país y en los 24 departamentos con ambas áreas")
    lima = dep.set_index("departamento").loc["Lima"]
    inf.info(f"Lima: {lima.tasa_pobreza:.2f} % frente a {nac.loc['Nacional', 'tasa_pobreza']:.2f} % nacional; diferencia "
             f"{lima.dif_nacional_pobreza:+.2f} puntos (IC 95 % {lima.ic95_inf_dif_nacional_pobreza:+.2f} a "
             f"{lima.ic95_sup_dif_nacional_pobreza:+.2f}): {lima.comparacion_nacional_pobreza}")

    inf.seccion(f"4. Error de muestreo: linealización frente a bootstrap de conglomerados ({REPLICAS} réplicas)")
    bs = Bootstrap(h)
    pais = np.ones(len(h), dtype=bool)
    dom = {"Nacional": pais, "Urbana": (h.area == "Urbana").to_numpy(), "Rural": (h.area == "Rural").to_numpy(),
           "Lima": (h.departamento == "15").to_numpy(), "Cajamarca": (h.departamento == "06").to_numpy(),
           "Ica": (h.departamento == "11").to_numpy()}
    rep = {k: bs.tasas(v) for k, v in dom.items()}
    dep_i = dep.set_index("departamento")
    for nombre, tasas in rep.items():
        se_l = nac.loc[nombre, "ee_pobreza"] if nombre in nac.index else dep_i.loc[nombre, "ee_pobreza"]
        razon = np.std(tasas, ddof=1) / se_l
        inf.check(0.8 <= razon <= 1.25, f"tasa {nombre}: EE linealizado {se_l:.3f}, bootstrap {np.std(tasas, ddof=1):.3f}, razón {razon:.2f}")
    for nombre in ["Lima", "Cajamarca"]:
        se_l = ee_de_ic(dep_i.loc[nombre, "ic95_inf_dif_nacional_pobreza"], dep_i.loc[nombre, "ic95_sup_dif_nacional_pobreza"])
        se_b = np.std(rep[nombre] - rep["Nacional"], ddof=1)
        inf.check(0.8 <= se_b / se_l <= 1.25, f"diferencia {nombre} − país: EE linealizado {se_l:.3f}, bootstrap {se_b:.3f}, razón {se_b / se_l:.2f}")
    b0 = br[(br.ccdd == "00") & (br.tipo == "pobreza")].iloc[0]
    se_b = np.std(rep["Rural"] - rep["Urbana"], ddof=1)
    inf.check(0.8 <= se_b / b0.ee_brecha <= 1.25,
              f"brecha rural − urbana del país: EE linealizado {b0.ee_brecha:.3f}, bootstrap {se_b:.3f}, razón {se_b / b0.ee_brecha:.2f}")
    refer = dep[dep.precision_pobreza == "referencial"].departamento.tolist()
    inf.info(f"departamentos con CV > 15 % en la pobreza total (estimación referencial): {', '.join(refer) or 'ninguno'}")

    resultado = "OK" if inf.fallas == 0 else f"FALLA ({inf.fallas} comprobaciones)"
    texto = "\n".join(["# Verificación de las tablas de pobreza 2024", "Fuente: INEI, ENAHO 2024, módulo 34 (Sumaria). "
                       "Alternativa B: miembros del hogar, factor07 × mieperho, una fila por hogar."] + inf.lineas
                      + [f"\nRESULTADO: {resultado}", ""])
    (P / "verificacion.txt").write_text(texto, encoding="utf-8")
    print(texto)
    if inf.fallas:
        sys.exit(1)


if __name__ == "__main__":
    main()
