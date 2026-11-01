# Pobreza monetaria en el Perú, 2024: departamentos y brecha urbano-rural

Tarea 3 del curso Python Intermedio: *Del dato a la historia: dashboard interactivo y reel con IA*
([enunciado](https://github.com/d2cml-ai/Data-Science-Python/issues/197)).

- **Dashboard:** https://miriandelacon13-ux.github.io/pobreza-peru-dashboard/web/
- **Publicación de LinkedIn:** *pendiente (etapa 4)*

## Tema y pregunta de investigación

**Tema:** pobreza y desigualdad territorial en el Perú.

**Pregunta:** ¿Cómo se distribuye la pobreza monetaria entre los departamentos del Perú y qué brecha existe entre las
áreas urbana y rural en 2024?

**Cobertura:** los 25 departamentos (Lima y Callao por separado), áreas urbana y rural, año 2024.

## Descripción

El proyecto estima la pobreza monetaria total, extrema y no extrema de 2024 con los microdatos de la Encuesta Nacional
de Hogares (ENAHO) del INEI.

- **Desagregación:** por departamento, por área y por departamento × área.
- **Además de cada tasa:** la población estimada, el número aproximado de pobres y el margen de error.
- **Productos:** un dashboard público e interactivo y un reel de divulgación (etapa 3).

## Estado del proyecto

| Etapa | Estado |
|---|---|
| **1. Obtención, procesamiento, análisis y verificación de datos** | ✅ Completa |
| **2. Dashboard público e interactivo** | ✅ Publicado en GitHub Pages |
| 3. Reel con IA (guion, narración con voz propia, imágenes, música, subtítulos) | ⏳ Pendiente |
| 4. Publicación en LinkedIn y README final | ⏳ Pendiente |

## Dashboard

[Abrir el dashboard](https://miriandelacon13-ux.github.io/pobreza-peru-dashboard/web/). Es una página estática en
`web/`, hecha con HTML, CSS, JavaScript y Plotly, y publicada con GitHub Pages.

**Controles.** Un solo bloque de filtros arriba actualiza todos los indicadores y gráficos:

- Departamento: todo el Perú o uno de los 25.
- Área: urbana y rural, urbana o rural.
- Tipo de pobreza: total, extrema o no extrema.
- Medida del mapa: tasa o número de personas.

También se puede elegir un departamento con un clic en el mapa o en el ranking. El estado de los filtros queda en la
URL, para compartirlo.

**Cuatro KPI:**

1. Tasa de pobreza con su IC 95 % y el número de hogares de la muestra.
2. Personas en pobreza, como estimación propia, con su participación en el total del país.
3. Brecha rural − urbana, con su IC y si la diferencia es clara.
4. Comparación del departamento con el país o, para todo el Perú, el departamento con la mayor tasa.

**Visualizaciones:**

- Mapa interactivo de los 25 departamentos.
- Ranking con intervalos de confianza.
- Brecha urbano-rural por departamento.
- Tasa frente a número de pobres.
- Composición extrema / no extrema / no pobre.
- Una tabla con todos los datos.

**Cómo se calculan las cifras.** El navegador no calcula ninguna tasa ni promedia porcentajes: muestra las
estimaciones de `web/data/pobreza_2024.json`, que salen de las tablas verificadas.

**Datos inexistentes.** Callao no tiene hogares rurales en la muestra. Por eso aparece como «sin dato» o «no
disponible», y en gris en el mapa, nunca como cero. Una tasa de 0 que sí está en la muestra (pobreza extrema rural de
Ica: ningún hogar de 217) se muestra como 0.0 %, con su intervalo y su CV marcados como no estimables.

**Prueba automática.** `scripts/probar_dashboard.py` abre el dashboard en Edge o Chrome sin interfaz y hace 816
comprobaciones, todas OK.

- Cambia los filtros como lo haría una persona, en 45 combinaciones de departamento × área × tipo.
- Compara los KPI, el mapa, el ranking, la dispersión y la composición con los CSV verificados.
- Prueba el clic en el mapa, el botón Restablecer, la URL, el modo oscuro y la vista de celular.
- Revisa la redacción de los textos.
- Falla ante cualquier error de JavaScript o petición fallida.

## Fuentes de datos y metodología

| Fuente | Enlace | Uso |
|---|---|---|
| INEI, ENAHO 2024, módulo 34 (Sumaria) | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip | Todas las cifras |
| INEI, *Una mirada al Perú en cifras* Nº 7 (julio 2024) | [PDF](https://cdn.www.gob.pe/uploads/document/file/6726276/5836665-una-mirada-al-peru-en-cifras.pdf) | Población proyectada al 2024: 34,038,457 |
| Límites de los 25 departamentos (GeoJSON) | [repositorio del curso](https://github.com/d2cml-ai/Data-Science-Python/blob/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson) | Mapa |
| Pobreza por departamento de la Sesión 16 del curso | [repositorio del curso](https://github.com/d2cml-ai/Data-Science-Python/blob/main/sessions/16-skills-enaho/referencias/pobreza_departamento_2024.csv) | Solo para verificar |

La URL, la fecha de obtención (31 oct. 2026) y el SHA-256 de cada archivo descargado están en
[`datos/originales/manifiesto.json`](datos/originales/manifiesto.json).

**Metodología.** Se cuenta a los **miembros del hogar** como lo hace la sumaria del INEI: `p204 = 1`, sin trabajadores
del hogar ni pensionistas.

- Cada hogar es una fila y representa a `factor07 × mieperho` personas.
- Cada tasa es el cociente de las personas pobres estimadas entre la población estimada del grupo, calculado desde los
  hogares. **Nunca se promedian porcentajes.**
- Los intervalos de confianza al 95 % usan linealización con el conglomerado como unidad de muestreo, como el do-file
  del INEI.

**Diferencias «claras».** Cuando se dice que un departamento es mayor o menor que el país, o que una brecha es clara,
se prueba la **diferencia** entre las dos tasas. Su intervalo incluye la covarianza, y la diferencia es clara si ese
intervalo no contiene el cero. No basta con que dos intervalos no se superpongan.

Detalle, variables y fórmulas en [`docs/metodologia.md`](docs/metodologia.md).

**Verificación.** `datos/procesados/verificacion.txt` tiene 42 comprobaciones, todas OK.

- Pobreza nacional 27.58 %, extrema 5.50 %, urbana 24.81 % y rural 39.30 %. Coinciden con las cifras del INEI al
  decimal publicado (27.6, 5.5, 24.8 y 39.3 %); esas cifras se confirmaron en notas de prensa.
- Los 25 departamentos quedan a 0.049 puntos o menos de la referencia del curso.
- Departamentos y áreas suman los totales.
- Los errores estándar de tasas y diferencias coinciden con un bootstrap de conglomerados.

## Tres hallazgos principales

Detalle en [`docs/hallazgos.md`](docs/hallazgos.md).

1. **La pobreza va de 6.0 % en Ica a 45.0 % en Cajamarca.**
   - 9 departamentos tienen una tasa claramente mayor que la del país (27.6 %): Cajamarca, Loreto, Puno, Pasco,
     Huánuco, Callao, Huancavelica, Ayacucho y Piura.
   - 9 tienen una tasa claramente menor y 7 no se distinguen.
   - Entre los cinco primeros no hay un orden exacto: la diferencia de Cajamarca con Loreto, Puno, Pasco y Huánuco no
     es clara.
2. **La tasa y el número de pobres señalan lugares distintos.**
   - Lima tiene una tasa de 27.1 %, 0.5 puntos por debajo de la del país. Esa diferencia no es clara: su IC 95 % va de
     −2.2 a +1.2 puntos.
   - Aun así, Lima concentra el 32.1 % de las personas pobres del país, unos 3.05 millones según la estimación propia.
     Son más que las de Cajamarca, Puno, Piura y La Libertad juntas.
   - El 72.7 % de los pobres vive en zonas urbanas.
3. **La pobreza rural (39.3 %) supera a la urbana (24.8 %) en 14.5 puntos**, con un IC 95 % de 12.4 a 16.6.
   - La pobreza extrema rural es casi 5 veces la urbana: 15.5 % frente a 3.1 %. El campo tiene el 19 % de la población
     y el 54 % de los pobres extremos.
   - La brecha es clara en 15 de los 24 departamentos con ambas áreas. Llega a 28.4 puntos en Loreto.

## Limitaciones

- **Error de muestreo.** Las cifras departamentales tienen intervalos amplios. Ica, Madre de Dios y Moquegua, y varias
  celdas departamento × área, tienen un CV mayor a 15 % y son referenciales.
- **Los números absolutos son estimaciones propias.** Expanden la muestra con `factor07 × mieperho`, que suma 34.48
  millones de personas, y dan 9.51 millones de pobres.
  - El INEI difundió 9.395 millones. Esa cifra es igual a su tasa (27.6 %) por la población proyectada al 2024
    (34,038,457).
  - Las tasas coinciden; la diferencia (+1.2 %) está solo en la población total.
- **Callao** no tiene hogares rurales en la muestra.
- **«Lima»** es el departamento completo. No es «Lima Metropolitana», que en la ENAHO incluye a Callao.
- **Un solo año**, y solo pobreza monetaria.

Ver [`docs/metodologia.md`](docs/metodologia.md#limitaciones).

## Cómo reproducir

Se necesita [uv](https://docs.astral.sh/uv/), o Python 3.13 con `pip install -r requirements.txt`.

```bash
uv sync
uv run scripts/obtener_datos.py     # baja la Sumaria del INEI y el GeoJSON; escribe el manifiesto con los SHA-256
uv run scripts/procesar_datos.py    # base de hogares limpia (datos/procesados/hogares_2024.parquet)
uv run scripts/analizar_datos.py    # tablas, comparaciones y cifras_clave_2024.json
uv run scripts/verificar_datos.py   # 42 comprobaciones -> datos/procesados/verificacion.txt
uv run scripts/exportar_web.py      # datos del dashboard -> web/data/
uv run scripts/probar_dashboard.py  # prueba el dashboard en un navegador (necesita Edge o Chrome)
```

- **Ver el dashboard en local:** `python -m http.server` en la raíz del repositorio y abrir
  http://localhost:8000/web/.
- **Si el portal del INEI rechaza la descarga automática:** baja `966-Modulo34.zip` desde el navegador a
  `datos/originales/` y vuelve a correr `obtener_datos.py`.

## Estructura

```text
datos/
  originales/   manifiesto.json, GeoJSON y referencia del curso (el zip del INEI no se sube: se descarga)
  procesados/   tablas CSV, cifras_clave_2024.json, verificacion.txt y su diccionario (README.md)
scripts/        obtener, procesar, analizar, verificar y exportar los datos; probar el dashboard (navegador.py)
docs/           metodologia.md, hallazgos.md
web/            dashboard: index.html, assets/ (estilos.css, app.js), data/ (JSON y GeoJSON)
index.html      redirige a web/ (raíz del sitio de GitHub Pages)
reel/           se creará en la etapa 3
```

## Recursos reutilizados

- **Lectura de la Sumaria.** La lectura y normalización están adaptadas de `scripts/limpiar.py` del proyecto anterior
  [`enaho-skills`](https://github.com/miriandelacon13-ux/enaho-skills) (commit `c40106c`): `aÑo` → `anio`, llaves como
  texto y nombres de departamento. También viene de ahí la decisión de usar la alternativa B.
- **Datos.** No se copiaron del proyecto anterior: se descargan de sus fuentes originales. El zip del INEI es idéntico
  byte a byte al usado allí.
- **Paleta.** Los colores del dashboard vienen de una paleta validada para daltonismo y contraste, en modo claro y
  oscuro.

## Uso de inteligencia artificial

Este proyecto se desarrolla con Claude Code, de Anthropic, como asistente para escribir el código, verificar las
cifras, construir el dashboard y redactar la documentación. La autora tomó las decisiones metodológicas, como usar la
alternativa B, y es responsable de revisar los resultados. Las cifras salen de los scripts del repositorio, no del
asistente; su verificación está en `datos/procesados/verificacion.txt`, y la del dashboard, en
`scripts/probar_dashboard.py`.
