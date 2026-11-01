"""Verifica el reel terminado (reel/reel.mp4) contra los requisitos de la Tarea 3, con ffprobe y ffmpeg.

- Video vertical 9:16 (1080 × 1920) de 45 a 75 segundos, con audio.
- Sonoridad del audio adecuada para redes y música claramente por debajo de la voz.
- Subtítulos (reel/subtitulos.srt) sincronizados dentro del video y con exactamente las palabras del guion.
- Narración entendible: WER de Whisper por escena (reel/calidad_narracion.json).
- Guion de 5 a 7 escenas, cada una con imágenes; aviso de voz con IA, fuente y créditos de la música.
También guarda cuadros del video en reel/salidas/cuadros/ para revisarlos a la vista.

Uso: uv run scripts/verificar_reel.py
"""

import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
REEL = RAIZ / "reel"


def ffprobe(ruta):
    r = subprocess.run([shutil.which("ffprobe"), "-v", "error", "-show_entries",
                        "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
                        "-of", "json", str(ruta)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def ebur128(ruta, inicio=None, fin=None):
    corte = ["-ss", f"{inicio}", "-to", f"{fin}"] if inicio is not None else []
    r = subprocess.run([shutil.which("ffmpeg"), "-hide_banner", "-nostats", *corte, "-i", str(ruta), "-vn",
                        "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True, errors="replace")
    resumen = r.stderr[r.stderr.rfind("Summary"):]
    integrada = float(re.search(r"I:\s+(-?[\d.]+) LUFS", resumen).group(1))
    pico = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", resumen)
    return integrada, float(pico.group(1)) if pico else None


def plano(s):
    s = unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^\w\s]", " ", s).split())


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    resultados = []
    check = lambda ok, t: resultados.append((bool(ok), t))
    guion = json.loads((REEL / "guion.json").read_text(encoding="utf-8"))
    video = REEL / "reel.mp4"
    info = ffprobe(video)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    mb = int(info["format"]["size"]) / 1e6

    check(v["width"] == 1080 and v["height"] == 1920, f"video vertical 9:16: {v['width']} × {v['height']} ({v['codec_name']}, {v['r_frame_rate']} fps)")
    check(45 <= dur <= 75, f"duración {dur:.1f} s (entre 45 y 75)")
    check(a is not None and a["codec_name"] == "aac", f"audio: {a and a['codec_name']}, {a and a['sample_rate']} Hz, {a and a['channels']} canales")
    check(mb < 50, f"tamaño {mb:.1f} MB (cabe en GitHub y en LinkedIn)")

    escenas = json.loads((REEL / "salidas/escenas.json").read_text(encoding="utf-8"))
    total, pico = ebur128(video)
    check(-17 <= total <= -12 and pico is not None and pico <= -0.5, f"sonoridad integrada {total:.1f} LUFS, pico {pico} dBFS")
    voz, _ = ebur128(video, escenas[0][0], escenas[-1][1])
    solo_musica, _ = ebur128(video, escenas[-1][1] + 0.6, escenas[-1][1] + 3.0)
    check(voz - solo_musica >= 15 and solo_musica > -50,
          f"música por debajo de la voz: voz {voz:.1f} LUFS, tramo solo con música {solo_musica:.1f} LUFS (diferencia {voz - solo_musica:.1f} dB)")

    srt = (REEL / "subtitulos.srt").read_text(encoding="utf-8")
    tiempos = [(sum(float(x) * f for x, f in zip(re.split(r"[:,]", ini)[:3], (3600, 60, 1))) + int(ini[-3:]) / 1000,
                sum(float(x) * f for x, f in zip(re.split(r"[:,]", fin)[:3], (3600, 60, 1))) + int(fin[-3:]) / 1000)
               for ini, fin in re.findall(r"(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})", srt)]
    textos = [b.split("\n", 2)[2].strip() for b in srt.strip().split("\n\n")]
    check(all(i < f for i, f in tiempos) and all(tiempos[k][0] >= tiempos[k - 1][0] for k in range(1, len(tiempos)))
          and tiempos[-1][1] <= dur, f"subtítulos: {len(tiempos)} bloques ordenados y dentro del video")
    check(plano(" ".join(textos)) == plano(" ".join(e["frase"] for e in guion["escenas"])),
          "los subtítulos dicen exactamente el guion")

    calidad = json.loads((REEL / "calidad_narracion.json").read_text(encoding="utf-8"))
    peor = max(calidad["escenas"], key=lambda e: e["wer"])
    check(peor["wer"] <= 0.15, f"pronunciación: WER máximo {peor['wer']:.3f} (escena {peor['escena']}); "
          + ", ".join(f"{e['wer']:.2f}" for e in calidad["escenas"]))
    for palabra in ["inei", "cajamarca", "ica", "lima"]:
        oido = plano(" ".join(e["oido"] for e in calidad["escenas"]))
        check(re.search(rf"\b{palabra}\b", oido), f"Whisper reconoce «{palabra}» en la narración")

    check(5 <= len(guion["escenas"]) <= 7, f"{len(guion['escenas'])} escenas")
    nombres = [n if isinstance(n, str) else n["captura"] for e in guion["escenas"] for n in e["imagenes"]]
    faltan = [n for n in nombres if not (REEL / f"recursos/capturas/{n}.png").exists()]
    check(all(e["imagenes"] for e in guion["escenas"]) and not faltan, "cada escena tiene imágenes del tablero")
    check(guion["aviso_en_pantalla"] == "Voz generada con IA" and "INEI" in guion["fuente_en_pantalla"],
          "aviso de voz con IA y fuente en pantalla")
    musica = next((c for c in guion["creditos"] if c.startswith("Música")), "")
    check("Kevin MacLeod" in musica and "Attribution 4.0" in musica, "créditos de la música con autor y licencia")

    cuadros = REEL / "salidas/cuadros"
    cuadros.mkdir(parents=True, exist_ok=True)
    marcas = [(e[0] + e[1]) / 2 for e in escenas] + [dur - 1.5]
    for k, t in enumerate(marcas, 1):
        subprocess.run([shutil.which("ffmpeg"), "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                        str(cuadros / f"cuadro_{k}.png")], check=True)

    for ok, t in resultados:
        print(f"[{'OK' if ok else 'FALLA'}] {t}")
    fallas = sum(not ok for ok, _ in resultados)
    print(f"\n{len(resultados) - fallas} OK, {fallas} con falla · cuadros para revisar en {cuadros}")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
