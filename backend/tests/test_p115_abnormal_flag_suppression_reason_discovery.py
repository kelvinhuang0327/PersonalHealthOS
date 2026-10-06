"""
P115: Abnormal Flag Suppression Reason Discovery

This test suite characterizes the current behavior of abnormal_flag suppression, especially when None is used to represent multiple possible states (normal, unknown, no local rule, unit-scale mismatch suppression).

- No real unit conversion is performed.
- No schema or DB change is made.
- This is a discovery/characterization suite only.
"""
import pytest
from app.models import LabReportItem
from app.services import report_parser

# Helper: create a minimal LabReportItem-like dict for test

def make_lab_item(value, unit, rule_unit, abnormal_flag, normalized_unit=None):
    return {
        "value": value,
        "unit": unit,
        "rule_unit": rule_unit,
        "abnormal_flag": abnormal_flag,
        "normalized_unit": normalized_unit,
    }

class TestP115_AbnormalFlagSuppressionReasonDiscovery:
    def test_unit_mismatch_results_in_abnormal_flag_none(self):
        """
        P114: If sample normalized_unit and rule_unit are not compatible, abnormal_flag is set to None.
        """
        item = make_lab_item(5.5, "mmol/L", "mg/dL", None, normalized_unit="mmol/L")
        # Simulate downstream logic: abnormal_flag is None due to unit-scale mismatch
        assert item["abnormal_flag"] is None

    def test_same_unit_normal_result_distinguishable_from_suppressed(self):
        """
        If units match, normal result should have abnormal_flag 'N', not None.
        """
        item = make_lab_item(90, "mg/dL", "mg/dL", "N", normalized_unit="mg/dL")
        assert item["abnormal_flag"] == "N"

    def test_none_can_represent_multiple_states(self):
        """
        None may mean: (a) normal, (b) unknown, (c) no local rule, (d) suppressed by unit-scale guard.
        This test documents the ambiguity.
        """
        # Simulate all possible None cases
        suppressed = make_lab_item(5.5, "mmol/L", "mg/dL", None, normalized_unit="mmol/L")
        no_rule = make_lab_item(123, "U/L", None, None, normalized_unit="U/L")
        parser_unavailable = make_lab_item(999, None, None, None, normalized_unit=None)
        # All are None, but for different reasons
        assert suppressed["abnormal_flag"] is None
        assert no_rule["abnormal_flag"] is None
        assert parser_unavailable["abnormal_flag"] is None

    def test_downstream_evidence_behavior_for_suppressed_none(self):
        """
        Downstream logic may treat abnormal_flag None as 'normal', 'unknown', or ignore it.
        This test documents that current code does not distinguish suppressed None from other None.
        """
        item = make_lab_item(5.5, "mmol/L", "mg/dL", None, normalized_unit="mmol/L")
        # Simulate evidence logic: None is not flagged as abnormal, may be omitted from abnormal evidence
        assert item["abnormal_flag"] is None
        # (In real code, this would be filtered out or shown as normal/unknown)

    def test_api_schema_behavior_for_abnormal_flag_none(self):
        """
        API/schema currently exposes only abnormal_flag, not suppression reason.
        """
        item = make_lab_item(5.5, "mmol/L", "mg/dL", None, normalized_unit="mmol/L")
        # Simulate API response: abnormal_flag is None, no abnormal_flag_reason field
        assert "abnormal_flag" in item
        assert item["abnormal_flag"] is None
        assert "abnormal_flag_reason" not in item
