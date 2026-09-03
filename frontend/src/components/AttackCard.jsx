import React from "react";
import StatusPill from "./StatusPill.jsx";

/**
 * An expandable card explaining an attack type in plain language.
 * Content comes from the backend's GET /attack-info/{type} endpoint.
 */
export default function AttackCard({ attack, info, expanded, onToggle }) {
  return (
    <div
      className={`attack-card ${expanded ? "expanded" : ""}`}
      onClick={() => onToggle(expanded ? null : attack)}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <StatusPill kind="attack">{attack}</StatusPill>
        <span className="small muted">
          {expanded ? "click to collapse" : "click for details"}
        </span>
      </div>

      {info && (
        <div style={{ marginTop: 10 }}>
          <h4>{info.name}</h4>
          <p style={{ margin: "6px 0" }}>{info.description}</p>

          {expanded && (
            <>
              <div className="section">
                <strong>How it works</strong>
                <p style={{ margin: "4px 0" }}>{info.how_it_works}</p>
              </div>
              <div className="section">
                <strong>What to look for</strong>
                <p style={{ margin: "4px 0" }}>{info.indicators}</p>
              </div>
              <div className="section">
                <strong>Real-world impact</strong>
                <p style={{ margin: "4px 0" }}>{info.impact}</p>
              </div>
              <div className="section">
                <strong>How it is defended</strong>
                <p style={{ margin: "4px 0" }}>{info.defense}</p>
              </div>
              <div className="section">
                <strong>Example</strong>
                <p style={{ margin: "4px 0" }}>{info.example}</p>
              </div>
            </>
          )}
        </div>
      )}

      {!info && (
        <p className="small muted" style={{ margin: "10px 0 0" }}>
          Loading explanation…
        </p>
      )}
    </div>
  );
}
