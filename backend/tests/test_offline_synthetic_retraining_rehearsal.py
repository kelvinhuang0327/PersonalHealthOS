from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "offline_synthetic_retraining_rehearsal.py"
BACKEND_ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_SUBSTRINGS = (
    "symptom",
    "patient",
    "diagnosis",
    "medication",
    "lab_report",
    "health_metric",
    "user_id",
    "@",  # no embedded email-shaped identifiers
)


def _run(tmp_path: Path, *, seed: int, metrics_json: Path | None = None) -> tuple[subprocess.CompletedProcess[str], Path]:
    output_dir = tmp_path / f"out-{seed}-{'ready' if metrics_json is None else metrics_json.stem}"
    args = [sys.executable, str(SCRIPT_PATH), "--seed", str(seed), "--output-dir", str(output_dir)]
    if metrics_json is not None:
        args.extend(["--metrics-json", str(metrics_json)])
    result = subprocess.run(args, cwd=BACKEND_ROOT, check=False, text=True, capture_output=True)
    return result, output_dir


def _write_metrics(tmp_path: Path, name: str, metrics: dict) -> Path:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(metrics), encoding="utf-8")
    return path


def _zero_outcome_metrics() -> dict:
    return {
        "total_feedback_events": 20,
        "feedback_distribution": {"accepted": 14, "not_useful": 2, "snoozed": 2, "not_applicable": 2},
        "outcome_status_counts": {"improved": 0, "unchanged": 0, "worse": 0},
        "rates": {"acceptance_rate": 0.7, "not_useful_rate": 0.1, "snooze_rate": 0.1},
    }


def _contradictory_metrics() -> dict:
    return {
        "total_feedback_events": 20,
        "feedback_distribution": {"accepted": 0, "not_useful": 2, "snoozed": 2, "not_applicable": 16},
        "outcome_status_counts": {"improved": 8, "unchanged": 2, "worse": 0},
        "rates": {"acceptance_rate": 1.0, "not_useful_rate": 0.1, "snooze_rate": 0.1},
    }


def test_ready_path_fits_and_exits_zero(tmp_path: Path) -> None:
    result, output_dir = _run(tmp_path, seed=20260710)

    assert result.returncode == 0
    assert result.stderr == ""

    data = json.loads((output_dir / "rehearsal.json").read_text(encoding="utf-8"))
    assert data["marker"] == "SYNTHETIC_REHEARSAL_ONLY"
    assert data["readiness"]["decision"] == "READY"
    assert data["fit_performed"] is True
    assert data["stages"] is not None
    assert data["deltas"] is not None
    assert data["same_holdout_confirmed"] is True


def test_zero_outcome_and_contradictory_never_fit(tmp_path: Path) -> None:
    for name, metrics in (("zero-outcome", _zero_outcome_metrics()), ("contradictory", _contradictory_metrics())):
        metrics_path = _write_metrics(tmp_path, name, metrics)
        result, output_dir = _run(tmp_path, seed=1, metrics_json=metrics_path)

        assert result.returncode == 1
        data = json.loads((output_dir / "rehearsal.json").read_text(encoding="utf-8"))
        assert data["readiness"]["decision"] == "NOT_READY"
        assert data["fit_performed"] is False
        assert data["stages"] is None
        assert data["deltas"] is None
        assert data["same_holdout_confirmed"] is None
        # dataset metadata is still reported even though no model was fit
        assert data["dataset"]["n_samples"] > 0


def test_blocked_run_returns_non_success(tmp_path: Path) -> None:
    metrics_path = _write_metrics(tmp_path, "zero-outcome", _zero_outcome_metrics())
    result, _ = _run(tmp_path, seed=42, metrics_json=metrics_path)
    assert result.returncode != 0


def test_same_seed_produces_byte_identical_json_and_markdown(tmp_path: Path) -> None:
    result1, dir1 = _run(tmp_path, seed=20260710)
    result2, dir2 = _run(tmp_path / "second", seed=20260710)

    assert result1.returncode == 0
    assert result2.returncode == 0
    assert (dir1 / "rehearsal.json").read_bytes() == (dir2 / "rehearsal.json").read_bytes()
    assert (dir1 / "rehearsal.md").read_bytes() == (dir2 / "rehearsal.md").read_bytes()


def test_different_seed_produces_valid_output(tmp_path: Path) -> None:
    result, output_dir = _run(tmp_path, seed=777)

    assert result.returncode == 0
    data = json.loads((output_dir / "rehearsal.json").read_text(encoding="utf-8"))
    assert data["seed"] == 777
    assert data["readiness"]["decision"] == "READY"
    assert set(data["dataset"]["class_balance"].keys()) == {"0", "1"}
    assert all(count > 0 for count in data["dataset"]["class_balance"].values())


