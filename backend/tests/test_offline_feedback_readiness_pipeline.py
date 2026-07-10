from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def _metrics(
    *,
    total: int,
    acceptance_rate: float = 0.7,
    not_useful_rate: float = 0.1,
    snooze_rate: float = 0.1,
) -> dict[str, object]:
    return {
        "total_feedback_events": total,
        "feedback_distribution": {
            "accepted": round(total * acceptance_rate),
            "not_useful": round(total * not_useful_rate),
            "snoozed": round(total * snooze_rate),
        },
        "outcome_status_counts": {
            "improved": 4,
            "unchanged": 1,
            "worse": 0,
        },
        "rates": {
            "acceptance_rate": acceptance_rate,
            "not_useful_rate": not_useful_rate,
            "snooze_rate": snooze_rate,
        },
    }


def _run_pipeline(metrics_path: Path, output_format: str = "json") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/offline_feedback_readiness.py",
            "--metrics-json",
            str(metrics_path),
            "--format",
            output_format,
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        text=True,
        capture_output=True,
    )


@pytest.mark.parametrize(
    ("metrics", "expected_decision", "expected_exit_code"),
    [
        (_metrics(total=10), "READY", 0),
        (_metrics(total=10, acceptance_rate=0.4), "NOT_READY", 1),
        (_metrics(total=4), "INSUFFICIENT_DATA", 1),
    ],
)
def test_pipeline_classifies_aggregate_metrics(
    tmp_path: Path,
    metrics: dict[str, object],
    expected_decision: str,
    expected_exit_code: int,
) -> None:
    metrics_path = tmp_path / "aggregate-metrics.json"
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")

    result = _run_pipeline(metrics_path)

    assert result.returncode == expected_exit_code
    assert json.loads(result.stdout)["decision"] == expected_decision
    assert result.stderr == ""


def test_pipeline_renders_markdown_with_shared_readiness_logic(tmp_path: Path) -> None:
    metrics_path = tmp_path / "aggregate-metrics.json"
    metrics_path.write_text(json.dumps(_metrics(total=10)), encoding="utf-8")

    result = _run_pipeline(metrics_path, "markdown")

    assert result.returncode == 0
    assert "# Offline Action Feedback Readiness Report" in result.stdout
    assert "- Decision: **READY**" in result.stdout
    assert "min_feedback_events: `5`" in result.stdout


def test_pipeline_zero_outcomes_fail_closed(tmp_path: Path) -> None:
    metrics = _metrics(total=10)
    metrics["outcome_status_counts"] = {"improved": 0, "unchanged": 0, "worse": 0}

    metrics_path = tmp_path / "zero-outcomes.json"
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")

    result = _run_pipeline(metrics_path)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["decision"] == "NOT_READY"
    assert any("Zero actual outcomes" in r for r in data["reasons"])


def test_pipeline_zero_accepted_with_rate_one_fail_closed(tmp_path: Path) -> None:
    metrics = _metrics(total=10)
    metrics["feedback_distribution"]["accepted"] = 0
    metrics["rates"]["acceptance_rate"] = 1.0

    metrics_path = tmp_path / "contradictory.json"
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")

    result = _run_pipeline(metrics_path)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["decision"] == "NOT_READY"
    assert any("Contradictory rate" in r for r in data["reasons"])


def test_pipeline_contradictory_rate_fail_closed(tmp_path: Path) -> None:
    metrics = _metrics(total=10)
    metrics["feedback_distribution"]["accepted"] = 7
    metrics["rates"]["acceptance_rate"] = 0.3

    metrics_path = tmp_path / "contradictory-rate.json"
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")

    result = _run_pipeline(metrics_path)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["decision"] == "NOT_READY"
    assert any("Contradictory rate" in r for r in data["reasons"])


def test_pipeline_invalid_rate_fail_closed(tmp_path: Path) -> None:
    metrics_low = _metrics(total=10)
    metrics_low["rates"]["acceptance_rate"] = -0.5

    metrics_high = _metrics(total=10)
    metrics_high["rates"]["acceptance_rate"] = 1.5

    for metrics, name in [(metrics_low, "low"), (metrics_high, "high")]:
        metrics_path = tmp_path / f"invalid-rate-{name}.json"
        metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
        result = _run_pipeline(metrics_path)
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["decision"] == "NOT_READY"
        assert any("is outside [0, 1] range" in r for r in data["reasons"])


