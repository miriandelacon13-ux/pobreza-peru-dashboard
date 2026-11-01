"""Hace el reel por pasos: voz -> subtítulos -> mezcla -> video. Cada paso guarda lo suyo y el siguiente lo reutiliza.

    reel/.venv/Scripts/python reel/hacer_reel.py --voz reel/recursos/mi_voz.m4a            # todo
    reel/.venv/Scripts/python reel/hacer_reel.py --voz reel/recursos/mi_voz.m4a --desde video   # solo rehace el video

Sale:  reel/reel.mp4, reel/subtitulos.srt, reel/portada.png, reel/calidad_narracion.json
       reel/salidas/ (no se sube a git: audio de cada escena, narración y mezcla con la voz clonada)
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

import reel

PASOS = ["voz", "subtitulos", "mezcla", "video"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voz", required=True, help="grabación de referencia de 15 a 25 s (m4a, wav, opus)")
    ap.add_argument("--desde", default="voz", choices=PASOS, help="primer paso a correr; los anteriores se reutilizan")
    ap.add_argument("--tts", default=reel.TTS)
    ap.add_argument("--musica", default=str(reel.AQUI / "recursos/musica/Dreamer.mp3"))
    ap.add_argument("--debajo-db", type=float, default=20.0, help="cuántos dB por debajo de la voz va la música")
    args = ap.parse_args()

    t0 = time.time()
    reloj = lambda msg: print(f"[{time.time() - t0:6.1f}s] {msg}", flush=True)
    guion = json.loads((reel.AQUI / "guion.json").read_text(encoding="utf-8"))
    salidas = reel.AQUI / "salidas"
    salidas.mkdir(exist_ok=True)
    corre = lambda paso: PASOS.index(paso) >= PASOS.index(args.desde)
    calidad_ruta = reel.AQUI / "calidad_narracion.json"

    if corre("voz"):
        voz = reel.Voz(args.voz, modelo=args.tts)
        reloj(f"voz cargada ({args.tts}); Whisper oyó en la referencia: «{voz.texto_ref}»")
        informe = reel.narrar(voz, guion, salidas)
        calidad_ruta.write_text(json.dumps({"modelo_voz": args.tts, "referencia_transcrita": voz.texto_ref,
                                            "escenas": informe}, ensure_ascii=False, indent=2), encoding="utf-8")
        for e in informe:
            reloj(f"escena {e['escena']}: {e['segundos']:.1f} s, WER {e['wer']:.3f} ({e['intentos']} intento(s)) · oído: «{e['oido']}»")

    audio, sr, escenas = reel.unir_narracion(salidas, len(guion["escenas"]))
    sf.write(salidas / "narracion.wav", audio, sr)
    (salidas / "escenas.json").write_text(json.dumps(escenas), encoding="utf-8")
    reloj(f"narración: {len(audio) / sr:.1f} s con la tarjeta final; voz hasta {escenas[-1][1]:.1f} s")

    if corre("subtitulos"):
        palabras = reel.subtitulos(guion, salidas, escenas)
        (salidas / "palabras.json").write_text(json.dumps(palabras, ensure_ascii=False), encoding="utf-8")
        reel.a_srt(reel.bloques(palabras), reel.AQUI / "subtitulos.srt")
        reloj(f"subtítulos: {sum(map(len, palabras))} palabras en {len(reel.bloques(palabras))} bloques")
    palabras = json.loads((salidas / "palabras.json").read_text(encoding="utf-8"))

    if corre("mezcla"):
        medidas = reel.mezclar(salidas / "narracion.wav", args.musica, salidas / "mezcla.wav", debajo_db=args.debajo_db)
        (salidas / "mezcla.json").write_text(json.dumps(medidas, indent=2), encoding="utf-8")
        reloj(f"mezcla: {medidas}")

    if corre("video"):
        reel.video(guion, salidas / "mezcla.wav", escenas, palabras, reel.AQUI / "reel.mp4")
        reloj(f"video: {reel.AQUI / 'reel.mp4'}")
    reloj("listo")


if __name__ == "__main__":
    main()
