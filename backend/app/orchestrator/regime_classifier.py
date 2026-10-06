"""
Regime Classifier — analyses recent task history to classify the orchestrator regime.

Regimes (adapted from SOURCE lottery signals to health-platform quality signals):
  ACTIVE     — healthy mix of COMPLETED tasks with PASS gate verdicts
  COLD       — mostly FAILED / REPLAN_REQUIRED; system is struggling
  SATURATED  — many completed tasks but gate verdicts increasingly non-PASS
  EXHAUSTED  — all/most recent tasks are INVALID_DELIVERY or POLICY_VIOLATION
  IDLE       — no recent tasks at all
"""
from __future__ import annotations

from typing import Any

# Gate verdict constants (mirrors common.py)
_GATE_PASS = 'PASS'
_GATE_INVALID_DELIVERY = 'INVALID_DELIVERY'
_GATE_FAILED_ACCEPTANCE = 'FAILED_ACCEPTANCE'
_GATE_POLICY_VIOLATION = 'POLICY_VIOLATION'
_GATE_WORKER_RUNTIME_FAILED = 'WORKER_RUNTIME_FAILED'

REGIME_ACTIVE = 'ACTIVE'
REGIME_COLD = 'COLD'
REGIME_SATURATED = 'SATURATED'
REGIME_EXHAUSTED = 'EXHAUSTED'
REGIME_IDLE = 'IDLE'


def classify_regime(tasks: list[dict[str, Any]], window: int = 20) -> dict[str, Any]:
    """
    Classify the current orchestrator regime based on recent task outcomes.

    Args:
        tasks: List of task dicts, most-recent first.
        window: Number of recent tasks to analyse.

    Returns:
        {
            'regime': str,
            'confidence': float,   # 0-1
            'reason': str,
            'stats': dict,
        }
    """
    recent = [t for t in tasks if t.get('status') not in ('QUEUED', 'RUNNING')][:window]
    if not recent:
        return {
            'regime': REGIME_IDLE,
            'confidence': 1.0,
            'reason': 'No finished tasks in recent history.',
            'stats': _empty_stats(),
        }

    total = len(recent)
    status_counts: dict[str, int] = {}
    gate_counts: dict[str, int] = {}
    for t in recent:
        s = t.get('status', 'UNKNOWN')
        status_counts[s] = status_counts.get(s, 0) + 1
        g = t.get('gate_verdict') or 'NONE'
        gate_counts[g] = gate_counts.get(g, 0) + 1

    completed = status_counts.get('COMPLETED', 0)
    failed = status_counts.get('FAILED', 0)
    replan = status_counts.get('REPLAN_REQUIRED', 0)
    cancelled = status_counts.get('CANCELLED', 0)

    gate_pass = gate_counts.get(_GATE_PASS, 0)
    gate_invalid = gate_counts.get(_GATE_INVALID_DELIVERY, 0)
    gate_policy = gate_counts.get(_GATE_POLICY_VIOLATION, 0)
    gate_runtime = gate_counts.get(_GATE_WORKER_RUNTIME_FAILED, 0)

    degrade_total = gate_invalid + gate_policy + gate_runtime
    failure_rate = (failed + replan) / total
    degradation_rate = degrade_total / total
    pass_rate = gate_pass / total

    stats = {
        'total': total,
        'completed': completed,
        'failed': failed,
        'replan_required': replan,
        'cancelled': cancelled,
        'gate_pass': gate_pass,
        'gate_invalid_delivery': gate_invalid,
        'gate_policy_violation': gate_policy,
        'gate_worker_runtime_failed': gate_runtime,
        'failure_rate': round(failure_rate, 2),
        'degradation_rate': round(degradation_rate, 2),
        'pass_rate': round(pass_rate, 2),
    }

    # EXHAUSTED: nearly all tasks have severe delivery failures
    if degradation_rate >= 0.7:
        return {
            'regime': REGIME_EXHAUSTED,
            'confidence': round(degradation_rate, 2),
            'reason': f'{int(degradation_rate * 100)}% of recent tasks failed delivery validation or violated policy.',
            'stats': stats,
        }

    # COLD: high failure/replan rate
    if failure_rate >= 0.6:
        return {
            'regime': REGIME_COLD,
            'confidence': round(failure_rate, 2),
            'reason': f'{int(failure_rate * 100)}% of recent tasks failed or required replanning.',
            'stats': stats,
        }

    # SATURATED: completing tasks but gate quality declining
    if completed >= max(1, total * 0.6) and pass_rate < 0.5:
        confidence = round(1 - pass_rate, 2)
        return {
            'regime': REGIME_SATURATED,
            'confidence': confidence,
            'reason': f'Tasks completing but gate quality degrading — only {int(pass_rate * 100)}% pass rate.',
            'stats': stats,
        }

    # ACTIVE: healthy
    return {
        'regime': REGIME_ACTIVE,
        'confidence': round(pass_rate, 2),
        'reason': f'{int(pass_rate * 100)}% gate pass rate across last {total} tasks.',
        'stats': stats,
    }


def _empty_stats() -> dict[str, Any]:
    return {
        'total': 0,
        'completed': 0,
        'failed': 0,
        'replan_required': 0,
        'cancelled': 0,
        'gate_pass': 0,
        'gate_invalid_delivery': 0,
        'gate_policy_violation': 0,
        'gate_worker_runtime_failed': 0,
        'failure_rate': 0.0,
        'degradation_rate': 0.0,
        'pass_rate': 0.0,
    }
