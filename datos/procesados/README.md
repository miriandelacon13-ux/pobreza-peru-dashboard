# Tablas procesadas: pobreza monetaria 2024

Las genera `scripts/analizar_datos.py` desde la Sumaria de la ENAHO 2024 del INEI, con la alternativa B: miembros del
hogar, `factor07 × mieperho`, una fila por hogar. La metodología completa está en
[`docs/metodologia.md`](../../docs/metodologia.md).

| Archivo | Una fila por | Filas |
|---|---|---|
| `pobreza_nacional_area_2024.csv` | Ámbito: Nacional, Urbana, Rural | 3 |
| `pobreza_departamento_2024.csv` | Departamento | 25 |
| `pobreza_departamento_area_2024.csv` | Departamento y área (Callao no tiene área rural en la muestra) | 49 |
| `brecha_urbano_rural_2024.csv` | Perú (`ccdd = 00`) o departamento con ambas áreas, y tipo de pobreza | 75 |
| `cifras_clave_2024.json` | Cifras resumidas para los hallazgos y los KPI del dashboard | — |
| `verificacion.txt` | Resultado de `scripts/verificar_datos.py` | — |

`hogares_2024.parquet` es la base de hogares que sale de `scripts/procesar_datos.py`. No se sube a git: se regenera
con ese script.

## Columnas de las tablas de pobreza

| Columna | Qué es |
|---|---|
| `ambito` / `ccdd`, `departamento` / `area` | Grupo. `ccdd` son los dos primeros dígitos del ubigeo, como texto (01 Amazonas … 25 Ucayali) |
| `n_hogares`, `n_conglomerados` | Hogares y conglomerados de la muestra en el grupo |
| `n_personas_muestra` | Miembros del hogar en la muestra (suma de `mieperho`) |
| `poblacion_estimada` | Σ `factor07 × mieperho`: personas que representa la muestra. Aproximada (ver limitaciones) |
| `pobres_estimados`, `pobres_extremos_estimados`, `pobres_no_extremos_estimados` | Personas estimadas en cada condición. Aproximadas |
| `tasa_pobreza`, `tasa_pobreza_extrema`, `tasa_pobreza_no_extrema` | % de personas: personas pobres / población estimada × 100. Total = extrema + no extrema |
| `ee_*` | Error estándar de la tasa, en puntos porcentuales (linealización; unidad primaria = conglomerado) |
| `ic95_inf_*`, `ic95_sup_*` | Intervalo de confianza al 95 % |
| `cv_*` | Coeficiente de variación de la tasa (%) |
| `precision_pobreza`, `precision_pobreza_extrema`, `precision_pobreza_no_extrema` | `adecuada` si el CV de esa tasa es 15 % o menos; si no, `referencial` |
| `dif_nacional_*`, `ic95_inf_dif_nacional_*`, `ic95_sup_dif_nacional_*` | Solo departamentos: tasa del departamento − tasa del país (puntos), con el IC 95 % de la diferencia (incluye la covarianza) |
| `comparacion_nacional_*` | Solo departamentos: `mayor`, `menor` o `no distinguible` frente al país, según si el IC de la diferencia excluye el 0 |
| `dif_area_nacional_*`, `ic95_*_dif_area_nacional_*`, `comparacion_area_nacional_*` | Solo departamento × área: lo mismo, frente a la misma área en el país (por ejemplo, Cusco rural frente al Perú rural) |
| `participacion_en_pobres_pct` | % del total nacional de pobres que está en el grupo |
| `participacion_en_pobres_del_departamento_pct` | % de los pobres del departamento que está en esa área |

El asterisco `*` es el tipo de pobreza: `pobreza`, `pobreza_extrema` o `pobreza_no_extrema`.

Los números absolutos (`poblacion_estimada` y `pobres_*_estimados`) son **estimaciones propias**: expanden la muestra
con `factor07 × mieperho`. Suman 1.2 % más que las cifras del INEI, que usan la población proyectada al 2024. Ver la
limitación 4 en `docs/metodologia.md`.

## Columnas de `brecha_urbano_rural_2024.csv`

Una fila por ámbito (Perú y cada departamento con ambas áreas) y tipo de pobreza: 25 × 3 = 75 filas.

| Columna | Qué es |
|---|---|
| `tipo` | `pobreza`, `pobreza_extrema` o `pobreza_no_extrema` |
| `tasa_urbana`, `tasa_rural` | Tasa (%) de cada área para ese tipo |
| `brecha_pp` | Rural − urbana, en puntos porcentuales |
| `ee_brecha`, `ic95_inf_brecha`, `ic95_sup_brecha` | Error estándar e IC 95 % de la brecha (incluye la covarianza) |
| `brecha_significativa_95` | `True` si el IC 95 % no incluye el cero |
| `razon_rural_urbana` | Tasa rural / tasa urbana |
