# Guion del reel: «¿Dónde está la pobreza?»

Reel vertical 9:16 (1080 × 1920) de unos 60 segundos, en 7 escenas. Resume los tres hallazgos del
[tablero](https://miriandelacon13-ux.github.io/pobreza-peru-dashboard/web/).

- **Duración estimada:** entre 53 y 64 s, según la voz (159 palabras a 3.0 o 2.5 palabras por segundo).
- **Versión para las herramientas:** [`guion.json`](guion.json), en el formato de la Sesión 15 del curso. En ese archivo
  los números van en palabras para la voz y en dígitos para la pantalla.
- **Verificación:** `uv run scripts/verificar_guion.py` hace 35 comprobaciones, todas OK. Revisa cada cifra y cada
  aproximación («casi la mitad», «casi cinco veces») contra los CSV del proyecto, además del formato y la duración.

## Siempre en pantalla

- **Arriba, en una esquina:** «Voz generada con IA».
- **Abajo:** «Fuente: INEI, ENAHO 2024 · cálculos propios».
- **Subtítulos** sincronizados con la narración, en la mitad inferior.

## Escenas

### 1. Pobreza en el Perú · 0:00–0:10

> En 2024, más de una de cada cuatro personas en el Perú vivía en pobreza monetaria. ¿Pero es igual en todo el país?

- **En pantalla:** «27.6 %» · *Pobreza monetaria en el Perú, 2024*
- **Visual:** el mapa del tablero (tasa total) aparece con un acercamiento lento, con la cifra encima.
- **Respaldo:** tasa nacional 27.58 %; el INEI publicó 27.6 %.

### 2. La encuesta · 0:10–0:20

> Analicé la encuesta del INEI a más de 33 mil hogares. Es pobre quien vive en un hogar que no cubre la canasta básica.

- **En pantalla:** «33,691» · *Hogares de la Encuesta Nacional de Hogares 2024*
- **Visual:** la cabecera del tablero (pregunta, cobertura, fuente, muestra) con un desplazamiento lento.
- **Respaldo:** 33,691 hogares en la Sumaria 2024.

### 3. Hallazgo 1: los departamentos · 0:20–0:29

> Las diferencias entre departamentos son enormes: en Cajamarca, casi la mitad de la población es pobre; en Ica, seis
> de cada cien.

- **En pantalla:** «45.0 % vs 6.0 %» · *Cajamarca frente a Ica, 2024*
- **Visual:** el mapa con Cajamarca resaltada y luego Ica; después, el ranking con sus intervalos.
- **Respaldo:** Cajamarca 45.01 %, Ica 6.01 %.

### 4. Hallazgo 2: Lima · 0:29–0:39

> La tasa no lo dice todo: Lima está cerca del promedio nacional, pero según mis cálculos reúne casi uno de cada tres
> pobres del Perú.

- **En pantalla:** «32.1 %» · *De los pobres viven en Lima (cálculo propio)*
- **Visual:** el mapa en modo «Personas», donde Lima destaca; luego, el gráfico de tasa frente a número de pobres, con
  Lima resaltada.
- **Respaldo:** Lima 27.07 % frente a 27.58 % del país. La participación de 32.1 % es una estimación propia.

### 5. Hallazgo 3: el campo y la ciudad · 0:39–0:49

> En el campo la pobreza es mayor: casi cuatro de cada diez personas son pobres, y en las ciudades, casi una de cada
> cuatro.

- **En pantalla:** «39.3 % vs 24.8 %» · *Pobreza rural frente a urbana, 2024*
- **Visual:** el gráfico de brecha urbano-rural por departamento; se alternan los mapas urbano y rural.
- **Respaldo:** rural 39.30 % y urbana 24.81 %; el INEI publicó 39.3 % y 24.8 %.

### 6. Hallazgo 3: la pobreza extrema · 0:49–0:56

> Y la pobreza extrema golpea más al campo: allí es casi cinco veces la de las ciudades.

- **En pantalla:** «15.5 % vs 3.1 %» · *Pobreza extrema rural frente a urbana*
- **Visual:** la composición con la pobreza extrema resaltada y el mapa de pobreza extrema rural.
- **Respaldo:** 15.52 % frente a 3.14 %, es decir, 4.95 veces.

### 7. Invitación · 0:56–1:04

> Busca tu departamento y compara el campo con la ciudad en mi tablero interactivo. El enlace está en la publicación.

- **En pantalla:** *Explora el tablero: enlace en la publicación*
- **Visual:** una grabación de pantalla del tablero público (elegir un departamento, cambiar de área) y luego la tarjeta
  de créditos.

Las capturas salen del tablero publicado con los filtros de cada URL:

| Escena | URL |
|---|---|
| 1 | `web/` |
| 2 | `web/` (cabecera) |
| 3 | `web/?dep=06`, `web/?dep=11` |
| 4 | `web/?medida=personas`, `web/?dep=15` |
| 5 | `web/`, `web/?area=urbana`, `web/?area=rural` |
| 6 | `web/?tipo=extrema`, `web/?area=rural&tipo=extrema` |
| 7 | grabación de pantalla del tablero público |

## Tarjeta final de créditos

- Datos: INEI, Encuesta Nacional de Hogares (ENAHO) 2024, módulo 34 (Sumaria). Cálculos propios.
- Análisis y tablero: Mirian de la Cruz Condori · github.com/miriandelacon13-ux/pobreza-peru-dashboard
- Mapa: límites departamentales del curso Data Science Python (d2cml-ai)
- Voz generada con IA (*[Qwen3-TTS o VoxCPM2]*) a partir de mi propia voz
- Música: *[título]* de *[autor]*, *[licencia y enlace]*
- Imágenes: capturas de mi tablero (si se agregan fotos o imágenes generadas con IA, se acredita cada una)

## Criterios del guion

- **Cifras.** Todas son tasas de la ENAHO 2024 calculadas y verificadas en este proyecto. La nacional, la urbana y la
  rural coinciden con las publicadas por el INEI.
  - Las cifras departamentales y la pobreza extrema por área son cálculos propios con los microdatos del INEI. Por eso
    la fuente en pantalla dice «cálculos propios».
- **Estimaciones propias.** No se usan números absolutos de personas («9.5 millones»), porque no coinciden con los
  oficiales. La única cifra que viene de la expansión propia, el 32.1 % de la escena 4, se anuncia como «según mis
  cálculos» y en pantalla como «cálculo propio».
- **Sin afirmaciones de significancia.** La narración describe tamaños («casi la mitad», «casi cinco veces», «cerca
  del promedio») sin decir «estadísticamente significativo».
  - Las comparaciones que se insinúan están respaldadas por las pruebas de `docs/metodologia.md`: Cajamarca e Ica
    frente al país, y la brecha rural − urbana.
  - No se dice que Cajamarca sea «el más pobre», porque no se distingue de Loreto, Puno, Pasco ni Huánuco.
- **Palabras sencillas.** En lugar de porcentajes con decimales, se usan proporciones («una de cada cuatro»). Los
  decimales quedan en pantalla.
- **«Lima»** es el departamento de Lima, como en el tablero.

## Pendiente para producir el reel

1. Tu grabación de voz ([`grabacion.md`](grabacion.md)).
2. Elegir la música (abajo) y completar los créditos con la herramienta de voz.
3. Generar la narración, revisar cómo se pronuncian «INEI», «Cajamarca» e «Ica», hacer los subtítulos con Whisper,
   tomar las capturas y armar el video.

### Cómo elegir la música

- Una pista instrumental y tranquila, con una licencia que permita usarla en redes. Por ejemplo, una con licencia
  Creative Commons BY, que pide atribución, o una de una biblioteca que autorice el uso en video.
- Anota el título, el autor, el enlace y la licencia para los créditos.
- En el video irá a un volumen claramente menor que la voz.
