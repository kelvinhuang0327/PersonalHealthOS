from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.services.health_assistant_service import build_evidence_bundle, get_action_recommendations


def _utc(days_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


def _make_report(days_ago: int = 1):
    report = SimpleNamespace()
    report.id = uuid4()
    report.created_at = _utc(days_ago)
    report.report_date = _utc(days_ago).date()
    report.document_id = uuid4()
    return report


def _make_item(
    report_id,
    item_name: str,
    abnormal_flag: str | None,
    *,
    value_num: float = 7.0,
    unit: str = "mg/dL",
    normalized_unit: str | None = None,
    range_source: str = "default_rule",
    parser_confidence: float = 0.9,
):
    item = SimpleNamespace()
    item.id = uuid4()
    item.report_id = report_id
    item.item_name = item_name
    item.item_code = item_name.lower().replace(" ", "_")
    item.value_num = value_num
    item.value_text = None
    item.unit = unit
    item.normalized_unit = normalized_unit
    item.ref_range = "4.0-6.0"
    item.ref_low = 4.0
    item.ref_high = 6.0
    item.range_source = range_source
    item.abnormal_flag = abnormal_flag
    item.parser_confidence = parser_confidence
    return item


class _FakeQuery:
    def __init__(self, rows=None):
        self._rows = rows or []

    def filter(self, *a, **kw):
        return self

    def order_by(self, *a):
        return self

    def limit(self, n):
        return _FakeQuery(self._rows[:n])

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def count(self):
        return len(self._rows)


def _make_db(*, reports=None, lab_items=None, alerts=None):
    db = MagicMock()
    reports = reports or []
    lab_items = lab_items or []
    alerts = alerts or []

    from app.models.entities import (
        ActionOutcome,
        HealthAction,
        HealthInsight,
        HealthMetric,
        LabReport,
        LabReportItem,
        PersonProfile,
        RiskAlert,
        SymptomLog,
        UserProfile,
    )

    def query_dispatch(model):
        mapping = {
            UserProfile: _FakeQuery([]),
            PersonProfile: _FakeQuery([]),
            SymptomLog: _FakeQuery([]),
            HealthMetric: _FakeQuery([]),
            LabReport: _FakeQuery(reports),
            LabReportItem: _FakeQuery(lab_items),
            RiskAlert: _FakeQuery(alerts),
            HealthInsight: _FakeQuery([]),
            HealthAction: _FakeQuery([]),
            ActionOutcome: _FakeQuery([]),
        }
        return mapping.get(model, _FakeQuery([]))

    db.query.side_effect = query_dispatch
    return db


def test_suppressed_unit_scale_row_is_visible_via_not_judged_path_with_reason():
    report = _make_report()
    suppressed = _make_item(
        report.id,
        "Glucose",
        None,
        unit="mg/dL",
        normalized_unit="mmol/L",
        range_source="default_rule",
    )
    db = _make_db(reports=[report], lab_items=[suppressed])

    bundle = build_evidence_bundle(db, str(uuid4()), str(uuid4()))

    assert bundle["lab_report_items"] == []
    assert len(bundle["lab_not_judged_items"]) == 1
    row = bundle["lab_not_judged_items"][0]
    assert row["abnormal_flag_reason"] == "suppressed_unit_scale_mismatch"
    assert row["judgement"] == "uncertain"
    assert row["not_judged"] is True


def test_suppressed_row_does_not_inflate_abnormal_lab_count_or_abnormality_count():
    report = _make_report()
    suppressed = _make_item(
        report.id,
        "Glucose",
        None,
        unit="mg/dL",
        normalized_unit="mmol/L",
        range_source="default_rule",
    )
    db = _make_db(reports=[report], lab_items=[suppressed])

    bundle = build_evidence_bundle(db, str(uuid4()), str(uuid4()))

    assert bundle["summary"]["abnormal_lab_count"] == 0
    assert bundle["summary"]["lab_abnormality_count"] == 0
    assert bundle["summary"]["not_judged_lab_count"] == 1


def test_suppressed_row_does_not_raise_recommendation_severity_or_ranking():
    report = _make_report()
    suppressed = _make_item(
        report.id,
        "Glucose",
        None,
        unit="mg/dL",
        normalized_unit="mmol/L",
        range_source="default_rule",
    )
    db = _make_db(reports=[report], lab_items=[suppressed])

    recs = get_action_recommendations(db, str(uuid4()), str(uuid4()))

    # No abnormal-driven recommendation should be generated from suppressed rows.
    assert all(r["source_type"] not in {"lab_abnormality", "lab_report_item"} for r in recs["recommendations"])
    assert recs["evidence_bundle_summary"]["abnormal_lab_count"] == 0


def test_high_low_abnormal_rows_keep_existing_abnormal_evidence_behavior():
    report = _make_report()
    high_row = _make_item(report.id, "HbA1c", "H")
    low_row = _make_item(report.id, "HDL", "L")
    db = _make_db(reports=[report], lab_items=[high_row, low_row])

    bundle = build_evidence_bundle(db, str(uuid4()), str(uuid4()))

    assert len(bundle["lab_report_items"]) == 2
    assert bundle["summary"]["abnormal_lab_count"] == 2
    assert bundle["lab_not_judged_items"] == []
    assert {row["abnormal_flag"] for row in bundle["lab_report_items"]} == {"H", "L"}
    assert len(bundle["lab_abnormalities"]) >= 1


def test_non_suppressed_none_or_normal_rows_are_not_mislabeled_as_suppressed():
    report = _make_report()

    normal_by_rule = _make_item(
        report.id,
        "NormalMarker",
        "N",
        unit="mg/dL",
        normalized_unit="mg/dL",
        range_source="default_rule",
    )
    no_rule = _make_item(
        report.id,
        "NoRuleMarker",
        None,
        unit="mg/dL",
        normalized_unit=None,
        range_source="unknown",
    )
    parser_uncertain = _make_item(
        report.id,
        "ParserLowConfMarker",
        None,
        unit="mg/dL",
        normalized_unit=None,
        range_source="extracted",
        parser_confidence=0.4,
    )

    db = _make_db(reports=[report], lab_items=[normal_by_rule, no_rule, parser_uncertain])

    bundle = build_evidence_bundle(db, str(uuid4()), str(uuid4()))

    assert bundle["lab_not_judged_items"] == []
    reasons = {row["item_name"]: row["abnormal_flag_reason"] for row in bundle["lab_report_items"]}
    assert reasons["NormalMarker"] == "normal_by_rule"
    # None-flag rows without suppression reason must not leak into not-judged path.
    assert "NoRuleMarker" not in reasons
    assert "ParserLowConfMarker" not in reasons


def test_suppressed_evidence_path_is_independent_from_lab_abnormalities():
    report = _make_report()
    suppressed = _make_item(
        report.id,
        "SuppressedMarker",
        None,
        unit="mg/dL",
        normalized_unit="mmol/L",
        range_source="default_rule",
    )
    high_row = _make_item(report.id, "TrueAbnormalMarker", "H")

    db = _make_db(reports=[report], lab_items=[suppressed, high_row])

    bundle = build_evidence_bundle(db, str(uuid4()), str(uuid4()))

    abnormal_names = {row["labItemName"] for row in bundle["lab_abnormalities"]}
    not_judged_names = {row["item_name"] for row in bundle["lab_not_judged_items"]}

    assert "SuppressedMarker" in not_judged_names
    assert "SuppressedMarker" not in abnormal_names
    assert "TrueAbnormalMarker" in abnormal_names
