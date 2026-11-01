# Tres hallazgos

Fuente: INEI, ENAHO 2024 (módulo 34, Sumaria). Cálculo propio con la alternativa B: miembros del hogar,
`factor07 × mieperho`, una fila por hogar. Las cifras salen de `datos/procesados/` y de `cifras_clave_2024.json`,
generadas por `scripts/analizar_datos.py`.

**Cómo leer las comparaciones.** Una diferencia es «clara» (estadísticamente significativa al 95 %) cuando el intervalo
de confianza **de la diferencia** no incluye el cero. Ese intervalo sale del error estándar de la diferencia, calculado
por linealización con el conglomerado como unidad de muestreo, e incluye la covarianza (un departamento forma parte del
total nacional). No basta con mirar si los intervalos de dos tasas se superponen. Ver
[metodologia.md](metodologia.md#comparaciones-y-significancia).

## 1. La pobreza va de 6 % a 45 % según el departamento

| | Departamentos (tasa de pobreza, %) |
|---|---|
| **Mayor** que la del país (27.6 %), diferencia clara | Cajamarca 45.0, Loreto 43.0, Puno 39.9, Pasco 39.0, Huánuco 39.0, Callao 33.9, Huancavelica 33.4, Ayacucho 32.8, Piura 31.9 |
| **No se distingue** de la del país | La Libertad 30.2, Lima 27.1, Ucayali 27.1, Tumbes 26.9, Amazonas 25.7, Apurímac 24.0, Tacna 24.0 |
| **Menor** que la del país, diferencia clara | Áncash 22.8, San Martín 22.0, Cusco 18.5, Junín 18.5, Arequipa 15.8, Lambayeque 14.0, Madre de Dios 11.1, Moquegua 11.0, Ica 6.0 |

- **La más alta: Cajamarca.** Su tasa es 45.0 % (IC 95 % de 40.5 a 49.5): casi la mitad de su población es pobre.
- **No hay un orden exacto entre los cinco primeros.** La diferencia de Cajamarca con los cuatro siguientes no es
  clara:

  | Cajamarca frente a | Diferencia | IC 95 % |
  |---|---|---|
  | Loreto | +2.0 puntos | −4.4 a +8.5 |
  | Puno | +5.1 puntos | −1.4 a +11.6 |
  | Pasco | +6.0 puntos | −0.6 a +12.7 |
  | Huánuco | +6.0 puntos | −0.8 a +12.9 |

  Lo que sí se sostiene es que los cinco están por encima del país.
- **La más baja: Ica**, con 6.0 % (IC de 4.2 a 7.8). Ica, Madre de Dios y Moquegua son estimaciones referenciales,
  porque su CV supera el 15 %.

## 2. La tasa y el número de pobres señalan lugares distintos: Lima concentra un tercio de los pobres

**La tasa de Lima no se distingue de la del país.** Lima (el departamento completo) tiene una tasa de 27.1 %, 0.5 puntos
por debajo de la nacional (27.6 %). Esa diferencia no es clara: su IC 95 % va de −2.2 a +1.2 puntos.

**Pero concentra a muchos más pobres.** Según la estimación propia, explicada abajo:

| Grupo | Tasa de pobreza | Pobres (estimación propia) | Participación en el total de pobres |
|---|---|---|---|
| Lima (departamento) | 27.1 % | 3.05 millones | **32.1 %** |
| Cajamarca, Puno, Piura y La Libertad juntos | — | 2.60 millones | 27.3 % |
| Cajamarca (la tasa más alta) | 45.0 % | 0.70 millones | 7.4 % |
| Área urbana | 24.8 % | 6.92 millones | **72.7 %** |

- **Lima tiene más pobres que los cuatro departamentos siguientes juntos.** En cambio, Cajamarca, el departamento con
  la tasa más alta, reúne el 7.4 % de los pobres del país.
- **Por área pasa lo mismo.** La tasa urbana es menor que la rural, pero el 72.7 % de los pobres vive en zonas urbanas,
  porque allí está el 80.9 % de la población.

**Sobre los números absolutos.** Son estimaciones propias: expanden la muestra con `factor07 × mieperho`, que suma
34.48 millones de personas. Dan 9.51 millones de pobres, 1.2 % más que los 9.395 millones que difundió el INEI. La cifra
del INEI es igual a su tasa publicada (27.6 %) por la población proyectada al 2024, que es de 34,038,457 personas (INEI,
*Una mirada al Perú en cifras* Nº 7, julio 2024). Las tasas coinciden; la diferencia está solo en la población total.
Las participaciones (32.1 %, 72.7 %) son cocientes dentro de la misma expansión: no cambiarían si toda la expansión se
ajustara proporcionalmente al total proyectado.

## 3. En el área rural la pobreza es 14.5 puntos mayor, y la pobreza extrema, casi cinco veces mayor

**En todo el país:**

| | Urbana | Rural | Brecha rural − urbana |
|---|---|---|---|
| Pobreza | 24.8 % (IC 23.6 a 26.0) | 39.3 % (IC 37.6 a 41.0) | **14.5 puntos** (IC 12.4 a 16.6); la tasa rural es 1.58 veces la urbana |
| Pobreza extrema | 3.1 % | 15.5 % | 12.4 puntos (IC 11.0 a 13.8); la tasa rural es 4.9 veces la urbana |

El área rural tiene el 19.1 % de la población, pero el **53.9 % de los pobres extremos**.

**Por departamento.** La brecha de pobreza total es clara en 15 de los 24 departamentos que tienen ambas áreas en la
muestra (Callao no tiene hogares rurales). Las mayores son:

| Departamento | Urbana | Rural | Brecha |
|---|---|---|---|
| Loreto | 35.0 % | 63.4 % | 28.4 puntos |
| Cajamarca | 31.2 % | 55.1 % | 23.9 puntos |
| La Libertad | 26.1 % | 49.9 % | 23.8 puntos |

- **Sin brecha clara: 8 departamentos.** Huancavelica, Lima, Madre de Dios, Pasco, San Martín, Tacna, Tumbes y Ucayali.
- **Ica es el único** donde la tasa rural sale claramente menor (−3.6 puntos). No se presenta como hallazgo: la tasa
  rural de Ica (2.6 %) se basa en 217 hogares y tiene un CV de 60 %.
