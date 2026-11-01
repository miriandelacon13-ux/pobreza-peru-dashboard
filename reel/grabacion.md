# Grabación de tu voz para la narración con IA

La narración del reel se genera con una herramienta de IA (Qwen3-TTS o VoxCPM2, como en la Sesión 15) a partir de una
grabación de **tu propia voz**. La IA copia el timbre, el ritmo y la energía de esa grabación, así que conviene grabarla
con el tono que quieres en el reel: claro, cercano y con ganas de contar algo, como si se lo explicaras a alguien de confianza.

## Texto para leer (unos 20 segundos)

> Hola. Te cuento lo que encontré en los datos de pobreza del Perú de dos mil veinticuatro. Revisé miles de hogares de la
> costa, la sierra y la selva, y comparé los veinticinco departamentos. Algunas cifras sorprenden, así que vamos con
> calma, una por una.

Son 45 palabras: a ritmo natural, entre 17 y 20 segundos. El enunciado pide entre 15 y 25 segundos.

- **Si te queda por debajo de 15 segundos**, léelo más despacio, con pausas en los puntos.
- **Si pasa de 25 segundos**, léelo un poco más ágil.

El texto incluye un año y un número dichos en palabras, como los que tendrá la narración. No hace falta escribir lo que
dijiste: Whisper lo transcribe.

## Cómo grabar

1. **Lugar:** un cuarto callado, sin música, televisor ni ventilador. Mejor uno con cortinas o muebles, que no haga eco.
2. **Equipo:** el celular sirve. Puede ser una nota de voz de WhatsApp (`.opus`) o la grabadora del teléfono (`.m4a`
   o `.wav`).
3. **Distancia:** el micrófono a un palmo de la boca (15 a 20 cm) y un poco de lado, para que no se oigan los golpes
   de aire de la «p». No toques ni muevas el teléfono mientras grabas.
4. **Volumen:** habla con tu voz normal, sin gritar. Si la grabación satura o tiene ruido, la voz clonada lo hereda.
5. **Silencio:** deja un segundo antes de empezar y otro al terminar.
6. **Tomas:** graba dos o tres y quédate con la mejor. Escúchala con audífonos: sin ruidos de fondo, sin cortes y con
   todas las palabras claras.

## Dónde dejar el archivo

- Guárdalo como `reel/recursos/mi_voz.m4a` (o `.opus` o `.wav`) dentro del proyecto.
- **No se sube a GitHub:** el `.gitignore` excluye las grabaciones de voz, porque son un dato personal.
- Avísame cuando esté listo y seguimos:
  1. Generar la narración con la voz clonada.
  2. Revisar la pronunciación de las cifras.
  3. Hacer los subtítulos.
  4. Agregar la música y armar el video.

## Reglas

- Solo se clona tu propia voz.
- El video muestra «Voz generada con IA» todo el tiempo, y la publicación de LinkedIn también lo dirá.
