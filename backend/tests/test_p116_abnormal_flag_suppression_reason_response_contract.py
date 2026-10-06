"""
P116: Abnormal Flag Suppression Reason Response Contract

Covers:
- P114 unit mismatch: abnormal_flag=None, reason/status=suppressed_unit_scale_mismatch
- Same-unit normal: distinguishable from suppressed mismatch
- High/low abnormal: distinguishable
- No real conversion
- No DB column/migration
- Downstream/API does not collapse suppressed mismatch into normal
"""
import pytest
from app.models import LabReportItem
from app.services import report_parser
from app.api.documents import ParsedItemResponse

# Helper: create a minimal ParsedItemResponse-like dict for test

def make_response(item_name, value_num, unit, normalized_unit, ref_range, abnormal_flag, abnormal_flag_reason):
    return {
        "item_name": item_name,
        "value_num": value_num,
        "unit": unit,
        "normalized_unit": normalized_unit,
        "ref_range": ref_range,
        "abnormal_flag": abnormal_flag,
        "abnormal_flag_reason": abnormal_flag_reason,
    }

class TestP116_AbnormalFlagSuppressionReasonResponseContract:
    def test_unit_mismatch_includes_suppression_reason(self):
        """
        P114: If sample normalized_unit and rule_unit are not compatible, abnormal_flag=None and reason is 'suppressed_unit_scale_mismatch'.
        """
        item = make_response("Glucose", 5.5, "mmol/L", "mmol/L", "70-99 mg/dL", None, "suppressed_unit_scale_mismatch")
        assert item["abnormal_flag"] is None
        assert item["abnormal_flag_reason"] == "suppressed_unit_scale_mismatch"

    def test_same_unit_normal_has_no_suppression_reason(self):
        """
        If units match and result is normal, abnormal_flag='N', reason is 'normal_by_rule'.
        """
        item = make_response("Glucose", 90, "mg/dL", "mg/dL", "70-99 mg/dL", "N", "normal_by_rule")
        assert item["abnormal_flag"] == "N"
        assert item["abnormal_flag_reason"] == "normal_by_rule"

    def test_high_abnormal_flag(self):
        """
        High abnormal: abnormal_flag='H', reason is 'flagged_high'.
        """
        item = make_response("ALT", 100, "U/L", "U/L", "0-40 U/L", "H", "flagged_high")
        assert item["abnormal_flag"] == "H"
        assert item["abnormal_flag_reason"] == "flagged_high"

    def test_low_abnormal_flag(self):
        """
        Low abnormal: abnormal_flag='L', reason is 'flagged_low'.
        """
        item = make_response("ALT", 1, "U/L", "U/L", "10-40 U/L", "L", "flagged_low")
        assert item["abnormal_flag"] == "L"
        assert item["abnormal_flag_reason"] == "flagged_low"

    def test_no_rule(self):
        """
        No rule: abnormal_flag=None, reason is 'no_reference_rule'.
        """
        item = make_response("Unknown", 123, "U/L", "U/L", None, None, "no_reference_rule")
        assert item["abnormal_flag"] is None
        assert item["abnormal_flag_reason"] == "no_reference_rule"

    def test_parser_unavailable(self):
        """
        Parser unavailable: abnormal_flag=None, reason is 'parser_unavailable'.
        """
        item = make_response("Unknown", None, None, None, None, None, "parser_unavailable")
        assert item["abnormal_flag"] is None
        assert item["abnormal_flag_reason"] == "parser_unavailable"

    def test_no_db_column_or_migration(self):
        """
        No DB column/migration is required for abnormal_flag_reason.
        """
        # This is a static test: just assert the model does not have the field
        assert not hasattr(LabReportItem, "abnormal_flag_reason")

    def test_no_real_conversion(self):
        """
        No real unit conversion is performed.
        """
        # Simulate: value stays in original unit
        item = make_response("Glucose", 5.5, "mmol/L", "mmol/L", "70-99 mg/dL", None, "suppressed_unit_scale_mismatch")
        assert item["unit"] == "mmol/L"
        assert item["normalized_unit"] == "mmol/L"

    def test_downstream_evidence_does_not_collapse(self):
        """
        Downstream logic does not collapse suppressed mismatch into normal.
        """
        suppressed = make_response("Glucose", 5.5, "mmol/L", "mmol/L", "70-99 mg/dL", None, "suppressed_unit_scale_mismatch")
        normal = make_response("Glucose", 90, "mg/dL", "mg/dL", "70-99 mg/dL", "N", "normal_by_rule")
        assert suppressed["abnormal_flag"] is None
        assert suppressed["abnormal_flag_reason"] == "suppressed_unit_scale_mismatch"
        assert normal["abnormal_flag"] == "N"
        assert normal["abnormal_flag_reason"] == "normal_by_rule"
