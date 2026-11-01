"use strict";
/*
 * Dashboard de pobreza monetaria 2024. Todas las cifras vienen de data/pobreza_2024.json, que exporta
 * scripts/exportar_web.py desde las tablas verificadas. Aquí no se recalcula ni se promedia ninguna tasa:
 * cada filtro solo elige qué estimación mostrar. Una celda sin hogares en la muestra (Callao rural) es null
 * y se muestra como «sin dato», nunca como cero.
 */

const TIPOS = { total: "pobreza total", extrema: "pobreza extrema", no_extrema: "pobreza no extrema" };
const AREAS = { total: "urbana y rural", urbana: "área urbana", rural: "área rural" };
// El país en cada área, con la preposición que pide cada frase («con el», «frente al», «la tasa del»)
const PERU_AREA = { total: "todo el Perú", urbana: "el Perú urbano", rural: "el Perú rural" };
const FRENTE_AL_PERU = { total: "frente a todo el Perú", urbana: "frente al Perú urbano", rural: "frente al Perú rural" };
const DEL_PERU = { total: "de todo el Perú", urbana: "del Perú urbano", rural: "del Perú rural" };
const PERU_CORTO = { total: "Perú", urbana: "Perú urbano", rural: "Perú rural" };
const INICIAL = { dep: "00", area: "total", tipo: "total", medida: "tasa" };
const CONFIG = { responsive: true, displayModeBar: false };
const FUENTE = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";

let estado = { ...INICIAL };
let DATOS = null;
let GEO = null;
const DEP = {};
const MAX_TASA = {};
const eventosConectados = new Set();

// ---------- formato ----------
const f1 = (x) => x.toFixed(1);
const signo = (x) => (x > 0.05 ? "+" : x < -0.05 ? "−" : "") + Math.abs(x).toFixed(1);
const miles = (x) => Math.round(x).toLocaleString("en-US");
function personasTexto(x) {
  if (x >= 1e6) return `${(x / 1e6).toFixed(2)} millones`;
  if (x >= 1e3) return `${Math.round(x / 1e3).toLocaleString("en-US")} mil`;
  return miles(x);
}
// Una tasa de 0 en la muestra (ningún hogar en esa condición) no tiene CV ni intervalo estimables
const sinVariacion = (e) => e.cv == null;
const icTexto = (e) => (sinVariacion(e) ? "no estimable (ningún hogar de la muestra en esta condición)" : `${f1(e.ic[0])}–${f1(e.ic[1])} %`);
const cvTexto = (e) => (sinVariacion(e) ? "no calculable" : `${f1(e.cv)} %`);
const avisoPrecision = (e) => (e.precision !== "referencial" ? null
  : sinVariacion(e) ? "Referencial: ningún hogar de la muestra en esta condición" : `Referencial: CV ${f1(e.cv)} %`);
const COMPARACION = {
  mayor: "claramente mayor",
  menor: "claramente menor",
  "no distinguible": "no se distingue (el intervalo de la diferencia incluye el 0)",
};

// ---------- acceso a datos (sin cálculos de tasas) ----------
const lugar = (dep) => (dep === "00" ? "Perú" : DEP[dep].nombre);
const ambito = (dep, area) => (area === "total" ? lugar(dep) : `${lugar(dep)}, ${AREAS[area]}`);
const celda = (dep, area) => (dep === "00" ? DATOS.nacional[area] : DEP[dep][area]);
const estimacion = (dep, area, tipo) => {
  const c = celda(dep, area);
  return c ? c.tipos[tipo] : null;
};
const brechaDe = (dep) => (dep === "00" ? DATOS.nacional.brecha : DEP[dep].brecha);

