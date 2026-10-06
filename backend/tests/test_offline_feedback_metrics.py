from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from app.services.offline_feedback_metrics import build_offline_feedback_metrics


def _synthetic_actions() -> list[dict[str, object]]:
    return [
        {
            "id": "action-1",
            "status": "done",
            "action_type": "lifestyle",
            "rule_id": "rule-ast-high",
            "impact_status": "improved",
        },
        {
            "id": "action-2",
            "status": "not_useful",
            "action_type": "lifestyle",
            "rule_id": "rule-ast-high",
        },
        {
            "id": "action-3",
            "status": "snoozed",
            "action_type": "monitor",
            "rule_id": "rule-bp-high",
        },
        {
            "id": "action-4",
            "status": "in_progress",
            "action_type": "monitor",
            "rule_id": "rule-bp-high",
            "impact_status": "no_change",
        },
        {
            "id": "action-5",
            "status": "not_applicable",
            "action_type": "follow_up",
        },
        {
            "id": "action-6",
            "status": "todo",
            "action_type": "habit",
            "rule_id": "rule-sleep",
        },
    ]


def test_build_offline_feedback_metrics_counts_and_rates_are_deterministic():
    metrics = build_offline_feedback_metrics(
        actions=_synthetic_actions(),
        outcomes=[
            {"action_id": "action-1", "outcome_label": "improved"},
            {"action_id": "action-4", "outcome_label": "no_change"},
            {"action_id": "action-x", "outcome_label": "worse"},
        ],
    )

    assert metrics == {
        "total_feedback_events": 6,
        "feedback_status_counts": {
            "done": 1,
            "in_progress": 1,
            "not_applicable": 1,
            "not_useful": 1,
            "snoozed": 1,
            "todo": 1,
        },
        "feedback_distribution": {
            "accepted": 2,
            "not_useful": 1,
            "snoozed": 1,
            "not_applicable": 1,
            "pending": 1,
        },
        "outcome_status_counts": {
            "improved": 1,
            "unchanged": 1,
            "worse": 1,
        },
        "rates": {
            "acceptance_rate": 0.3333,
            "not_useful_rate": 0.1667,
            "snooze_rate": 0.1667,
        },
        "per_action_type": {
            "follow_up": {
                "total": 1,
                "accepted": 0,
                "not_useful": 0,
                "snoozed": 0,
                "acceptance_rate": 0.0,
            },
            "habit": {
                "total": 1,
                "accepted": 0,
                "not_useful": 0,
                "snoozed": 0,
                "acceptance_rate": 0.0,
            },
            "lifestyle": {
                "total": 2,
                "accepted": 1,
                "not_useful": 1,
                "snoozed": 0,
                "acceptance_rate": 0.5,
            },
            "monitor": {
                "total": 2,
                "accepted": 1,
                "not_useful": 0,
                "snoozed": 1,
                "acceptance_rate": 0.5,
            },
        },
        "per_rule": {
            "rule-ast-high": {
                "total": 2,
                "accepted": 1,
                "not_useful": 1,
                "snoozed": 0,
                "acceptance_rate": 0.5,
            },
            "rule-bp-high": {
                "total": 2,
                "accepted": 1,
                "not_useful": 0,
                "snoozed": 1,
                "acceptance_rate": 0.5,
            },
            "rule-sleep": {
                "total": 1,
                "accepted": 0,
                "not_useful": 0,
                "snoozed": 0,
                "acceptance_rate": 0.0,
            },
        },
    }


def test_build_offline_feedback_metrics_accepts_object_records_and_impact_only_outcomes():
    actions = [
        SimpleNamespace(id="a1", status="accepted", action_type="habit", rule_id="rule-sleep", impact_status="unchanged"),
        SimpleNamespace(id="a2", status="not_useful", action_type="habit", rule_id="rule-sleep", impact_status="improved"),
    ]

    metrics = build_offline_feedback_metrics(actions=actions)

    assert metrics["total_feedback_events"] == 2
    assert metrics["feedback_distribution"] == {"accepted": 1, "not_useful": 1}
    assert metrics["outcome_status_counts"] == {"improved": 1, "unchanged": 1}
    assert metrics["per_rule"]["rule-sleep"]["acceptance_rate"] == 0.5


def test_offline_feedback_metrics_cli_outputs_sorted_json(tmp_path: Path):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        json.dumps(
            {
                "actions": _synthetic_actions(),
                "outcomes": [
                    {"action_id": "action-1", "outcome_label": "improved"},
                    {"action_id": "action-4", "outcome_label": "no_change"},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "scripts/offline_feedback_metrics.py", str(fixture)],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        text=True,
        capture_output=True,
    )

    metrics = json.loads(result.stdout)
    assert list(metrics) == [
        "feedback_distribution",
        "feedback_status_counts",
        "outcome_status_counts",
        "per_action_type",
        "per_rule",
        "rates",
        "total_feedback_events",
    ]
    assert metrics["rates"]["acceptance_rate"] == 0.3333
    assert metrics["outcome_status_counts"] == {"improved": 1, "unchanged": 1}
