/* app.js — the panel interface. Plain JavaScript, no build step.
   Everything is fetched from the DB-backed API. */

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function pill(text, kind) {
  return `<span class="pill ${kind}">${esc(text)}</span>`;
}
function pct(x) { return x == null ? "—" : (x * 100).toFixed(1) + "%"; }

/* ------------------------------------------------------------------ */
/* tab switching                                                       */
/* ------------------------------------------------------------------ */
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    btn.classList.add("active");
    $("#tab-" + btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "log") loadLog();
  });
});

/* ------------------------------------------------------------------ */
/* OVERVIEW                                                            */
/* ------------------------------------------------------------------ */
async function loadOverview() {
  const [o, ds] = await Promise.all([
    fetch("/api/overview").then((r) => r.json()),
    fetch("/api/datasets").then((r) => r.json()),
  ]);
  $("#overview-cards").innerHTML = [
    { v: o.models, l: "trained models (in DB)", c: "" },
    { v: o.predictions_logged, l: "detections logged to DB", c: "green" },
    { v: o.attacks_logged, l: "attacks caught & logged", c: "red" },
    { v: o.matches_logged, l: "correctly classified", c: "" },
    { v: o.last_prediction || "—", l: "last detection written", c: "", s: "small" },
    { v: o.db_file, l: "database file", c: "", s: "small" },
  ].map((c) => `<div class="card"><div class="value ${c.c} ${c.s || ""}">${esc(c.v)}</div><div class="label">${esc(c.l)}</div></div>`).join("");

  $("#dataset-table tbody").innerHTML = ds.map((d) => `
    <tr>
      <td><strong>${esc(d.name)}</strong></td>
      <td>${d.year}</td>
      <td>${d.rows_train_raw.toLocaleString()}</td>
      <td>${d.rows_train_after_smote.toLocaleString()}</td>
      <td>${d.rows_test.toLocaleString()}</td>
      <td>${d.n_features}</td>
      <td>${d.n_classes}</td>
    </tr>`).join("");
}

/* ------------------------------------------------------------------ */
/* UNDER THE HOOD                                                      */
/* ------------------------------------------------------------------ */
async function loadUnderHood() {
  const [steps, tables] = await Promise.all([
    fetch("/api/pipeline").then((r) => r.json()),
    fetch("/api/db_info").then((r) => r.json()),
  ]);
  $("#pipeline-list").innerHTML = steps.map((s) =>
    `<li><span class="phase">${esc(s.phase)} — ${esc(s.title)}</span><br><span class="detail">${esc(s.detail)}</span></li>`
  ).join("");
  const colText = (cols) => {
    const full = cols.join(", ");
    return cols.length > 6 ? cols.slice(0, 6).join(", ") + ", … +" + (cols.length - 6) + " more" : full;
  };
  $("#db-tables").innerHTML = tables.map((t) =>
    `<tr><td><code>${esc(t.table)}</code></td><td>${t.rows.toLocaleString()}</td>` +
    `<td class="muted" title="${esc(t.columns.join(", "))}">${esc(colText(t.columns))}</td></tr>`
  ).join("");
}

/* ------------------------------------------------------------------ */
/* MODELS & EVALUATION                                                 */
/* ------------------------------------------------------------------ */
async function loadModels() {
  const ds = $("#models-dataset").value;
  const [metrics, models, perclass] = await Promise.all([
    fetch(`/api/test_metrics?dataset=${ds}`).then((r) => r.json()),
    fetch(`/api/models?dataset=${ds}`).then((r) => r.json()),
    fetch(`/api/per_class?dataset=${ds}&model=xgboost`).then((r) => r.json()),
  ]);

  $("#metrics-body").innerHTML = metrics.map((m) => `
    <tr>
      <td><strong>${esc(m.model_name.replace(/_/g, " "))}</strong></td>
      <td>${pct(m.accuracy)}</td><td>${pct(m.precision_macro)}</td>
      <td>${pct(m.recall_macro)}</td><td><strong>${pct(m.f1_macro)}</strong></td>
      <td>${m.auc_roc_macro.toFixed(4)}</td>
      <td>${m.test_latency_ms_per_row.toFixed(4)}</td>
    </tr>`).join("");

  $("#models-body").innerHTML = models.map((m) => {
    let params = "";
    try { params = Object.entries(JSON.parse(m.best_params)).map(([k, v]) => `${k}=${v}`).join(", "); } catch {}
    const short = params.length > 110 ? params.slice(0, 110) + " …" : params;
    return `<tr>
      <td><strong>${esc(m.model_label)}</strong></td>
      <td>${m.cv_f1_macro.toFixed(4)}</td>
      <td>${m.latency_ms_per_row.toFixed(4)}</td>
      <td>${m.n_train_rows.toLocaleString()}</td>
      <td>${m.n_hyperparameter_combinations}</td>
      <td class="muted" title="${esc(params)}">${esc(short || "—")}</td>
      <td>${esc(m.trained_at)}</td>
    </tr>`;
  }).join("");

  const rows = perclass.map((p) => `
    <tr>
      <td>${esc(p.class_name)}</td>
      <td>${pct(p.precision)}</td><td>${pct(p.recall)}</td><td>${pct(p.f1)}</td>
    </tr>`).join("");
  $("#perclass").innerHTML = `
    <div class="table-scroll">
    <table class="data">
      <thead><tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    </div>`;
}

