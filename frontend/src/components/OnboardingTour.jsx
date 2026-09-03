import React, { useCallback, useEffect, useState } from "react";

/**
 * OnboardingTour — a self-guided, 10-step spotlight walkthrough.
 *
 * Each step dims the page, highlights one UI element (by CSS selector) and
 * shows a plain-language card explaining it. Steps 8-10 switch to the other
 * tabs so the user sees every part of the app. `setTab` is lifted from App so
 * the tour can navigate; `onFinish` is called on Skip/Finish.
 *
 * Keys: Enter/→ next, ← back, Esc skip. Clicking the dimmed area also advances.
 */

const STEPS = [
  {
    tab: "monitor",
    sel: ".topbar .brand",
    title: "Welcome to CyberGuard",
    body: "An AI-based network threat detection demo. Four machine-learning " +
      "models classify network connections as normal or as a specific attack, " +
      "trained on the NSL-KDD and CICIDS2017 datasets. The amber badge on the " +
      "right reminds you this is simulated, educational traffic.",
  },
  {
    tab: "monitor",
    sel: ".nav .nav-btn:nth-child(1)",
    title: "Live Monitor",
    body: "This page streams classified test-set connections in near-real " +
      "time. Green rows are judged normal; red rows are flagged attacks you " +
      "can click for a plain-language explanation.",
  },
  {
    tab: "monitor",
    sel: "#ds",
    title: "Pick a dataset",
    body: "NSL-KDD has 5 classes (4 attack families + normal) on classic " +
      "1999-style traffic. CICIDS2017 is the modern benchmark with 9 classes. " +
      "Every model is trained separately on both.",
  },
  {
    tab: "monitor",
    sel: "#md",
    title: "Pick a model",
    body: "Four classifiers: Logistic Regression, Decision Tree, Random " +
      "Forest and XGBoost. XGBoost is the strongest detector overall; the " +
      "Decision Tree is the most human-readable when you need to explain an alert.",
  },
  {
    tab: "monitor",
    sel: "button.primary",
    title: "Start monitoring",
    body: "Press this to replay a batch of test-set rows every 1.6 seconds. " +
      "The stream keeps running even when you switch tabs, so the counters " +
      "and the Database tab stay live while you explore.",
  },
  {
    tab: "monitor",
    sel: ".stats",
    title: "Read the counters",
    body: "normal = rows judged benign, attacks caught = rows classified as " +
      "an attack, flows shown = the recent window on screen. Hover the ? " +
      "marks for a quick reminder of what each one means.",
  },
  {
    tab: "monitor",
    sel: ".howto",
    title: "How to read this monitor",
    body: "An expandable, plain-language guide to the page written for a " +
      "non-technical reader. Every row is clickable to see exactly why the " +
      "model made its decision, and every classified row is also stored in " +
      "the Database tab.",
  },
  {
    tab: "compare",
    sel: ".nav .nav-btn:nth-child(2)",
    title: "Model Comparison",
    body: "The scoreboard: accuracy, precision, recall, F1 and AUC on the " +
      "untouched test set, plus latency — the table gains a live column " +
      "measured while the monitor runs. You will also find how much " +
      "hyperparameter tuning really helped and real training curves.",
  },
  {
    tab: "database",
    sel: ".nav .nav-btn:nth-child(3)",
    title: "Database",
    body: "Every flow the monitor classifies lands in a small server-side " +
      "database (persisted to data/processed/prediction_log.json). Filter by " +
      "dataset or verdict, and watch the newest records appear at the top.",
  },
  {
    tab: "learn",
    sel: ".nav .nav-btn:nth-child(4)",
    title: "How It Works",
    body: "The whole pipeline explained step by step: data → features → " +
      "SMOTE balancing → models → evaluation — and why these four algorithms " +
      "were chosen instead of deep learning or SVM. That's the tour — enjoy!",
  },
];

const CARD_W = 340;

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

