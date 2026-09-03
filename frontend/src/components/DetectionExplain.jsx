import React from "react";
import StatusPill from "./StatusPill.jsx";

/**
 * DetectionExplain — turns ONE prediction into plain language for a
 * non-technical viewer:
 *   * what the model looked at,
 *   * the probabilities it considered (top 3),
 *   * a plain-English "what just happened" sentence,
 *   * whether the model matched the dataset's recorded truth.
 */
export default function DetectionExplain({ packet, datasetLabel, modelLabel }) {
  if (!packet) return null;

  const probEntries = Object.entries(packet.probabilities || {});
  const sorted = probEntries.sort((a, b) => b[1] - a[1]);
  const top = sorted.slice(0, 3);
  const winner = sorted[0];
  const winnerName = winner ? winner[0] : packet.prediction;
  const winnerPct = winner ? Math.round(winner[1] * 100) : Math.round(packet.confidence * 100);

  const story = packet.is_attack
    ? `The ${modelLabel} model looked at the numbers describing this connection, compared them with the patterns it learned from ${datasetLabel} during training, and was ${winnerPct}% sure this is a ${packet.prediction}.`
    : `The ${modelLabel} model looked at the numbers describing this connection and was ${winnerPct}% sure it is normal traffic — none of the attack patterns it learned from ${datasetLabel} matched strongly enough.`;

  return (
    <div className="explain-card">
      <h3>Why the model made this call</h3>

      <div className="explain-verdict">
        <StatusPill kind={packet.is_attack ? "attack" : "normal"}>
          {packet.is_attack ? packet.prediction : "Normal"}
        </StatusPill>
        <span className="small muted">
          confidence {winnerPct}% · model {modelLabel} · {datasetLabel}
        </span>
      </div>

      <p className="explain-story">{story}</p>

      <div className="section">
        <strong>The model's thinking — its top {top.length} choices</strong>
        <div className="prob-list">
          {top.map(([name, prob]) => (
            <div key={name} className="prob-row">
              <span className="prob-name">{name}</span>
              <div className="confidence-track prob-track">
                <div
                  className={`confidence-fill ${
                    name === winnerName ? (packet.is_attack ? "attack" : "normal") : ""
                  }`}
                  style={{ width: `${Math.max(Math.round(prob * 100), 1)}%` }}
                />
              </div>
              <span className="prob-value">{(prob * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
        <p className="small muted" style={{ margin: "8px 0 0" }}>
          The model does not see an attack or a label — it only sees numbers,
          and each number is the model's "guess score" for that category. The
          highest score wins.
        </p>
      </div>

      <div className="section">
        <strong>Was it right?</strong>
        <p className="small" style={{ margin: "4px 0 0" }}>
          {packet.matched
            ? "Yes — this prediction matches the label recorded in the original dataset."
            : `No — the dataset says the true label was "${packet.true_label}". No model is perfect.`}
        </p>
      </div>
    </div>
  );
}
