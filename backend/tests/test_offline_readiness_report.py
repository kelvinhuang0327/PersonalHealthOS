from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.services.action_feedback_readiness import (
    OfflineReadinessThresholds,
    evaluate_offline_feedback_readiness,
)


def _make_metrics(
    total=6,
    acceptance_rate=0.6,
    not_useful_rate=0.1,
    snooze_rate=0.1,
    improved=3,
    unchanged=1,
    worse=1,
):
    return {
        "total_feedback_events": total,
        "rates": {
            "acceptance_rate": acceptance_rate,
            "not_useful_rate": not_useful_rate,
            "snooze_rate": snooze_rate,
        },
        "feedback_distribution": {
            "accepted": int(total * acceptance_rate),
            "not_useful": int(total * not_useful_rate),
            "snoozed": int(total * snooze_rate),
        },
        "outcome_status_counts": {
            "improved": improved,
            "unchanged": unchanged,
            "worse": worse,
        },
    }


def test_offline_readiness_insufficient_data():
    metrics = _make_metrics(total=4)
    thresholds = OfflineReadinessThresholds(min_feedback_events=5)
    result = evaluate_offline_feedback_readiness(metrics, thresholds)
    assert result.decision == "INSUFFICIENT_DATA"
    assert len(result.reasons) == 1
    assert "total_feedback_events (4) < min_feedback_events (5)" in result.reasons[0]


def test_offline_readiness_not_ready_low_acceptance():
    metrics = _make_metrics(total=10, acceptance_rate=0.4)
    thresholds = OfflineReadinessThresholds(min_feedback_events=5, min_acceptance_rate=0.5)
    result = evaluate_offline_feedback_readiness(metrics, thresholds)
    assert result.decision == "NOT_READY"
    assert any("acceptance_rate (0.4) < min_acceptance_rate (0.5)" in r for r in result.reasons)


def test_offline_readiness_not_ready_high_not_useful():
    metrics = _make_metrics(total=10, not_useful_rate=0.4)
    thresholds = OfflineReadinessThresholds(min_feedback_events=5, max_not_useful_rate=0.3)
    result = evaluate_offline_feedback_readiness(metrics, thresholds)
    assert result.decision == "NOT_READY"
    assert any("not_useful_rate (0.4) > max_not_useful_rate (0.3)" in r for r in result.reasons)


def test_offline_readiness_not_ready_high_snooze():
    metrics = _make_metrics(total=10, snooze_rate=0.4)
    thresholds = OfflineReadinessThresholds(min_feedback_events=5, max_snooze_rate=0.3)
    result = evaluate_offline_feedback_readiness(metrics, thresholds)
    assert result.decision == "NOT_READY"
    assert any("snooze_rate (0.4) > max_snooze_rate (0.3)" in r for r in result.reasons)


def test_offline_readiness_not_ready_low_improvement():
    metrics = _make_metrics(total=10, improved=1, unchanged=3, worse=1)
    thresholds = OfflineReadinessThresholds(min_feedback_events=5, min_improvement_rate=0.5)
    result = evaluate_offline_feedback_readiness(metrics, thresholds)
    assert result.decision == "NOT_READY"
    # improvement_rate = 1 / 5 = 0.2
    assert any("improvement_rate (0.2) < min_improvement_rate (0.5)" in r for r in result.reasons)


def test_offline_readiness_ready():
    metrics = _make_metrics(total=10, acceptance_rate=0.7, not_useful_rate=0.1, snooze_rate=0.1, improved=4, unchanged=1, worse=0)
    thresholds = OfflineReadinessThresholds(
        min_feedback_events=5,
        min_acceptance_rate=0.5,
        max_not_useful_rate=0.3,
        max_snooze_rate=0.3,
        min_improvement_rate=0.5,
    )
    result = evaluate_offline_feedback_readiness(metrics, thresholds)
    assert result.decision == "READY"
    assert result.reasons == ["All synthetic offline feedback metrics meet or exceed readiness thresholds"]


def test_offline_readiness_cli_json(tmp_path: Path):
    fixture = tmp_path / "fixture.json"
    actions = [
        {"id": f"a-{i}", "status": "accepted" if i < 4 else "not_useful", "action_type": "habit", "rule_id": "rule-sleep"}
        for i in range(6)
    ]
    # 4/6 accepted = 0.6667 acceptance rate, 2/6 not useful = 0.3333 not useful rate.
    # Note: 0.3333 not useful rate exceeds default threshold of 0.3, so decision should be NOT_READY.
    fixture.write_text(json.dumps({"actions": actions, "outcomes": []}), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "app/services/action_feedback_readiness.py",
            "--fixture",
            str(fixture),
            "--format",
            "json",
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        text=True,
        capture_output=True,
    )

    # NOT_READY decision returns exit code 1
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["decision"] == "NOT_READY"
    assert "metrics_summary" in data
    assert "thresholds" in data
    assert "reasons" in data
    assert any("not_useful_rate (0.3333) > max_not_useful_rate (0.3)" in r for r in data["reasons"])


def test_offline_readiness_cli_markdown(tmp_path: Path):
    fixture = tmp_path / "fixture.json"
    # Meet all thresholds to return READY
    actions = [
        {"id": f"a-{i}", "status": "accepted", "action_type": "habit", "rule_id": "rule-sleep"}
        for i in range(6)
    ]
    fixture.write_text(json.dumps({"actions": actions, "outcomes": []}), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "app/services/action_feedback_readiness.py",
            "--fixture",
            str(fixture),
            "--format",
            "markdown",
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        text=True,
        capture_output=True,
    )

    # READY decision returns exit code 0
    assert result.returncode == 0
    assert "# Offline Action Feedback Readiness Report" in result.stdout
    assert "- Decision: **READY**" in result.stdout
    assert "All synthetic offline feedback metrics meet or exceed readiness thresholds" in result.stdout
