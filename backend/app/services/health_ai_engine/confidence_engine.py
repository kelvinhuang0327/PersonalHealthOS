from __future__ import annotations


def calibrate_confidence(
    metrics_count: int,
    labs_count: int,
    timeline_length: int,
    rule_coverage: float,
    base_confidence: float = 0.7,
) -> float:
    completeness = min(1.0, (metrics_count / 7.0) * 0.4 + (labs_count / 5.0) * 0.3 + (timeline_length / 30.0) * 0.3)
    coverage = max(0.0, min(1.0, rule_coverage))
    calibrated = 0.45 + (completeness * 0.3) + (coverage * 0.2) + (base_confidence * 0.05)
    return round(max(0.5, min(0.95, calibrated)), 2)


def combine_confidence(calibrated_confidence: float, rule_confidence: float | int | None) -> float:
    rule = float(rule_confidence or 0.7)
    return round(max(0.5, min(0.95, (calibrated_confidence * 0.6) + (rule * 0.4))), 2)
