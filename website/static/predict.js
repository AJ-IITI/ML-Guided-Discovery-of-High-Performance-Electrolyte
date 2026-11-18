import { byId as $, choices, get, toolStatus, error } from "./ui.js";
export async function predict(s) {
  const f = $("prediction-form"),
    fields = f.elements,
    msg = $("form-result");
  const keys = [
    "concentration_mol_kg",
    "viscosity_mpa_s",
    "coordination_cation_anion",
    "coordination_cation_solvent",
  ];
  for (const k of ["cation", "anion", "solvent", "concentration_mol_kg"])
    choices(
      fields[k],
      s.choices[k],
      "Select " + (k === "concentration_mol_kg" ? "concentration" : k),
      (v) =>
        k === "solvent" ? s.solvent_names[v] + " (" + v + ")" : String(v),
    );
  const { models } = await get("/api/models/status");
  for (const m of Object.values(models)) {
    const row = document.createElement("div");
    row.className = "out-row";
    const top = document.createElement("div");
    top.className = "section-line";
    const label = document.createElement("strong"),
      status = document.createElement("span");
    label.textContent = m.model;
    toolStatus(status, m);
    top.append(label, status);
    const v = document.createElement("span");
    v.className = "out-value";
    v.textContent = "— ";
    const units = document.createElement("small");
    units.textContent = "mS/cm";
    v.append(units);
    row.append(top, v);
    $("model-panels").append(row);
  }
  function validate() {
    for (const k of keys.slice(1)) {
      const el = fields[k];
      el.setCustomValidity(
        el.value && !(el.valueAsNumber > 0 && Number.isFinite(el.valueAsNumber))
          ? "Enter a finite value greater than zero."
          : "",
      );
    }
  }
  let generation = 0;
  f.addEventListener("input", () => {
    generation++;
    msg.textContent = "";
    validate();
  });
  $("example").onclick = async () => {
    try {
      const data = await get(
        "/api/dataset/records?availability=reported&limit=1",
      );
      const r = data.records[0];
      for (const k of ["cation", "anion", "solvent", ...keys])
        fields[k].value = r[k];
      generation++;
      validate();
      msg.className = "message";
      msg.textContent =
        "Inputs copied from OEDB record " +
        r.id +
        ". You can edit the physical properties.";
    } catch (e) {
      error(e);
    }
  };
  f.onsubmit = async (e) => {
    e.preventDefault();
    validate();
    if (!f.reportValidity()) return;
    const seq = ++generation,
      body = Object.fromEntries(new FormData(f));
    keys.forEach((k) => (body[k] = Number(body[k])));
    body.temperature_K = 298;
    const button = f.querySelector("[type=submit]");
    button.disabled = true;
    msg.textContent = "Validating…";
    msg.className = "message";
    try {
      const res = await fetch("/api/predict", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }),
        out = await res.json();
      if (seq !== generation) return;
      if (
        res.status === 503 &&
        out.status === "MODEL_NOT_LOADED" &&
        out.input_valid
      ) {
        msg.textContent =
          "Formulation validated at 298 K. Both models are not loaded; no conductivity was predicted.";
      } else if (res.status === 422) {
        msg.className = "message bad";
        msg.textContent = Array.isArray(out.detail)
          ? out.detail.map((v) => v.field + ": " + v.message).join("; ")
          : out.detail;
      } else
        throw new Error(
          "Prediction service unavailable. No result was returned.",
        );
    } catch (e) {
      if (seq === generation) {
        msg.className = "message bad";
        msg.textContent = e.message;
      }
    } finally {
      button.disabled = false;
    }
  };
}
