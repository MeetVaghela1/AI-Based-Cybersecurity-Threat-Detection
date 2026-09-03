import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import AttackCard from "../components/AttackCard.jsx";

const ALGORITHMS = [
  {
    name: "Logistic Regression",
    color: "#007bff",
    text: "Draws a straight boundary through feature space and asks which side each connection falls on. Fast, simple, and its weights tell you which features matter — but it only sees linear patterns, so it struggles with sneaky non-linear attacks.",
  },
  {
    name: "Decision Tree",
    color: "#fd7e14",
    text: "Asks a series of yes/no questions: “is src_bytes above 5000? is the flag SF? is count below 3?” until it reaches an answer. Readable like a rulebook, but one tree can overfit — memorize quirks instead of patterns.",
  },
  {
    name: "Random Forest",
    color: "#28a745",
    text: "Hundreds of decision trees, each trained on a random slice of the data and features, voting together. The vote smooths out any one tree's mistakes — robust and hard to overfit, at the cost of being slower and unreadable.",
  },
  {
    name: "XGBoost",
    color: "#6f42c1",
    text: "Builds trees one after another, each new tree focusing on the mistakes the previous ones made (gradient boosting). State-of-the-art on tabular data and great with imbalanced classes — the usual winner on this project's datasets.",
  },
];

const ATTACK_CATEGORIES = [
  "DoS", "Probe", "R2L", "U2R", "DDoS", "PortScan",
  "Brute Force", "Web Attack", "Botnet", "Infiltration", "Heartbleed",
];

