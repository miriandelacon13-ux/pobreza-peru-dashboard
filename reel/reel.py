"""Reel de la Tarea 3: guion.json -> voz clonada -> subtítulos -> video vertical con capturas del tablero y música.

La voz clonada con Qwen3-TTS, el control de calidad con Whisper (WER por escena) y la normalización de números están
adaptados de sessions/15-texto-a-reel/reel.py del curso (github.com/d2cml-ai/Data-Science-Python). Lo propio de este
proyecto: cada escena muestra capturas del tablero con movimiento lento; los subtítulos muestran exactamente las
palabras del guion, alineadas con los tiempos que da Whisper; hay música de fondo bajo la voz; el aviso de voz con IA
y la fuente están siempre en pantalla, y el video cierra con una tarjeta de créditos.

Va en su propio entorno (reel/.venv): qwen-tts fija transformers 4.57.3. Ver reel/README.md.
"""
import difflib
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path

import imageio_ffmpeg
import jiwer
import numpy as np
import soundfile as sf
from num2words import num2words
from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).parent
FUENTES = AQUI / "fuentes"
CAPTURAS = AQUI / "recursos" / "capturas"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

TTS = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
ASR = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"   # large-v3-turbo en formato de faster-whisper
MODELOS = Path(os.environ.get("REEL_MODELOS", Path.home() / ".cache" / "modelos_reel"))

ANCHO, ALTO, FPS = 1080, 1920, 30
MARGEN = 60
INICIO, PAUSA, FINAL = 0.4, 0.4, 4.5   # silencio al inicio, entre escenas y al final (tarjeta de créditos)
FONDO, TEXTO, SUAVE, ACENTO, CAJA = "#10161D", "#F3F1EC", "#AAB4BF", "#F08A4B", "#1E2731"
VISUAL = (MARGEN, 650, ANCHO - MARGEN, 1400)   # caja donde van las capturas
FUNDIDO = 0.45                                  # segundos de fundido entre capturas


# ---------- modelos ----------

def modelo_local(repo):
    """Baja un repositorio de Hugging Face a una carpeta con archivos normales y devuelve su ruta.

    En Windows sin modo de desarrollador, la caché de Hugging Face falla al crear enlaces simbólicos
    (WinError 1314: «El cliente no dispone de un privilegio requerido»). Con local_dir se guardan copias.
    """
    if Path(repo).is_dir():
        return str(repo)
    destino = MODELOS / repo.replace("/", "--")
    marca = destino / ".descarga_completa"
    if not marca.exists():
        from huggingface_hub import snapshot_download
        snapshot_download(repo, local_dir=destino)
        marca.write_text(repo, encoding="utf-8")
    return str(destino)


# ---------- audio ----------

