import React, { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api.js";
import HelpTip from "../components/HelpTip.jsx";
import { useMonitor } from "../components/MonitorContext.jsx";
import {
  Seg,
  XgbLossChart,
  RandomForestChart,
  DecisionTreeChart,
  LogisticChart,
  ProgressionChart,
} from "../components/TrainingCharts.jsx";

const DATASET_LABEL = { nslkdd: "NSL-KDD", cicids: "CICIDS2017" };
const MODEL_LABEL = {
  logistic: "Logistic Regression",
  decision_tree: "Decision Tree",
  random_forest: "Random Forest",
  xgboost: "XGBoost",
};

// The five headline metrics and the model comparison page shows.
const METRICS = [
  { key: "accuracy", label: "Accuracy" },
  { key: "precision_macro", label: "Precision" },
  { key: "recall_macro", label: "Recall" },
  { key: "f1_macro", label: "F1" },
  { key: "auc_roc_macro", label: "AUC-ROC" },
];

const MODEL_COLORS = ["#007bff", "#fd7e14", "#28a745", "#6f42c1"];

/** Clickable-legend state: clicking a legend item hides/shows its series. */
function useLegendToggle() {
  const [hidden, setHidden] = useState({});
  const onLegendClick = (entry) =>
    setHidden((h) => ({ ...h, [entry.dataKey || entry.value]: !h[entry.dataKey || entry.value] }));
  return { hidden, onLegendClick };
}

/**
 * Compare — the model comparison page.
 *
 * Shows the Phase 4 test-set metrics for all four models, with a toggle to
 * switch between the NSL-KDD and CICIDS2017 results.  Data comes from the
 * backend's GET /models, GET /compare, GET /progression and
 * GET /training-curves endpoints.
 */
export default function Compare() {
  const [dataset, setDataset] = useState("nslkdd");
  const [data, setData] = useState(null);
  const [tuning, setTuning] = useState(null);
  const [progression, setProgression] = useState(null);
  const [curves, setCurves] = useState(null);
  const [saved, setSaved] = useState(null);
  const [insightsMode, setInsightsMode] = useState("nslkdd");
  const [error, setError] = useState(null);
  const { running, log } = useMonitor();

  const headlineLegend = useLegendToggle();
  const radarLegend = useLegendToggle();
  const tuningLegend = useLegendToggle();

  useEffect(() => {
    api
      .compare()
      .then(setData)
      .catch((e) => setError(e.message));
    api.tuningImpact().then(setTuning).catch(() => setTuning(null));
    api.progression().then(setProgression).catch(() => setProgression(null));
    api
      .trainingCurves()
      .then(({ curves: c, saved: s }) => {
        setCurves(c);
        setSaved(s);
      })
      .catch(() => {
        setCurves(null);
        setSaved(null);
      });
  }, []);

  const rows = useMemo(() => {
    if (!data) return [];
    return data[dataset].map((r) => ({
      model: r.model,
      label: r.model_label,
      ...r,
    }));
  }, [data, dataset]);

  const barData = useMemo(
    () =>
      METRICS.map((m) => {
        const point = { metric: m.label };
        rows.forEach((r) => {
          point[r.label] = r[m.key];
        });
        return point;
      }),
    [rows]
  );

  const radarData = useMemo(
    () =>
      METRICS.map((m) => {
        const point = { metric: m.label };
        rows.forEach((r) => {
          point[r.label] = r[m.key];
        });
        return point;
      }),
    [rows]
  );

  const tuningRows = useMemo(() => {
    if (!tuning) return [];
    return tuning[dataset].map((t) => ({
      model: t.model,
      label: t.model_label,
      baseline: t.baseline.f1_macro,
      tuned: t.tuned.f1_macro,
      delta: t.delta_f1_macro,
    }));
  }, [tuning, dataset]);

  // Live per-model average latency, measured on the fly from the predictions
  // stored in the log ("database").  Only counts rows for the dataset shown and
  // rows that actually recorded a latency.
  const liveLatency = useMemo(() => {
    const acc = {};
    (log.items || []).forEach((e) => {
      if (e.dataset !== dataset || typeof e.latency_ms !== "number") return;
      acc[e.model] = acc[e.model] || [];
      acc[e.model].push(e.latency_ms);
    });
    const out = {};
    Object.entries(acc).forEach(([m, arr]) => {
      out[m] = arr.reduce((a, b) => a + b, 0) / arr.length;
    });
    return out;
  }, [log, dataset]);

  if (error) {
    return <div className="error-box">Could not load comparison data: {error}</div>;
  }

  if (!data) {
    return <div className="loading">Loading comparison data…</div>;
  }

  return (
    <div>
      <div className="toggle-row">
        {Object.entries(DATASET_LABEL).map(([key, label]) => (
          <button
            key={key}
            className={`ghost ${dataset === key ? "active" : ""}`}
            onClick={() => setDataset(key)}
          >
            {label}
          </button>
        ))}
        <HelpTip
          text="Same models, same pipeline, two benchmarks. Switch to see how each
          dataset changes the scores — CICIDS2017 is the modern benchmark."
        />
      </div>

      <div className="grid grid-3">
        <div className="panel" style={{ gridColumn: "1 / -1" }}>
          <h3>{DATASET_LABEL[dataset]} — headline metrics on the test set</h3>
          <p className="chart-title">
            Higher is better on every axis. XGBoost is typically the strongest
            detector; the Decision Tree is the most human-readable.
          </p>
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={barData} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
              <XAxis dataKey="metric" stroke="#6c757d" />
              <YAxis domain={[0, 1]} stroke="#6c757d" />
              <Tooltip
                contentStyle={{
                  background: "#fff",
                  border: "1px solid #dee2e6",
                  borderRadius: 8,
                }}
                labelStyle={{ color: "#212529" }}
              />
              <Legend onClick={headlineLegend.onLegendClick} />
              {rows.map((r, i) => (
                <Bar
                  key={r.model}
                  dataKey={r.label}
                  fill={MODEL_COLORS[i % MODEL_COLORS.length]}
                  radius={[4, 4, 0, 0]}
                  hide={!!headlineLegend.hidden[r.label]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <h3>Radar — shape of each model</h3>
          <p className="chart-title">
            A model with a big, round radar is strong on every metric at once.
          </p>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData} outerRadius="70%">
              <PolarGrid stroke="#e9ecef" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: "#6c757d", fontSize: 11 }} />
              {rows.map((r, i) => (
                <Radar
                  key={r.model}
                  name={r.label}
                  dataKey={r.label}
                  stroke={MODEL_COLORS[i % MODEL_COLORS.length]}
                  fill={MODEL_COLORS[i % MODEL_COLORS.length]}
                  fillOpacity={0.18}
                  hide={!!radarLegend.hidden[r.label]}
                />
              ))}
              <Legend onClick={radarLegend.onLegendClick} />
              <Tooltip
                contentStyle={{
                  background: "#fff",
                  border: "1px solid #dee2e6",
                  borderRadius: 8,
                }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <h3>
            Latency &amp; speed
            {running && <span className="live-dot" title="Monitoring is running — latency values are live"> LIVE</span>}
          </h3>
          <p className="chart-title">
            Milliseconds per row on the test set — every model answers in under
            a tenth of a millisecond, so speed is not the deciding factor. The
            live column is measured end-to-end on the server while the monitor
            runs (preprocessing included, so a little higher than pure
            inference).
          </p>
          <div className="metrics-table" role="table">
            <table className="metrics-table">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Test set (ms / row)</th>
                  <th>Live (ms / row)</th>
                </tr>
              </thead>
              <tbody>
                {rows
                  .slice()
                  .sort((a, b) => a.test_latency_ms_per_row - b.test_latency_ms_per_row)
                  .map((r) => (
                    <tr key={r.model}>
                      <td>{r.label}</td>
                      <td className="mono">{r.test_latency_ms_per_row.toFixed(4)}</td>
                      <td className="mono">
                        {liveLatency[r.model] !== undefined ? (
                          liveLatency[r.model].toFixed(4)
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel" style={{ gridColumn: "1 / -1" }}>
          <h3>Scoreboard — {DATASET_LABEL[dataset]} test set</h3>
          <table className="metrics-table">
            <thead>
              <tr>
                <th>Model</th>
                {METRICS.map((m) => (
                  <th key={m.key}>{m.label}</th>
                ))}
                <th>Latency (ms/row)</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const bestF1 = Math.max(...rows.map((x) => x.f1_macro));
                return (
                  <tr key={r.model}>
                    <td>{r.label}</td>
                    {METRICS.map((m) => (
                      <td
                        key={m.key}
                        className={r[m.key] === Math.max(...rows.map((x) => x[m.key])) ? "best" : ""}
                      >
                        {r[m.key].toFixed(4)}
                      </td>
                    ))}
                    <td className="mono">{r.test_latency_ms_per_row.toFixed(4)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="small muted" style={{ marginTop: 10 }}>
            Green = best score for that metric. Best overall model by F1:{" "}
            <b>{MODEL_LABEL[[...rows].sort((a, b) => b.f1_macro - a.f1_macro)[0].model]}</b>
          </p>
        </div>

        {tuning && (
          <div className="panel" style={{ gridColumn: "1 / -1" }}>
            <h3>How much did hyperparameter tuning help — {DATASET_LABEL[dataset]}</h3>
            <p className="chart-title">
              Baseline = default scikit-learn / XGBoost settings inside the same
              preprocessing pipeline. Tuned = the saved grid-searched models.
            </p>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={tuningRows}
                margin={{ top: 8, right: 16, left: 0, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
                <XAxis dataKey="label" stroke="#6c757d" interval={0} />
                <YAxis domain={[0, 1]} stroke="#6c757d" />
                <Tooltip
                  contentStyle={{
                    background: "#fff",
                    border: "1px solid #dee2e6",
                    borderRadius: 8,
                  }}
                />
                <Legend onClick={tuningLegend.onLegendClick} />
                <Bar dataKey="baseline" name="Baseline F1" fill="#6c757d" radius={[4, 4, 0, 0]} hide={!!tuningLegend.hidden.baseline} />
                <Bar dataKey="tuned" name="Tuned F1" fill="#007bff" radius={[4, 4, 0, 0]} hide={!!tuningLegend.hidden.tuned} />
              </BarChart>
            </ResponsiveContainer>
            <table className="metrics-table" style={{ marginTop: 14 }}>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Baseline F1</th>
                  <th>Tuned F1</th>
                  <th>Δ F1</th>
                </tr>
              </thead>
              <tbody>
                {tuningRows.map((t) => (
                  <tr key={t.model}>
                    <td>{t.label}</td>
                    <td className="mono">{t.baseline.toFixed(4)}</td>
                    <td className="mono">{t.tuned.toFixed(4)}</td>
                    <td className={`mono ${t.delta >= 0 ? "good" : "bad"}`}>
                      {t.delta >= 0 ? "+" : ""}
                      {t.delta.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="small muted" style={{ marginTop: 10 }}>
              Honest result: tuning helps XGBoost and Logistic Regression but can
              leave Decision Tree / Random Forest roughly unchanged — their
              defaults are already strong.
            </p>
          </div>
        )}

        <div className="panel" style={{ gridColumn: "1 / -1" }}>
          <div className="curve-head">
            <h3>Training insights &amp; development progression</h3>
            <div className="curve-toggles">
              <Seg
                options={[
                  { value: "nslkdd", label: "NSL-KDD" },
                  { value: "cicids", label: "CICIDS2017" },
                  { value: "both", label: "Compare both" },
                ]}
                value={insightsMode}
                onChange={setInsightsMode}
              />
            </div>
          </div>
          <p className="chart-title">
            Real convergence/behaviour curves collected during Phase 3 training,
            redrawn interactively from the logged data — hover any line for the
            exact values, click a legend entry to hide a series, and the dashed
            line marks the setting the saved model actually uses.
          </p>
          {curves && saved ? (
            <div className="curve-grid">
              <XgbLossChart curves={curves} saved={saved} mode={insightsMode} />
              <RandomForestChart curves={curves} saved={saved} mode={insightsMode} />
              <DecisionTreeChart curves={curves} saved={saved} mode={insightsMode} />
              <LogisticChart curves={curves} saved={saved} mode={insightsMode} />
              {progression && (
                <div style={{ gridColumn: "1 / -1" }}>
                  <ProgressionChart progression={progression} mode={insightsMode} />
                  <p className="small muted" style={{ marginTop: 10 }}>
                    A = raw features · B = + cleaning/scaling/encoding · C = +
                    aggressive consensus feature selection (hurts LR — too few
                    features) · D = + SMOTE · E = + grid-search tuning. Most of
                    the lift comes from cleaning + balancing.
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="muted">Training curves could not be loaded.</p>
          )}
        </div>
      </div>
    </div>
  );
}
