# Pobreza monetaria en el Perú, 2024: departamentos y brecha urbano-rural

Tarea 3 del curso Python Intermedio: *Del dato a la historia: dashboard interactivo y reel con IA*
([enunciado](https://github.com/d2cml-ai/Data-Science-Python/issues/197)).

## Tema y pregunta de investigación

**Tema:** pobreza y desigualdad territorial en el Perú.

**Pregunta:** ¿Cómo se distribuye la pobreza monetaria entre los departamentos del Perú y qué brecha existe entre las
áreas urbana y rural en 2024?

**Cobertura:** los 25 departamentos (Lima y Callao por separado), áreas urbana y rural, año 2024.

## Descripción

El proyecto estima la pobreza monetaria total, extrema y no extrema de 2024 con los microdatos de la Encuesta Nacional
de Hogares (ENAHO) del INEI.

- **Desagregación:** por departamento, por área y por departamento × área.
- **Además de cada tasa:** la población estimada, el número aproximado de pobres y el error de muestreo.
- **Resultados finales:** un dashboard público e interactivo y un reel de divulgación (etapas siguientes).

## Estado del proyecto

| Etapa | Estado |
|---|---|
| **1. Obtención, procesamiento, análisis y verificación de datos** | ✅ Completa |
| 2. Dashboard público e interactivo (4 KPIs, 4 visualizaciones con mapa, 3 controles) | ⏳ Pendiente |
| 3. Reel con IA (guion, narración con voz propia, imágenes, música, subtítulos) | ⏳ Pendiente |
| 4. Publicación en LinkedIn y README final | ⏳ Pendiente |

## Fuentes de datos y metodología

| Fuente | Enlace | Uso |
|---|---|---|
| INEI, ENAHO 2024, módulo 34 (Sumaria) | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip | Todas las cifras |
| Límites de los 25 departamentos (GeoJSON) | [repositorio del curso](https://github.com/d2cml-ai/Data-Science-Python/blob/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson) | Mapa (etapa 2) |
| Pobreza por departamento de la Sesión 16 del curso | [repositorio del curso](https://github.com/d2cml-ai/Data-Science-Python/blob/main/sessions/16-skills-enaho/referencias/pobreza_departamento_2024.csv) | Solo para verificar |

La URL, la fecha de obtención (31 oct. 2026) y el SHA-256 de cada archivo están en
[`datos/originales/manifiesto.json`](datos/originales/manifiesto.json).

**Metodología.** Se cuenta a los **miembros del hogar** como lo hace la sumaria del INEI: `p204 = 1`, sin trabajadores
del hogar ni pensionistas.

- Cada hogar es **una fila** y representa a `factor07 × mieperho` personas.
- Cada tasa es el cociente de las personas pobres estimadas entre la población estimada del grupo. **Nunca se promedian
  porcentajes.**
- Cada tasa trae su intervalo de confianza al 95 %, con el conglomerado como unidad de muestreo, como en el do-file del
  INEI.

Detalle, variables, fórmulas y verificación en [`docs/metodologia.md`](docs/metodologia.md).

**Verificación.** `datos/procesados/verificacion.txt`: 32 comprobaciones, todas OK.

- Pobreza nacional 27.58 %, extrema 5.50 %, urbana 24.81 % y rural 39.30 %. Coinciden con las cifras del INEI (27.6,
  5.5, 24.8 y 39.3 %), que se confirmaron en notas de prensa.
- Los 25 departamentos quedan a 0.049 puntos o menos de la referencia del curso.
- Departamentos y áreas suman los totales nacionales.
- El error estándar coincide con un bootstrap de conglomerados.

## Tres hallazgos principales

Detalle en [`docs/hallazgos.md`](docs/hallazgos.md).

1. **La pobreza va de 6.0 % en Ica a 45.0 % en Cajamarca.**
   - 9 departamentos están por encima del promedio nacional (27.6 %), aun considerando el error de muestreo: Cajamarca,
     Loreto, Puno, Pasco, Huánuco, Callao, Huancavelica, Ayacucho y Piura.
   - 9 están por debajo y 7 no se distinguen del promedio.
2. **La tasa y el número de pobres cuentan historias distintas.** Lima tiene una tasa igual al promedio (27.1 %), pero
   concentra el 32.1 % de los pobres del país, unos 3.05 millones. Son más que los de Cajamarca, Puno, Piura y La
   Libertad juntos. Además, el 72.7 % de los pobres vive en zonas urbanas.
3. **La pobreza rural (39.3 %) supera a la urbana (24.8 %) en 14.5 puntos**, con un IC 95 % de 12.4 a 16.6.
   - La pobreza extrema rural es casi 5 veces la urbana: 15.5 % frente a 3.1 %. El campo tiene el 19 % de la población
     y el 54 % de los pobres extremos.
   - La brecha es significativa en 15 de los 24 departamentos con ambas áreas. Llega a 28.4 puntos en Loreto (63.4 %
     rural frente a 35.0 % urbana).

## Limitaciones

- **Error de muestreo.** Las cifras departamentales tienen intervalos amplios: no se puede ordenar con precisión a los
  departamentos más pobres. Ica, Madre de Dios y Moquegua, y 13 de las 49 celdas departamento × área, tienen un CV
  mayor a 15 %.
- **Callao** no tiene hogares rurales en la muestra.
- **«Lima»** es el departamento completo. No es «Lima Metropolitana», que en la ENAHO incluye a Callao.
- **Los números absolutos son aproximados:** 9.51 millones de pobres frente a los 9.395 millones que difundió el INEI.
  Las tasas sí coinciden.
- **Un solo año**, y solo pobreza monetaria.

Ver [`docs/metodologia.md`](docs/metodologia.md#limitaciones).

## Enlaces

- Dashboard: *pendiente (etapa 2)*
- Publicación de LinkedIn: *pendiente (etapa 4)*

## Cómo reproducir

Se necesita [uv](https://docs.astral.sh/uv/), o Python 3.13 con `pip install -r requirements.txt`.

```bash
uv sync
uv run scripts/obtener_datos.py     # baja la Sumaria del INEI y el GeoJSON; escribe el manifiesto con los SHA-256
uv run scripts/procesar_datos.py    # base de hogares limpia (datos/procesados/hogares_2024.parquet)
uv run scripts/analizar_datos.py    # tablas por departamento y área + cifras_clave_2024.json
uv run scripts/verificar_datos.py   # 32 comprobaciones -> datos/procesados/verificacion.txt
```

Si el portal del INEI rechaza la descarga automática, baja `966-Modulo34.zip` desde el navegador a
`datos/originales/` y vuelve a correr `obtener_datos.py`.

## Estructura

```text
datos/
  originales/   manifiesto.json, GeoJSON y referencia del curso (el zip del INEI no se sube: se descarga)
  procesados/   tablas CSV, cifras_clave_2024.json, verificacion.txt y su diccionario (README.md)
scripts/        obtener_datos.py, procesar_datos.py, analizar_datos.py, verificar_datos.py
docs/           metodologia.md, hallazgos.md
web/  reel/     se crearán en las etapas 2 y 3
```

## Recursos reutilizados

- **Lectura de la Sumaria.** La lectura y normalización están adaptadas de `scripts/limpiar.py` del proyecto anterior
  [`enaho-skills`](https://github.com/miriandelacon13-ux/enaho-skills) (commit `c40106c`): `aÑo` → `anio`, llaves como
  texto y nombres de departamento. También viene de ahí la decisión de usar la alternativa B.
- **Datos.** No se copiaron del proyecto anterior: se descargan de sus fuentes originales. El zip del INEI es idéntico
  byte a byte al usado allí.

## Uso de inteligencia artificial

Este proyecto se desarrolla con Claude Code, de Anthropic, como asistente para escribir el código, verificar las
cifras y redactar la documentación. La autora tomó las decisiones metodológicas, como usar la alternativa B, y es
responsable de revisar los resultados. Las cifras salen de los scripts del repositorio, no del asistente, y su
verificación está en `datos/procesados/verificacion.txt`.