def cargar_audio(ruta, sr=16000):
    """Cualquier audio (wav, m4a, ogg de WhatsApp, mp3) a mono float32 con ffmpeg."""
    crudo = subprocess.run([FFMPEG, "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                           capture_output=True, check=True).stdout
    return np.frombuffer(crudo, np.float32)


def a16k(w, sr):
    w = np.asarray(w, np.float32)
    return np.interp(np.arange(0, len(w), sr / 16000), np.arange(len(w)), w).astype(np.float32)


_ASR = None


def whisper():
    global _ASR
    if _ASR is None:
        from faster_whisper import WhisperModel
        _ASR = WhisperModel(modelo_local(ASR), device="cpu", compute_type="int8")
    return _ASR


def transcribir(audio16k, contexto=None, palabras=False):
    segs, _ = whisper().transcribe(audio16k, language="es", word_timestamps=palabras, initial_prompt=contexto)
    segs = list(segs)
    texto = " ".join(s.text.strip() for s in segs)
    if not palabras:
        return texto
    return texto, [(w.start, w.end, w.word.strip()) for s in segs for w in s.words if w.word.strip()]


class Voz:
    """Clona una voz con Qwen3-TTS a partir de una grabación de 15 a 25 s y su transcripción (la hace Whisper)."""

    def __init__(self, referencia, modelo=TTS, device="cpu"):
        import torch
        from qwen_tts import Qwen3TTSModel

        self.referencia = cargar_audio(referencia)
        self.texto_ref = transcribir(self.referencia)
        self.tts = Qwen3TTSModel.from_pretrained(modelo_local(modelo), device_map=device, dtype=torch.float32)
        self.prompt = self.tts.create_voice_clone_prompt(ref_audio=(self.referencia, 16000), ref_text=self.texto_ref)

    def decir(self, frases):
        wavs, self.sr = self.tts.generate_voice_clone(text=frases, language=["Spanish"] * len(frases),
                                                      voice_clone_prompt=self.prompt)
        return [np.asarray(w, np.float32) for w in wavs]


# ---------- control de calidad ----------

def normalizar(s):
    """Para comparar lo escrito con lo que oyó Whisper: números en palabras, sin tildes ni puntuación."""
    s = s.lower().replace("%", " por ciento")
    s = re.sub(r"(?<=\d)[,.](?=\d{3}\b)", "", s)
    s = re.sub(r"\d+", lambda m: num2words(int(m.group()), lang="es"), s)
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^\w\s]", " ", s).split())


def wer(referencia, oido):
    return jiwer.wer(normalizar(referencia), normalizar(oido)) if normalizar(oido) else 1.0


def narrar(voz, guion, salidas, max_wer=0.15, reintentos=2):
    """Narra cada escena; si Whisper no entiende bien una escena, la vuelve a generar. Guarda un wav por escena."""
    frases = [e["frase"] for e in guion["escenas"]]
    wavs = voz.decir(frases)
    informe = []
    for i, (frase, w) in enumerate(zip(frases, wavs)):
        for intento in range(reintentos + 1):
            oido = transcribir(a16k(w, voz.sr), contexto=frase)
            error = wer(frase, oido)
            if error <= max_wer or intento == reintentos:
                break
            w = voz.decir([frase])[0]
        sf.write(salidas / f"escena_{i + 1}.wav", w, voz.sr)
        informe.append({"escena": i + 1, "wer": round(error, 3), "intentos": intento + 1, "oido": oido,
                        "segundos": round(len(w) / voz.sr, 2)})
    return informe


# ---------- montaje de la narración y subtítulos ----------

def unir_narracion(salidas, n):
    """Une los wav de las escenas con silencios y devuelve el audio, su frecuencia y el inicio y fin de cada escena."""
    partes, escenas = [], []
    sr = sf.info(salidas / "escena_1.wav").samplerate
    t = INICIO
    partes.append(np.zeros(int(INICIO * sr), np.float32))
    for i in range(n):
        w, _ = sf.read(salidas / f"escena_{i + 1}.wav", dtype="float32")
        escenas.append((t, t + len(w) / sr))
        partes += [w, np.zeros(int(PAUSA * sr), np.float32)]
        t += len(w) / sr + PAUSA
    partes.append(np.zeros(int((FINAL - PAUSA) * sr), np.float32))
    return np.concatenate(partes), sr, escenas


def alinear(frase, palabras_whisper, inicio):
    """Tiempos para cada palabra del guion: se emparejan con las palabras de Whisper (normalizadas) y las que no
    coinciden se interpolan. Así el subtítulo muestra exactamente el guion, sincronizado con la voz."""
    guion = frase.split()
    clave_g = [normalizar(p) for p in guion]
    sub, tiempos = [], []   # palabras de Whisper partidas en sus partes normalizadas («2024» -> «dos mil veinticuatro»)
    for ini, fin, p in palabras_whisper:
        partes = normalizar(p).split() or [""]
        paso = (fin - ini) / len(partes)
        for k, x in enumerate(partes):
            sub.append(x)
            tiempos.append((inicio + ini + k * paso, inicio + ini + (k + 1) * paso))
    plano_g = [(i, x) for i, c in enumerate(clave_g) for x in (c.split() or [""])]
    sm = difflib.SequenceMatcher(a=[x for _, x in plano_g], b=sub, autojunk=False)
    t_ini, t_fin = [None] * len(guion), [None] * len(guion)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            i = plano_g[a + k][0]
            ti, tf = tiempos[b + k]
            t_ini[i] = ti if t_ini[i] is None else min(t_ini[i], ti)
            t_fin[i] = tf if t_fin[i] is None else max(t_fin[i], tf)
    conocidos = [i for i in range(len(guion)) if t_ini[i] is not None]
    if not conocidos:
        raise ValueError(f"Whisper no reconoció ninguna palabra de: {frase}")
    for i in range(len(guion)):
        if t_ini[i] is None:
            antes = max((k for k in conocidos if k < i), default=None)
            despues = min((k for k in conocidos if k > i), default=None)
            a = t_fin[antes] if antes is not None else t_ini[despues]
            b = t_ini[despues] if despues is not None else t_fin[antes]
            j0 = antes if antes is not None else -1
            j1 = despues if despues is not None else len(guion)
            paso = (b - a) / (j1 - j0) if j1 > j0 else 0
            t_ini[i], t_fin[i] = a + (i - j0 - 1) * paso, a + (i - j0) * paso
    return [(t_ini[i], t_fin[i], guion[i]) for i in range(len(guion))]


def subtitulos(guion, salidas, escenas, sr_unused=None):
    """Palabras del guion con tiempo, escena por escena (Whisper sobre el audio de cada escena)."""
    palabras = []
    for i, (e, (ini, _)) in enumerate(zip(guion["escenas"], escenas)):
        audio = cargar_audio(salidas / f"escena_{i + 1}.wav")
        _, pw = transcribir(audio, contexto=e["frase"], palabras=True)
        palabras.append(alinear(e["frase"], pw, ini))
    return palabras


def bloques(palabras_escena, max_palabras=4, max_letras=26):
    """Bloques cortos para leer en el celular; corta en los signos de puntuación."""
    salida = []
    for palabras in palabras_escena:
        actual = []
        for p in palabras:
            actual.append(p)
            largo = sum(len(x[2]) + 1 for x in actual)
            if len(actual) >= max_palabras or largo >= max_letras or p[2][-1] in ".,;:?!":
                salida.append(actual)
                actual = []
        if actual:
            salida.append(actual)
    return salida


def a_srt(bloques_, ruta):
    def hms(t):
        return f"{int(t // 3600):02}:{int(t % 3600 // 60):02}:{int(t % 60):02},{int(round(t % 1 * 1000)):03}"
    lineas = []
    for i, b in enumerate(bloques_, 1):
        lineas += [str(i), f"{hms(b[0][0])} --> {hms(b[-1][1])}", " ".join(p[2] for p in b), ""]
    Path(ruta).write_text("\n".join(lineas), encoding="utf-8")


# ---------- video ----------

def fuente(nombre, tam, peso):
    ruta = FUENTES / f"{nombre}.ttf"
    if not ruta.exists():   # Oswald y Public Sans, de Google Fonts (licencia OFL)
        import urllib.request
        FUENTES.mkdir(exist_ok=True)
        urllib.request.urlretrieve(f"https://github.com/google/fonts/raw/main/ofl/{nombre.lower()}/{nombre}%5Bwght%5D.ttf", ruta)
    f = ImageFont.truetype(str(ruta), tam)
    f.set_variation_by_axes([peso])
    return f


def envolver(d, texto, f, ancho):
    piezas = []
    for palabra in texto.split():
        if d.textlength(palabra, font=f) > ancho and "/" in palabra:
            partes = palabra.split("/")
            piezas += [x + "/" for x in partes[:-1]] + [partes[-1]]
        else:
            piezas.append(palabra)
    lineas, actual = [], ""
    for palabra in piezas:
        prueba = actual + palabra if actual.endswith("/") else f"{actual} {palabra}".strip()
        if d.textlength(prueba, font=f) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    return lineas + [actual]


def base(guion):
    """Lo que no cambia en todo el video: título, aviso de voz con IA, fuente y autora."""
    img = Image.new("RGB", (ANCHO, ALTO), FONDO)
    d = ImageDraw.Draw(img)
    d.text((MARGEN, 215), guion["titulo"].upper(), font=fuente("PublicSans", 38, 800), fill=ACENTO, anchor="lm")
    aviso, f = guion["aviso_en_pantalla"].upper(), fuente("PublicSans", 28, 700)
    w = d.textlength(aviso, font=f)
    d.rounded_rectangle((ANCHO - MARGEN - w - 40, 185, ANCHO - MARGEN, 245), radius=30, outline=TEXTO, width=2)
    d.text((ANCHO - MARGEN - w - 20, 215), aviso, font=f, fill=TEXTO, anchor="lm")
    pie = fuente("PublicSans", 30, 500)
    d.text((MARGEN, 1690), guion["fuente_en_pantalla"], font=pie, fill=SUAVE, anchor="lm")
    d.text((MARGEN, 1735), guion["autora"], font=pie, fill=SUAVE, anchor="lm")
    return img


def capa_texto(e):
    """Cifra grande y etiqueta de la escena, centradas entre el encabezado y las capturas."""
    capa = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    ancho = ANCHO - 2 * MARGEN
    lineas = []
    if e.get("cifra"):
        for tam in range(170, 80, -10):
            fc = fuente("Oswald", tam, 700)
            if d.textlength(e["cifra"], font=fc) <= ancho:
                break
        lineas.append((e["cifra"], fc, TEXTO))
        fe, color = fuente("PublicSans", 46, 600), SUAVE
    else:
        fe, color = fuente("Oswald", 84, 600), TEXTO
    lineas += [(x, fe, color) for x in envolver(d, e["etiqueta"], fe, ancho)]
    altos = [d.textbbox((0, 0), t, font=f, anchor="ls")[3] - d.textbbox((0, 0), t, font=f, anchor="ls")[1] for t, f, _ in lineas]
    total = sum(altos) + 18 * (len(lineas) - 1)
    y = 290 + (620 - 290 - total) / 2
    for (t, f, color), h in zip(lineas, altos):
        y += h
        d.text((MARGEN, y), t, font=f, fill=color, anchor="ls")
        y += 18
    return capa


class Captura:
    """Una captura ajustada al ancho de la caja: si es más alta que la caja se desplaza hacia abajo; si no, se acerca."""

    def __init__(self, nombre):
        img = Image.open(CAPTURAS / f"{nombre}.png").convert("RGB")
        x0, y0, x1, y1 = VISUAL
        self.w, self.h_caja = x1 - x0, y1 - y0
        escala = self.w / img.width
        self.img = img.resize((self.w, round(img.height * escala)), Image.LANCZOS)
        self.alta = self.img.height > self.h_caja

    def cuadro(self, p):
        """Lienzo del tamaño de la caja con la captura en el avance p (de 0 a 1), con esquinas redondeadas."""
        p = 0.5 - 0.5 * np.cos(np.pi * min(max(p, 0), 1))   # suave al empezar y al terminar
        if self.alta:
            y = round((self.img.height - self.h_caja) * p)
            img = self.img.crop((0, y, self.w, y + self.h_caja))
        else:
            z = 1 + 0.05 * p
            w, h = self.w / z, self.img.height / z
            x0, y0 = (self.w - w) / 2, (self.img.height - h) / 2
            img = self.img.resize((self.w, self.img.height), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h))
        lienzo = Image.new("RGB", (self.w, self.h_caja), FONDO)
        lienzo.paste(img, (0, (self.h_caja - img.height) // 2), mascara(img.width, img.height))
        return lienzo


_MASCARAS = {}


def mascara(w, h, radio=28):
    if (w, h) not in _MASCARAS:
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=radio, fill=255)
        _MASCARAS[(w, h)] = m
    return _MASCARAS[(w, h)]


def nombre_captura(imagen):
    return imagen if isinstance(imagen, str) else imagen["captura"]


def tramos_visuales(guion, escenas, duracion, palabras_escena, anticipo=0.15):
    """(inicio, fin, captura) para cada captura. La primera captura de una escena empieza con la escena; las demás,
    cuando la narración dice su palabra «desde» (por ejemplo, el mapa de Ica aparece al decir «Ica»)."""
    tramos = []
    limites = [ini - (PAUSA / 2 if i else INICIO) for i, (ini, _) in enumerate(escenas)] + [duracion]
    for i, e in enumerate(guion["escenas"]):
        a, b = limites[i], limites[i + 1]
        if i == len(escenas) - 1:
            b = escenas[-1][1] + 0.3   # la tarjeta de créditos ocupa el final
        inicios = [a]
        for imagen in e["imagenes"][1:]:
            clave = normalizar(imagen["desde"])
            t = next((pi for pi, _, palabra in palabras_escena[i] if normalizar(palabra) == clave and pi > inicios[-1]), None)
            if t is None:
                raise ValueError(f"escena {i + 1}: la palabra «{imagen['desde']}» no está en la narración")
            inicios.append(max(inicios[-1] + 0.5, t - anticipo))
        for k, imagen in enumerate(e["imagenes"]):
            fin = inicios[k + 1] if k + 1 < len(inicios) else b
            tramos.append((inicios[k], fin, nombre_captura(imagen)))
    return tramos


def tarjeta_creditos(guion):
    capa = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    x0, y0, x1, y1 = MARGEN, 300, ANCHO - MARGEN, 1620
    d.rounded_rectangle((x0, y0, x1, y1), radius=32, fill=CAJA)
    f, alto_linea, separacion = fuente("PublicSans", 31, 500), 44, 26
    bloques_ = [envolver(d, linea, f, x1 - x0 - 100) for linea in guion["creditos"]]
    alto = 110 + sum(len(b) * alto_linea + separacion for b in bloques_)
    y = y0 + (y1 - y0 - alto) / 2 + 70
    d.text((x0 + 50, y), "Créditos", font=fuente("Oswald", 72, 600), fill=TEXTO, anchor="ls")
    y += 80
    for b in bloques_:
        for t in b:
            d.text((x0 + 50, y), t, font=f, fill=TEXTO, anchor="ls")
            y += alto_linea
        y += separacion
    return capa


def video(guion, audio_mezclado, escenas, palabras_escena, ruta):
    """Dibuja cada cuadro con Pillow y se lo pasa a ffmpeg junto con el audio ya mezclado."""
    duracion = sf.info(audio_mezclado).duration
    fondo = base(guion)
    textos = [capa_texto(e) for e in guion["escenas"]]
    capturas = {nombre_captura(n): Captura(nombre_captura(n)) for e in guion["escenas"] for n in e["imagenes"]}
    tramos = tramos_visuales(guion, escenas, duracion, palabras_escena)
    subs = bloques(palabras_escena)
    creditos = tarjeta_creditos(guion)
    f_sub = fuente("PublicSans", 58, 800)
    x0, y0, x1, y1 = VISUAL
    fin_voz = escenas[-1][1]
    cmd = [FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ANCHO}x{ALTO}", "-r", str(FPS),
           "-i", "-", "-i", str(audio_mezclado), "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(ruta)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(int(duracion * FPS)):
        t = k / FPS
        img = fondo.copy()
        d = ImageDraw.Draw(img)
        # barra de avance
        d.rounded_rectangle((MARGEN, 140, ANCHO - MARGEN, 148), radius=4, fill=CAJA)
        d.rounded_rectangle((MARGEN, 140, MARGEN + (ANCHO - 2 * MARGEN) * min(t / duracion, 1), 148), radius=4, fill=ACENTO)
        if t < fin_voz + 0.3:
            # cifra y etiqueta de la escena, con una entrada suave
            i = max([j for j, (ini, _) in enumerate(escenas) if ini - PAUSA <= t] or [0])
            a = min(1.0, max(0.0, (t - escenas[i][0] + PAUSA) / 0.35))
            capa = textos[i]
            if a < 1:
                capa = capa.copy()
                capa.putalpha(capa.getchannel("A").point(lambda v: int(v * a)))
            img.paste(capa, (0, int(30 * (1 - a))), capa)
            # captura actual, con fundido desde la anterior
            j = max([q for q, (ini, _, _) in enumerate(tramos) if ini <= t] or [0])
            ini, fin, nombre = tramos[j]
            cuadro = capturas[nombre].cuadro((t - ini) / (fin - ini))
            if j > 0 and t - ini < FUNDIDO:
                ai, af, an = tramos[j - 1]
                anterior = capturas[an].cuadro(1.0)
                cuadro = Image.blend(anterior, cuadro, (t - ini) / FUNDIDO)
            img.paste(cuadro, (x0, y0))
            # subtítulo: el bloque que se está diciendo, con la palabra actual resaltada
            b = next((b for b in subs if b[0][0] - 0.1 <= t <= b[-1][1] + 0.25), None)
            if b:
                texto = " ".join(p[2] for p in b)
                w = d.textlength(texto, font=f_sub)
                x, y = (ANCHO - w) / 2, 1480
                d.rounded_rectangle((x - 34, y - 24, x + w + 34, y + f_sub.size + 30), radius=26, fill=CAJA)
                for pi, pf, palabra in b:
                    d.text((x, y), palabra, font=f_sub, fill=ACENTO if pi <= t < pf else TEXTO)
                    x += d.textlength(palabra + " ", font=f_sub)
        else:
            a = min(1.0, (t - fin_voz - 0.3) / 0.5)
            capa = creditos if a >= 1 else creditos.copy()
            if a < 1:
                capa.putalpha(capa.getchannel("A").point(lambda v: int(v * a)))
            img.paste(capa, (0, 0), capa)
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg no pudo escribir el video")
    return ruta


# ---------- música ----------

def sonoridad(ruta, inicio=None, fin=None):
    """Sonoridad integrada (LUFS) con el filtro ebur128 de ffmpeg, opcionalmente de un tramo."""
    corte = ["-ss", str(inicio), "-to", str(fin)] if inicio is not None else []
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", *corte, "-i", str(ruta), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace")
    valores = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(valores[-1]) if valores else float("-inf")


