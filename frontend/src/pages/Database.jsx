// Database.jsx — the "database" tab.  Shows every prediction the monitor has
// stored on the server (GET /predictions, persisted to
// data/processed/prediction_log.json).  Polls every 2s so it stays live while
// monitoring runs on any tab.
import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import StatusPill from "../components/StatusPill.jsx";
import HelpTip from "../components/HelpTip.jsx";

const DATASET_LABEL = { nslkdd: "NSL-KDD", cicids: "CICIDS2017" };
const MODEL_LABEL = {
  xgboost: "XGBoost",
  random_forest: "Random Forest",
  decision_tree: "Decision Tree",
  logistic: "Logistic Regression",
};

// Latency in milliseconds with a plain "ms" unit — friendlier than µs.
const fmtMs = (v) =>
  v === null || v === undefined ? "—" : `${Number(v.toPrecision(3))} ms`;

export default function Database() {
  const [log, setLog] = useState({ count: 0, items: [] });
  const [dsFilter, setDsFilter] = useState("all");
  const [verdictFilter, setVerdictFilter] = useState("all");
  const [limit, setLimit] = useState(15);

  useEffect(() => {
    let alive = true;
    const refresh = async () => {
      try {
        const d = await api.predictions();
        if (alive) setLog(d);
      } catch {
        /* backend not running — keep the last data */
      }
    };
    refresh();
    const id = setInterval(refresh, 2000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const filtered = useMemo(() => {
    return (log.items || []).filter((e) => {
      if (dsFilter !== "all" && e.dataset !== dsFilter) return false;
      if (verdictFilter !== "all" && e.is_attack !== (verdictFilter === "attack")) return false;
      return true;
    });
  }, [log, dsFilter, verdictFilter]);

  const rows = useMemo(() => filtered.slice(0, limit), [filtered, limit]);

  const stats = useMemo(() => {
    const items = log.items || [];
    const attacks = items.filter((e) => e.is_attack).length;
    const confs = items.map((e) => e.confidence).filter((c) => typeof c === "number");
    const lat = items
      .map((e) => e.latency_ms)
      .filter((l) => typeof l === "number" && l !== null);
    return {
      total: items.length,
      attacks,
      normal: items.length - attacks,
      avgConf: confs.length ? confs.reduce((a, b) => a + b, 0) / confs.length : null,
      avgLat: lat.length ? lat.reduce((a, b) => a + b, 0) / lat.length : null,
    };
  }, [log]);

  return (
    <div>
      <div className="panel">
        <h2>Prediction database</h2>
        <p className="small muted" style={{ marginTop: 0 }}>
          Every flow the monitor classifies is stored here — the same data the
          Live Monitor keeps in memory, but persisted by the backend. The
          newest entries are on top.
        </p>
        <div className="stat-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.total}</div>
            <div className="stat-label">stored records</div>
          </div>
          <div className="stat-card">
            <div className="stat-value stat-attack">{stats.attacks}</div>
            <div className="stat-label">attacks flagged</div>
          </div>
          <div className="stat-card">
            <div className="stat-value stat-normal">{stats.normal}</div>
            <div className="stat-label">normal flows</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">
              {stats.avgConf !== null ? `${(stats.avgConf * 100).toFixed(0)}%` : "—"}
            </div>
            <div className="stat-label">avg confidence</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{fmtMs(stats.avgLat)}</div>
            <div className="stat-label">avg live latency</div>
          </div>
        </div>
      </div>

      <div className="panel">
        <h3>About this database</h3>
        <div className="about-grid">
          <div className="about-card">
            <div className="about-title">Persistent storage</div>
            Saved on the server at{" "}
            <span className="mono">data/processed/prediction_log.json</span> —
            it survives restarts.
          </div>
          <div className="about-card">
            <div className="about-title">Keeps the newest 200</div>
            Records are trimmed to the most recent 200, dropping the oldest.
          </div>
          <div className="about-card">
            <div className="about-title">Written on every batch</div>
            One record is added for each batch of flows the monitor simulates (
            <span className="mono">POST /simulate</span>).
          </div>
          <div className="about-card">
            <div className="about-title">Powers live latency</div>
            Latency is measured on the server while the monitor runs, so the{" "}
            <span className="mono">Compare</span> page can show live numbers
            next to the recorded test-set speeds.
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="filter-row">
          <label>
            Dataset
            <select value={dsFilter} onChange={(e) => setDsFilter(e.target.value)}>
              <option value="all">All datasets</option>
              <option value="nslkdd">NSL-KDD</option>
              <option value="cicids">CICIDS2017</option>
            </select>
          </label>
          <label>
            Verdict
            <select value={verdictFilter} onChange={(e) => setVerdictFilter(e.target.value)}>
              <option value="all">All verdicts</option>
              <option value="attack">Attack</option>
              <option value="normal">Normal</option>
            </select>
          </label>
          <label>
            Show rows
            <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              <option value={15}>15</option>
              <option value={20}>20</option>
              <option value={30}>30</option>
            </select>
          </label>
          <span className="muted" style={{ flex: 1, fontSize: 13 }}>
            Showing {rows.length} of {filtered.length} matching records
          </span>
          <HelpTip text="Filters only change what this page shows — the stored database keeps everything." />
        </div>

        <table className="metrics-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>#</th>
              <th>Dataset</th>
              <th>Model</th>
              <th>Prediction</th>
              <th>Confidence</th>
              <th>Latency</th>
              <th>True label</th>
              <th>Correct</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => (
              <tr key={e.seq}>
                <td className="mono">{e.time}</td>
                <td className="mono">{e.seq}</td>
                <td>{DATASET_LABEL[e.dataset] || e.dataset}</td>
                <td>{MODEL_LABEL[e.model] || e.model}</td>
                <td>
                  {e.is_attack ? (
                    <StatusPill kind="attack">{e.prediction}</StatusPill>
                  ) : (
                    <StatusPill kind="normal">Normal</StatusPill>
                  )}
                </td>
                <td className="mono">{(e.confidence * 100).toFixed(1)}%</td>
                <td className="mono">{fmtMs(e.latency_ms)}</td>
                <td>{e.true_label ?? "—"}</td>
                <td>
                  {e.matched === null || e.matched === undefined ? (
                    "—"
                  ) : e.matched ? (
                    <span className="tag tag-ok">Yes</span>
                  ) : (
                    <span className="tag tag-bad">No</span>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan="9" className="empty-cell">
                  No records yet. Start monitoring on the Live Monitor tab and
                  every classified flow will appear here.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