export default function HowItWorks() {
  const [infoMap, setInfoMap] = useState({});
  const [open, setOpen] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const entries = {};
      for (const cat of ATTACK_CATEGORIES) {
        try {
          entries[cat] = await api.attackInfo(cat);
        } catch {
          /* ignore */
        }
      }
      if (!cancelled) setInfoMap(entries);
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="learn">
      <h1>How machine-learning intrusion detection works</h1>
      <p>
        Every connection on a network is a row of numbers: how long it lasted,
        how many bytes went each way, which ports were used, how the connection
        ended. A machine-learning model learns patterns in those numbers — “this
        shape of connection is a DoS attack, that shape is normal” — and then
        classifies new connections it has never seen. This project trains four
        such models on two famous research datasets and compares them.
      </p>

      <h2>The pipeline, step by step</h2>
      <div className="card-grid">
        <div className="panel">
          <h3>1 · Data</h3>
          <p className="small">
            Two benchmark datasets,{" "}
            <a
              href="https://www.unb.ca/cic/datasets/nsl.html"
              target="_blank"
              rel="noreferrer"
              style={{ color: "#007bff" }}
            >
              NSL-KDD
            </a>{" "}
            and{" "}
            <a
              href="https://www.unb.ca/cic/datasets/ids-2017.html"
              target="_blank"
              rel="noreferrer"
              style={{ color: "#007bff" }}
            >
              CICIDS2017
            </a>
            , each row labelled Normal or a specific attack. Split into training
            (what the model studies) and test (the exam it has never seen).
          </p>
        </div>
        <div className="panel">
          <h3>2 · Preprocessing</h3>
          <p className="small">
            Median imputation fills gaps; min-max scaling puts every number in
            [0, 1]; one-hot encoding turns text (protocol, service, flag) into
            0/1 columns; <b>SMOTE</b> invents extra synthetic rows of the rare
            attack classes so the model sees enough of them. Everything is
            fitted on training only — never the test set (<b>no data leakage</b>).
          </p>
        </div>
        <div className="panel">
          <h3>3 · Model</h3>
          <p className="small">
            Each algorithm is tuned with grid search + stratified k-fold
            cross-validation and trained on the balanced data. Training time and
            inference latency are measured — both matter for the
            accuracy-vs-speed trade-off in real security infrastructure.
          </p>
        </div>
        <div className="panel">
          <h3>4 · Prediction</h3>
          <p className="small">
            A new connection is preprocessed exactly like training, the model
            returns a probability for every class, and the highest wins. The
            Live Monitor page streams simulated test rows through this pipeline
            so you can watch detection happen.
          </p>
        </div>
      </div>

      <h2>The four algorithms compared</h2>
      <div className="card-grid">
        {ALGORITHMS.map((a) => (
          <div className="panel" key={a.name}>
            <h3 style={{ color: a.color }}>{a.name}</h3>
            <p className="small">{a.text}</p>
          </div>
        ))}
      </div>

      <h2>Why these four algorithms — and not others</h2>
      <p>
        The four models are a deliberate ladder, not a random pick: a simple
        linear baseline (Logistic Regression), a readable single tree (Decision
        Tree), a voting crowd (Random Forest) and a correcting crowd (XGBoost).
        That spread is what lets the project measure the accuracy-vs-explainability
        trade-off — the whole point of the study. The full justification lives in{" "}
        <code>reports/algorithm_selection_justification.md</code>.
      </p>
      <details style={{ marginTop: 12 }}>
        <summary>Why not deep learning, SVM, or another classifier? (tap to expand)</summary>
        <div className="algo-table-wrap">
          <table className="algo-table">
            <thead>
              <tr>
                <th>Algorithm</th>
                <th>Family</th>
                <th>Verdict</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Logistic Regression</td>
                <td>Linear</td>
                <td>Included — fast, explainable baseline.</td>
              </tr>
              <tr>
                <td>Decision Tree</td>
                <td>Single tree</td>
                <td>Included — readable "if/then" rules; explains the black boxes.</td>
              </tr>
              <tr>
                <td>Random Forest</td>
                <td>Bagging ensemble</td>
                <td>Included — many independent trees that vote.</td>
              </tr>
              <tr>
                <td>XGBoost</td>
                <td>Boosting ensemble</td>
                <td>Included — each tree fixes the last one's mistakes; strongest classical contender.</td>
              </tr>
              <tr>
                <td>SVM</td>
                <td>Kernel</td>
                <td>Excluded — too slow and memory-hungry to scale to tens of thousands of rows.</td>
              </tr>
              <tr>
                <td>k-Nearest Neighbours</td>
                <td>Instance-based</td>
                <td>Excluded — stores every training row and pays for it on every prediction.</td>
              </tr>
              <tr>
                <td>Naive Bayes</td>
                <td>Probabilistic</td>
                <td>Excluded — assumes features are unrelated, but network flow features are strongly linked.</td>
              </tr>
              <tr>
                <td>Deep learning</td>
                <td>Neural</td>
                <td>Excluded here — high compute and tuning cost for a 16-week project; listed as future work.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>

      <h2>Why we report recall so loudly</h2>
      <p>
        With mostly-normal traffic, a model can score ~80% accuracy by flagging
        nothing. <b>Recall</b> asks the dangerous question: of the real attacks,
        how many did we catch? A missed attack is a false negative — an attacker
        already inside. That is worse than a false alarm. So this project's
        headline metric is <b>F1</b> (a balance of precision and recall) and
        <b> AUC-ROC</b> (how confidently the model ranks attacks above normal).
      </p>

      <h2>Attack categories this project detects</h2>
      <p>Click a category to read a plain-language explanation.</p>
      <div className="attack-tags">
        {ATTACK_CATEGORIES.map((cat) => (
          <button key={cat} onClick={() => setOpen(open === cat ? null : cat)}>
            {cat}
          </button>
        ))}
      </div>
      {open && (
        <div style={{ marginTop: 16 }}>
          <AttackCard
            attack={open}
            info={infoMap[open]}
            expanded
            onToggle={() => setOpen(null)}
          />
        </div>
      )}

      <h2>Where this would sit in a real network</h2>
      <p>
        In production, such a model would watch traffic mirrored from a switch
        (a <b>SPAN port</b>) — reading a copy of the traffic, not standing
        inline and blocking it. Alarms go to security analysts, who decide what
        to act on. Retraining happens on a schedule, and the model's drift is
        monitored as traffic changes over time. The full guidance is in
        <code> reports/deployment_guidelines.md</code>.
      </p>
    </div>
  );
}
