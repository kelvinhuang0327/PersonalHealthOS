"""Offline feedback outcome metrics for synthetic/local-safe fixtures.

This module deliberately has no database dependency.  It accepts plain dicts
or lightweight objects so tests and CLI fixtures can run without touching
runtime data.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable


_ACCEPTED_STATUSES = frozenset({"accepted", "done", "completed", "in_progress"})
_NOT_USEFUL_STATUSES = frozenset({"not_useful"})
_NOT_APPLICABLE_STATUSES = frozenset({"not_applicable"})
_SNOOZED_STATUSES = frozenset({"snoozed"})
_PENDING_STATUSES = frozenset({"todo", "pending", "tracking"})

_IMPROVED_LABELS = frozenset({"improved"})
_UNCHANGED_LABELS = frozenset({"no_change", "unchanged"})
_WORSE_LABELS = frozenset({"worse", "deteriorated"})


@dataclass(frozen=True)
class _ActionRecord:
    id: str | None
    status: str
    action_type: str | None
    rule_id: str | None
    impact_status: str | None


@dataclass(frozen=True)
class _OutcomeRecord:
    action_id: str | None
    outcome_label: str


def build_offline_feedback_metrics(
    actions: Iterable[Any],
    outcomes: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic feedback metrics from synthetic action/outcome rows.

    The resulting shape is intentionally JSON-serializable and stable:
    breakdown keys are sorted, rates are rounded to four decimals, and missing
    optional fields simply omit per-rule/per-action-type groups.
    """
    action_rows = [_normalize_action(action) for action in actions]
    outcome_rows = [_normalize_outcome(outcome) for outcome in (outcomes or [])]

    total_feedback_events = len(action_rows)
    status_counts = Counter(row.status for row in action_rows)
    feedback_counts = Counter(_feedback_bucket(row.status) for row in action_rows)
    outcome_counts = _count_outcomes(action_rows, outcome_rows)

    accepted_count = feedback_counts["accepted"]
    not_useful_count = feedback_counts["not_useful"]
    snoozed_count = feedback_counts["snoozed"]

    return {
        "total_feedback_events": total_feedback_events,
        "feedback_status_counts": _sorted_counter(status_counts),
        "feedback_distribution": _ordered_distribution(
            feedback_counts,
            ["accepted", "not_useful", "snoozed", "not_applicable", "pending", "other"],
        ),
        "outcome_status_counts": _ordered_distribution(
            outcome_counts,
            ["improved", "unchanged", "worse", "unknown"],
        ),
        "rates": {
            "acceptance_rate": _rate(accepted_count, total_feedback_events),
            "not_useful_rate": _rate(not_useful_count, total_feedback_events),
            "snooze_rate": _rate(snoozed_count, total_feedback_events),
        },
        "per_action_type": _acceptance_breakdown(action_rows, "action_type"),
        "per_rule": _acceptance_breakdown(action_rows, "rule_id"),
    }


def _normalize_action(action: Any) -> _ActionRecord:
    return _ActionRecord(
        id=_as_optional_str(_get(action, "id")),
        status=_as_status(_get(action, "feedback_status", _get(action, "status", "unknown"))),
        action_type=_as_optional_str(_get(action, "action_type")),
        rule_id=_as_optional_str(_get(action, "rule_id")),
        impact_status=_as_optional_str(_get(action, "impact_status")),
    )


def _normalize_outcome(outcome: Any) -> _OutcomeRecord:
    return _OutcomeRecord(
        action_id=_as_optional_str(_get(outcome, "action_id")),
        outcome_label=_as_status(_get(outcome, "outcome_label", _get(outcome, "outcome_status", "unknown"))),
    )


def _get(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_status(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    return text or "unknown"


def _feedback_bucket(status: str) -> str:
    if status in _ACCEPTED_STATUSES:
        return "accepted"
    if status in _NOT_USEFUL_STATUSES:
        return "not_useful"
    if status in _SNOOZED_STATUSES:
        return "snoozed"
    if status in _NOT_APPLICABLE_STATUSES:
        return "not_applicable"
    if status in _PENDING_STATUSES:
        return "pending"
    return "other"


def _outcome_bucket(label: str | None) -> str:
    normalized = _as_status(label)
    if normalized in _IMPROVED_LABELS:
        return "improved"
    if normalized in _UNCHANGED_LABELS:
        return "unchanged"
    if normalized in _WORSE_LABELS:
        return "worse"
    return "unknown"


def _count_outcomes(
    actions: list[_ActionRecord],
    outcomes: list[_OutcomeRecord],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for outcome in outcomes:
        counts[_outcome_bucket(outcome.outcome_label)] += 1

    outcome_action_ids = {outcome.action_id for outcome in outcomes if outcome.action_id}
    for action in actions:
        if action.impact_status and action.id not in outcome_action_ids:
            counts[_outcome_bucket(action.impact_status)] += 1

    return counts


def _acceptance_breakdown(
    actions: list[_ActionRecord],
    field_name: str,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for action in actions:
        key = getattr(action, field_name)
        if key:
            grouped[key][_feedback_bucket(action.status)] += 1

    result: dict[str, dict[str, Any]] = {}
    for key in sorted(grouped):
        counts = grouped[key]
        total = sum(counts.values())
        result[key] = {
            "total": total,
            "accepted": counts["accepted"],
            "not_useful": counts["not_useful"],
            "snoozed": counts["snoozed"],
            "acceptance_rate": _rate(counts["accepted"], total),
        }
    return result


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _sorted_counter(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _ordered_distribution(counter: Counter[str], ordered_keys: list[str]) -> dict[str, int]:
    result = {key: counter[key] for key in ordered_keys if counter[key]}
    for key in sorted(set(counter) - set(ordered_keys)):
        result[key] = counter[key]
    return result
