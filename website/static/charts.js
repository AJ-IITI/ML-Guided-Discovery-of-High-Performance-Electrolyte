// Coordinates and bin heights are derived exclusively from the filtered figures API.
const NS = "http://www.w3.org/2000/svg";
const palette = { Li: "#205a80", Na: "#148079", K: "#a26437" };
const names = { Li: "Lithium", Na: "Sodium", K: "Potassium" };
function node(tag, attrs = {}, value) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (value !== undefined) e.textContent = value;
  return e;
}
const fmt = (v) => Number(v.toPrecision(3)).toString();
function table(el, headers, rows) {
  const details = document.createElement("details"),
    summary = document.createElement("summary");
  summary.textContent = "View values as a table";
  details.append(summary);
  const t = document.createElement("table"),
    head = t.createTHead().insertRow();
  for (const h of headers) {
    const th = document.createElement("th");
    th.textContent = h;
    head.append(th);
  }
  const body = t.createTBody();
  for (const r of rows) {
    const tr = body.insertRow();
    for (const v of r) tr.insertCell().textContent = v;
  }
  details.append(t);
  el.append(details);
}
function empty(el) {
  el.replaceChildren();
  const p = document.createElement("p");
  p.className = "blank";
  p.textContent = "No reported conductivity values match these filters.";
  el.append(p);
}
function frame(el, label, xlabel, ylabel, compact) {
  el.replaceChildren();
  const w = Math.max(265, Math.min(compact ? 560 : 830, el.clientWidth || 480)),
    h = compact ? 171 : 220;
  const x0 = 46,
    x1 = w - 15,
    y0 = 18,
    y1 = h - 46;
  const svg = node("svg", {
    viewBox: "0 0 " + w + " " + h,
    role: "img",
    "aria-label": label,
  });
  el.append(svg);
  const add = (t, a, v) => {
    const n = node(t, a, v);
    svg.append(n);
    return n;
  };
  add("text", { x: x0, y: 12, class: "axis-name" }, ylabel);
  add(
    "text",
    { x: (x0 + x1) / 2, y: h - 4, "text-anchor": "middle", class: "axis-name" },
    xlabel,
  );
  function yaxis(high, integer = false) {
    const raw = high / 4 || 1,
      base = 10 ** Math.floor(Math.log10(raw)),
      step = Math.max(
        integer ? 1 : 0,
        ([1, 2, 2.5, 5, 10].find((v) => v * base >= raw) || 10) * base,
      );
    const max = Math.ceil(high / step) * step || step;
    const y = (n) => y1 - (n / max) * (y1 - y0);
    for (let v = 0; v <= max + step * 0.01; v += step) {
      add("line", {
        x1: x0,
        x2: x1,
        y1: y(v),
        y2: y(v),
        class: v === 0 ? "baseline" : "grid",
      });
      add(
        "text",
        { x: x0 - 6, y: y(v) + 4, "text-anchor": "end" },
        v >= 1000 ? v / 1000 + "k" : fmt(v),
      );
    }
    return y;
  }
  return { w, h, x0, x1, y0, y1, add, yaxis };
}
export function trend(el, data, compact = false) {
  if (!data.length) return empty(el);
  const f = frame(
    el,
    "Median simulated ionic conductivity by cation and molality",
    "Molality (mol/kg)",
    "Median σ (mS/cm)",
    compact,
  );
  const xs = [...new Set(data.map((p) => p.x))].sort((a, b) => a - b);
  const x = (v) =>
    xs.length === 1
      ? (f.x0 + f.x1) / 2
      : f.x0 + ((v - xs[0]) / (xs.at(-1) - xs[0])) * (f.x1 - f.x0);
  const y = f.yaxis(Math.max(...data.map((p) => p.median)));
  for (const v of xs)
    f.add(
      "text",
      { x: x(v), y: f.y1 + 16, "text-anchor": "middle" },
      String(v),
    );
  const legend = document.createElement("div");
  legend.className = "legend";
  for (const c of ["Li", "Na", "K"]) {
    const points = data.filter((p) => p.cation === c);
    if (!points.length) continue;
    f.add("polyline", {
      points: points.map((p) => x(p.x) + "," + y(p.median)).join(" "),
      fill: "none",
      stroke: palette[c],
      "stroke-width": 2.1,
      "stroke-dasharray": c === "Na" ? "6 2" : c === "K" ? "2 2" : "none",
    });
    for (const p of points) {
      const n = f.add("circle", {
        cx: x(p.x),
        cy: y(p.median),
        r: 3.25,
        fill: palette[c],
        stroke: "#fff",
        "stroke-width": 0.8,
      });
      n.append(
        node(
          "title",
          {},
          names[c] +
            ": " +
            p.x +
            " mol/kg · median " +
            fmt(p.median) +
            " mS/cm · n=" +
            p.n,
        ),
      );
    }
    const item = document.createElement("span"),
      swatch = document.createElement("i");
    swatch.style.backgroundColor = palette[c];
    item.append(swatch, document.createTextNode(c + "⁺"));
    legend.append(item);
  }
  el.append(legend);
  if (!compact)
    table(
      el,
      ["Cation", "Mol/kg", "Median (mS/cm)", "Records"],
      data.map((p) => [p.cation, p.x, fmt(p.median), p.n]),
    );
}
export function histogram(el, data) {
  if (!data.length) return empty(el);
  const f = frame(
    el,
    "Counts by decade of simulated ionic conductivity",
    "Conductivity (mS/cm) · logarithmic bins",
    "Records",
    false,
  );
  const y = f.yaxis(Math.max(...data.map((b) => b.count)), true),
    pw = (f.x1 - f.x0) / data.length;
  data.forEach((b, i) => {
    const xx = f.x0 + i * pw,
      bar = f.add("rect", {
        x: xx + 0.12 * pw,
        y: y(b.count),
        width: 0.76 * pw,
        height: f.y1 - y(b.count),
        fill: "#477b85",
      });
    bar.append(
      node(
        "title",
        {},
        b.low + " to <" + b.high + " mS/cm: " + b.count + " records",
      ),
    );
    if (f.w > 490 || i % 2 === 0)
      f.add(
        "text",
        { x: xx, y: f.y1 + 16, "text-anchor": "middle" },
        "1e" + Math.round(Math.log10(b.low)),
      );
    if (i === data.length - 1)
      f.add(
        "text",
        { x: f.x1, y: f.y1 + 16, "text-anchor": "middle" },
        "1e" + Math.round(Math.log10(b.high)),
      );
  });
  table(
    el,
    ["Lower (inclusive)", "Upper (exclusive)", "Records"],
    data.map((b) => [b.low, b.high, b.count]),
  );
}
export function solvents(el, data) {
  if (!data.length) return empty(el);
  el.replaceChildren();
  const bars = document.createElement("div");
  bars.className = "bars";
  const max = Math.max(...data.map((d) => d.median));
  for (const s of data) {
    const row = document.createElement("div");
    row.className = "sbar";
    row.title = s.name + " (" + s.code + "), n=" + s.n;
    const label = document.createElement("span"),
      track = document.createElement("span"),
      bar = document.createElement("i"),
      v = document.createElement("span");
    label.textContent = s.name + " (" + s.code + ")";
    track.className = "track";
    bar.style.width = (max ? (100 * s.median) / max : 0) + "%";
    track.append(bar);
    v.textContent = fmt(s.median);
    row.append(label, track, v);
    bars.append(row);
  }
  el.append(bars);
  table(
    el,
    ["Solvent", "Median (mS/cm)", "Records"],
    data.map((s) => [s.name, fmt(s.median), s.n]),
  );
}
