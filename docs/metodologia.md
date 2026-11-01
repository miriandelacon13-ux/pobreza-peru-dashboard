# Metodología: pobreza monetaria 2024 por departamento y área

## Pregunta

¿Cómo se distribuye la pobreza monetaria entre los departamentos del Perú y qué brecha existe entre las áreas urbana y
rural en 2024?

- **Cobertura:** Perú, los 25 departamentos (Lima y Callao por separado), áreas urbana y rural, año 2024.
- **Unidad:** personas que son miembros de hogares particulares, estimadas desde una muestra de hogares.

## Fuentes

Las descarga `scripts/obtener_datos.py`, que guarda la URL, la fecha y el SHA-256 de cada archivo en
`datos/originales/manifiesto.json`.

| Archivo | Fuente | Uso |
|---|---|---|
| `966-Modulo34.zip` (16 MB, no se sube a git) | [INEI, ENAHO 2024, módulo 34 «Sumaria»](https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip). Portal de microdatos del INEI, código 966 = ENAHO 2024. Contiene `sumaria-2024.dta` (fechado el 8 may. 2025) y la documentación (`Sumaria-2024.pdf`, `Diccionario2024.pdf`, `FichaTecnica.pdf`) | Datos de todas las tablas |
| `peru_departamental_simple.geojson` | [Repositorio del curso](https://github.com/d2cml-ai/Data-Science-Python/blob/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson), 25 departamentos con `FIRST_IDDP` | Mapa del dashboard (siguiente etapa) |
| `referencia_curso_pobreza_departamento_2024.csv` | [Repositorio del curso](https://github.com/d2cml-ai/Data-Science-Python/blob/main/sessions/16-skills-enaho/referencias/pobreza_departamento_2024.csv), Sesión 16 | Solo para verificar |

Se descargaron el 31 de octubre de 2026. El zip es idéntico, byte a byte, al usado en el proyecto anterior
[`enaho-skills`](https://github.com/miriandelacon13-ux/enaho-skills) (SHA-256 `5ee98dad…`).

Las cifras oficiales con las que se compara salen del informe del INEI «Perú: Evolución de la pobreza monetaria
2015-2024» (mayo de 2025): nacional 27.6 %, extrema 5.5 %, urbana 24.8 % y rural 39.3 %. **Solo se pudieron confirmar
en notas de prensa** (Canal N, Forbes Perú, Expreso), porque gob.pe no permite la descarga automática del informe.

## Variables usadas (Sumaria 2024)

| Variable | Qué es | Uso |
|---|---|---|
| `conglome`, `vivienda`, `hogar` | Llaves del hogar, como texto con ceros a la izquierda | Identificar hogares; `conglome` es la unidad primaria de muestreo |
| `ubigeo` | Ubicación geográfica (6 dígitos) | Departamento = `ubigeo[:2]` |
| `estrato` | Estrato geográfico: 1 a 5 urbano (centros poblados de 2,000 habitantes o más), 6 a 8 rural | Área urbana o rural |
| `pobreza` | Condición de pobreza del hogar calculada por el INEI: 1 pobre extremo, 2 pobre no extremo, 3 no pobre | Indicadores |
| `mieperho` | Total de miembros del hogar: p204 = 1, sin trabajadores del hogar (p203 = 8) ni pensionistas (p203 = 9) | Personas que cuenta cada hogar |
| `factor07` | Factor de expansión anual (proyecciones CPV-2007) | Expansión a la población |

## Procedimiento

**1. Obtener** (`scripts/obtener_datos.py`). Descarga los archivos y compara su SHA-256 con el verificado.

**2. Procesar** (`scripts/procesar_datos.py`).
- Lee `sumaria-2024.dta` desde el zip con `convert_categoricals=False`, para quedarse con los códigos y no con las
  etiquetas.
- Pasa los nombres de columna a minúscula. La columna del año llega como `aÑo` y queda como `anio`.
- Comprueba:
  - que las llaves y el `ubigeo` tengan su ancho completo;
  - que no haya hogares repetidos ni faltantes;
  - que `pobreza` solo tenga los códigos 1, 2 y 3;
  - que `mieperho` sea al menos 1 y `factor07` sea positivo.
- Construye `departamento`, `area`, `pobre`, `pobre_extremo`, `pobre_no_extremo` y `peso = factor07 × mieperho`.

**3. Analizar** (`scripts/analizar_datos.py`).

Alternativa B, miembros del hogar: una fila por hogar, y cada hogar representa a `factor07 × mieperho` personas. Es el
procedimiento de la sumaria. El do-file oficial del INEI (`01.ConstrVarGastoIngreso2014-2024.do`, dentro del
módulo 34) usa `gen factornd07=round(factor07*mieperho,1)` y `svyset [pweight = factornd07], psu(conglome)`. Aquí no se
redondea; el efecto sobre la tasa nacional es de 0.0001 puntos.

Para cada grupo (país, área, departamento, departamento × área):

```text
población estimada  = Σ factor07 × mieperho                                (todos los hogares del grupo)
pobres estimados    = Σ factor07 × mieperho                                (hogares con pobreza = 1 o 2)
tasa de pobreza     = pobres estimados / población estimada × 100
tasa extrema        = Σ (factor07 × mieperho | pobreza = 1) / población × 100
tasa no extrema     = Σ (factor07 × mieperho | pobreza = 2) / población × 100   (total = extrema + no extrema)
```

**Ninguna tasa promedia porcentajes.** La tasa nacional sale de los totales: el promedio simple de las 25 tasas
departamentales daría 26.50 % en vez de 27.58 %, porque ignora que Lima tiene 11.3 millones de habitantes y Moquegua
0.2 millones.

**Error de muestreo.** Para cada tasa se calcula el error estándar por linealización de Taylor de un cociente, con
`conglome` como unidad primaria de muestreo y sin estratos, igual que el do-file del INEI. Con ese error se obtienen:

- el intervalo de confianza al 95 % (tasa ± 1.96 × error estándar);
- el coeficiente de variación (CV = error estándar / tasa).

Cuando el CV es mayor que 15 %, la estimación se marca como **referencial**. Es un criterio de precisión de este
proyecto.

Los dominios se estiman sobre la muestra completa, con ceros fuera del dominio. Cada conglomerado pertenece a un solo
departamento y a una sola área.

### Comparaciones y significancia

Cuando el proyecto dice que una tasa es «mayor», «menor» o que una brecha es «clara», se refiere a una prueba sobre la
**diferencia** de dos tasas, no a si sus intervalos se superponen.

1. **La diferencia.** `D = tasa(A) − tasa(B)`.
2. **Su error estándar.** Se calcula por linealización. La contribución de cada conglomerado es la de A menos la de B,
   así que el error **incluye la covarianza** entre las dos tasas. Eso importa porque un departamento es parte del
   total nacional, y el área urbana y la rural son partes del mismo país.
3. **El intervalo.** IC 95 % = `D ± 1.96 × error estándar`.
4. **La clasificación:**
   - **Mayor** si el intervalo está entero por encima de 0.
   - **Menor** si está entero por debajo de 0.
   - **No distinguible** si incluye el 0.

Comparaciones calculadas (`scripts/analizar_datos.py`):

| Comparación | Columnas o archivo |
|---|---|
| Cada departamento frente al país, para los tres tipos de pobreza | `dif_nacional_*`, `ic95_*_dif_nacional_*` y `comparacion_nacional_*` en `pobreza_departamento_2024.csv` |
| Cada celda departamento × área frente a la misma área en el país | `*_area_nacional_*` en `pobreza_departamento_area_2024.csv` |
| Brecha rural − urbana del país y de los 24 departamentos con ambas áreas, por tipo de pobreza | `brecha_urbano_rural_2024.csv` |
| El departamento con la tasa más alta frente a los cuatro siguientes | `cifras_clave_2024.json` |

Es una prueba por comparación, con un nivel de 95 % en cada una. Al revisar 25 departamentos a la vez, se pueden
esperar uno o dos falsos positivos por azar. Las diferencias pequeñas que apenas excluyen el cero deben leerse con
cuidado.

**4. Verificar** (`scripts/verificar_datos.py` → `datos/procesados/verificacion.txt`). Son 42 comprobaciones; todas
dan OK:

- La pobreza nacional (27.58 %), extrema (5.50 %), urbana (24.81 %) y rural (39.30 %) coinciden con las cifras del
  INEI al decimal publicado.
- Los 25 departamentos quedan a 0.049 puntos o menos de la referencia del curso.
- Las cifras absolutas del INEI son iguales a su tasa publicada por la población proyectada al 2024 (ver limitación 4).
- Los departamentos, las áreas y las celdas departamento × área suman los totales.
- Pobreza total = extrema + no extrema.
- Las diferencias y las brechas cuadran con las tasas, y su clasificación con su IC.
- Los errores estándar linealizados coinciden con un bootstrap de 500 réplicas de conglomerados (razón entre 0.95 y
  1.04). Se comparan seis tasas, dos diferencias departamento − país y la brecha nacional.

## Limitaciones

1. **Es una muestra.** Las cifras departamentales tienen error de muestreo; por ejemplo, Cajamarca es 45.0 % con un
   IC 95 % de 40.5 a 49.5. Diferencias de pocos puntos entre departamentos pueden no ser significativas: Cajamarca no
   se distingue de Loreto, Puno, Pasco ni Huánuco. Por eso el INEI publica los departamentos en grupos.
   - Departamentos referenciales (CV > 15 %): Ica, Madre de Dios y Moquegua.
   - Celdas departamento × área referenciales: 13 de 49. La de Ica rural (2.6 %) tiene un CV de 60 %.
2. **Callao no tiene hogares rurales en la muestra**, así que no hay brecha urbano-rural para Callao.
3. **«Lima» es el departamento completo**: la provincia de Lima (Lima Metropolitana sin Callao) más Lima Provincias.
   En la ENAHO, el dominio «Lima Metropolitana» (`dominio = 8`) incluye Callao: los 1,027 hogares de Callao de la
   muestra están en ese dominio. Por eso las cifras de Lima Metropolitana no son comparables con las del departamento
   de Lima.
4. **Las cifras absolutas son estimaciones propias.** Personas pobres y población salen de expandir la muestra con
   `factor07 × mieperho`, que suma 34,482,699 personas. Así se obtienen 9,510,145 pobres y 1,898,111 pobres extremos.
   - **El INEI difundió 9 395 000 y 1 872 000.** Esas cifras son iguales a su tasa publicada (27.6 % y 5.5 %) por la
     población total proyectada al 2024: 34,038,457 personas, según
     [*Una mirada al Perú en cifras* Nº 7, julio 2024](https://cdn.www.gob.pe/uploads/document/file/6726276/5836665-una-mirada-al-peru-en-cifras.pdf).
     La comprobación está en `verificar_datos.py`.
   - **La diferencia (+1.2 %) no viene de las tasas, que coinciden.** Viene de la población total: la de la expansión
     es 444,242 personas mayor que la proyectada.
   - **Por eso los números absolutos se presentan como estimaciones propias y aproximadas.** Las tasas no dependen
     de esa población total. Las participaciones (por ejemplo, el 32.1 % de los pobres que vive en Lima) son cocientes
     dentro de la misma expansión: no cambiarían si toda la expansión se ajustara proporcionalmente al total
     proyectado.
5. **Población cubierta.** Miembros de hogares particulares, sin trabajadores del hogar ni pensionistas y sin
   viviendas colectivas. Es la población de la pobreza monetaria del INEI.
6. **Área urbana y rural.** Se definen por el estrato del conglomerado (2,000 habitantes), no por límites
   administrativos.
7. **La pobreza monetaria mide el gasto per cápita frente a una línea de pobreza.** No mide otras carencias, como la
   pobreza multidimensional.
8. **Un solo año (2024).** No hay tendencias ni comparación con años anteriores.