$("#models-dataset").addEventListener("change", loadModels);

/* ------------------------------------------------------------------ */
/* LIVE DETECTION                                                      */
/* ------------------------------------------------------------------ */
let lastLiveItems = [];

async function runDetection() {
  const payload = {
    dataset: $("#live-dataset").value,
    model: $("#live-model").value,
    count: parseInt($("#live-count").value, 10),
  };
  const res = await fetch("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    alert("Error: " + (body.detail || res.status));
    return;
  }
  const data = await res.json();
  lastLiveItems = data.items;

  $("#live-result").classList.add("show");
  $("#live-result").innerHTML =
    `<span class="badge">${data.inserted_into_db} rows written to the <code>predictions</code> table</span> ` +
    `(${data.items.length} classified, ${data.items.filter((i) => i.is_attack).length} attacks)`;

  $("#live-body").innerHTML = data.items.map((it, i) => `
    <tr>
      <td><a class="clickable" data-row="${it.row_index}">${i + 1}</a></td>
      <td>${pill(it.predicted_label, it.is_attack ? "attack" : "normal")}</td>
      <td>${pct(it.confidence)}</td>
      <td>${pill(it.true_label, it.true_label !== "Normal" ? "attack" : "normal")}</td>
      <td>${it.matched ? pill("correct", "normal") : pill("wrong", "bad")}</td>
      <td>${it.latency_ms}</td>
    </tr>`).join("");

  document.querySelectorAll("#live-body a[data-row]").forEach((a) => {
    a.addEventListener("click", () => showRowDetail(parseInt(a.dataset.row, 10)));
  });
}

async function showRowDetail(rowIndex) {
  const ds = $("#live-dataset").value;
  const res = await fetch(`/api/row_features?dataset=${ds}&row_index=${rowIndex}&top_n=10`);
  if (!res.ok) return;
  const d = await res.json();
  const rows = d.features.map((f) =>
    `<tr><td><code>${esc(f.name)}</code></td><td class="mono">${f.value.toFixed(4)}</td></tr>`
  ).join("");
  $("#row-detail").classList.add("show");
  $("#row-detail").innerHTML = `
    <h3>What the model saw — test row #${d.row_index} (true label: ${esc(d.true_label)})</h3>
    <p class="muted">${d.n_features_total} features in total; the 10 most distinctive values (largest absolute deviation after scaling) are shown.</p>
    <div class="table-scroll">
    <table class="data"><thead><tr><th>Feature</th><th>Value</th></tr></thead><tbody>${rows}</tbody></table>
    </div>`;
}

$("#run-detection").addEventListener("click", runDetection);

/* ------------------------------------------------------------------ */
/* STEP-BY-STEP DETECTION TRACE (real per-stage timings)               */
/* ------------------------------------------------------------------ */
const TRACE_NOTE =
  "Classical machine learning models like these process a single row of " +
  "~40-80 numeric features in a fraction of a millisecond — this is expected " +
  "and is one advantage of this approach over deep learning for real-time " +
  "network monitoring, not an error. The timings shown above are measured in " +
  "real time from this exact run, not simulated.";

async function runTrace() {
  const box = $("#trace-result");
  box.innerHTML = `<div class="muted">Running the pipeline on one real test row…</div>`;
  const res = await fetch("/api/trace_predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dataset: $("#live-dataset").value,
      model: $("#live-model").value,
    }),
  });
  if (!res.ok) {
    const b = await res.json().catch(() => ({}));
    box.innerHTML = "";
    alert("Error: " + (b.detail || res.status));
    return;
  }
  renderTrace(box, await res.json());
}

function traceStepHTML(t, no, title, body, meta) {
  return `<div class="trace-step">
    <div class="step-head"><span class="step-no">Step ${no}</span>
      <span class="step-title">${esc(title)}</span>
      ${meta ? `<span class="timing">${meta}</span>` : ""}</div>
    <div class="step-body">${body}</div>
  </div>`;
}

