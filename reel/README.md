# Reel: «¿Dónde está la pobreza?»

Video vertical (1080 × 1920) que cuenta los tres hallazgos del
[tablero](https://miriandelacon13-ux.github.io/pobreza-peru-dashboard/web/). La narración es una **voz generada con
IA** a partir de la voz de la autora.

| Archivo | Qué es |
|---|---|
| `reel.mp4` | El video final |
| `subtitulos.srt` | Los subtítulos, sincronizados con la voz |
| `guion.json`, `guion.md` | El guion por escenas, con la cifra, la etiqueta, las imágenes y el respaldo de cada escena |
| `grabacion.md` | Cómo se grabó la voz de referencia y el texto leído |
| `calidad_narracion.json` | Lo que Whisper entendió de cada escena narrada y su WER |
| `recursos/capturas/` | Capturas del tablero (`scripts/capturas_reel.py`) |
| `recursos/musica/` | «Dreamer» de Kevin MacLeod (CC BY 4.0) y su ficha de créditos |
| `reel.py`, `hacer_reel.py` | Voz clonada, subtítulos, mezcla y montaje |

**No se suben a GitHub:** la grabación de referencia (`recursos/mi_voz.*`) y el audio intermedio de la voz clonada
(`salidas/`).

## Cómo se hace

Va en un entorno propio, porque `qwen-tts` fija `transformers==4.57.3`:

```bash
uv venv reel/.venv --python 3.13
uv pip install --python reel/.venv/Scripts/python.exe -r reel/requirements-reel.txt
uv run scripts/capturas_reel.py                                              # capturas del tablero publicado
reel/.venv/Scripts/python.exe reel/hacer_reel.py --voz reel/recursos/mi_voz.m4a  # voz, subtítulos, mezcla y video
uv run scripts/verificar_guion.py && uv run scripts/verificar_reel.py        # comprobaciones
```

La primera vez se bajan los modelos: Qwen3-TTS 1.7B y Whisper large-v3-turbo. En Mac o Linux la ruta del intérprete
es `reel/.venv/bin/python`.

1. **Voz.** Whisper transcribe la grabación de referencia y Qwen3-TTS (Alibaba, Apache 2.0) clona la voz para narrar
   cada escena. Whisper vuelve a transcribir cada escena narrada. Si el error de palabras (WER) pasa de 0.15, la escena
   se genera de nuevo.
2. **Subtítulos.** Whisper da los tiempos de cada palabra. El subtítulo muestra exactamente las palabras del guion,
   alineadas con esos tiempos.
3. **Mezcla.**
   - La voz queda a −16 LUFS y la música 20 dB por debajo, con fundidos al entrar y al salir.
   - Un limitador evita picos.
4. **Montaje.** Cada cuadro se dibuja con Pillow y ffmpeg lo codifica en H.264. Cada cuadro lleva:
   - Arriba: la barra de avance, el título y el aviso «Voz generada con IA».
   - En el centro: la cifra y la etiqueta de la escena, y las capturas del tablero con movimiento lento.
   - Abajo: los subtítulos, la fuente y la autora.

   El video cierra con una tarjeta de créditos.

La voz clonada, el control con Whisper y la normalización de números están adaptados de la
[Sesión 15 del curso](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/15-texto-a-reel).

## Créditos

- Datos: INEI, Encuesta Nacional de Hogares (ENAHO) 2024, módulo 34 (Sumaria). Cálculos propios.
- Guion, análisis, tablero y montaje: Mirian de la Cruz Condori.
- Voz generada con IA (Qwen3-TTS) a partir de la voz de Mirian de la Cruz Condori.
- Música: «Dreamer» Kevin MacLeod (incompetech.com). Licensed under Creative Commons: By Attribution 4.0 ·
  https://creativecommons.org/licenses/by/4.0/. Ver `recursos/musica/CREDITOS.md`.
- Mapa: límites departamentales del curso Data Science Python (d2cml-ai).
- Imágenes: capturas del tablero propio.
- Tipografías: Oswald y Public Sans (Google Fonts, licencia OFL).
