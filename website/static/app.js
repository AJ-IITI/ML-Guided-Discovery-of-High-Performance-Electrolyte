const $ = (id) => document.getElementById(id);
let options = null;
function setSelect(id, values, placeholder) {
  const select = $(id); select.innerHTML = "";
  const first = document.createElement("option"); first.value = ""; first.textContent = placeholder || "Select"; select.appendChild(first);
  values.forEach((value) => { const option = document.createElement("option"); option.value = String(value); option.textContent = String(value); select.appendChild(option); });
}
async function api(path, init) {
  const response = await fetch(path, init); const payload = await response.json();
  if (!response.ok) { const detail = payload.detail; throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail)); }
  return payload;
}
function setModelStatus(name, status) {
  const prefix = name === "hgb_svr" ? "hgb" : "smi";
  $(prefix + "-dot").className = "status-dot " + (status.loaded ? "" : "bad");
  $(prefix + "-status").textContent = status.loaded ? "Loaded · " + status.version : "Not loaded";
  $(prefix + "-meta").textContent = status.loaded ? "Ready for prediction" : (status.error || "Model adapter unavailable");
}
async function loadHealth() {
  try {
    const health = await api("/api/health");
    $("header-status").textContent = health.dataset.loaded ? "Dataset connected" : "Dataset unavailable";
    setModelStatus("hgb_svr", health.models.hgb_svr); setModelStatus("smited", health.models.smited);
  } catch (_) { $("header-status").textContent = "API unavailable"; }
}
async function loadOptions() {
  options = await api("/api/options");
  setSelect("cation", options.cations, "Select cation"); setSelect("anion", options.anions, "Select anion");
  setSelect("solvent", options.solvents, "Select solvent"); setSelect("concentration", options.concentrations_mol_kg, "Select concentration");
  setSelect("filter-cation", options.cations, "All cations"); setSelect("filter-anion", options.anions, "All anions");
  setSelect("filter-solvent", options.solvents, "All solvents");
  $("data-count").textContent = options.dataset_rows.toLocaleString() + " records";
}
function renderPrediction(data) {
  [["hgb_svr","hgb"],["smited","smi"]].forEach(([key,prefix]) => {
    const result = data.predictions[key]; if (!result) return;
    if (result.status === "ok") {
      $(prefix + "-value").textContent = Number(result.conductivity_mS_cm).toFixed(3);
      $(prefix + "-meta").textContent = "Model prediction · " + (result.message || "No calibrated interval");
    } else { $(prefix + "-value").textContent = "—"; $(prefix + "-meta").textContent = result.message || "Model unavailable"; }
  });
  $("uncertainty-note").textContent = data.uncertainty_note || "No calibrated prediction interval available.";
}
$("prediction-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const button = $("predict-button"); const message = $("form-message");
  button.disabled = true; button.textContent = "Predicting…"; message.textContent = "";
  $("hgb-value").textContent = "—"; $("smi-value").textContent = "—";
  const payload = {cation:$("cation").value,anion:$("anion").value,solvent:$("solvent").value,concentration_mol_kg:Number($("concentration").value),models:["hgb_svr","smited"]};
  try {
    const result = await api("/api/predict",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    renderPrediction(result);
  } catch (error) {
    message.textContent = error.message;
    try { const health = await api("/api/health"); setModelStatus("hgb_svr",health.models.hgb_svr); setModelStatus("smited",health.models.smited); } catch (_) {}
  } finally { button.disabled = false; button.innerHTML = 'Predict conductivity <span>→</span>'; }
});
async function loadExplore() {
  const params = new URLSearchParams();
  if ($("filter-cation").value) params.set("cation",$("filter-cation").value);
  if ($("filter-anion").value) params.set("anion",$("filter-anion").value);
  if ($("filter-solvent").value) params.set("solvent",$("filter-solvent").value);
  params.set("limit","500");
  const data = await api("/api/explore?" + params.toString());
  $("record-count").textContent = "(" + data.total_matching.toLocaleString() + ")";
  const body = $("records-body"); body.innerHTML = "";
  data.records.forEach((row) => {
    const tr = document.createElement("tr");
    [row.cation,row.anion,row.solvent,formatNumber(row.concentration_mol_kg,2),formatNumber(row.ionic_conductivity_ms_cm,3),formatNumber(row.viscosity_mpa_s,3),formatNumber(row.density_g_cm3,3)].forEach((value) => {
      const td = document.createElement("td"); td.textContent = value; tr.appendChild(td);
    }); body.appendChild(tr);
  });
  if (!data.records.length) { const tr=document.createElement("tr");const td=document.createElement("td");td.colSpan=7;td.textContent="No matching records.";tr.appendChild(td);body.appendChild(tr); }
  drawChart(data);
}
function formatNumber(value,digits) { return value===null||value===undefined||!Number.isFinite(Number(value)) ? "—" : Number(value).toFixed(digits); }
function drawChart(data) {
  const target=$("conductivity-chart");
  if (!window.Plotly) { target.textContent="Plotly could not be loaded. The table remains available."; return; }
  const trace={x:data.concentration,y:data.conductivity,type:"scatter",mode:"markers",marker:{size:7,color:"#e8793b",opacity:.65},name:"OEDB records",hovertemplate:"Concentration: %{x} mol/kg<br>Conductivity: %{y:.3f} mS/cm<extra></extra>"};
  const layout={margin:{l:60,r:20,t:12,b:55},paper_bgcolor:"#fff",plot_bgcolor:"#fff",xaxis:{title:"Concentration (mol/kg)",gridcolor:"#edf0f3"},yaxis:{title:"Ionic conductivity (mS/cm)",gridcolor:"#edf0f3"},font:{family:"DM Sans, sans-serif",color:"#536171"}};
  Plotly.react(target,[trace],layout,{responsive:true,displayModeBar:false});
}
["filter-cation","filter-anion","filter-solvent"].forEach((id)=>$(id).addEventListener("change",()=>loadExplore().catch((e)=>{$("records-body").textContent=e.message;})));
$("clear-filters").addEventListener("click",()=>{$("filter-cation").value="";$("filter-anion").value="";$("filter-solvent").value="";loadExplore().catch((e)=>{$("records-body").textContent=e.message;});});
document.querySelectorAll(".nav-link").forEach((button)=>button.addEventListener("click",()=>{
  document.querySelectorAll(".nav-link").forEach((item)=>item.classList.remove("active"));
  document.querySelectorAll(".view").forEach((item)=>item.classList.remove("active"));
  button.classList.add("active"); $("view-"+button.dataset.view).classList.add("active");
  if(button.dataset.view==="explore") loadExplore().catch((e)=>{$("records-body").textContent=e.message;});
}));
(async function init(){await loadHealth();try{await loadOptions();await loadExplore();}catch(error){$("header-status").textContent="Dataset unavailable";$("form-message").textContent=error.message;}})();