function renderTrace(box, t) {
  const s = t.steps;
  const classList = Object.keys(t.probabilities).sort(
    (a, b) => t.probabilities[b] - t.probabilities[a]
  );

  const probsRows = classList.map((k) => {
    const p = t.probabilities[k];
    const w = (p * 100).toFixed(1);
    return `<div class="prob-row">
      <span class="prob-label">${esc(k)}</span>
      <span class="prob-bar"><span class="prob-fill" style="width:${w}%"></span></span>
      <span class="prob-pct">${w}%</span>
    </div>`;
  }).join("");

  const feats = s.input.preview.map((f) => {
    const v = typeof f.value === "number" ? f.value.toFixed(4) : esc(f.value);
    return `<tr><td><code>${esc(f.name)}</code></td><td class="mono">${v}</td></tr>`;
  }).join("");
  const cats = Object.entries(s.input.categorical || {}).map(([k, v]) =>
    `<tr><td><code>${esc(k)}</code></td><td>${esc(v)}</td></tr>`
  ).join("");

  const head = `<div class="trace-head">
    <strong>${esc(t.dataset)}</strong> &middot; ${esc(t.model_label)} &middot; test row #${t.row_index}
    &middot; true label ${pill(t.true_label, t.true_label !== "Normal" ? "attack" : "normal")}
    &nbsp;<span class="muted">(${esc(t.timestamp)})</span></div>`;

  const step1 = traceStepHTML(t, 1, s.input.title, `
    <p class="muted">Raw row as it arrives from the test set (${s.input.n_raw_features}
      raw features; ${t.n_features} after encoding). The ${s.input.preview.length} most
      distinctive values:</p>
    <div class="table-scroll"><table class="data"><thead><tr><th>Feature</th><th>Raw value</th></tr></thead>
      <tbody>${feats}${cats}</tbody></table></div>`);

  const step2 = traceStepHTML(t, 2, s.preprocessing.title,
    `<p class="muted">Actually running the saved preprocessor on that raw row —
       ${s.preprocessing.n_output_features} output features.</p>` +
    (s.preprocessing.reproduces_stored_row
      ? `<p><span class="pill normal">PASS</span> &nbsp;transforming the raw row
         reproduces the stored row <em>exactly</em> — proof the stored test data
         came from precisely this pipeline.</p>`
      : `<p><span class="pill bad">FAIL</span> &nbsp;the transformed row differs from
         the stored one.</p>`),
    s.preprocessing.ms.toFixed(4) + " ms");

  const step3 = traceStepHTML(t, 3, s.inference.title,
    `<div class="prob-list">${probsRows}</div>
     <p class="muted">All class probabilities for this row, from
        ${esc(t.model_label)}'s real predict_proba output.</p>`,
    s.inference.ms.toFixed(4) + " ms");

  const step4 = traceStepHTML(t, 4, s.decision.title,
    `<p>Prediction: ${pill(t.predicted_label, t.is_attack ? "attack" : "normal")}
        &nbsp;confidence ${pct(t.confidence)}
        &nbsp;${t.matched ? pill("correct", "normal") : pill("wrong", "bad")}</p>
     <p class="muted">Argmax over the class probabilities above; “correct/wrong”
        compares the prediction to the row's true label.</p>`,
    s.decision.ms.toFixed(4) + " ms");

  const tms = t.timings;
  const step5 = traceStepHTML(t, 5, "Total time breakdown",
    `<div class="table-scroll"><table class="data">
       <thead><tr><th>Stage</th><th>Measured time (ms)</th></tr></thead>
       <tbody>
         <tr><td>Step 2 — Preprocessing</td><td class="mono">${tms.preprocessing_ms.toFixed(4)}</td></tr>
         <tr><td>Step 3 — Model inference</td><td class="mono">${tms.inference_ms.toFixed(4)}</td></tr>
         <tr><td>Step 4 — Decision</td><td class="mono">${tms.decision_ms.toFixed(4)}</td></tr>
         <tr><td><strong>Total (Steps 2–4)</strong></td><td class="mono"><strong>${tms.total_ms.toFixed(4)}</strong></td></tr>
       </tbody></table></div>
     <p class="note">${TRACE_NOTE}</p>`);

  box.innerHTML = head;
  [step1, step2, step3, step4, step5].forEach((html, i) => {
    setTimeout(() => box.insertAdjacentHTML("beforeend", html), 260 * (i + 1));
  });
}