def mezclar(narracion_wav, musica, salida, debajo_db=20.0, inicio_musica=0.0):
    """Voz a -16 LUFS y música recortada, con fundidos, a `debajo_db` dB por debajo de la voz. Devuelve las medidas."""
    duracion = sf.info(narracion_wav).duration
    voz_lufs = sonoridad(narracion_wav)
    mus_lufs = sonoridad(musica, inicio_musica, inicio_musica + duracion)
    ganancia_voz = -16.0 - voz_lufs
    ganancia_musica = (-16.0 - debajo_db) - mus_lufs
    filtro = (f"[0:a]aresample=48000,volume={ganancia_voz:.2f}dB[v];"
              f"[1:a]atrim={inicio_musica}:{inicio_musica + duracion},asetpts=PTS-STARTPTS,aresample=48000,"
              f"volume={ganancia_musica:.2f}dB,afade=t=in:d=1.5,afade=t=out:st={duracion - 3.0:.2f}:d=3.0[m];"
              f"[v][m]amix=inputs=2:normalize=0,alimiter=limit=0.79:level=false[s]")
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(narracion_wav), "-i", str(musica), "-filter_complex", filtro,
                    "-map", "[s]", "-ac", "2", "-c:a", "pcm_s16le", str(salida)], check=True)
    return {"voz_lufs_original": voz_lufs, "musica_lufs_original": mus_lufs,
            "ganancia_voz_db": round(ganancia_voz, 2), "ganancia_musica_db": round(ganancia_musica, 2)}
