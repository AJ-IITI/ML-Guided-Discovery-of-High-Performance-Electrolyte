import { byId as $, count, number, choices, get, error } from "./ui.js";
import { trend, histogram, solvents } from "./charts.js";
export async function explore(s) {
  const form = $("filters"),
    params = new URLSearchParams(location.search),
    limit = 20;
  const select = form.elements,
    chart = $("explore-chart");
  for (const [key, label] of [
    ["cation", "All cations"],
    ["anion", "All anions"],
    ["solvent", "All solvents"],
  ]) {
    choices(select[key], s.choices[key], label, (v) =>
      key === "solvent" ? s.solvent_names[v] + " (" + v + ")" : v,
    );
  }
  for (const k of ["q", "cation", "anion", "solvent", "availability"])
    if (params.has(k)) select[k].value = params.get(k);
  let offset = 0,
    active = "distribution",
    figure = null,
    request = 0,
    timer,
    abort;
  function filters() {
    return new URLSearchParams(
      [...new FormData(form)].filter(([, v]) => v !== ""),
    );
  }
  function renderPlot() {
    if (!figure) return;
    const titles = {
      distribution: "Conductivity distribution",
      trend: "Conductivity versus concentration",
      solvents: "Median conductivity by solvent",
    };
    const captions = {
      distribution: "Bars count source records in each decade of conductivity.",
      trend:
        "Each point is the median for a cation at a sampled molality; lines connect medians, not model fits.",
      solvents:
        "Solvents are ordered by median simulated conductivity (mS/cm) within the current filters.",
    };
    $("plot-title").textContent = titles[active];
    $("plot-caption").textContent =
      captions[active] +
      " " +
      count(figure.n) +
      " reported values; " +
      count(figure.missing) +
      " missing excluded.";
    if (active === "trend") trend(chart, figure.trend);
    else if (active === "distribution") histogram(chart, figure.histogram);
    else solvents(chart, figure.solvents);
  }
  async function refresh(replot = true) {
    const id = ++request;
    if (abort) abort.abort();
    abort = new AbortController();
    const opts = { signal: abort.signal },
      p = filters();
    $("error").hidden = true;
    $("prev").disabled = $("next").disabled = true;
    const url = p.toString();
    history.replaceState(null, "", location.pathname + (url ? "?" + url : ""));
    $("export").href = "/api/dataset/export.csv?" + url;
    try {
      const [data, newFig] = await Promise.all([
        get(
          "/api/dataset/records?" + p + "&offset=" + offset + "&limit=" + limit,
          opts,
        ),
        replot || !figure ? get("/api/dataset/figures?" + p, opts) : null,
      ]);
      if (id !== request) return;
      if (newFig) {
        figure = newFig;
        renderPlot();
      }
      $("count").textContent = count(data.total) + " records";
      const body = $("rows");
      body.replaceChildren();
      for (const r of data.records) {
        const tr = body.insertRow();
        for (const v of [
          r.id,
          r.cation,
          r.anion,
          r.solvent_name + " (" + r.solvent + ")",
          number(r.concentration_mol_kg),
          number(r.ionic_conductivity_ms_cm),
          number(r.viscosity_mpa_s),
          number(r.coordination_cation_anion),
          number(r.coordination_cation_solvent),
          r.experimental_reference || "—",
        ]) {
          const td = tr.insertCell();
          td.textContent = String(v);
          if (v === "Missing") td.className = "missing";
        }
      }
      if (!data.total) {
        const td = body.insertRow().insertCell();
        td.colSpan = 10;
        td.textContent = "No matching records. Change or reset the filters.";
      }
      $("page-info").textContent = data.total
        ? count(offset + 1) +
          "–" +
          count(offset + data.records.length) +
          " of " +
          count(data.total) +
          " records"
        : "0 records";
      $("prev").disabled = offset === 0;
      $("next").disabled = offset + limit >= data.total;
    } catch (e) {
      if (id === request && e.name !== "AbortError") {
        figure = null;
        chart.textContent = "Figure unavailable.";
        $("rows").replaceChildren();
        $("count").textContent = "Unavailable";
        $("page-info").textContent = "";
        error(e);
      }
    }
  }
  function changed() {
    offset = 0;
    clearTimeout(timer);
    refresh();
  }
  select.q.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(changed, 180);
  });
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    changed();
  });
  form.addEventListener("change", (e) => {
    if (e.target !== select.q) changed();
  });
  form.addEventListener("reset", () => setTimeout(changed, 0));
  $("prev").onclick = () => {
    offset = Math.max(0, offset - limit);
    refresh(false);
  };
  $("next").onclick = () => {
    offset += limit;
    refresh(false);
  };
  document.querySelectorAll("[data-plot]").forEach(
    (b) =>
      (b.onclick = () => {
        active = b.dataset.plot;
        document
          .querySelectorAll("[data-plot]")
          .forEach((t) => t.setAttribute("aria-pressed", String(t === b)));
        renderPlot();
      }),
  );
  let width = 0;
  new ResizeObserver((entries) => {
    const w = Math.round(entries[0].contentRect.width);
    if (w !== width) {
      width = w;
      renderPlot();
    }
  }).observe(chart);
  await refresh();
}