def test_json_and_markdown_modes_work(tmp_path: Path) -> None:
    result, output_dir = _run(tmp_path, seed=20260710)
    assert result.returncode == 0

    json_path = output_dir / "rehearsal.json"
    md_path = output_dir / "rehearsal.md"
    assert json_path.exists()
    assert md_path.exists()

    data = json.loads(json_path.read_text(encoding="utf-8"))
    md_text = md_path.read_text(encoding="utf-8")
    assert "SYNTHETIC_REHEARSAL_ONLY" in md_text
    assert "- Decision: **READY**" in md_text
    assert f"- scikit-learn: `{data['dependency']['scikit_learn_version']}`" in md_text


def test_baseline_initial_retrained_use_same_holdout(tmp_path: Path) -> None:
    result, output_dir = _run(tmp_path, seed=20260710)
    assert result.returncode == 0

    data = json.loads((output_dir / "rehearsal.json").read_text(encoding="utf-8"))
    stages = data["stages"]
    fingerprints = {
        stages["naive_baseline"]["holdout_fingerprint"],
        stages["initial_model"]["holdout_fingerprint"],
        stages["retrained_model"]["holdout_fingerprint"],
    }
    assert len(fingerprints) == 1
    assert data["same_holdout_confirmed"] is True

    holdout_size = data["dataset"]["splits"]["holdout_size"]
    for stage_name in ("naive_baseline", "initial_model", "retrained_model"):
        cm = stages[stage_name]["confusion_matrix"]
        total_evaluated = sum(sum(row) for row in cm)
        assert total_evaluated == holdout_size


def test_retrained_fit_uses_initial_train_plus_feedback_batch(tmp_path: Path) -> None:
    result, output_dir = _run(tmp_path, seed=20260710)
    assert result.returncode == 0

    data = json.loads((output_dir / "rehearsal.json").read_text(encoding="utf-8"))
    splits = data["dataset"]["splits"]
    stages = data["stages"]

    assert stages["initial_model"]["train_size"] == splits["initial_train_size"]
    assert stages["naive_baseline"]["train_size"] == splits["initial_train_size"]
    assert stages["retrained_model"]["train_size"] == splits["initial_train_size"] + splits["feedback_batch_size"]


def test_holdout_excluded_from_both_fits(tmp_path: Path) -> None:
    result, output_dir = _run(tmp_path, seed=20260710)
    assert result.returncode == 0

    data = json.loads((output_dir / "rehearsal.json").read_text(encoding="utf-8"))
    splits = data["dataset"]["splits"]
    stages = data["stages"]

    assert stages["initial_model"]["train_size"] != splits["holdout_size"]
    assert stages["retrained_model"]["train_size"] != splits["holdout_size"]
    assert (
        splits["initial_train_size"] + splits["feedback_batch_size"] + splits["holdout_size"]
        == data["dataset"]["n_samples"]
    )


def test_metrics_exist_and_are_bounded(tmp_path: Path) -> None:
    result, output_dir = _run(tmp_path, seed=20260710)
    assert result.returncode == 0

    data = json.loads((output_dir / "rehearsal.json").read_text(encoding="utf-8"))
    for stage_name in ("naive_baseline", "initial_model", "retrained_model"):
        stage = data["stages"][stage_name]
        for key in ("accuracy", "balanced_accuracy", "precision", "recall", "f1", "roc_auc"):
            assert key in stage
            assert 0.0 <= stage[key] <= 1.0
        cm = stage["confusion_matrix"]
        assert len(cm) == 2
        assert all(len(row) == 2 for row in cm)
        assert all(isinstance(value, int) for row in cm for value in row)


def test_reports_contain_no_row_level_or_identifying_data(tmp_path: Path) -> None:
    result, output_dir = _run(tmp_path, seed=20260710)
    assert result.returncode == 0

    json_text = (output_dir / "rehearsal.json").read_text(encoding="utf-8").lower()
    md_text = (output_dir / "rehearsal.md").read_text(encoding="utf-8").lower()

    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in json_text
        assert forbidden not in md_text


def test_no_database_engine_created_by_script_source() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "create_engine" not in source
    assert "run_with_database_url" not in source
    assert "requests" not in source
    assert "socket" not in source


def test_report_declares_required_boundaries(tmp_path: Path) -> None:
    result, output_dir = _run(tmp_path, seed=20260710)
    assert result.returncode == 0

    data = json.loads((output_dir / "rehearsal.json").read_text(encoding="utf-8"))
    assert data["DB_ACTIVITY"] == "NOT_RUN"
    assert data["REAL_DATA"] == "NOT_USED"
    assert data["CLINICAL_USE"] == "NOT_AUTHORIZED"
    assert data["PRODUCTION_READY"] == "NO"
    assert len(data["limitations"]) > 0
