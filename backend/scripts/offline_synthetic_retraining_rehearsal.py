#!/usr/bin/env python3
"""Deterministic synthetic-only prediction and retraining rehearsal.

SYNTHETIC_REHEARSAL_ONLY: every input here is generated in-process from an
explicit seed. No real health, product, dogfood, or database data is read or
written, and no clinical claim or production-readiness claim is made.
"""
from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Any, Callable

import numpy as np

from sklearn import __version__ as SKLEARN_VERSION
from sklearn.datasets import make_classification
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.services.action_feedback_readiness import evaluate_offline_feedback_readiness

MARKER = "SYNTHETIC_REHEARSAL_ONLY"
ROUND_DECIMALS = 6

N_SAMPLES = 600
N_FEATURES = 10
N_INFORMATIVE = 6
N_REDUNDANT = 2
CLASS_WEIGHTS = (0.55, 0.45)
HOLDOUT_FRACTION = 0.2
FEEDBACK_FRACTION = 0.3

_VERIFIED_MATMUL_WARNING_MESSAGES = (
    r"^divide by zero encountered in matmul$",
    r"^overflow encountered in matmul$",
    r"^invalid value encountered in matmul$",
)
_VERIFIED_MATMUL_WARNING_MODULE = r"^sklearn\.utils\.extmath$"


def _default_ready_metrics() -> dict[str, Any]:
    """Fixed synthetic aggregate feedback-metrics shape that clears the readiness gate."""
    return {
        "total_feedback_events": 20,
        "feedback_distribution": {"accepted": 14, "not_useful": 2, "snoozed": 2, "not_applicable": 2},
        "outcome_status_counts": {"improved": 8, "unchanged": 2, "worse": 0},
        "rates": {"acceptance_rate": 0.7, "not_useful_rate": 0.1, "snooze_rate": 0.1},
    }


def _generate_synthetic_dataset(seed: int) -> dict[str, Any]:
    X, y = make_classification(
        n_samples=N_SAMPLES,
        n_features=N_FEATURES,
        n_informative=N_INFORMATIVE,
        n_redundant=N_REDUNDANT,
        n_repeated=0,
        n_classes=2,
        n_clusters_per_class=2,
        weights=list(CLASS_WEIGHTS),
        flip_y=0.02,
        class_sep=1.0,
        random_state=seed,
    )

    classes, counts = np.unique(y, return_counts=True)
    if len(classes) < 2:
        raise RuntimeError("synthetic dataset invariant violated: both classes must be represented")

    indices = np.arange(N_SAMPLES)
    rest_idx, holdout_idx = train_test_split(
        indices, test_size=HOLDOUT_FRACTION, random_state=seed, stratify=y
    )
    initial_idx, feedback_idx = train_test_split(
        rest_idx, test_size=FEEDBACK_FRACTION, random_state=seed, stratify=y[rest_idx]
    )

    if set(holdout_idx.tolist()) & (set(initial_idx.tolist()) | set(feedback_idx.tolist())):
        raise RuntimeError("synthetic split invariant violated: holdout overlaps with training indices")

    return {
        "X": X,
        "y": y,
        "feature_names": [f"feature_{i}" for i in range(N_FEATURES)],
        "initial_idx": initial_idx,
        "feedback_idx": feedback_idx,
        "holdout_idx": holdout_idx,
        "class_balance": {str(int(c)): int(n) for c, n in zip(classes, counts)},
    }


def _fingerprint(y_holdout: np.ndarray) -> str:
    import hashlib

    return hashlib.sha256(np.ascontiguousarray(y_holdout).tobytes()).hexdigest()


def _metrics_for(y_true: np.ndarray, y_pred: np.ndarray, y_score: np.ndarray) -> dict[str, Any]:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), ROUND_DECIMALS),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), ROUND_DECIMALS),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), ROUND_DECIMALS),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), ROUND_DECIMALS),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), ROUND_DECIMALS),
        "roc_auc": round(float(roc_auc_score(y_true, y_score)), ROUND_DECIMALS),
        "confusion_matrix": cm.tolist(),
    }


def _run_with_scoped_matmul_warning_filter(operation: Callable[[], Any]) -> Any:
    """Hide only verified Accelerate noise for one prediction operation."""
    with warnings.catch_warnings():
        for message in _VERIFIED_MATMUL_WARNING_MESSAGES:
            warnings.filterwarnings(
                "ignore",
                message=message,
                category=RuntimeWarning,
                module=_VERIFIED_MATMUL_WARNING_MODULE,
            )
        return operation()


