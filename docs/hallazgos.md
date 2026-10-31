# Tres hallazgos

Fuente: INEI, ENAHO 2024 (módulo 34, Sumaria). Cálculo propio con la alternativa B: miembros del hogar,
`factor07 × mieperho`, una fila por hogar. Los intervalos son al 95 % de confianza. Las cifras salen de las tablas de
`datos/procesados/` y de `cifras_clave_2024.json`, generadas por `scripts/analizar_datos.py`.

## 1. La pobreza va de 6 % a 45 % según el departamento

| | Departamentos (tasa de pobreza, %) |
|---|---|
| **Por encima** del promedio nacional (27.6 %), aun considerando el error de muestreo | Cajamarca 45.0, Loreto 43.0, Puno 39.9, Pasco 39.0, Huánuco 39.0, Callao 33.9, Huancavelica 33.4, Ayacucho 32.8, Piura 31.9 |
| **No se distinguen** del promedio nacional | La Libertad 30.2, Lima 27.1, Ucayali 27.1, Tumbes 26.9, Amazonas 25.7, Apurímac 24.0, Tacna 24.0 |
| **Por debajo** del promedio nacional | Áncash 22.8, San Martín 22.0, Cusco 18.5, Junín 18.5, Arequipa 15.8, Lambayeque 14.0, Madre de Dios 11.1, Moquegua 11.0, Ica 6.0 |

- **Los extremos.** La tasa más alta es la de Cajamarca: 45.0 %, con IC de 40.5 a 49.5. Casi la mitad de su población
  es pobre. La más baja es la de Ica: 6.0 %, con IC de 4.2 a 7.8.
- **Cuidado al ordenar.** Los intervalos de los cinco primeros se superponen; por ejemplo, Loreto va de 38.4 a 47.5.
  Por eso no se puede afirmar que Cajamarca sea más pobre que Loreto o Puno. Lo que sí se sostiene es que los cinco
  están muy por encima del promedio.
- **Estimaciones referenciales.** Ica, Madre de Dios y Moquegua tienen un CV mayor a 15 %.

## 2. La tasa y el número de pobres cuentan historias distintas: Lima concentra un tercio de los pobres

| Grupo | Tasa de pobreza | Pobres estimados | Participación en el total de pobres |
|---|---|---|---|
| Lima (departamento) | 27.1 % (≈ promedio nacional) | 3.05 millones | **32.1 %** |
| Cajamarca, Puno, Piura y La Libertad juntos | — | 2.60 millones | 27.3 % |
| Cajamarca (la tasa más alta) | 45.0 % | 0.70 millones | 7.4 % |
| Área urbana | 24.8 % | 6.92 millones | **72.7 %** |

- **Lima tiene más pobres que los cuatro departamentos siguientes juntos**, aunque su tasa está en el promedio
  nacional. El departamento con la tasa más alta, Cajamarca, solo reúne el 7.4 % de los pobres del país.
- **Lo mismo pasa por área.** La tasa urbana es menor que la rural, pero el 72.7 % de los pobres vive en zonas urbanas,
  porque allí está el 80.9 % de la población.

Un mapa de tasas y uno de número de pobres señalan lugares distintos. Los números absolutos son aproximados: suman
1.2 % más que la cifra que difundió el INEI (ver limitaciones).

## 3. En el área rural la pobreza es 14.5 puntos mayor, y la pobreza extrema es cinco veces mayor

**En todo el país:**

| | Urbana | Rural | Diferencia |
|---|---|---|---|
| Pobreza | 24.8 % (IC 23.6–26.0) | 39.3 % (IC 37.6–41.0) | **14.5 puntos** (IC 12.4–16.6); la rural es 1.58 veces la urbana |
| Pobreza extrema | 3.1 % | 15.5 % | Casi 5 veces |

El área rural tiene el 19.1 % de la población, pero el **53.9 % de los pobres extremos**.

**Por departamento.** La brecha rural − urbana es significativa en 15 de los 24 departamentos que tienen ambas áreas en
la muestra (Callao no tiene hogares rurales).

| Departamento | Urbana | Rural | Brecha |
|---|---|---|---|
| Loreto | 35.0 % | 63.4 % | 28.4 puntos |
| Cajamarca | 31.2 % | 55.1 % | 23.9 puntos |
| La Libertad | 26.1 % | 49.9 % | 23.8 puntos |

- **Sin brecha significativa: 8 departamentos.** Entre ellos, Lima (3.1 puntos), Pasco (−1.0) y San Martín (−1.1),
  donde la tasa rural sale apenas menor y Tumbes (−8.2 puntos, con un intervalo que incluye el cero).
- **Ica es el único** donde la tasa rural sale menor y la diferencia es significativa (−3.6 puntos). No se presenta como
  hallazgo: la tasa rural de Ica (2.6 %) se basa en 217 hogares y tiene un CV de 60 %.
