"""Verifica el guion del reel (reel/guion.json) contra las tablas de datos y las reglas del curso.

1. Formato (Sesión 15 y Tarea 3): de 5 a 7 escenas; frases de 15 a 26 palabras y sin dígitos (los números van en
   palabras para la voz); etiquetas de 3 a 8 palabras sin rótulos como «gancho»; aviso de voz con IA y fuente.
2. Duración estimada entre 45 y 75 segundos, a 2.5 palabras/s (Qwen3-TTS) y a 3.0 palabras/s (VoxCPM2).
3. Cada cifra en pantalla y cada aproximación dicha en voz alta («casi la mitad», «casi cinco veces») frente a los CSV.

Uso: uv run scripts/verificar_guion.py
"""

import json
import re
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
P = RAIZ / "datos/procesados"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    g = json.loads((RAIZ / "reel/guion.json").read_text(encoding="utf-8"))
    nac = pd.read_csv(P / "pobreza_nacional_area_2024.csv").set_index("ambito")
    dep = pd.read_csv(P / "pobreza_departamento_2024.csv", dtype={"ccdd": str}).set_index("departamento")
    br = pd.read_csv(P / "brecha_urbano_rural_2024.csv", dtype={"ccdd": str})
    ext = br[(br.ccdd == "00") & (br.tipo == "pobreza_extrema")].iloc[0]
    esc = g["escenas"]
    frases = [e["frase"] for e in esc]
    resultados = []

    def check(ok, texto):
        resultados.append((ok, texto))

    # 1. Formato
    check(5 <= len(esc) <= 7, f"{len(esc)} escenas (entre 5 y 7)")
    for i, e in enumerate(esc, 1):
        n = len(e["frase"].split())
        check(15 <= n <= 26, f"escena {i}: {n} palabras")
        check(not re.search(r"\d", e["frase"]), f"escena {i}: la frase no tiene dígitos")
        m = len(e["etiqueta"].split())
        check(3 <= m <= 8 and not re.search(r"gancho|invitaci|cierre", e["etiqueta"], re.I), f"escena {i}: etiqueta de {m} palabras")
    check(g.get("aviso_en_pantalla") == "Voz generada con IA", "aviso «Voz generada con IA» en pantalla")
    check("INEI" in g.get("fuente_en_pantalla", "") and "propios" in g.get("fuente_en_pantalla", ""),
          "fuente en pantalla: INEI y cálculos propios")
    check(any("Voz generada con IA" in c for c in g["creditos"]) and any("Música" in c for c in g["creditos"]),
          "créditos de voz y música")

    # 2. Duración estimada
    palabras = sum(len(f.split()) for f in frases)
    for ritmo in (2.5, 3.0):
        seg = palabras / ritmo
        check(45 <= seg <= 75, f"{palabras} palabras a {ritmo} palabras/s ≈ {seg:.0f} s (entre 45 y 75)")

    # 3. Cifras y aproximaciones
    t_nac = nac.loc["Nacional", "tasa_pobreza"]
    t_urb, t_rur = nac.loc["Urbana", "tasa_pobreza"], nac.loc["Rural", "tasa_pobreza"]
    caj, ica, lima = dep.loc["Cajamarca"], dep.loc["Ica"], dep.loc["Lima"]
    cifras = {e["cifra"] for e in esc}
    reglas = [
        (f"{t_nac:.1f} %" in cifras and t_nac > 25, f"«más de una de cada cuatro» y 27.6 %: tasa nacional {t_nac:.2f} %"),
        (nac.loc["Nacional", "n_hogares"] == 33_691 and "33,691" in cifras, "«más de treinta y tres mil hogares»: 33,691"),
        (40 < caj.tasa_pobreza < 50 and f"{caj.tasa_pobreza:.1f} % vs {ica.tasa_pobreza:.1f} %" in cifras,
         f"«casi la mitad» en Cajamarca: {caj.tasa_pobreza:.2f} %"),
        (round(ica.tasa_pobreza) == 6, f"«seis de cada cien» en Ica: {ica.tasa_pobreza:.2f} %"),
        (abs(lima.tasa_pobreza - t_nac) < 1, f"Lima «cerca del promedio nacional»: {lima.tasa_pobreza:.2f} % frente a {t_nac:.2f} %"),
        (30 < lima.participacion_en_pobres_pct < 100 / 3 and f"{lima.participacion_en_pobres_pct:.1f} %" in cifras,
         f"«casi uno de cada tres pobres» en Lima: {lima.participacion_en_pobres_pct:.2f} % (estimación propia)"),
        (35 < t_rur < 40 and 20 < t_urb < 25 and f"{t_rur:.1f} % vs {t_urb:.1f} %" in cifras,
         f"«casi cuatro de cada diez» rural ({t_rur:.2f} %) y «casi una de cada cuatro» urbana ({t_urb:.2f} %)"),
        (4.5 < ext.razon_rural_urbana < 5 and f"{ext.tasa_rural:.1f} % vs {ext.tasa_urbana:.1f} %" in cifras,
         f"pobreza extrema rural «casi cinco veces» la urbana: {ext.tasa_rural:.2f} / {ext.tasa_urbana:.2f} = {ext.razon_rural_urbana:.2f}"),
    ]
    for ok, texto in reglas:
        check(bool(ok), texto)

    for ok, texto in resultados:
        print(f"[{'OK' if ok else 'FALLA'}] {texto}")
    fallas = sum(not ok for ok, _ in resultados)
    print(f"\n{len(resultados) - fallas} OK, {fallas} con falla")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
