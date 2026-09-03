// TrainingCharts.jsx — interactive versions of the Phase 3 training curves
// (XGBoost rounds, Random Forest trees, Decision Tree depth, Logistic
// Regression iterations) and the A->E development progression.
//
// Every chart gets:
//   * a hover tooltip with the exact values at that point,
//   * a dashed reference line at the configuration the SAVED model uses,
//   * a true numeric x-axis (no equal-spacing distortion),
//   * a "Compare Both" overlay mode (NSL-KDD solid, CICIDS2017 dashed),
//   * a small "i" plain-language hint,
//   * a clickable legend that shows/hides each series.
//
// Chart-specific extras:
//   * XGBoost: log-scale toggle for the loss y-axis + train/val gap in tooltip
//   * Random Forest: error-rate <-> accuracy toggle
//   * Decision Tree: red band over the overfitting depth range
//   * Logistic: log-scale toggle for the iterations x-axis (max_iter budget)
//   * Progression: F1 value labels on every point + per-stage delta labels
import React, { useMemo, useState } from "react";
import {
  CartesianGrid,
  ComposedChart,
  LabelList,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import HelpTip from "./HelpTip.jsx";

const DS = { nslkdd: "NSL-KDD", cicids: "CICIDS2017" };
const DS_COLOR = { nslkdd: "#007bff", cicids: "#fd7e14" };
const TT_STYLE = {
  background: "#fff",
  border: "1px solid #dee2e6",
  borderRadius: 8,
  fontSize: 13,
  color: "#212529",
};

// One-sentence plain-language explanations for the "i" icons.
const INFO = {
  xgb: "Shows training vs validation loss across boosting rounds — the gap "
    + "widening at the end is the overfitting signal.",
  rf: "Shows how quickly adding more trees cuts the error rate — a handful "
    + "of trees already do most of the work.",
  dt: "Shows training vs validation accuracy as the tree may grow deeper — "
    + "the red band is where it starts to overfit.",
  lr: "Shows how quickly logistic regression's loss converges as it is "
    + "allowed more iterations.",
  prog: "Shows how the model's F1 score improved as the pipeline grew step "
    + "by step from raw data to the final tuned model.",
};

const STAGE_NOTES = [
  "Raw features — no cleaning, no scaling, no balancing. Baseline.",
  "Cleaning, scaling and encoding — usually the single biggest jump.",
  "Aggressive consensus feature selection hurt logistic regression — too few "
    + "features were kept.",
  "SMOTE class balancing recovers most of the ground lost at step C.",
  "Grid-search tuning on top of the balanced pipeline adds a final nudge.",
];

const fmtDelta = (d) =>
  Math.abs(d) < 0.0005 ? "0.00" : `${d > 0 ? "+" : ""}${d.toFixed(2)}`;

/**
 * Label object for a reference-line annotation. The x is anchored to the line
 * itself ('100%' of the line's zero-width rect) with the text extending to the
 * left. The y is a negative pixel offset measured UP from the top edge of the
 * plotting area, so the label renders as a caption in the top margin — fully
 * above the plot (clear of the data lines and shaded regions), yet still
 * sitting directly over the dashed line it labels. `yPx` staggers datasets
 * vertically when two reference lines share a chart. The chart's top margin
 * must be large enough to hold the label(s) without clipping.
 */
const refLineLabel = (text, color, yPx) => ({
  value: text,
  position: { x: "100%", y: yPx },
  fill: color,
  fontSize: 11,
  fontWeight: 600,
});

// Caption rows sit in the top margin, above the plotting area. `Y_ROW_1` is
// the lower row (closer to the plot), `Y_ROW_2` the upper one. Both are
// negative pixels measured from the plot's top edge; the top margin must clear
// the highest row plus the label's own height (~13px at fontSize 11).
const Y_ROW_1 = -18;
const Y_ROW_2 = -42;
// Top margin shared by every chart that shows a reference-line caption.
const REF_LINE_TOP = 58;

// ---------------------------------------------------------------------------
// Small building blocks
// ---------------------------------------------------------------------------

/** A tiny segmented toggle (e.g. "Error rate | Accuracy"). */
export function Seg({ options, value, onChange }) {
  return (
    <div className="seg">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          className={`seg-btn ${value === o.value ? "on" : ""}`}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Clickable-legend state: clicking a legend item hides/shows its series. */
function useLegendToggle() {
  const [hidden, setHidden] = useState({});
  const onLegendClick = (entry) =>
    setHidden((h) => ({ ...h, [entry.dataKey || entry.value]: !h[entry.dataKey || entry.value] }));
  return { hidden, onLegendClick };
}

/** The shared card shell: title + toggles + "i" info + caption + chart. */
function ChartCard({ title, info, toggles, caption, children }) {
  return (
    <div className="curve-card">
      <div className="curve-head">
        <h4 className="curve-title">{title}</h4>
        <div className="curve-toggles">
          {toggles}
          <HelpTip glyph="i" text={info} />
        </div>
      </div>
      {caption && <p className="chart-title">{caption}</p>}
      {children}
    </div>
  );
}

/** Tooltip row used by the loss charts (train / validation / gap). */
function LossTip({ active, payload, label, xLabel }) {
  if (!active || !payload || !payload.length) return null;
  const p0 = payload[0].payload;
  const keys = payload.map((p) => p.dataKey);
  const datasets =
    keys[0].includes(".") ? [...new Set(keys.map((k) => k.split(".")[0]))] : ["single"];

  const rows = [];
  if (datasets.length === 1 && datasets[0] === "single") {
    rows.push(
      { color: "#007bff", name: "train loss", value: p0.train_loss },
      { color: "#fd7e14", name: "validation loss", value: p0.val_loss },
      { color: "#6c757d", name: "gap (overfit signal)", value: p0.train_loss - p0.val_loss }
    );
  } else {
    datasets.forEach((ds) => {
      const train = p0[`${ds}.train_loss`];
      if (train == null) return;
      rows.push(
        { color: DS_COLOR[ds], name: `${DS[ds]} train`, value: train },
        { color: DS_COLOR[ds], name: `${DS[ds]} validation`, value: p0[`${ds}.val_loss`] },
        { color: "#6c757d", name: `${DS[ds]} gap`, value: train - p0[`${ds}.val_loss`] }
      );
    });
  }
  return (
    <div className="chart-tip">
      <div className="chart-tip-title">
        {xLabel}: {label}
      </div>
      {rows.map((r, i) => (
        <div className="chart-tip-row" key={i}>
          <span className="chart-tip-dot" style={{ background: r.color }} />
          <span>{r.name}:</span>
          <b>{Number(r.value).toFixed(4)}</b>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 1. XGBoost boosting rounds (train vs validation loss)
// ---------------------------------------------------------------------------
export function XgbLossChart({ curves, saved, mode }) {
  const [logY, setLogY] = useState(false);
  const { hidden, onLegendClick } = useLegendToggle();
  const dsName = mode === "both" ? "both datasets" : DS[mode];

  const data = useMemo(() => {
    if (mode === "both") {
      const map = new Map();
      Object.keys(curves).forEach((d) => {
        curves[d].xgb_loss.round.forEach((x, i) => {
          const p = map.get(x) || { x };
          p[`${d}.train_loss`] = curves[d].xgb_loss.train_loss[i];
          p[`${d}.val_loss`] = curves[d].xgb_loss.val_loss[i];
          map.set(x, p);
        });
      });
      return [...map.values()].sort((a, b) => a.x - b.x);
    }
    const c = curves[mode].xgb_loss;
    return c.round.map((x, i) => ({
      x,
      train_loss: c.train_loss[i],
      val_loss: c.val_loss[i],
    }));
  }, [curves, mode]);

  const series = useMemo(() => {
    if (mode === "both")
      return [
        { key: "nslkdd.train_loss", name: "NSL-KDD train", color: DS_COLOR.nslkdd },
        { key: "nslkdd.val_loss", name: "NSL-KDD validation", color: DS_COLOR.nslkdd, dash: "6 4" },
        { key: "cicids.train_loss", name: "CICIDS2017 train", color: DS_COLOR.cicids },
        { key: "cicids.val_loss", name: "CICIDS2017 validation", color: DS_COLOR.cicids, dash: "6 4" },
      ];
    return [
      { key: "train_loss", name: "Train loss", color: "#007bff" },
      { key: "val_loss", name: "Validation loss", color: "#fd7e14" },
    ];
  }, [mode]);

  const refLines = useMemo(() => {
    if (mode === "both")
      return [
        { x: saved.nslkdd.xgboost.rounds, color: DS_COLOR.nslkdd, label: `NSL-KDD saved: ${saved.nslkdd.xgboost.rounds} rounds`, y: Y_ROW_1 },
        { x: saved.cicids.xgboost.rounds, color: DS_COLOR.cicids, label: `CICIDS2017 saved: ${saved.cicids.xgboost.rounds} rounds`, y: Y_ROW_2 },
      ];
    const r = saved[mode].xgboost.rounds;
    return [{ x: r, color: "#6c757d", label: `saved model: ${r} rounds`, y: Y_ROW_1 }];
  }, [mode, saved]);

  return (
    <ChartCard
      title={`XGBoost boosting rounds — ${dsName}`}
      info={INFO.xgb}
      caption="Validation loss falls steeply then flattens — the tuned model uses 100–200 rounds."
      toggles={
        <Seg
          options={[
            { value: false, label: "linear" },
            { value: true, label: "log scale" },
          ]}
          value={logY}
          onChange={setLogY}
        />
      }
    >
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: REF_LINE_TOP, right: 14, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
          <XAxis dataKey="x" type="number" domain={[0, "dataMax"]} stroke="#6c757d" tick={{ fontSize: 11 }} />
          <YAxis
            scale={logY ? "log" : "auto"}
            domain={logY ? [0.0005, "dataMax"] : [0, "auto"]}
            stroke="#6c757d"
            tick={{ fontSize: 11 }}
            width={46}
          />
          <Tooltip content={<LossTip xLabel="Round" />} contentStyle={TT_STYLE} />
          <Legend onClick={onLegendClick} wrapperStyle={{ fontSize: 13 }} />
          {refLines.map((r) => (
            <ReferenceLine
              key={r.label}
              x={r.x}
              stroke={r.color}
              strokeDasharray="5 5"
              label={refLineLabel(r.label, r.color, r.y)}
            />
          ))}
          {series.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stroke={s.color}
              strokeWidth={2}
              strokeDasharray={s.dash}
              dot={false}
              hide={!!hidden[s.key]}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// ---------------------------------------------------------------------------
// 2. Random Forest tree count (error rate / accuracy)
// ---------------------------------------------------------------------------
export function RandomForestChart({ curves, saved, mode }) {
  const [yMode, setYMode] = useState("error");
  const { hidden, onLegendClick } = useLegendToggle();
  const dsName = mode === "both" ? "both datasets" : DS[mode];

  const data = useMemo(() => {
    const key = yMode === "error" ? "error_rate" : "accuracy";
    if (mode === "both") {
      const map = new Map();
      Object.keys(curves).forEach((d) => {
        curves[d].rf_error.trees.forEach((x, i) => {
          const p = map.get(x) || { x };
          p[`${d}.error_rate`] = curves[d].rf_error.error_rate[i];
          p[`${d}.f1_macro`] = curves[d].rf_error.f1_macro[i];
          map.set(x, p);
        });
      });
      return [...map.values()].sort((a, b) => a.x - b.x).map((p) => {
        Object.keys(curves).forEach((d) => {
          if (p[`${d}.error_rate`] != null) p[`${d}.accuracy`] = 1 - p[`${d}.error_rate`];
        });
        return p;
      });
    }
    const c = curves[mode].rf_error;
    return c.trees.map((x, i) => ({
      x,
      error_rate: c.error_rate[i],
      accuracy: 1 - c.error_rate[i],
      f1_macro: c.f1_macro[i],
    }));
  }, [curves, mode, yMode]);

  const dataKey = (d) => (mode === "both" ? `${d}.${yMode === "error" ? "error_rate" : "accuracy"}` : yMode === "error" ? "error_rate" : "accuracy");

  const series = useMemo(() => {
    const k = yMode === "error" ? "error_rate" : "accuracy";
    const label = yMode === "error" ? "Error rate" : "Accuracy (1 − error)";
    if (mode === "both")
      return [
        { key: `nslkdd.${k}`, name: `NSL-KDD ${label}`, color: DS_COLOR.nslkdd },
        { key: `cicids.${k}`, name: `CICIDS2017 ${label}`, color: DS_COLOR.cicids },
      ];
    return [{ key: k, name: label, color: "#007bff" }];
  }, [mode, yMode]);

  const refLines = useMemo(() => {
    if (mode === "both")
      return [
        { x: saved.nslkdd.random_forest.trees, color: DS_COLOR.nslkdd, label: `NSL-KDD saved: ${saved.nslkdd.random_forest.trees} trees`, y: Y_ROW_1 },
        { x: saved.cicids.random_forest.trees, color: DS_COLOR.cicids, label: `CICIDS2017 saved: ${saved.cicids.random_forest.trees} trees`, y: Y_ROW_2 },
      ];
    const t = saved[mode].random_forest.trees;
    return [{ x: t, color: "#6c757d", label: `saved model: ${t} trees`, y: Y_ROW_1 }];
  }, [mode, saved]);

  return (
    <ChartCard
      title={`Random forest tree count — ${dsName}`}
      info={INFO.rf}
      caption="Test error settles within ~30 trees; the saved model uses 100–200."
      toggles={
        <Seg
          options={[
            { value: "error", label: "error rate" },
            { value: "accuracy", label: "accuracy" },
          ]}
          value={yMode}
          onChange={setYMode}
        />
      }
    >
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: REF_LINE_TOP, right: 14, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
          <XAxis dataKey="x" type="number" domain={[0, "dataMax"]} stroke="#6c757d" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 1]} stroke="#6c757d" tick={{ fontSize: 11 }} width={46} />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload || !payload.length) return null;
              const p0 = payload[0].payload;
              const rows =
                mode === "both"
                  ? Object.keys(curves).map((d) => ({
                      color: DS_COLOR[d],
                      name: `${DS[d]} error rate`,
                      value: p0[`${d}.error_rate`],
                      f1: p0[`${d}.f1_macro`],
                    }))
                  : [{ color: "#007bff", name: "error rate", value: p0.error_rate, f1: p0.f1_macro }];
              return (
                <div className="chart-tip">
                  <div className="chart-tip-title">Trees: {label}</div>
                  {rows.map((r, i) => (
                    <div className="chart-tip-row" key={i}>
                      <span className="chart-tip-dot" style={{ background: r.color }} />
                      <span>{r.name}:</span>
                      <b>{Number(r.value).toFixed(4)}</b>
                    </div>
                  ))}
                  {rows.map((r, i) => (
                    <div className="chart-tip-row" key={`f1-${i}`}>
                      <span className="chart-tip-dot" style={{ background: "transparent" }} />
                      <span>{mode === "both" ? `${DS[mode]} ` : ""}accuracy: </span>
                      <b>{(1 - r.value).toFixed(4)}</b>
                    </div>
                  ))}
                  {rows.map((r, i) => (
                    <div className="chart-tip-row" key={`f1b-${i}`}>
                      <span className="chart-tip-dot" style={{ background: "transparent" }} />
                      <span>F1 (macro): </span>
                      <b>{r.f1.toFixed(4)}</b>
                    </div>
                  ))}
                </div>
              );
            }}
            contentStyle={TT_STYLE}
          />
          <Legend onClick={onLegendClick} wrapperStyle={{ fontSize: 13 }} />
          {refLines.map((r) => (
            <ReferenceLine
              key={r.label}
              x={r.x}
              stroke={r.color}
              strokeDasharray="5 5"
              label={refLineLabel(r.label, r.color, r.y)}
            />
          ))}
          {series.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stroke={s.color}
              strokeWidth={2}
              dot={false}
              hide={!!hidden[s.key]}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// ---------------------------------------------------------------------------
// 3. Decision Tree depth (overfitting view)
// ---------------------------------------------------------------------------
function overfitStart(points) {
  for (let i = 1; i < points.length - 1; i++) {
    let flat = true;
    for (let j = i; j < points.length - 1; j++) {
      if (points[j + 1].val - points[j].val >= 0.0015) {
        flat = false;
        break;
      }
    }
    if (flat) return points[i].x;
  }
  return null;
}

export function DecisionTreeChart({ curves, saved, mode }) {
  const { hidden, onLegendClick } = useLegendToggle();
  const dsName = mode === "both" ? "both datasets" : DS[mode];

  const data = useMemo(() => {
    if (mode === "both") {
      const map = new Map();
      Object.keys(curves).forEach((d) => {
        curves[d].dt_depth.max_depth.forEach((depth, i) => {
          const x = depth === "None" ? 30 : depth;
          const p = map.get(x) || { x };
          p[`${d}.train`] = curves[d].dt_depth.train_accuracy[i];
          p[`${d}.val`] = curves[d].dt_depth.val_accuracy[i];
          map.set(x, p);
        });
      });
      return [...map.values()].sort((a, b) => a.x - b.x);
    }
    const c = curves[mode].dt_depth;
    return c.max_depth.map((depth, i) => ({
      x: depth === "None" ? 30 : depth,
      train: c.train_accuracy[i],
      val: c.val_accuracy[i],
    }));
  }, [curves, mode]);

  const starts = useMemo(() => {
    if (mode === "both")
      return Object.keys(curves)
        .map((d) =>
          overfitStart(curves[d].dt_depth.max_depth.map((depth, i) => ({
            x: depth === "None" ? 30 : depth,
            val: curves[d].dt_depth.val_accuracy[i],
          })))
        )
        .filter((v) => v != null);
    const s = overfitStart(data);
    return s != null ? [s] : [];
  }, [curves, mode, data]);

  const series = useMemo(() => {
    if (mode === "both")
      return [
        { key: "nslkdd.train", name: "NSL-KDD train", color: DS_COLOR.nslkdd },
        { key: "nslkdd.val", name: "NSL-KDD validation", color: DS_COLOR.nslkdd, dash: "6 4" },
        { key: "cicids.train", name: "CICIDS2017 train", color: DS_COLOR.cicids },
        { key: "cicids.val", name: "CICIDS2017 validation", color: DS_COLOR.cicids, dash: "6 4" },
      ];
    return [
      { key: "train", name: "Train accuracy", color: "#007bff" },
      { key: "val", name: "Validation accuracy", color: "#fd7e14" },
    ];
  }, [mode]);

  const refLines = useMemo(() => {
    const mk = (d) => {
      const depth = saved[d].decision_tree.max_depth;
      if (depth === null)
        return { x: 30, color: DS_COLOR[d], label: `${DS[d]} saved: full tree (no depth limit)` };
      return { x: depth, color: DS_COLOR[d], label: `${DS[d]} saved: depth ${depth}` };
    };
    if (mode === "both")
      return [mk("nslkdd"), mk("cicids")].map((r, i) => ({ ...r, y: i === 0 ? Y_ROW_1 : Y_ROW_2 }));
    const depth = saved[mode].decision_tree.max_depth;
    return depth === null
      ? [{ x: 30, color: "#6c757d", label: "saved model: full tree (no depth limit)", y: Y_ROW_1 }]
      : [{ x: depth, color: "#6c757d", label: `saved model: depth ${depth}`, y: Y_ROW_1 }];
  }, [mode, saved]);

  return (
    <ChartCard
      title={`Decision tree depth — ${dsName}`}
      info={INFO.dt}
      caption="Accuracy plateaus around depth 15–20; deeper trees only memorise the training set."
    >
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: REF_LINE_TOP, right: 14, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
          <XAxis
            dataKey="x"
            type="number"
            domain={[0, 30]}
            ticks={[1, 2, 3, 5, 8, 10, 15, 20, 25, 30]}
            tickFormatter={(v) => (v >= 30 ? "None" : String(v))}
            stroke="#6c757d"
            tick={{ fontSize: 11 }}
          />
          <YAxis domain={[0, 1]} stroke="#6c757d" tick={{ fontSize: 11 }} width={46} />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload || !payload.length) return null;
              const p0 = payload[0].payload;
              const entries =
                mode === "both"
                  ? Object.keys(curves).map((d) => ({
                      color: DS_COLOR[d],
                      name: DS[d],
                      train: p0[`${d}.train`],
                      val: p0[`${d}.val`],
                    }))
                  : [{ color: "#007bff", name: DS[mode], train: p0.train, val: p0.val }];
              return (
                <div className="chart-tip">
                  <div className="chart-tip-title">
                    Max depth: {label >= 30 ? "None (unlimited)" : label}
                  </div>
                  {entries.map((e) => (
                    <div key={e.name}>
                      <div className="chart-tip-row">
                        <span className="chart-tip-dot" style={{ background: e.color }} />
                        <span>{e.name} train acc:</span>
                        <b>{e.train.toFixed(4)}</b>
                      </div>
                      <div className="chart-tip-row">
                        <span className="chart-tip-dot" style={{ background: e.color }} />
                        <span>{e.name} validation acc:</span>
                        <b>{e.val.toFixed(4)}</b>
                      </div>
                      <div className="chart-tip-row">
                        <span className="chart-tip-dot" style={{ background: "#6c757d" }} />
                        <span>gap (overfitting):</span>
                        <b>{(e.train - e.val).toFixed(4)}</b>
                      </div>
                    </div>
                  ))}
                </div>
              );
            }}
            contentStyle={TT_STYLE}
          />
          <Legend onClick={onLegendClick} wrapperStyle={{ fontSize: 13 }} />
          {starts.map((s, i) => (
            <ReferenceArea
              key={`of-${i}`}
              x1={s}
              x2={30}
              fill="#dc3545"
              fillOpacity={0.08}
              label={
                i === 0
                  ? { value: "overfitting", position: "center", fill: "#dc3545", fontSize: 11, fontWeight: 600 }
                  : undefined
              }
            />
          ))}
          {refLines.map((r) => (
            <ReferenceLine
              key={r.label}
              x={r.x}
              stroke={r.color}
              strokeDasharray="5 5"
              label={refLineLabel(r.label, r.color, r.y)}
            />
          ))}
          {series.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stroke={s.color}
              strokeWidth={2}
              strokeDasharray={s.dash}
              dot={false}
              hide={!!hidden[s.key]}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// ---------------------------------------------------------------------------
// 4. Logistic Regression iterations (convergence)
// ---------------------------------------------------------------------------
export function LogisticChart({ curves, saved, mode }) {
  const [xLog, setXLog] = useState(true);
  const { hidden, onLegendClick } = useLegendToggle();
  const dsName = mode === "both" ? "both datasets" : DS[mode];

  const data = useMemo(() => {
    if (mode === "both") {
      const map = new Map();
      Object.keys(curves).forEach((d) => {
        curves[d].lr_convergence.max_iter.forEach((x, i) => {
          const p = map.get(x) || { x };
          p[`${d}.train_loss`] = curves[d].lr_convergence.train_loss[i];
          p[`${d}.val_loss`] = curves[d].lr_convergence.val_loss[i];
          map.set(x, p);
        });
      });
      return [...map.values()].sort((a, b) => a.x - b.x);
    }
    const c = curves[mode].lr_convergence;
    return c.max_iter.map((x, i) => ({
      x,
      train_loss: c.train_loss[i],
      val_loss: c.val_loss[i],
    }));
  }, [curves, mode]);

  const series = useMemo(() => {
    if (mode === "both")
      return [
        { key: "nslkdd.train_loss", name: "NSL-KDD train", color: DS_COLOR.nslkdd },
        { key: "nslkdd.val_loss", name: "NSL-KDD validation", color: DS_COLOR.nslkdd, dash: "6 4" },
        { key: "cicids.train_loss", name: "CICIDS2017 train", color: DS_COLOR.cicids },
        { key: "cicids.val_loss", name: "CICIDS2017 validation", color: DS_COLOR.cicids, dash: "6 4" },
      ];
    return [
      { key: "train_loss", name: "Train loss", color: "#007bff" },
      { key: "val_loss", name: "Validation loss", color: "#fd7e14" },
    ];
  }, [mode]);

  // The iteration budget is a shared constant in the training script, so the
  // saved model uses the same max_iter on both datasets.
  const maxIter = saved.nslkdd.logistic.max_iter;
  const refLabel =
    mode === "both"
      ? `saved model: ${maxIter} iterations (budget, both datasets)`
      : `saved model: ${maxIter} iterations (budget)`;

  return (
    <ChartCard
      title={`Logistic regression iterations — ${dsName}`}
      info={INFO.lr}
      caption="Loss converges quickly on NSL-KDD but CICIDS2017 needs several hundred iterations."
      toggles={
        <Seg
          options={[
            { value: true, label: "log scale" },
            { value: false, label: "linear" },
          ]}
          value={xLog}
          onChange={setXLog}
        />
      }
    >
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: REF_LINE_TOP, right: 14, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
          <XAxis
            dataKey="x"
            type="number"
            scale={xLog ? "log" : "linear"}
            domain={xLog ? [1, maxIter] : [0, "dataMax"]}
            ticks={xLog ? [1, 10, 100, 200, maxIter] : undefined}
            stroke="#6c757d"
            tick={{ fontSize: 11 }}
          />
          <YAxis domain={[0, "dataMax"]} stroke="#6c757d" tick={{ fontSize: 11 }} width={46} />
          <Tooltip content={<LossTip xLabel="Iterations" />} contentStyle={TT_STYLE} />
          <Legend onClick={onLegendClick} wrapperStyle={{ fontSize: 13 }} />
          {xLog && (
            <ReferenceLine
              x={maxIter}
              stroke="#6c757d"
              strokeDasharray="5 5"
              label={refLineLabel(refLabel, "#6c757d", Y_ROW_1)}
            />
          )}
          {series.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stroke={s.color}
              strokeWidth={2}
              strokeDasharray={s.dash}
              dot={false}
              hide={!!hidden[s.key]}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// ---------------------------------------------------------------------------
// 5. Development progression (A -> B -> C -> D -> E)
// ---------------------------------------------------------------------------
function progressionData(progression, mode) {
  const fields = (s, i, d) => ({
    x: i,
    stage: s.stage,
    f1: s.f1_macro,
    auc: s.auc_roc_macro,
    features: s.features,
    note: STAGE_NOTES[i],
    label: s.label,
  });
  if (mode === "both") {
    const map = new Map();
    Object.keys(progression).forEach((d) => {
      progression[d].forEach((s, i) => {
        const p = map.get(i) || { x: i };
        p[`${d}.f1`] = s.f1_macro;
        p[`${d}.auc`] = s.auc_roc_macro;
        p[`${d}.features`] = s.features;
        p[`${d}.label`] = s.label;
        p[`${d}.note`] = STAGE_NOTES[i];
        p.stage = s.stage;
        map.set(i, p);
      });
    });
    return [...map.values()].sort((a, b) => a.x - b.x);
  }
  return progression[mode].map((s, i) => fields(s, i, mode));
}

function deltaData(points, key, xKey) {
  const out = [];
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    out.push({
      x: a.x + 0.5,
      y: (a[key] + b[key]) / 2,
      delta: fmtDelta(b[key] - a[key]),
    });
  }
  return out;
}

export function ProgressionChart({ progression, mode }) {
  const { hidden, onLegendClick } = useLegendToggle();
  const dsName = mode === "both" ? "both datasets" : DS[mode];

  const points = useMemo(() => progressionData(progression, mode), [progression, mode]);

  const mainSeries = useMemo(() => {
    if (mode === "both")
      return [
        { key: "nslkdd.f1", name: "NSL-KDD F1", color: DS_COLOR.nslkdd },
        { key: "cicids.f1", name: "CICIDS2017 F1", color: DS_COLOR.cicids },
      ];
    return [{ key: "f1", name: "F1 (macro)", color: "#28a745" }];
  }, [mode]);

  const deltas = useMemo(() => {
    if (mode === "both")
      return ["nslkdd", "cicids"].map((d) => ({
        name: d,
        data: deltaData(points, `${d}.f1`),
        color: DS_COLOR[d],
      }));
    return [{ name: "single", data: deltaData(points, "f1"), color: "#28a745" }];
  }, [mode, points]);

  const tooltipRows = (p0) => {
    const block = (name, ds, label, f1, auc, features, note) => (
      <div key={name} style={{ marginTop: name && 6 }}>
        {name && (
          <div className="chart-tip-sub">{name}</div>
        )}
        <div className="chart-tip-row"><span>Stage:</span><b>{label}</b></div>
        <div className="chart-tip-row"><span>F1 (macro):</span><b>{f1.toFixed(4)}</b></div>
        <div className="chart-tip-row"><span>AUC-ROC:</span><b>{auc.toFixed(4)}</b></div>
        <div className="chart-tip-row"><span>Features:</span><b>{features}</b></div>
        <div className="chart-tip-row note"><span>Note:</span><b>{note}</b></div>
      </div>
    );
    if (mode === "both")
      return ["nslkdd", "cicids"].map((d) =>
        block(d, d, `${p0.stage} — ${p0[`${d}.label`]}`, p0[`${d}.f1`], p0[`${d}.auc`], p0[`${d}.features`], p0[`${d}.note`])
      );
    const prev = points.find((p) => p.x === p0.x - 1);
    return [
      block("", mode, `${p0.stage} — ${p0.label}`, p0.f1, p0.auc, p0.features, p0.note),
      prev
        ? <div className="chart-tip-row" key="delta"><span>Δ vs previous:</span><b>{fmtDelta(p0.f1 - prev.f1)}</b></div>
        : null,
    ];
  };

  return (
    <ChartCard
      title={`Development progression — ${dsName}`}
      info={INFO.prog}
      caption="Logistic Regression test F1 as the pipeline grows: raw → cleaned → feature-selected → SMOTE → tuned."
    >
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={points} margin={{ top: 24, right: 18, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
          <XAxis
            dataKey="x"
            type="number"
            domain={[-0.3, 4.3]}
            ticks={[0, 1, 2, 3, 4]}
            tickFormatter={(v) => "ABCDE"[v]}
            stroke="#6c757d"
            tick={{ fontSize: 12 }}
          />
          <YAxis domain={[0, 1]} stroke="#6c757d" tick={{ fontSize: 11 }} width={46} />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload || !payload.length) return null;
              return <div className="chart-tip">{tooltipRows(payload[0].payload)}</div>;
            }}
            contentStyle={TT_STYLE}
          />
          <Legend onClick={onLegendClick} wrapperStyle={{ fontSize: 13 }} />
          {mainSeries.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stroke={s.color}
              strokeWidth={2}
              dot={{ r: 4 }}
              hide={!!hidden[s.key]}
            >
              <LabelList
                dataKey={s.key}
                position="top"
                formatter={(v) => Number(v).toFixed(3)}
                style={{ fill: s.color, fontSize: 11, fontWeight: 600 }}
              />
            </Line>
          ))}
          {deltas.map((dl) => (
            <Scatter
              key={`delta-${dl.name}`}
              data={dl.data}
              dataKey="y"
              fill="transparent"
              stroke="transparent"
              legendType="none"
              isAnimationActive={false}
            >
              <LabelList
                dataKey="delta"
                position="center"
                style={{ fill: dl.color, fontSize: 11, fontWeight: 700 }}
              />
            </Scatter>
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
