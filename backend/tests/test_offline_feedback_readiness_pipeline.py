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