def _fit_and_evaluate(
    model: Any,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_holdout: np.ndarray,
    y_holdout: np.ndarray,
    *,
    scope_verified_matmul_warning: bool = False,
) -> dict[str, Any]:
    model.fit(X_train, y_train)
    if scope_verified_matmul_warning:
        y_pred = _run_with_scoped_matmul_warning_filter(lambda: model.predict(X_holdout))
        y_score = _run_with_scoped_matmul_warning_filter(lambda: model.predict_proba(X_holdout))[:, 1]
    else:
        y_pred = model.predict(X_holdout)
        y_score = model.predict_proba(X_holdout)[:, 1]

    metrics = _metrics_for(y_holdout, y_pred, y_score)
    metrics["train_size"] = int(len(y_train))
    metrics["holdout_fingerprint"] = _fingerprint(y_holdout)
    return metrics


def _compute_deltas(initial: dict[str, Any], retrained: dict[str, Any]) -> dict[str, Any]:
    scalar_keys = ["accuracy", "balanced_accuracy", "precision", "recall", "f1", "roc_auc"]
    deltas = {key: round(retrained[key] - initial[key], ROUND_DECIMALS) for key in scalar_keys}
    deltas["confusion_matrix_delta"] = [
        [retrained["confusion_matrix"][i][j] - initial["confusion_matrix"][i][j] for j in range(2)]
        for i in range(2)
    ]
    return deltas


def build_rehearsal_report(seed: int, metrics: dict[str, Any]) -> dict[str, Any]:
    readiness = evaluate_offline_feedback_readiness(metrics)
    dataset = _generate_synthetic_dataset(seed)

    dataset_metadata = {
        "n_samples": N_SAMPLES,
        "n_features": N_FEATURES,
        "feature_names": dataset["feature_names"],
        "class_balance": dataset["class_balance"],
        "splits": {
            "initial_train_size": int(len(dataset["initial_idx"])),
            "feedback_batch_size": int(len(dataset["feedback_idx"])),
            "holdout_size": int(len(dataset["holdout_idx"])),
        },
    }

    fit_performed = readiness.decision == "READY"
    stages: dict[str, Any] | None = None
    deltas: dict[str, Any] | None = None
    same_holdout_confirmed: bool | None = None

    if fit_performed:
        X, y = dataset["X"], dataset["y"]
        X_initial, y_initial = X[dataset["initial_idx"]], y[dataset["initial_idx"]]
        X_feedback, y_feedback = X[dataset["feedback_idx"]], y[dataset["feedback_idx"]]
        X_holdout, y_holdout = X[dataset["holdout_idx"]], y[dataset["holdout_idx"]]
        X_retrain = np.concatenate([X_initial, X_feedback])
        y_retrain = np.concatenate([y_initial, y_feedback])

        naive_baseline = _fit_and_evaluate(
            DummyClassifier(strategy="most_frequent"), X_initial, y_initial, X_holdout, y_holdout
        )
        initial_model = _fit_and_evaluate(
            make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=seed, solver="liblinear")),
            X_initial, y_initial, X_holdout, y_holdout,
            scope_verified_matmul_warning=True,
        )
        retrained_model = _fit_and_evaluate(
            make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=seed, solver="liblinear")),
            X_retrain, y_retrain, X_holdout, y_holdout,
            scope_verified_matmul_warning=True,
        )

        same_holdout_confirmed = (
            naive_baseline["holdout_fingerprint"]
            == initial_model["holdout_fingerprint"]
            == retrained_model["holdout_fingerprint"]
        )
        if not same_holdout_confirmed:
            raise RuntimeError("holdout fingerprint mismatch across stages")

        stages = {
            "naive_baseline": naive_baseline,
            "initial_model": initial_model,
            "retrained_model": retrained_model,
        }
        deltas = _compute_deltas(initial_model, retrained_model)

    return {
        "marker": MARKER,
        "seed": seed,
        "readiness": readiness.to_dict(),
        "fit_performed": fit_performed,
        "dataset": dataset_metadata,
        "stages": stages,
        "deltas": deltas,
        "same_holdout_confirmed": same_holdout_confirmed,
        "dependency": {"scikit_learn_version": SKLEARN_VERSION},
        "DB_ACTIVITY": "NOT_RUN",
        "REAL_DATA": "NOT_USED",
        "CLINICAL_USE": "NOT_AUTHORIZED",
        "PRODUCTION_READY": "NO",
        "limitations": [
            "Synthetic abstract dataset only; no real health, product, or dogfood data was read or written.",
            "Metrics reflect a single deterministic seed on a small synthetic holdout and are not evidence of production model quality.",
            "Precision/recall/F1 use zero_division=0, so a stage with no predicted or true positive samples reports 0 rather than raising.",
            "Improvement across stages is not guaranteed; flat or worse retraining deltas are expected and reported as-is.",
            "This rehearsal is an offline engineering exercise only and does not authorize clinical use, production deployment, or external publication.",
        ],
    }


