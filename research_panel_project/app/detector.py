"""detector.py — load the copied models and test data, classify rows.

The models were trained in the main project. Here they are loaded lazily
(cached after first use) and applied to REAL rows from the test sets — the part
of the data the models never trained on. Every prediction is returned with the
information needed to log it to the database.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime

import joblib
import numpy as np
import pandas as pd

from . import config


class Detector:
    def __init__(self) -> None:
        self._models_cache: dict[tuple[str, str], object] = {}
        self._encoders_cache: dict[str, object] = {}
        self._preproc_cache: dict[str, object] = {}
        self._test_x_cache: dict[str, pd.DataFrame] = {}
        self._test_y_cache: dict[str, pd.Series] = {}

    # ------------------------------------------------------------------
    # lazy loading (cached)
    # ------------------------------------------------------------------
    def _model_path(self, dataset: str, model: str):
        path = config.MODELS_DIR / f"{dataset}_{model}.joblib"
        if not path.exists():
            raise FileNotFoundError(
                f"Model file missing: {path}. Run  scripts/setup.py  first."
            )
        return path

    def _encoder(self, dataset: str):
        if dataset not in self._encoders_cache:
            path = config.ENCODERS_DIR / f"{dataset}_label_encoder.joblib"
            if not path.exists():
                raise FileNotFoundError(
                    f"Label encoder missing: {path}. Run  scripts/setup.py  first."
                )
            self._encoders_cache[dataset] = joblib.load(path)
        return self._encoders_cache[dataset]

    def _preprocessor(self, dataset: str):
        if dataset not in self._preproc_cache:
            path = config.PREPROCESSOR_DIR / f"{dataset}_preprocessor.joblib"
            if not path.exists():
                raise FileNotFoundError(
                    f"Preprocessor missing: {path}. Run  scripts/setup.py  first."
                )
            # the pickle refers to the custom Preprocessor class, which lives in
            # the MAIN project's src/ package, so make it importable.
            root = str(config.PARENT_PROJECT)
            if root not in sys.path:
                sys.path.insert(0, root)
            self._preproc_cache[dataset] = joblib.load(path)
        return self._preproc_cache[dataset]

    def _test_x(self, dataset: str) -> pd.DataFrame:
        if dataset not in self._test_x_cache:
            path = config.TEST_DATA_DIR / f"{dataset}_test_X.pkl"
            if not path.exists():
                raise FileNotFoundError(
                    f"Test data missing: {path}. Run  scripts/setup.py  first."
                )
            self._test_x_cache[dataset] = pd.read_pickle(path).reset_index(drop=True)
        return self._test_x_cache[dataset]

    def _test_y(self, dataset: str) -> pd.Series:
        if dataset not in self._test_y_cache:
            path = config.TEST_DATA_DIR / f"{dataset}_test_y.pkl"
            if not path.exists():
                raise FileNotFoundError(
                    f"Test data missing: {path}. Run  scripts/setup.py  first."
                )
            self._test_y_cache[dataset] = pd.read_pickle(path).reset_index(drop=True)
        return self._test_y_cache[dataset]

    def _model(self, dataset: str, model: str):
        key = (dataset, model)
        if key not in self._models_cache:
            self._models_cache[key] = joblib.load(self._model_path(dataset, model))
        return self._models_cache[key]

    # ------------------------------------------------------------------
    # predictions
    # ------------------------------------------------------------------
    def predict(
        self, dataset: str, model: str, count: int = 10, random_state: int | None = None
    ) -> list[dict]:
        """Classify `count` random rows from the test set and describe them.

        Each item carries everything the caller needs to log the detection:
        timestamp, row index, prediction, true label, confidence, whether it
        matched, and the inference latency.
        """
        if dataset not in config.DATASETS:
            raise ValueError(f"Unknown dataset: {dataset}")
        if model not in config.MODELS:
            raise ValueError(f"Unknown model: {model}")

        X = self._test_x(dataset)
        y = self._test_y(dataset)
        if count > len(X):
            count = len(X)

        rng = np.random.default_rng(random_state)
        indices = rng.choice(len(X), size=count, replace=False)

        model_obj = self._model(dataset, model)
        encoder = self._encoder(dataset)

        rows = X.iloc[indices]
        true_labels = y.iloc[indices].tolist()

        start = time.perf_counter()
        probs = model_obj.predict_proba(rows)
        preds_num = model_obj.predict(rows)
        elapsed = time.perf_counter() - start

        labels = encoder.inverse_transform(preds_num)
        class_list = list(encoder.classes_)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        items = []
        for i, idx in enumerate(indices):
            proba = dict(zip(class_list, [float(p) for p in probs[i]]))
            confidence = float(max(probs[i]))
            is_attack = labels[i] != config.NORMAL_CLASSES[dataset]
            matched = labels[i] == true_labels[i]
            items.append(
                {
                    "timestamp": now,
                    "dataset": dataset,
                    "model_name": model,
                    "model_label": config.MODEL_LABELS[model],
                    "source": "live-detection",
                    "row_index": int(idx),
                    "predicted_label": str(labels[i]),
                    "true_label": str(true_labels[i]),
                    "is_attack": int(is_attack),
                    "confidence": confidence,
                    "matched": int(matched),
                    "latency_ms": round(elapsed / max(count, 1) * 1000.0, 4),
                    "probabilities": proba,
                }
            )
        return items

    def row_features(self, dataset: str, row_index: int, top_n: int = 12) -> dict:
        """What the model 'saw' for one test row: its feature values.

        Sorted by absolute value so the viewer sees the most distinctive
        numbers first (biggest deviations from zero after scaling).
        """
        X = self._test_x(dataset)
        y = self._test_y(dataset)
        if row_index < 0 or row_index >= len(X):
            raise IndexError(f"row_index {row_index} out of range (0..{len(X) - 1})")

        values = X.iloc[row_index]
        pairs = sorted(
            values.items(), key=lambda kv: abs(float(kv[1])), reverse=True
        )[:top_n]
        return {
            "dataset": dataset,
            "row_index": int(row_index),
            "true_label": str(y.iloc[row_index]),
            "n_features_total": int(X.shape[1]),
            "features": [{"name": k, "value": float(v)} for k, v in pairs],
        }

    # ------------------------------------------------------------------
    # custom user-defined input
    # ------------------------------------------------------------------
    def _feature_importance(self, dataset: str, model: str) -> pd.Series:
        """Per-feature importance taken from the trained model itself.

        Tree models expose `feature_importances_`; for logistic regression we
        use the largest absolute coefficient across classes — the most a
        change in that feature can swing any class score.
        """
        X = self._test_x(dataset)
        model_obj = self._model(dataset, model)
        est = model_obj.steps[-1][1] if hasattr(model_obj, "steps") else model_obj
        if model == "logistic":
            coef = np.asarray(est.coef_)
            scores = np.abs(coef).max(axis=0) if coef.ndim > 1 else np.abs(coef)
        else:
            scores = np.asarray(est.feature_importances_)
        return pd.Series(scores, index=X.columns)

    def feature_stats(self, dataset: str, model: str, n: int = 10) -> dict:
        """The `n` most important features, with the real stats needed to fill
        an input form (mean as default, std/min/max as hints)."""
        if dataset not in config.DATASETS:
            raise ValueError(f"Unknown dataset: {dataset}")
        if model not in config.MODELS:
            raise ValueError(f"Unknown model: {model}")

        X = self._test_x(dataset)
        imp = self._feature_importance(dataset, model).sort_values(ascending=False)
        top = imp.head(n)
        features = []
        for name in top.index:
            col = X[name]
            features.append(
                {
                    "name": str(name),
                    "importance": float(top[name]),
                    "mean": float(col.mean()),
                    "std": float(col.std(ddof=0)),
                    "min": float(col.min()),
                    "max": float(col.max()),
                }
            )
        return {
            "dataset": dataset,
            "model": model,
            "model_label": config.MODEL_LABELS[model],
            "total_features": int(X.shape[1]),
            "features": features,
        }

    def predict_custom(
        self, dataset: str, model: str, overrides: dict[str, float]
    ) -> list[dict]:
        """Predict on a user-supplied feature vector.

        The user only fills the features shown in the form; every other
        feature is set to the dataset mean of that column, so the vector has
        exactly the columns/order the model was trained on.
        """
        if dataset not in config.DATASETS:
            raise ValueError(f"Unknown dataset: {dataset}")
        if model not in config.MODELS:
            raise ValueError(f"Unknown model: {model}")

        X = self._test_x(dataset)
        row = {col: float(X[col].mean()) for col in X.columns}
        for name, value in overrides.items():
            if name not in row:
                raise ValueError(f"Unknown feature: {name}")
            row[name] = float(value)
        frame = pd.DataFrame([row], columns=list(X.columns))

        model_obj = self._model(dataset, model)
        encoder = self._encoder(dataset)

        start = time.perf_counter()
        probs = model_obj.predict_proba(frame)
        preds_num = model_obj.predict(frame)
        elapsed = time.perf_counter() - start

        labels = encoder.inverse_transform(preds_num)
        class_list = list(encoder.classes_)
        label = str(labels[0])
        proba = dict(zip(class_list, [float(p) for p in probs[0]]))

        return [
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "dataset": dataset,
                "model_name": model,
                "model_label": config.MODEL_LABELS[model],
                "source": "user-input",
                "row_index": None,
                "predicted_label": label,
                "true_label": None,
                "is_attack": int(label != config.NORMAL_CLASSES[dataset]),
                "confidence": float(max(probs[0])),
                "matched": None,
                "latency_ms": round(elapsed * 1000.0, 4),
                "probabilities": proba,
                "user_features": {k: row[k] for k in overrides.keys()},
            }
        ]

    # ------------------------------------------------------------------
    # step-by-step trace (one real row, real measured timings)
    # ------------------------------------------------------------------
    def _reconstruct_raw(self, pp, stored_row: pd.DataFrame) -> pd.DataFrame:
        """Turn one stored (already preprocessed) row back into its raw form.

        Inverse min-max scaling for numerics, argmax of the one-hot block for
        categoricals. Cells that were missing/infinite at collection time
        naturally come back as the imputed value (that value is what the
        pipeline would have filled in anyway).
        """
        numeric_cols = list(pp.numeric_features_)
        n_num = len(numeric_cols)
        scaler = pp._column_transformer.named_transformers_["num"]["scale"]
        raw_num = scaler.inverse_transform(
            np.asarray(stored_row.iloc[:, :n_num], dtype=float)
        )[0]
        rec = dict(zip(numeric_cols, [float(v) for v in raw_num]))

        cat_feats = list(pp.categorical_features)
        if cat_feats:
            oh = pp._column_transformer.named_transformers_["cat"]["onehot"]
            cats = oh.categories_
            offset = n_num
            for feat, cat_list in zip(cat_feats, cats):
                block = np.asarray(stored_row.iloc[:, offset:offset + len(cat_list)], dtype=float)[0]
                rec[feat] = cat_list[int(np.argmax(block))] if block.sum() > 0 else "missing"
                offset += len(cat_list)
        return pd.DataFrame([rec], columns=numeric_cols + cat_feats)

    def trace_predict(
        self,
        dataset: str,
        model: str,
        row_index: int | None = None,
        random_state: int | None = None,
    ) -> dict:
        """Classify ONE real test row through the actual pipeline, measuring
        each stage with time.perf_counter() — the timings are from this exact
        run, not precomputed.

        Step 1: raw input arrives (the raw row reconstructed from the stored one)
        Step 2: preprocessing — real preprocessor.transform(raw), measured
        Step 3: inference — real model.predict_proba, measured, all classes
        Step 4: decision — argmax/confidence/attack/match, measured
        Step 5: total time breakdown
        """
        if dataset not in config.DATASETS:
            raise ValueError(f"Unknown dataset: {dataset}")
        if model not in config.MODELS:
            raise ValueError(f"Unknown model: {model}")

        X = self._test_x(dataset)
        y = self._test_y(dataset)
        n = len(X)
        if row_index is None:
            row_index = int(np.random.default_rng(random_state).integers(0, n))
        elif not isinstance(row_index, int) or not (0 <= row_index < n):
            raise IndexError(f"row_index {row_index} out of range (0..{n - 1})")

        model_obj = self._model(dataset, model)
        encoder = self._encoder(dataset)
        pp = self._preprocessor(dataset)
        class_list = list(encoder.classes_)
        stored_row = X.iloc[[row_index]]
        true_label = str(y.iloc[row_index])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ---- Step 1: raw input ------------------------------------------
        raw_row = self._reconstruct_raw(pp, stored_row)
        preview = sorted(
            ((k, v) for k, v in raw_row.iloc[0].items() if _is_num(v)),
            key=lambda kv: abs(float(kv[1])),
            reverse=True,
        )[:12]
        raw_preview = [
            {"name": str(k), "value": float(v) if _is_num(v) else str(v)}
            for k, v in preview
        ]

        # ---- Step 2: real preprocessing pass ----------------------------
        t0 = time.perf_counter()
        transformed = pp.transform(raw_row)
        t1 = time.perf_counter()
        preprocess_ms = (t1 - t0) * 1000.0
        # integrity check: re-transforming the raw row must reproduce the
        # stored row exactly (proves the stored data came from this pipeline)
        integ_ok = bool(np.allclose(
            np.asarray(transformed, dtype=float),
            np.asarray(stored_row, dtype=float),
            rtol=1e-9, atol=1e-12,
        ))

        # ---- Step 3: real inference -------------------------------------
        t2 = time.perf_counter()
        probs = np.asarray(model_obj.predict_proba(transformed))
        t3 = time.perf_counter()
        inference_ms = (t3 - t2) * 1000.0
        proba = {c: float(p) for c, p in zip(class_list, probs[0])}
        confidence = float(probs[0].max())

        # ---- Step 4: decision -------------------------------------------
        t4 = time.perf_counter()
        predicted_label = str(encoder.inverse_transform([int(np.argmax(probs[0]))])[0])
        is_attack = predicted_label != config.NORMAL_CLASSES[dataset]
        matched = predicted_label == true_label
        t5 = time.perf_counter()
        decision_ms = (t5 - t4) * 1000.0

        total_ms = (t5 - t0) * 1000.0
        return {
            "timestamp": now,
            "dataset": dataset,
            "model": model,
            "model_label": config.MODEL_LABELS[model],
            "source": "step-by-step",
            "row_index": int(row_index),
            "true_label": true_label,
            "predicted_label": predicted_label,
            "is_attack": int(is_attack),
            "matched": int(matched),
            "confidence": confidence,
            "n_features": int(transformed.shape[1]),
            "probabilities": proba,
            "steps": {
                "input": {
                    "title": "Raw input received",
                    "n_raw_features": int(raw_row.shape[1]),
                    "preview": raw_preview,
                    "categorical": {
                        str(k): str(v) for k, v in raw_row.iloc[0].items()
                        if k in pp.categorical_features
                    },
                },
                "preprocessing": {
                    "title": "Preprocessing (impute → scale → one-hot)",
                    "ms": preprocess_ms,
                    "n_output_features": int(transformed.shape[1]),
                    "reproduces_stored_row": integ_ok,
                },
                "inference": {
                    "title": "Model inference (predict_proba)",
                    "ms": inference_ms,
                },
                "decision": {
                    "title": "Decision (argmax + confidence)",
                    "ms": decision_ms,
                },
            },
            "timings": {
                "preprocessing_ms": preprocess_ms,
                "inference_ms": inference_ms,
                "decision_ms": decision_ms,
                "total_ms": total_ms,
                "latency_ms": round(total_ms, 4),
            },
        }


def _is_num(v) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False
