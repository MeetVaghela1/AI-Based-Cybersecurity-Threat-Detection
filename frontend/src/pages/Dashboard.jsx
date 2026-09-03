import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import StatusPill from "../components/StatusPill.jsx";
import AttackCard from "../components/AttackCard.jsx";
import DetectionExplain from "../components/DetectionExplain.jsx";
import HelpTip from "../components/HelpTip.jsx";
import { useMonitor } from "../components/MonitorContext.jsx";

const DATASET_LABELS = { nslkdd: "NSL-KDD", cicids: "CICIDS2017" };
const MODEL_LABELS = {
  xgboost: "XGBoost",
  random_forest: "Random Forest",
  decision_tree: "Decision Tree",
  logistic: "Logistic Regression",
};

/**
 * Dashboard — the "live" traffic monitor.
 *
 * The stream itself lives in MonitorContext, so it keeps running no matter
 * which tab you are on.  Every ~1.6s the backend is asked to POST /simulate:
 * replay a handful of rows from the recorded test set and classify them with
 * the chosen model.  Packets stream into the list and any attack is flagged
 * with a red banner and an explainer card.  All of this is a *simulated replay
 * of dataset traffic* for demonstration — it is not live packet capture.
 */
export default function Dashboard({ onStartTour }) {
  const { dataset, setDataset, model, setModel, running, start, stop, packets, error, log } =
    useMonitor();
  const [selectedAttack, setSelectedAttack] = useState(null);
  const [selectedPacket, setSelectedPacket] = useState(null);
  const [attackInfo, setAttackInfo] = useState(null);
  const [loadingInfo, setLoadingInfo] = useState(false);

  const attackInfoCache = useRef({});
  const lastAuto = useRef(null);

  // Fetch the explanation for a flagged attack (cached so we don't spam).
  const ensureAttackInfo = async (attack) => {
    if (attackInfoCache.current[attack]) {
      setAttackInfo(attackInfoCache.current[attack]);
      return;
    }
    setLoadingInfo(true);
    try {
      const info = await api.attackInfo(attack);
      attackInfoCache.current[attack] = info;
      setAttackInfo(info);
    } catch {
      setAttackInfo(null);
    } finally {
      setLoadingInfo(false);
    }
  };

  // Clicking a packet (or a new alert arriving) opens its explainer card.
  const selectAttack = (attack) => {
    setSelectedAttack(attack);
    ensureAttackInfo(attack);
  };

  // Clicking ANY packet opens the plain-language "what just happened" view.
  const selectPacket = (p) => {
    setSelectedPacket(p);
    if (p.is_attack) {
      selectAttack(p.prediction);
    } else {
      setSelectedAttack(null);
      setAttackInfo(null);
    }
  };

  // Auto-open the explainer when a NEW attack arrives in the stream (each
  // attack row has a unique seq, so this only fires once per row).
  useEffect(() => {
    const top = packets[0];
    if (top && top.is_attack && top.seq !== lastAuto.current) {
      lastAuto.current = top.seq;
      selectAttack(top.prediction);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [packets]);

  const latest = packets[0] || null;
  const attacks = packets.filter((p) => p.is_attack).length;
  const normal = packets.length - attacks;

  return (
    <div>
      <div className="grid grid-2">
        {/* ------------------------- controls ------------------------- */}
        <div className="panel">
          <h2>Traffic monitor</h2>
          <p className="small muted" style={{ marginTop: 0 }}>
            Streams classified rows from the test set — a replay for
            demonstration, not live network capture.
          </p>

          <div className="field">
            <label htmlFor="ds">
              Dataset
              <HelpTip
                text="Which benchmark dataset to replay. NSL-KDD (5 classes) is the classic
                one; CICIDS2017 (9 classes) is the modern benchmark."
              />
            </label>
            <select id="ds" value={dataset} onChange={(e) => setDataset(e.target.value)}>
              <option value="nslkdd">NSL-KDD</option>
              <option value="cicids">CICIDS2017</option>
            </select>
          </div>

          <div className="field">
            <label htmlFor="md">
              Model
              <HelpTip
                text="Which classifier runs on the stream. XGBoost is the strongest overall;
                the Decision Tree is easiest to read when explaining an alert."
              />
            </label>
            <select id="md" value={model} onChange={(e) => setModel(e.target.value)}>
              <option value="xgboost">XGBoost</option>
              <option value="random_forest">Random Forest</option>
              <option value="decision_tree">Decision Tree</option>
              <option value="logistic">Logistic Regression</option>
            </select>
          </div>

          {!running ? (
            <button className="primary" onClick={start} style={{ width: "100%" }}>
              ▶ Start monitoring
            </button>
          ) : (
            <button className="primary" onClick={stop} style={{ width: "100%" }}>
              ■ Stop
            </button>
          )}

          {error && <div className="error-box" style={{ marginTop: 14 }}>{error}</div>}
        </div>

        {/* ------------------------- status + stream ------------------ */}
        <div>
          {latest ? (
            <div className={`status-banner ${latest.is_attack ? "attack" : "normal"}`}>
              <span className="status-dot" />
              {latest.is_attack
                ? `ATTACK DETECTED — ${latest.prediction}`
                : "ALL CLEAR — traffic looks normal"}
              <span style={{ marginLeft: "auto", fontSize: 13, fontWeight: 500 }}>
                {latest.time}
              </span>
            </div>
          ) : (
            <div className="status-banner normal">
              <span className="status-dot" />
              {running ? "Streaming…" : "Standby — press Start monitoring"}
            </div>
          )}

          <div className="stats">
            <div className="stat normal">
              <div className="stat-value">{normal}</div>
              <div className="stat-label">
                normal
                <HelpTip text="Flows where the model judged the connection benign." />
              </div>
            </div>
            <div className="stat attack">
              <div className="stat-value">{attacks}</div>
              <div className="stat-label">
                attacks caught
                <HelpTip text="Flows the model classified as an attack class." />
              </div>
            </div>
            <div className="stat">
              <div className="stat-value">{packets.length}</div>
              <div className="stat-label">
                flows shown
                <HelpTip text="How many of the most recent flows are visible (max 28)." />
              </div>
            </div>
          </div>

          <div className="panel" style={{ padding: 12 }}>
            {packets.length === 0 && !running && (
              <div className="empty-state">
                <svg
                  viewBox="0 0 24 24"
                  width="44"
                  height="44"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 2l8 3v6c0 5-3.5 9.5-8 11-4.5-1.5-8-6-8-11V5l8-3z" />
                  <path d="M9 12l2 2 4-4" />
                </svg>
                <h3>Your traffic monitor is standing by</h3>
                <p>
                  This replays <b>recorded dataset traffic</b> through the
                  chosen model — not live network capture. Pick a dataset and a
                  model above, then press{" "}
                  <button className="link-inline" onClick={start}>
                    Start monitoring
                  </button>{" "}
                  to watch connections stream in. Attacks light up red and are
                  clickable for a plain-language explanation.
                </p>
                <div className="empty-actions">
                  <button className="primary" onClick={start}>
                    ▶ Start monitoring
                  </button>
                  {onStartTour && (
                    <button className="ghost" onClick={onStartTour}>
                      Take the guided tour
                    </button>
                  )}
                </div>
              </div>
            )}
            {packets.length === 0 && running && (
              <div className="loading">Waiting for simulated traffic…</div>
            )}
            <div className="packet-list">
              {packets.map((p) => (
                <div
                  key={p.seq}
                  className={`packet ${p.is_attack ? "attack-row" : "normal-row"}`}
                  style={{ cursor: "pointer" }}
                  onClick={() => selectPacket(p)}
                  title="click to see why the model decided this"
                >
                  <span className="muted">{p.time}</span>
                  <span className="muted small">#{p.seq}</span>
                  <span className="mono">
                    {p.is_attack ? (
                      <StatusPill kind="attack">{p.prediction}</StatusPill>
                    ) : (
                      <StatusPill kind="normal">Normal</StatusPill>
                    )}
                  </span>
                  <div className="confidence-track" title={`confidence ${p.confidence}`}>
                    <div
                      className="confidence-fill"
                      style={{ width: `${Math.round(p.confidence * 100)}%` }}
                    />
                  </div>
                  <span className="small muted">
                    {p.matched ? "correct" : "wrong"}
                    {p.true_label ? ` · ${p.true_label}` : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* ---------------- stored prediction log (database) ------------- */}
          <div className="panel" style={{ marginTop: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h3 style={{ margin: 0 }}>Stored prediction log</h3>
              <span className="small muted">({log.count} records)</span>
            </div>
            <p className="small muted" style={{ marginTop: 6 }}>
              Every flow the monitor classifies is saved to the server-side
              database ({" "}
              <span className="mono">data/processed/prediction_log.json</span>
              ), newest first.
            </p>
            {log.items.length === 0 ? (
              <div className="muted small" style={{ padding: "14px 0" }}>
                No predictions recorded yet — start monitoring to fill the log.
              </div>
            ) : (
              <div style={{ maxHeight: 300, overflowY: "auto", marginTop: 8 }}>
                <table className="metrics-table log-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>#</th>
                      <th>Dataset</th>
                      <th>Model</th>
                      <th>Prediction</th>
                      <th>Conf</th>
                      <th>True label</th>
                      <th>Correct</th>
                    </tr>
                  </thead>
                  <tbody>
                    {log.items.slice(0, 60).map((e) => (
                      <tr key={e.seq}>
                        <td className="mono small">{e.time}</td>
                        <td className="mono small">{e.seq}</td>
                        <td>{DATASET_LABELS[e.dataset] ?? e.dataset}</td>
                        <td>{MODEL_LABELS[e.model] ?? e.model}</td>
                        <td>
                          {e.is_attack ? (
                            <StatusPill kind="attack">{e.prediction}</StatusPill>
                          ) : (
                            <StatusPill kind="normal">Normal</StatusPill>
                          )}
                        </td>
                        <td className="mono small">
                          {Math.round(e.confidence * 100)}%
                        </td>
                        <td className="small">{e.true_label ?? "—"}</td>
                        <td
                          className={`small ${
                            e.matched === true
                              ? "good"
                              : e.matched === false
                                ? "bad"
                                : "muted"
                          }`}
                        >
                          {e.matched === true
                            ? "correct"
                            : e.matched === false
                              ? "wrong"
                              : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ------------------- "how to read this page" ------------------- */}
      <div className="panel howto" style={{ marginTop: 18 }}>
        <details open>
          <summary>How to read this monitor (no technical background needed)</summary>
          <ol className="howto-list">
            <li>
              <strong>Each row is one connection</strong> ("flow") from the
              dataset, replayed for the demo. It is <em>not</em> your real
              network traffic.
            </li>
            <li>
              <strong>Numbers, not pictures.</strong> The model can't "see" an
              attack. Each connection is first turned into numbers — packet
              sizes, duration, byte counts ({dataset === "nslkdd" ? "41" : "78"}{" "}
              features).
            </li>
            <li>
              <strong>The model compares.</strong> It holds the patterns it
              learned from {DATASET_LABELS[dataset].toUpperCase()} during
              training (tens of thousands of labelled examples) and checks how
              closely this connection matches each pattern.
            </li>
            <li>
              <strong>It votes with percentages.</strong> The model gives every
              category a score; the highest score wins. The{" "}
              <strong>confidence bar</strong> shows how sure it is.
            </li>
            <li>
              <strong>Read the counters.</strong>{" "}
              <em>normal</em> = flows where "Normal" won;{" "}
              <em>attacks caught</em> = flows where an attack class won;{" "}
              <em>flows shown</em> = the recent window you can see (max 28).
            </li>
            <li>
              <strong>Correct / wrong</strong> compares the prediction to the
              label already recorded in the dataset (the dataset is our "answer
              key"), so you can see when the model gets it right.
            </li>
            <li>
              <strong>Click any row</strong> to see exactly what the model was
              thinking, and what that attack actually does.
            </li>
            <li>
              <strong>Everything is also logged.</strong> Below the stream, the
              "Stored prediction log" panel lists every flow the monitor
              classified — saved on the server as a small JSON database so it
              survives a restart.
            </li>
          </ol>
        </details>
      </div>

      {/* ------------------- per-packet explainer ---------------------- */}
      {selectedPacket && (
        <div style={{ marginTop: 18 }}>
          <DetectionExplain
            packet={selectedPacket}
            datasetLabel={DATASET_LABELS[dataset]}
            modelLabel={MODEL_LABELS[model]}
          />
          {selectedAttack && (
            <div style={{ marginTop: 12 }}>
              <AttackCard
                attack={selectedAttack}
                info={attackInfo}
                expanded={true}
                onToggle={() => {
                  setSelectedAttack(null);
                  setAttackInfo(null);
                  setSelectedPacket(null);
                }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
