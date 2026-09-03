"""db.py — SQLite layer for the research panel project.

A real, file-based SQLite database (db/research_panel.db). Every table holds
genuine data produced by the main project or by this panel's live detection:
nothing is fabricated.

Schema overview:
    datasets          one row per benchmark dataset (real sizes)
    models            one row per trained model (CV score, latency, params...)
    test_metrics      one row per model on the untouched test set
    per_class_metrics one row per (model, class) — recall/precision/F1
    predictions       every live detection made from this panel
    pipeline_steps    the phases of the project, stored as rows
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    year INTEGER,
    rows_train_raw INTEGER,
    rows_train_after_smote INTEGER,
    rows_test INTEGER,
    n_features INTEGER,
    n_classes INTEGER,
    classes TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_label TEXT NOT NULL,
    cv_f1_macro REAL,
    cv_f1_std REAL,
    fit_time_s REAL,
    n_hyperparameter_combinations INTEGER,
    cv_folds INTEGER,
    latency_ms_per_row REAL,
    n_train_rows INTEGER,
    n_features INTEGER,
    classes TEXT,
    best_params TEXT,
    trained_at TEXT,
    UNIQUE (dataset, model_name)
);

CREATE TABLE IF NOT EXISTS test_metrics (
    dataset TEXT NOT NULL,
    model_name TEXT NOT NULL,
    n_test_rows INTEGER,
    accuracy REAL,
    precision_macro REAL,
    recall_macro REAL,
    f1_macro REAL,
    auc_roc_macro REAL,
    test_latency_ms_per_row REAL,
    PRIMARY KEY (dataset, model_name)
);

CREATE TABLE IF NOT EXISTS per_class_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset TEXT NOT NULL,
    model_name TEXT NOT NULL,
    class_name TEXT NOT NULL,
    precision REAL,
    recall REAL,
    f1 REAL
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    dataset TEXT NOT NULL,
    model_name TEXT NOT NULL,
    source TEXT,
    row_index INTEGER,
    predicted_label TEXT NOT NULL,
    true_label TEXT,
    is_attack INTEGER,
    confidence REAL,
    matched INTEGER,
    latency_ms REAL
);

CREATE TABLE IF NOT EXISTS pipeline_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase TEXT NOT NULL,
    title TEXT NOT NULL,
    detail TEXT,
    ord INTEGER
);
"""


def get_conn() -> sqlite3.Connection:
    config.DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables if they do not exist yet (idempotent)."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def table_counts() -> list[dict]:
    """Row count + column list for every table, for the 'Under the Hood' tab."""
    with get_conn() as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        out = []
        for table in tables:
            cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            out.append({"table": table, "columns": cols, "rows": count})
        return out


def insert_predictions(rows: list[dict]) -> int:
    """Insert a batch of detection rows into `predictions`. Returns count."""
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO predictions (
                timestamp, dataset, model_name, source, row_index,
                predicted_label, true_label, is_attack, confidence,
                matched, latency_ms
            ) VALUES (
                :timestamp, :dataset, :model_name, :source, :row_index,
                :predicted_label, :true_label, :is_attack, :confidence,
                :matched, :latency_ms
            )
            """,
            rows,
        )
        return len(rows)