def test_pipeline_negative_count_fail_closed(tmp_path: Path) -> None:
    metrics = _metrics(total=10)
    metrics["total_feedback_events"] = -5

    metrics_path = tmp_path / "negative-count.json"
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")

    result = _run_pipeline(metrics_path)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["decision"] == "NOT_READY"
    assert any("Negative count" in r for r in data["reasons"])


def test_pipeline_missing_required_count_fail_closed(tmp_path: Path) -> None:
    metrics = _metrics(total=10)
    metrics.pop("total_feedback_events")

    metrics_path = tmp_path / "missing-required.json"
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")

    result = _run_pipeline(metrics_path)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["decision"] == "NOT_READY"
    assert any("Missing required field: total_feedback_events" in r for r in data["reasons"])


def test_pipeline_unknown_fields_not_echoed(tmp_path: Path) -> None:
    metrics = _metrics(total=10)
    metrics["unknown_top_field"] = "SYNTHETIC_MARKER_TOP"
    metrics["feedback_distribution"]["unknown_nested"] = "SYNTHETIC_MARKER_NESTED"

    metrics_path = tmp_path / "unknown-fields.json"
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")

    # Check JSON output format compatibility
    result_json = _run_pipeline(metrics_path, "json")
    assert result_json.returncode == 0
    assert "SYNTHETIC_MARKER_TOP" not in result_json.stdout
    assert "SYNTHETIC_MARKER_NESTED" not in result_json.stdout

    # Check Markdown output format compatibility
    result_md = _run_pipeline(metrics_path, "markdown")
    assert result_md.returncode == 0
    assert "SYNTHETIC_MARKER_TOP" not in result_md.stdout
    assert "SYNTHETIC_MARKER_NESTED" not in result_md.stdout


def test_pipeline_valid_fixtures_preserve_behavior(tmp_path: Path) -> None:
    # Valid READY fixture remains READY
    metrics_ready = _metrics(total=10)
    path_ready = tmp_path / "ready.json"
    path_ready.write_text(json.dumps(metrics_ready), encoding="utf-8")
    res_ready = _run_pipeline(path_ready)
    assert res_ready.returncode == 0
    assert json.loads(res_ready.stdout)["decision"] == "READY"

    # Valid NOT_READY fixture remains NOT_READY
    metrics_not_ready = _metrics(total=10, acceptance_rate=0.4)
    path_not_ready = tmp_path / "not-ready.json"
    path_not_ready.write_text(json.dumps(metrics_not_ready), encoding="utf-8")
    res_not_ready = _run_pipeline(path_not_ready)
    assert res_not_ready.returncode == 1
    assert json.loads(res_not_ready.stdout)["decision"] == "NOT_READY"

    # Valid INSUFFICIENT_DATA fixture remains INSUFFICIENT_DATA
    metrics_insufficient = _metrics(total=4)
    path_insufficient = tmp_path / "insufficient.json"
    path_insufficient.write_text(json.dumps(metrics_insufficient), encoding="utf-8")
    res_insufficient = _run_pipeline(path_insufficient)
    assert res_insufficient.returncode == 1
    assert json.loads(res_insufficient.stdout)["decision"] == "INSUFFICIENT_DATA"


def test_pipeline_modes_and_cli_compat(tmp_path: Path) -> None:
    # Existing app.services.action_feedback_readiness modes remain compatible
    metrics_ready = _metrics(total=10)
    metrics_json_path = tmp_path / "cli-metrics.json"
    metrics_json_path.write_text(json.dumps(metrics_ready), encoding="utf-8")

    res1 = subprocess.run(
        [
            sys.executable,
            "app/services/action_feedback_readiness.py",
            "--metrics-json",
            str(metrics_json_path),
            "--format",
            "json",
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        text=True,
        capture_output=True,
    )
    assert res1.returncode == 0
    assert json.loads(res1.stdout)["decision"] == "READY"

    fixture_path = tmp_path / "cli-fixture.json"
    actions = [
        {"id": f"a-{i}", "status": "accepted", "action_type": "habit", "rule_id": "rule-sleep"}
        for i in range(6)
    ]
    outcomes = [{"action_id": "a-0", "outcome_label": "improved"}]
    fixture_path.write_text(json.dumps({"actions": actions, "outcomes": outcomes}), encoding="utf-8")

    res2 = subprocess.run(
        [
            sys.executable,
            "app/services/action_feedback_readiness.py",
            "--fixture",
            str(fixture_path),
            "--format",
            "json",
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        text=True,
        capture_output=True,
    )
    assert res2.returncode == 0
    assert json.loads(res2.stdout)["decision"] == "READY"