// ---------- colores desde CSS (modo claro u oscuro) ----------
function colores() {
  const s = getComputedStyle(document.documentElement);
  const v = (n) => s.getPropertyValue(n).trim();
  return {
    superficie: v("--superficie"), tinta: v("--tinta"), tinta2: v("--tinta-2"), rejilla: v("--rejilla"), eje: v("--eje"),
    urbana: v("--serie-urbana"), rural: v("--serie-rural"), barra: v("--barra"), resaltada: v("--barra-resaltada"),
    tenue: v("--barra-tenue"), extrema: v("--extrema"), noExtrema: v("--no-extrema"), noPobre: v("--no-pobre"),
    sinDato: v("--sin-dato"), rampa: v("--rampa").split(",").map((x) => x.trim()),
  };
}
function tintaSobre(hex) {
  const n = parseInt(hex.slice(1), 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((x) => {
    const c = x / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.35 ? "#0b0b0b" : "#ffffff";
}
function base(c, extra) {
  return {
    paper_bgcolor: c.superficie, plot_bgcolor: c.superficie, showlegend: false,
    font: { family: FUENTE, size: 13, color: c.tinta },
    margin: { l: 8, r: 16, t: 8, b: 36 },
    hoverlabel: { bgcolor: c.superficie, bordercolor: c.eje, font: { family: FUENTE, color: c.tinta, size: 13 } },
    ...extra,
  };
}
const ejeValor = (c, extra) => ({
  gridcolor: c.rejilla, linecolor: c.eje, zeroline: false, tickfont: { color: c.tinta2 }, fixedrange: true, ...extra,
});

// ---------- estado y URL ----------
function leerURL() {
  const p = new URLSearchParams(location.search);
  const dep = p.get("dep");
  if (dep && (dep === "00" || DEP[dep])) estado.dep = dep;
  if (AREAS[p.get("area")]) estado.area = p.get("area");
  if (TIPOS[p.get("tipo")]) estado.tipo = p.get("tipo");
  if (["tasa", "personas"].includes(p.get("medida"))) estado.medida = p.get("medida");
}
function escribirURL() {
  const p = new URLSearchParams();
  for (const k of Object.keys(INICIAL)) if (estado[k] !== INICIAL[k]) p.set(k, estado[k]);
  const q = p.toString();
  history.replaceState(null, "", q ? `?${q}` : location.pathname);
}
function sincronizarControles() {
  document.getElementById("f-dep").value = estado.dep;
  for (const nombre of ["area", "tipo", "medida"]) {
    document.querySelector(`input[name="${nombre}"][value="${estado[nombre]}"]`).checked = true;
  }
}
function cambiar(nuevo) {
  estado = { ...estado, ...nuevo };
  sincronizarControles();
  escribirURL();
  dibujar();
}

// ---------- KPIs ----------
function kpi(id, etiqueta, valor, detalle, { sinDato = false, aviso = null } = {}) {
  const el = document.getElementById(id);
  el.querySelector(".kpi-etiqueta").textContent = etiqueta;
  const v = el.querySelector(".kpi-valor");
  v.textContent = valor;
  v.classList.toggle("sin-dato", sinDato);
  const d = el.querySelector(".kpi-detalle");
  d.textContent = detalle;
  if (aviso) {
    const s = document.createElement("span");
    s.className = "etiqueta-aviso";
    s.textContent = aviso;
    d.append(document.createElement("br"), s);
  }
  el.dataset.valor = valor;
}

function dibujarKPIs() {
  const { dep, area, tipo } = estado;
  const c = celda(dep, area);
  const e = c ? c.tipos[tipo] : null;
  const sinHogares = `La muestra no tiene hogares del ${AREAS[area]} en ${lugar(dep)}.`;

  // 1. Tasa
  if (e) {
    kpi("kpi-tasa", `Tasa de ${TIPOS[tipo]} · ${ambito(dep, area)}`, `${f1(e.tasa)} %`,
      `IC 95 %: ${icTexto(e)} · ${miles(c.n_hogares)} hogares en la muestra`, { aviso: avisoPrecision(e) });
  } else {
    kpi("kpi-tasa", `Tasa de ${TIPOS[tipo]} · ${ambito(dep, area)}`, "Sin dato", sinHogares, { sinDato: true });
  }

  // 2. Personas (estimación propia)
  const etiquetaP = `Personas en ${TIPOS[tipo]} · ${ambito(dep, area)} (estimación propia)`;
  if (e) {
    const pais = DATOS.nacional.total.tipos[tipo].personas;
    const detalle = dep === "00" && area === "total"
      ? `De una población estimada de ${personasTexto(c.poblacion)}. Cifra aproximada: el INEI difunde otra base de población (ver Limitaciones).`
      : `${f1((100 * e.personas) / pais)} % de las personas en ${TIPOS[tipo]} del país · población estimada: ${personasTexto(c.poblacion)}`;
    kpi("kpi-personas", etiquetaP, personasTexto(e.personas), detalle);
  } else {
    kpi("kpi-personas", etiquetaP, "Sin dato", sinHogares, { sinDato: true });
  }

  // 3. Brecha rural − urbana (no depende del filtro de área)
  const b = brechaDe(dep);
  const etiquetaB = `Brecha rural − urbana · ${TIPOS[tipo]} · ${lugar(dep)}`;
  if (b) {
    const t = b[tipo];
    const lectura = t.clara ? "diferencia clara" : "diferencia no clara (el intervalo incluye el 0)";
    kpi("kpi-brecha", etiquetaB, `${signo(t.brecha)} puntos`,
      `Rural ${f1(t.rural)} % frente a urbana ${f1(t.urbana)} % · IC 95 %: ${signo(t.ic[0])} a ${signo(t.ic[1])} · ${lectura}. Compara ambas áreas, por eso no cambia con el filtro de área.`);
  } else {
    kpi("kpi-brecha", etiquetaB, "No disponible", `${lugar(dep)} no tiene hogares rurales en la muestra.`, { sinDato: true });
  }

  // 4. Comparación con el país, o el departamento con la mayor tasa
  if (dep !== "00") {
    const ref = DATOS.nacional[area].tipos[tipo];
    const etiquetaC = `${ambito(dep, area)} ${FRENTE_AL_PERU[area]}`;
    if (e) {
      kpi("kpi-comparacion", etiquetaC, `${signo(e.dif)} puntos`,
        `${f1(e.tasa)} % frente a ${f1(ref.tasa)} % · IC 95 % de la diferencia: ${signo(e.dif_ic[0])} a ${signo(e.dif_ic[1])} · ${COMPARACION[e.comparacion]}`);
    } else {
      kpi("kpi-comparacion", etiquetaC, "Sin dato", sinHogares, { sinDato: true });
    }
  } else {
    const candidatos = DATOS.departamentos.map((d) => [d, estimacion(d.ccdd, area, tipo)]).filter(([, x]) => x);
    const [d, x] = candidatos.reduce((m, f) => (f[1].tasa > m[1].tasa ? f : m));
    let detalle = `IC 95 %: ${f1(x.ic[0])}–${f1(x.ic[1])} %. `;
    if (area === "total" && tipo === "total") {
      const otros = DATOS.meta.mayor_tasa_vs_siguientes;
      const nombres = otros.map((o) => o.frente_a);
      const todos = otros.every((o) => o.comparacion === "no distinguible");
      detalle += todos
        ? `No se distingue de ${nombres.slice(0, -1).join(", ")} ni ${nombres.at(-1)}: el intervalo de cada diferencia incluye el 0.`
        : "Ver la comparación con los departamentos siguientes en la metodología.";
    } else {
      detalle += "Para esta combinación no se probó si se distingue de los siguientes.";
    }
    kpi("kpi-comparacion", `Mayor tasa de ${TIPOS[tipo]} por departamento${area === "total" ? "" : ` · ${AREAS[area]}`}`,
      `${d.nombre} ${f1(x.tasa)} %`, detalle,
      { aviso: avisoPrecision(x) });
  }
}

// ---------- gráficos ----------
function textoTitulos() {
  const { area, tipo, medida, dep } = estado;
  const areaTxt = area === "total" ? "" : `, ${AREAS[area]}`;
  const set = (id, t) => { document.getElementById(id).textContent = t; };
  set("t-mapa", medida === "tasa"
    ? `Tasa de ${TIPOS[tipo]} por departamento${areaTxt}, 2024`
    : `Personas en ${TIPOS[tipo]} por departamento${areaTxt}, 2024 (estimación propia)`);
  set("s-mapa", "Haz clic en un departamento para seleccionarlo. Unión por código de departamento (ubigeo). Escala de 0 al máximo de cada tipo de pobreza, igual para las tres opciones de área.");
  set("t-ranking", `Ranking: tasa de ${TIPOS[tipo]}${areaTxt} con su intervalo de confianza al 95 %`);
  set("s-ranking", `% de personas. La línea vertical es la tasa ${DEL_PERU[area]}.`);
  set("t-brecha", `Brecha urbano-rural: ${TIPOS[tipo]} por departamento`);
  set("s-brecha", "% de personas en cada área. Ordenado de mayor a menor brecha. No depende del filtro de área.");
  set("t-dispersion", `Tasa frente a número de personas en ${TIPOS[tipo]}${areaTxt}`);
  set("t-composicion", `Composición de la población · ${lugar(dep)}`);
  set("s-composicion", "% de personas en pobreza extrema, no extrema y no pobres, por área. Resalta el tipo de pobreza elegido.");
  const partes = [TIPOS[tipo], area === "total" ? "área urbana y rural" : AREAS[area], dep === "00" ? "todo el Perú" : `${lugar(dep)} resaltado`];
  set("resumen-seleccion", `Mostrando: ${partes.join(" · ")}.`);
}

function filasDepartamentos() {
  const { area, tipo } = estado;
  return DATOS.departamentos.map((d) => ({ d, e: estimacion(d.ccdd, area, tipo) }));
}

function dibujarMapa(c) {
  const { dep, area, tipo, medida } = estado;
  const filas = filasDepartamentos();
  const con = filas.filter((f) => f.e);
  const sin = filas.filter((f) => !f.e);
  const valor = (f) => (medida === "tasa" ? f.e.tasa : f.e.personas / 1e6);
  const z = con.map(valor);
  const zmax = medida === "tasa" ? MAX_TASA[tipo] : Math.max(...z);
  const escala = c.rampa.map((col, i) => [i / (c.rampa.length - 1), col]);
  const trazas = [{
    type: "choropleth", geojson: GEO, featureidkey: "properties.ccdd", name: "datos",
    locations: con.map((f) => f.d.ccdd), z, zmin: 0, zmax, colorscale: escala,
    marker: { line: { color: c.superficie, width: 1 } },
    colorbar: {
      // Barra de color horizontal, debajo del mapa: así el mapa usa todo el ancho de la tarjeta
      title: { text: medida === "tasa" ? "% de personas" : "millones de personas", font: { color: c.tinta2, size: 12 }, side: "top" },
      outlinewidth: 0, tickfont: { color: c.tinta2 }, ticksuffix: medida === "tasa" ? " %" : "",
      orientation: "h", x: 0.5, xanchor: "center", y: 0.01, yanchor: "bottom", len: 0.8, thickness: 10,
    },
    customdata: con.map((f) => [f.d.nombre, f.e.tasa, icTexto(f.e), "", f.e.personas,
      avisoPrecision(f.e) ? `<br>${avisoPrecision(f.e)}` : ""]),
    hovertemplate: `<b>%{customdata[0]}</b><br>Tasa de ${TIPOS[tipo]}: %{customdata[1]:.1f} % (IC 95 %: %{customdata[2]})` +
      "<br>Personas: %{customdata[4]:,.0f} (estimación propia)%{customdata[5]}<extra></extra>",
  }];
  if (sin.length) {
    trazas.push({
      type: "choropleth", geojson: GEO, featureidkey: "properties.ccdd", name: "sin dato",
      locations: sin.map((f) => f.d.ccdd), z: sin.map(() => 1), zmin: 0, zmax: 1,
      colorscale: [[0, c.sinDato], [1, c.sinDato]], showscale: false, marker: { line: { color: c.superficie, width: 1 } },
      customdata: sin.map((f) => [f.d.nombre]),
      hovertemplate: `<b>%{customdata[0]}</b><br>Sin dato: no hay hogares del ${AREAS[area]} en la muestra<extra></extra>`,
    });
  }
  if (dep !== "00") {
    trazas.push({
      type: "choropleth", geojson: GEO, featureidkey: "properties.ccdd", name: "selección",
      locations: [dep], z: [1], colorscale: [[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], showscale: false,
      marker: { line: { color: c.tinta, width: 3 } }, hoverinfo: "skip",
    });
  }
  const layout = base(c, {
    margin: { l: 0, r: 0, t: 0, b: 0 }, dragmode: false,
    geo: { fitbounds: "locations", visible: false, projection: { type: "mercator" }, bgcolor: c.superficie, domain: { x: [0, 1], y: [0.14, 1] } },
  });
  const promesa = Plotly.react("g-mapa", trazas, layout, CONFIG);
  const nota = [];
  if (sin.length) nota.push(`Gris: sin dato (${sin.map((f) => f.d.nombre).join(", ")} no tiene hogares del ${AREAS[area]} en la muestra); no es cero.`);
  if (medida === "personas") nota.push("Personas: estimación propia; el INEI usa otra base de población (ver Limitaciones).");
  nota.push("Callao es muy pequeño en el mapa: selecciónalo en el filtro de departamento.");
  document.getElementById("n-mapa").textContent = nota.join(" ");
  return promesa;
}

function dibujarRanking(c) {
  const { dep, area, tipo } = estado;
  const filas = filasDepartamentos().filter((f) => f.e).sort((a, b) => a.e.tasa - b.e.tasa);
  const ref = DATOS.nacional[area].tipos[tipo].tasa;
  const etiquetas = filas.map((f) => (f.e.precision === "referencial" ? `${f.d.nombre} *` : f.d.nombre));
  const color = filas.map((f) => (dep === "00" ? c.barra : f.d.ccdd === dep ? c.resaltada : c.tenue));
  const xmax = Math.max(...filas.map((f) => f.e.ic[1]), ref) * 1.06;
  const traza = {
    type: "bar", orientation: "h", y: etiquetas, x: filas.map((f) => f.e.tasa), marker: { color },
    error_x: {
      type: "data", symmetric: false, array: filas.map((f) => f.e.ic[1] - f.e.tasa),
      arrayminus: filas.map((f) => f.e.tasa - f.e.ic[0]), color: c.tinta2, thickness: 1, width: 3,
    },
    customdata: filas.map((f) => [f.d.ccdd, f.d.nombre, icTexto(f.e), "", cvTexto(f.e), f.e.personas]),
    hovertemplate: "<b>%{customdata[1]}</b><br>%{x:.1f} % (IC 95 %: %{customdata[2]}; CV %{customdata[4]})" +
      "<br>Personas: %{customdata[5]:,.0f} (estimación propia)<extra></extra>",
  };
  const layout = base(c, {
    height: filas.length * 24 + 56, bargap: 0.3, barcornerradius: 4,
    margin: { l: 8, r: 20, t: 22, b: 30 },
    xaxis: ejeValor(c, { range: [0, xmax], ticksuffix: " %" }),
    yaxis: { automargin: true, tickfont: { size: 12, color: c.tinta }, fixedrange: true, linecolor: c.eje },
    shapes: [{ type: "line", x0: ref, x1: ref, yref: "paper", y0: 0, y1: 1, line: { color: c.tinta2, width: 1 } }],
    annotations: [{
      x: ref, yref: "paper", y: 1, yanchor: "bottom", text: `${PERU_CORTO[area]}: ${f1(ref)} %`,
      showarrow: false, font: { size: 12, color: c.tinta2 },
    }],
  });
  const promesa = Plotly.react("g-ranking", [traza], layout, CONFIG);
  const nota = ["* Estimación referencial: coeficiente de variación mayor a 15 %. Las líneas finas son el intervalo de confianza al 95 %."];
  const faltan = filasDepartamentos().filter((f) => !f.e).map((f) => f.d.nombre);
  if (faltan.length) nota.push(`No aparece ${faltan.join(", ")}: sin hogares del ${AREAS[area]} en la muestra.`);
  document.getElementById("n-ranking").textContent = nota.join(" ");
  return promesa;
}

function dibujarBrecha(c) {
  const { dep, tipo } = estado;
  const filas = DATOS.departamentos.filter((d) => d.brecha).map((d) => ({ ccdd: d.ccdd, nombre: d.nombre, t: d.brecha[tipo] }));
  filas.sort((a, b) => a.t.brecha - b.t.brecha);
  filas.push({ ccdd: "00", nombre: "Perú", t: DATOS.nacional.brecha[tipo] });
  const etiqueta = (f) => (f.ccdd === dep || (f.ccdd === "00" && dep === "00") ? `<b>${f.nombre}</b>` : f.nombre);
  const y = filas.map((f) => f.nombre);
  const conector = { x: [], y: [] };
  filas.forEach((f) => { conector.x.push(f.t.urbana, f.t.rural, null); conector.y.push(f.nombre, f.nombre, null); });
  const simbolo = (f) => (f.t.clara ? "circle" : "circle-open");
  const punto = (area, color) => ({
    type: "scatter", mode: "markers", name: area === "urbana" ? "Urbana" : "Rural", y, showlegend: false,
    x: filas.map((f) => f.t[area]),
    marker: { size: 10, color, symbol: filas.map(simbolo), line: { color: filas.map((f) => (f.t.clara ? c.superficie : color)), width: 2 } },
    customdata: filas.map((f) => [f.nombre, f.t.urbana, f.t.rural, f.t.brecha, f.t.ic[0], f.t.ic[1], f.t.clara ? "clara" : "no clara"]),
    hovertemplate: "<b>%{customdata[0]}</b><br>Urbana %{customdata[1]:.1f} % · Rural %{customdata[2]:.1f} %" +
      "<br>Brecha %{customdata[3]:+.1f} puntos (IC 95 %: %{customdata[4]:+.1f} a %{customdata[5]:+.1f}), %{customdata[6]}<extra></extra>",
  });
  const trazas = [
    { type: "scatter", mode: "lines", x: conector.x, y: conector.y, line: { color: c.eje, width: 2 }, hoverinfo: "skip", showlegend: false },
    punto("urbana", c.urbana), punto("rural", c.rural),
    // Solo para la leyenda: marcador relleno, sin datos (la leyenda de Plotly copia el estilo del primer punto)
    ...[["Urbana", c.urbana], ["Rural", c.rural]].map(([nombre, color]) => ({
      type: "scatter", mode: "markers", name: nombre, x: [null], y: [null], showlegend: true, hoverinfo: "skip",
      marker: { size: 10, color, symbol: "circle", line: { color: c.superficie, width: 2 } },
    })),
  ];
  const callao = DEP["07"];
  const xmax = Math.max(...filas.map((f) => Math.max(f.t.urbana, f.t.rural))) * 1.08;
  const layout = base(c, {
    height: filas.length * 22 + 70, showlegend: true,
    legend: { orientation: "h", x: 0, y: 1.02, yanchor: "bottom", font: { color: c.tinta2 } },
    margin: { l: 8, r: 16, t: 30, b: 30 },
    xaxis: ejeValor(c, { range: [0, xmax], ticksuffix: " %" }),
    yaxis: { automargin: true, tickvals: y, ticktext: filas.map(etiqueta), tickfont: { size: 12, color: c.tinta }, fixedrange: true, linecolor: c.eje },
  });
  const promesa = Plotly.react("g-brecha", trazas, layout, CONFIG);
  document.getElementById("n-brecha").textContent =
    `Punto relleno: brecha clara (su IC 95 % no incluye el 0); punto hueco: no clara. Callao no aparece porque no tiene hogares rurales en la muestra (tasa urbana de ${TIPOS[tipo]}: ${f1(callao.urbana.tipos[tipo].tasa)} %).`;
  return promesa;
}

function dibujarDispersion(c) {
  const { dep, area, tipo } = estado;
  const filas = filasDepartamentos().filter((f) => f.e);
  const ref = DATOS.nacional[area].tipos[tipo].tasa;
  const maxPersonas = Math.max(...filas.map((f) => f.e.personas));
  const enMillones = maxPersonas >= 5e5;
  const escala = enMillones ? 1e6 : 1e3;
  const masPersonas = filas.reduce((m, f) => (f.e.personas > m.e.personas ? f : m));
  const masTasa = filas.reduce((m, f) => (f.e.tasa > m.e.tasa ? f : m));
  const conEtiqueta = new Set([masPersonas.d.ccdd, masTasa.d.ccdd, dep]);
  const traza = {
    type: "scatter", mode: "markers+text", x: filas.map((f) => f.e.tasa), y: filas.map((f) => f.e.personas / escala),
    text: filas.map((f) => (conEtiqueta.has(f.d.ccdd) ? f.d.nombre : "")),
    textposition: filas.map((f) => (f.e.tasa < ref ? "top left" : "top right")),
    textfont: { size: 12, color: c.tinta },
    marker: {
      size: filas.map((f) => (f.d.ccdd === dep ? 14 : 10)),
      color: filas.map((f) => (dep === "00" ? c.barra : f.d.ccdd === dep ? c.resaltada : c.tenue)),
      line: { color: c.superficie, width: 2 },
    },
    customdata: filas.map((f) => [f.d.nombre, f.e.personas, icTexto(f.e)]),
    hovertemplate: "<b>%{customdata[0]}</b><br>Tasa %{x:.1f} % (IC 95 %: %{customdata[2]})" +
      "<br>Personas: %{customdata[1]:,.0f} (estimación propia)<extra></extra>",
    cliponaxis: false,
  };
  const layout = base(c, {
    height: 420, hovermode: "closest", hoverdistance: 30, margin: { l: 8, r: 20, t: 24, b: 44 },
    xaxis: ejeValor(c, { ticksuffix: " %", title: { text: `Tasa de ${TIPOS[tipo]}`, font: { size: 12, color: c.tinta2 } },
                         range: [0, Math.max(...filas.map((f) => f.e.tasa)) * 1.22] }),
    yaxis: ejeValor(c, { automargin: true, rangemode: "tozero", title: { text: `${enMillones ? "Millones" : "Miles"} de personas (estimación propia)`, font: { size: 12, color: c.tinta2 } } }),
    shapes: [{ type: "line", x0: ref, x1: ref, yref: "paper", y0: 0, y1: 1, line: { color: c.tinta2, width: 1 } }],
  });
  const promesa = Plotly.react("g-dispersion", [traza], layout, CONFIG);
  document.getElementById("s-dispersion").textContent =
    `Cada punto es un departamento; la línea vertical es la tasa ${DEL_PERU[area]} (${f1(ref)} %). Un departamento grande puede tener muchos pobres con una tasa moderada.`;
  const faltan = filasDepartamentos().filter((f) => !f.e).map((f) => f.d.nombre);
  document.getElementById("n-dispersion").textContent =
    `Con etiqueta: el departamento con más personas en ${TIPOS[tipo]}, el de mayor tasa y el seleccionado.` +
    (faltan.length ? ` No aparece ${faltan.join(", ")}: sin hogares del ${AREAS[area]} en la muestra.` : "");
  return promesa;
}

function dibujarComposicion(c) {
  const { dep, tipo } = estado;
  const areas = [["total", "Urbana y rural"], ["urbana", "Urbana"], ["rural", "Rural"]];
  const etiquetas = areas.map(([a, n]) => (celda(dep, a) ? n : `${n} (sin dato)`));
  const valores = (fn) => areas.map(([a]) => { const x = celda(dep, a); return x ? fn(x) : null; });
  const partes = [
    { nombre: "Pobreza extrema", color: c.extrema, x: valores((x) => x.tipos.extrema.tasa), activa: tipo !== "no_extrema" },
    { nombre: "Pobreza no extrema", color: c.noExtrema, x: valores((x) => x.tipos.no_extrema.tasa), activa: tipo !== "extrema" },
    { nombre: "No pobre", color: c.noPobre, x: valores((x) => 100 - x.tipos.total.tasa), activa: true },
  ];
  const trazas = partes.map((p) => ({
    type: "bar", orientation: "h", name: p.nombre, y: etiquetas, x: p.x,
    marker: { color: p.color, opacity: p.activa ? 1 : 0.35, line: { color: c.superficie, width: 2 } },
    text: p.x.map((v) => (v != null && v >= 8 ? `${f1(v)} %` : "")), textposition: "inside", insidetextanchor: "start",
    textfont: { color: tintaSobre(p.color), size: 12 },
    hovertemplate: `%{y}<br>${p.nombre}: %{x:.1f} %<extra></extra>`,
  }));
  const layout = base(c, {
    barmode: "stack", height: 250, showlegend: true, bargap: 0.35,
    legend: { orientation: "h", x: 0, y: 1.04, yanchor: "bottom", traceorder: "normal", font: { color: c.tinta2 } },
    margin: { l: 8, r: 16, t: 30, b: 30 },
    xaxis: ejeValor(c, { range: [0, 100], ticksuffix: " %" }),
    yaxis: { automargin: true, autorange: "reversed", tickfont: { size: 12, color: c.tinta }, fixedrange: true },
  });
  const promesa = Plotly.react("g-composicion", trazas, layout, CONFIG);
  const sin = areas.filter(([a]) => !celda(dep, a)).map(([, n]) => n.toLowerCase());
  document.getElementById("n-composicion").textContent =
    "Extrema + no extrema = pobreza total. Los valores menores a 8 % se leen al pasar el cursor o en la tabla." +
    (sin.length ? ` Área ${sin.join(", ")}: sin hogares en la muestra.` : "");
  return promesa;
}

function dibujarTabla() {
  const { dep, area, tipo } = estado;
  const tabla = document.getElementById("tabla");
  const cab = ["Departamento", `Tasa de ${TIPOS[tipo]} (%)`, "IC 95 %", "CV (%)", "Personas (estimación propia)", `Diferencia con ${PERU_AREA[area]} (puntos)`, "Lectura"];
  const trCab = document.createElement("tr");
  cab.forEach((t) => { const th = document.createElement("th"); th.textContent = t; trCab.append(th); });
  tabla.tHead.replaceChildren(trCab);
  const filas = [{ ccdd: "00", nombre: `Perú (${AREAS[area]})`, e: DATOS.nacional[area].tipos[tipo] }]
    .concat(filasDepartamentos().map((f) => ({ ccdd: f.d.ccdd, nombre: f.d.nombre, e: f.e }))
      .sort((a, b) => (b.e ? b.e.tasa : -1) - (a.e ? a.e.tasa : -1)));
  const cuerpo = filas.map((f) => {
    const tr = document.createElement("tr");
    if (f.ccdd === dep) tr.className = "resaltada";
    const e = f.e;
    const celdas = e
      ? [f.nombre, f1(e.tasa), sinVariacion(e) ? "no estimable" : `${f1(e.ic[0])}–${f1(e.ic[1])}`,
        `${sinVariacion(e) ? "—" : f1(e.cv)}${e.precision === "referencial" ? " *" : ""}`, miles(e.personas),
        f.ccdd === "00" ? "—" : signo(e.dif), f.ccdd === "00" ? "—" : e.comparacion]
      : [f.nombre, "Sin dato", "—", "—", "—", "—", "sin hogares en la muestra"];
    celdas.forEach((t) => { const td = document.createElement("td"); td.textContent = t; tr.append(td); });
    return tr;
  });
  tabla.tBodies[0].replaceChildren(...cuerpo);
  document.getElementById("s-tabla").textContent =
    `${TIPOS[tipo][0].toUpperCase()}${TIPOS[tipo].slice(1)}, ${AREAS[area]}. * CV mayor a 15 %: estimación referencial. «Lectura» compara cada departamento con ${PERU_AREA[area]}.`;
}

function conectarClics() {
  for (const id of ["g-mapa", "g-ranking"]) {
    const el = document.getElementById(id);
    if (eventosConectados.has(id) || !el.on) continue;
    el.on("plotly_click", (ev) => {
      const p = ev.points && ev.points[0];
      if (!p) return;
      const ccdd = id === "g-mapa" ? p.location : p.customdata && p.customdata[0];
      if (ccdd && DEP[ccdd]) cambiar({ dep: ccdd === estado.dep ? "00" : ccdd });
    });
    eventosConectados.add(id);
  }
}

// Un solo redibujo a la vez: Plotly.react es asíncrono y dos redibujos superpuestos del mismo gráfico fallan.
// Si los filtros cambian mientras se dibuja, al terminar se dibuja el último estado.
let enCurso = null;
let pendiente = false;
function dibujar() {
  pendiente = true;
  if (!enCurso) enCurso = ciclo();
  return enCurso;
}
async function ciclo() {
  try {
    while (pendiente) {
      pendiente = false;
      await dibujarAhora();
    }
  } finally {
    enCurso = null;
  }
}
async function dibujarAhora() {
  const objetivo = { ...estado };
  const c = colores();
  textoTitulos();
  dibujarKPIs();
  dibujarTabla();
  await Promise.all([dibujarMapa(c), dibujarRanking(c), dibujarBrecha(c), dibujarDispersion(c), dibujarComposicion(c)]);
  conectarClics();
  window.tablero.dibujado = JSON.stringify(objetivo);
  window.tablero.dibujos += 1;
}

async function iniciar() {
  window.tablero = { listo: false, dibujos: 0, dibujado: null, error: null };
  try {
    const [datos, geo] = await Promise.all([
      fetch("data/pobreza_2024.json").then((r) => { if (!r.ok) throw new Error(`datos: HTTP ${r.status}`); return r.json(); }),
      fetch("data/departamentos.geojson").then((r) => { if (!r.ok) throw new Error(`mapa: HTTP ${r.status}`); return r.json(); }),
    ]);
    DATOS = datos;
    GEO = geo;
    for (const d of DATOS.departamentos) DEP[d.ccdd] = d;
    for (const t of Object.keys(TIPOS)) {
      const tasas = DATOS.departamentos.flatMap((d) => ["total", "urbana", "rural"].map((a) => estimacion(d.ccdd, a, t)))
        .filter(Boolean).map((e) => e.tasa);
      MAX_TASA[t] = Math.ceil(Math.max(...tasas) / 10) * 10;
    }
    const sel = document.getElementById("f-dep");
    [...DATOS.departamentos].sort((a, b) => a.nombre.localeCompare(b.nombre, "es")).forEach((d) => {
      const o = document.createElement("option");
      o.value = d.ccdd;
      o.textContent = d.nombre;
      sel.append(o);
    });
    leerURL();
    sincronizarControles();
    sel.addEventListener("change", () => cambiar({ dep: sel.value }));
    for (const nombre of ["area", "tipo", "medida"]) {
      document.querySelectorAll(`input[name="${nombre}"]`).forEach((i) => i.addEventListener("change", () => cambiar({ [nombre]: i.value })));
    }
    document.getElementById("f-reiniciar").addEventListener("click", () => cambiar({ ...INICIAL }));
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", dibujar);
    await dibujar();
    window.tablero.listo = true;
  } catch (err) {
    window.tablero.error = String(err);
    document.getElementById("resumen-seleccion").textContent = `No se pudieron cargar los datos: ${err.message}`;
    throw err;
  }
}

document.addEventListener("DOMContentLoaded", iniciar);
