"""Limpia la Sumaria de la ENAHO 2024 y arma la base de hogares (alternativa B: miembros del hogar).

Una fila por hogar. Cada hogar representa a factor07 × mieperho personas: mieperho cuenta a los miembros del hogar
(p204 = 1, sin trabajadores del hogar ni pensionistas, según Sumaria-2024.pdf, p. 2) y factor07 es el factor de
expansión. Es el procedimiento de la sumaria con el que el INEI y el curso calculan la pobreza.

La lectura y la normalización están adaptadas de scripts/limpiar.py del proyecto anterior
(github.com/miriandelacon13-ux/enaho-skills, commit c40106c).

Entra: datos/originales/966-Modulo34.zip (corre antes scripts/obtener_datos.py)
Sale:  datos/procesados/hogares_2024.parquet (no se sube a git: se regenera con este script)

Uso: uv run scripts/procesar_datos.py
"""

import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ZIP = Path("datos/originales/966-Modulo34.zip")
MIEMBRO_ZIP = "966-Modulo34/sumaria-2024.dta"
SALIDA = Path("datos/procesados/hogares_2024.parquet")

LLAVES = ["conglome", "vivienda", "hogar"]
ANCHO = {"conglome": 6, "vivienda": 3, "hogar": 2, "ubigeo": 6}
VARIABLES = LLAVES + ["anio", "ubigeo", "dominio", "estrato", "pobreza", "mieperho", "factor07"]

DEPARTAMENTOS = {
    "01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa", "05": "Ayacucho",
    "06": "Cajamarca", "07": "Callao", "08": "Cusco", "09": "Huancavelica", "10": "Huánuco",
    "11": "Ica", "12": "Junín", "13": "La Libertad", "14": "Lambayeque", "15": "Lima",
    "16": "Loreto", "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
    "21": "Puno", "22": "San Martín", "23": "Tacna", "24": "Tumbes", "25": "Ucayali",
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if not ZIP.exists():
        sys.exit(f"Falta {ZIP}. Corre antes: uv run scripts/obtener_datos.py")

    with zipfile.ZipFile(ZIP) as zf, zf.open(MIEMBRO_ZIP) as f:
        df = pd.read_stata(f, convert_categoricals=False)  # códigos, no etiquetas
    filas_leidas = len(df)
    df.columns = [c.lower().replace("ñ", "ni") for c in df.columns]  # «aÑo» llega con la eñe rota -> anio
    df = df[VARIABLES].copy()
    for c in LLAVES + ["ubigeo"]:
        df[c] = df[c].astype(str)

    # Comprobaciones de limpieza: si alguna falla, no se guarda nada
    problemas = []
    for c, ancho in ANCHO.items():
        if not (df[c].str.len() == ancho).all():
            problemas.append(f"{c} no tiene siempre {ancho} caracteres (¿se perdieron ceros a la izquierda?)")
    if df.duplicated(LLAVES).any():
        problemas.append(f"{int(df.duplicated(LLAVES).sum())} hogares repetidos")
    faltantes = df[["pobreza", "factor07", "mieperho", "ubigeo", "estrato"]].isna().sum()
    if faltantes.any():
        problemas.append(f"valores faltantes: {faltantes[faltantes > 0].to_dict()}")
    if not df.pobreza.isin([1, 2, 3]).all():
        problemas.append("pobreza tiene códigos distintos de 1, 2 y 3")
    if not ((df.mieperho >= 1) & (df.factor07 > 0)).all():
        problemas.append("hay hogares sin miembros o con factor de expansión no positivo")
    if (df.anio != "2024").any():
        problemas.append("hay hogares de otro año")
    if problemas:
        sys.exit("No se guardó la base:\n- " + "\n- ".join(problemas))

    # Variables derivadas
    df["departamento"] = df.ubigeo.str[:2]
    df["nombre_departamento"] = df.departamento.map(DEPARTAMENTOS)
    if df.nombre_departamento.isna().any():
        sys.exit(f"códigos de departamento desconocidos: {sorted(df.loc[df.nombre_departamento.isna(), 'departamento'].unique())}")
    df["area"] = np.where(df.estrato <= 5, "Urbana", "Rural")  # estratos 1-5: centros poblados de 2,000 habitantes o más
    df["pobre"] = df.pobreza <= 2
    df["pobre_extremo"] = df.pobreza == 1
    df["pobre_no_extremo"] = df.pobreza == 2
    df["peso"] = df.factor07.astype("float64") * df.mieperho  # personas que representa el hogar

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SALIDA, index=False)
    print(f"Leídos {filas_leidas:,} hogares de {MIEMBRO_ZIP}; sin duplicados ni faltantes.")
    print(f"Personas en la muestra (suma de mieperho): {int(df.mieperho.sum()):,}")
    print(f"Población estimada (suma de factor07 × mieperho): {df.peso.sum():,.0f}")
    print(f"Base guardada: {SALIDA}")


if __name__ == "__main__":
    main()