def render_markdown(result: dict[str, Any]) -> str:
    readiness = result["readiness"]
    dataset = result["dataset"]
    lines = [
        f"# {MARKER}",
        "",
        "Offline synthetic-only prediction and retraining rehearsal. No real data, no database access.",
        "",
        "## Readiness Gate",
        f"- Decision: **{readiness['decision']}**",
        f"- Fit Performed: `{result['fit_performed']}`",
        "",
        "### Reasons",
    ]
    lines.extend(f"- {reason}" for reason in readiness["reasons"])

    lines.extend([
        "",
        "## Seed and Dataset Metadata",
        f"- Seed: `{result['seed']}`",
        f"- Samples: `{dataset['n_samples']}`",
        f"- Features: `{dataset['n_features']}` ({', '.join(dataset['feature_names'])})",
        f"- Class Balance: `{dataset['class_balance']}`",
        f"- Initial Train Size: `{dataset['splits']['initial_train_size']}`",
        f"- Feedback Batch Size: `{dataset['splits']['feedback_batch_size']}`",
        f"- Holdout Size: `{dataset['splits']['holdout_size']}`",
        f"- Same Holdout Confirmed: `{result['same_holdout_confirmed']}`",
    ])

    lines.extend(["", "## Stage Metrics"])
    if result["stages"] is None:
        lines.append("- No fitting occurred: readiness gate did not return READY.")
    else:
        for stage_name in ("naive_baseline", "initial_model", "retrained_model"):
            stage = result["stages"][stage_name]
            lines.extend([
                f"### {stage_name}",
                f"- Train Size: `{stage['train_size']}`",
                f"- Accuracy: `{stage['accuracy']}`",
                f"- Balanced Accuracy: `{stage['balanced_accuracy']}`",
                f"- Precision: `{stage['precision']}`",
                f"- Recall: `{stage['recall']}`",
                f"- F1: `{stage['f1']}`",
                f"- ROC-AUC: `{stage['roc_auc']}`",
                f"- Confusion Matrix: `{stage['confusion_matrix']}`",
                "",
            ])

        deltas = result["deltas"]
        lines.extend([
            "## Retrained-Minus-Initial Deltas",
            f"- Accuracy: `{deltas['accuracy']}`",
            f"- Balanced Accuracy: `{deltas['balanced_accuracy']}`",
            f"- Precision: `{deltas['precision']}`",
            f"- Recall: `{deltas['recall']}`",
            f"- F1: `{deltas['f1']}`",
            f"- ROC-AUC: `{deltas['roc_auc']}`",
            f"- Confusion Matrix Delta: `{deltas['confusion_matrix_delta']}`",
        ])

    lines.extend([
        "",
        "## Dependency",
        f"- scikit-learn: `{result['dependency']['scikit_learn_version']}`",
        "",
        "## Boundaries",
        f"- DB_ACTIVITY: {result['DB_ACTIVITY']}",
        f"- REAL_DATA: {result['REAL_DATA']}",
        f"- CLINICAL_USE: {result['CLINICAL_USE']}",
        f"- PRODUCTION_READY: {result['PRODUCTION_READY']}",
        "",
        "## Limitations",
    ])
    lines.extend(f"- {item}" for item in result["limitations"])

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline synthetic-only prediction and retraining rehearsal (no real data, no DB)."
    )
    parser.add_argument("--seed", type=int, default=20260710, help="Deterministic seed for synthetic data generation.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory to write rehearsal.json/rehearsal.md")
    parser.add_argument(
        "--metrics-json",
        type=Path,
        default=None,
        help="Optional synthetic aggregate feedback-metrics JSON overriding the default READY gate input, "
        "used to exercise NOT_READY/INSUFFICIENT_DATA blocked paths.",
    )
    args = parser.parse_args(argv)

    if args.metrics_json is not None:
        with args.metrics_json.open("r", encoding="utf-8") as handle:
            metrics = json.load(handle)
    else:
        metrics = _default_ready_metrics()

    result = build_rehearsal_report(args.seed, metrics)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "rehearsal.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "rehearsal.md").write_text(render_markdown(result), encoding="utf-8")

    return 0 if result["fit_performed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