export default function OnboardingTour({ tab, setTab, visible, onFinish }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [rect, setRect] = useState(null);

  const step = STEPS[Math.min(stepIndex, STEPS.length - 1)];

  const measure = useCallback(() => {
    const el = document.querySelector(step.sel);
    if (!el) {
      setRect(null);
      return;
    }
    el.scrollIntoView({ block: "center" });
    const r = el.getBoundingClientRect();
    setRect({
      top: r.top,
      bottom: r.bottom,
      left: r.left,
      right: r.right,
      width: r.width,
      height: r.height,
    });
  }, [step.sel]);

  // Reset to step 0 whenever the tour is (re)opened.
  useEffect(() => {
    if (visible) setStepIndex(0);
  }, [visible]);

  // When the current step lives on another tab, switch to it first; the
  // tab-change re-runs this effect and only then do we measure the element.
  useEffect(() => {
    if (!visible) return;
    if (step.tab !== tab) {
      setTab(step.tab);
      return;
    }
    let raf;
    const doMeasure = () => {
      raf = requestAnimationFrame(measure);
    };
    doMeasure();
    window.addEventListener("resize", doMeasure);
    window.addEventListener("scroll", doMeasure, true);
    return () => {
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener("resize", doMeasure);
      window.removeEventListener("scroll", doMeasure, true);
    };
  }, [visible, stepIndex, tab, step.sel, setTab, measure]);

  const next = useCallback(() => {
    if (stepIndex >= STEPS.length - 1) {
      onFinish();
      return;
    }
    setStepIndex(stepIndex + 1);
  }, [stepIndex, onFinish]);

  const prev = useCallback(() => {
    setStepIndex((i) => Math.max(0, i - 1));
  }, []);

  useEffect(() => {
    if (!visible) return;
    const onKey = (e) => {
      if (e.key === "Escape") onFinish();
      else if (e.key === "ArrowRight" || e.key === "Enter") next();
      else if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, next, prev, onFinish]);

  if (!visible) return null;

  const vw = typeof window !== "undefined" ? window.innerWidth : 0;
  const cardLeft = rect
    ? clamp(rect.left + rect.width / 2 - CARD_W / 2, 12, vw - CARD_W - 12)
    : 12;
  const cardTop = rect ? rect.top - 14 : 12;
  const cardAbove = rect && rect.top > (window.innerHeight || 0) * 0.55;

  return (
    <div
      className="tour-overlay"
      onClick={next}
      role="dialog"
      aria-modal="true"
      aria-label={step.title}
    >
      {rect && (
        <>
          <div
            className="tour-mask"
            style={{ top: 0, left: 0, width: "100%", height: rect.top }}
          />
          <div
            className="tour-mask"
            style={{
              top: rect.bottom,
              left: 0,
              width: "100%",
              height: `calc(100% - ${rect.bottom}px)`,
            }}
          />
          <div
            className="tour-mask"
            style={{
              top: rect.top,
              left: 0,
              width: rect.left,
              height: rect.height,
            }}
          />
          <div
            className="tour-mask"
            style={{
              top: rect.top,
              left: rect.right,
              width: `calc(100% - ${rect.right}px)`,
              height: rect.height,
            }}
          />
          <div
            className="tour-highlight"
            style={{
              top: rect.top - 4,
              left: rect.left - 4,
              width: rect.width + 8,
              height: rect.height + 8,
            }}
          />
        </>
      )}

      <div
        className="tour-card"
        style={{
          left: cardLeft,
          top: cardTop,
          ...(cardAbove ? { transform: "translateY(-100%)" } : {}),
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="tour-step">
          Step {stepIndex + 1} of {STEPS.length}
        </div>
        <h3>{step.title}</h3>
        <p>{step.body}</p>
        <div className="tour-actions">
          <button type="button" className="ghost" onClick={onFinish}>
            Skip tour
          </button>
          {stepIndex > 0 && (
            <button type="button" className="ghost" onClick={prev}>
              ← Back
            </button>
          )}
          <span style={{ flex: 1 }} />
          <button type="button" className="primary" onClick={next}>
            {stepIndex === STEPS.length - 1 ? "Finish" : "Next →"}
          </button>
        </div>
        <div className="tour-dots">
          {STEPS.map((_, i) => (
            <span
              key={i}
              className={i === stepIndex ? "dot on" : "dot"}
              onClick={() => setStepIndex(i)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