$("#run-trace").addEventListener("click", runTrace);

/* ------------------------------------------------------------------ */
/* CUSTOM USER INPUT                                                   */
/* ------------------------------------------------------------------ */
let featureTotal = 0;

async function loadFeatureForm() {
  const ds = $("#live-dataset").value;
  const m = $("#live-model").value;
  const res = await fetch(`/api/feature_input?dataset=${ds}&model=${m}&n=10`);
  if (!res.ok) { alert("Failed to load feature inputs: " + res.status); return; }
  const d = await res.json();
  featureTotal = d.total_features;

  $("#custom-form").innerHTML = d.features.map((f) => `
    <label class="feature-field" title="dataset avg ${f.mean.toFixed(4)} &plusmn; ${f.std.toFixed(4)} &middot; typical range ${f.min.toFixed(3)} .. ${f.max.toFixed(3)}">
      <span class="fname">${esc(f.name)}</span>
      <input type="number" step="any" data-fname="${esc(f.name)}" value="${f.mean.toFixed(4)}" />
      <span class="fmeta">avg ${f.mean.toFixed(2)} &middot; range ${f.min.toFixed(2)} .. ${f.max.toFixed(2)}</span>
    </label>`).join("");
  $("#custom-result").classList.remove("show");
  $("#custom-probs").innerHTML = "";
  $("#run-custom").disabled = false;
}

async function runCustom() {
  const features = {};
  document.querySelectorAll("#custom-form input[data-fname]").forEach((inp) => {
    const v = parseFloat(inp.value);
    if (!Number.isNaN(v)) features[inp.dataset.fname] = v;
  });
  if (!Object.keys(features).length) { alert("Enter at least one feature value."); return; }

  const res = await fetch("/api/predict_custom", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dataset: $("#live-dataset").value,
      model: $("#live-model").value,
      features,
    }),
  });
  if (!res.ok) {
    const b = await res.json().catch(() => ({}));
    alert("Error: " + (b.detail || res.status));
    return;
  }
  const data = await res.json();
  const it = data.items[0];
  const setCount = Object.keys(it.user_features || {}).length;

  $("#custom-result").classList.add("show");
  $("#custom-result").innerHTML =
    `<span class="badge">${data.inserted_into_db} detection written to the <code>predictions</code> table</span><br>` +
    `Prediction: ${pill(it.predicted_label, it.is_attack ? "attack" : "normal")} &nbsp;confidence ${pct(it.confidence)} &nbsp;latency ${it.latency_ms} ms<br>` +
    `<span class="muted">${setCount} feature(s) set by you; the other ${featureTotal - setCount} features were left at their dataset average.</span>`;

  $("#custom-probs").innerHTML =
    `<h2>Class probabilities</h2>` +
    `<div class="table-scroll"><table class="data">` +
    `<thead><tr><th>Class</th><th>Probability</th></tr></thead><tbody>` +
    Object.entries(it.probabilities).sort((a, b) => b[1] - a[1])
      .map(([k, v]) => `<tr><td>${esc(k)}</td><td>${pct(v)}</td></tr>`).join("") +
    `</tbody></table></div>`;
}

$("#load-features").addEventListener("click", loadFeatureForm);
$("#run-custom").addEventListener("click", runCustom);
$("#live-model").addEventListener("change", () => {
  if ($("#custom-form").innerHTML) loadFeatureForm();
});

/* ------------------------------------------------------------------ */
/* PREDICTION LOG                                                      */
/* ------------------------------------------------------------------ */
async function loadLog() {
  const rows = await fetch("/api/predictions?limit=100").then((r) => r.json());
  $("#log-count").textContent = `showing ${rows.length} most recent rows`;
  $("#log-body").innerHTML = rows.map((r) => `
    <tr>
      <td>${r.id}</td>
      <td>${esc(r.timestamp)}</td>
      <td>${esc(r.dataset)}</td>
      <td>${esc(r.model_name)}</td>
      <td>${pill(r.predicted_label, r.is_attack ? "attack" : "normal")}</td>
      <td>${esc(r.true_label || "—")}</td>
      <td>${r.matched ? pill("correct", "normal") : pill("wrong", "bad")}</td>
      <td>${pct(r.confidence)}</td>
      <td>${r.latency_ms}</td>
      <td>${r.row_index}</td>
    </tr>`).join("");
}

$("#refresh-log").addEventListener("click", loadLog);

/* ------------------------------------------------------------------ */
/* boot                                                               */
/* ------------------------------------------------------------------ */
Promise.all([loadOverview(), loadUnderHood(), loadModels()]);
