"""Descarga los datos originales y registra su procedencia en datos/originales/manifiesto.json.

Fuentes:
  1. INEI, ENAHO 2024 (código 966), módulo 34 «Sumaria»: condición de pobreza, miembros y factor de expansión.
  2. Límites departamentales del Perú (GeoJSON simplificado, 25 departamentos) del repositorio del curso.
  3. Pobreza 2024 por departamento calculada por el profesor del curso: solo para verificar resultados.

Si el portal del INEI rechaza la descarga automática, baja el zip desde el navegador a datos/originales/ y vuelve a
correr este script: verificará el archivo y completará el manifiesto.

Uso: uv run scripts/obtener_datos.py [--forzar]
"""

import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ORIGINALES = Path("datos/originales")
FUENTES = [
    {
        "archivo": "966-Modulo34.zip",
        "url": "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip",
        "descripcion": "INEI, ENAHO 2024, módulo 34 (Sumaria): una fila por hogar",
        "sha256_verificado": "5ee98dad87810d42d7e252401d8366feac2fbce151c7af986d9644a40952567c",
    },
    {
        "archivo": "peru_departamental_simple.geojson",
        "url": "https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson",
        "descripcion": "Límites de los 25 departamentos (FIRST_IDDP = código de departamento), repositorio del curso",
        "sha256_verificado": "3d34d5450a1b1f059eebdf7386e5b5d071a5063bf3679fcbbbc5314493791290",
    },
    {
        "archivo": "referencia_curso_pobreza_departamento_2024.csv",
        "url": "https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/16-skills-enaho/referencias/pobreza_departamento_2024.csv",
        "descripcion": "Pobreza 2024 por departamento calculada por el profesor con la sumaria (solo para verificar)",
        "sha256_verificado": "59b66d00a14880fdbaf8c8925b37c39847c7ef16efc68f450ef5539c9dbaee8e",
    },
]


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def descargar(url, destino):
    with urllib.request.urlopen(url, timeout=120) as r, open(destino, "wb") as f:
        f.write(r.read())


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--forzar", action="store_true", help="vuelve a descargar aunque el archivo exista")
    args = ap.parse_args()
    ORIGINALES.mkdir(parents=True, exist_ok=True)

    manifiesto_ruta = ORIGINALES / "manifiesto.json"
    previo = json.loads(manifiesto_ruta.read_text(encoding="utf-8")) if manifiesto_ruta.exists() else {}
    manifiesto = {}
    for fuente in FUENTES:
        ruta = ORIGINALES / fuente["archivo"]
        descargado = False
        if args.forzar or not ruta.exists():
            try:
                descargar(fuente["url"], ruta)
                descargado = True
            except Exception as e:  # noqa: BLE001
                sys.exit(f"No se pudo bajar {fuente['url']} ({e}). Bájalo desde el navegador a {ruta} y vuelve a correr.")
        if ruta.suffix == ".zip" and not zipfile.is_zipfile(ruta):
            ruta.unlink()
            sys.exit(f"{fuente['url']} no devolvió un zip (¿bloqueo del portal?). Bájalo desde el navegador a {ruta}.")

        huella = sha256(ruta)
        coincide = huella == fuente["sha256_verificado"]
        anterior = previo.get(fuente["archivo"], {})
        entrada = {
            "url": fuente["url"],
            "descripcion": fuente["descripcion"],
            "bytes": ruta.stat().st_size,
            "sha256": huella,
            "igual_al_verificado_en_este_proyecto": coincide,
            "fecha_obtencion": dt.date.today().isoformat() if descargado else anterior.get("fecha_obtencion", "desconocida"),
        }
        if ruta.suffix == ".zip":
            with zipfile.ZipFile(ruta) as zf:
                entrada["contenido"] = [
                    {"nombre": i.filename, "bytes": i.file_size, "fecha": dt.datetime(*i.date_time).isoformat()}
                    for i in zf.infolist() if not i.is_dir()
                ]
        manifiesto[fuente["archivo"]] = entrada
        estado = "descargado" if descargado else "ya existía"
        aviso = "" if coincide else "  AVISO: el hash cambió; la fuente pudo actualizarse, revisa la verificación"
        print(f"{fuente['archivo']}: {estado}, {entrada['bytes']:,} bytes, sha256 {huella[:16]}…{aviso}")

    manifiesto_ruta.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manifiesto: {manifiesto_ruta}")


if __name__ == "__main__":
    main()
