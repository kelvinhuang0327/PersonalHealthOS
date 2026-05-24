# P41 – Risk Engine UUID Hygiene Fix

**Stage**: P41  
**Classification**: P41_RISK_ENGINE_UUID_HYGIENE_FIXED  
**Status**: COMPLETE  
**Branch**: main  
**Commits**: `d7be418` (fix), `7592ca0` (tests)  
**Date**: 2026-05-24  

---

## Summary

`_make_alert` in `risk_engine.py` received `str` UUID values (from callers that pass `str(current_user.id)`) but passed them directly into a `RiskAlert` ORM column typed `UUID(as_uuid=True)`. On SQLite this crashed with `StatementError: 'str' object has no attribute 'hex'`. PostgreSQL/psycopg2 silently coerced the string, masking the bug.

This was **R4** from the P40 parity smoke audit (reclassified from "PostgreSQL-only safe" to "latent type smell / SQLite crash").

---

## Root Cause

```python
# api/metrics.py:34
evaluate_metric_risks(str(current_user.id), ...)   # str UUID

# api/documents.py:122
evaluate_lab_item_risks(str(current_user.id), ...)  # str UUID

# risk_engine.py (pre-fix) _make_alert:
return RiskAlert(user_id=user_id, ...)              # user_id is str → crash on SQLite
```

SQLAlchemy's `UUID(as_uuid=True)` calls `.hex` on the value; strings have no `.hex` attribute.

---

## Fix Applied (`risk_engine.py`)

Added `import uuid` and str→UUID coercion at the entry point of `_make_alert`:

```python
import uuid

def _make_alert(user_id: uuid.UUID | str, ...) -> RiskAlert:
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)    # coerce str to UUID object
    return RiskAlert(user_id=user_id, ...)
```

Both public functions updated to annotate `user_id: uuid.UUID | str` to signal they accept either form. Callers (`metrics.py`, `documents.py`) are **not changed** — the coercion handles them.

---

## P35 Mock Removal

The P35 audit (`test_metrics_symptoms_response_leakage.py`) had 4 test functions with `unittest.mock.patch` wrapping `evaluate_metric_risks` solely to prevent the SQLite crash. These mocks were removed:

- `test_create_metric_status_201`
- `test_create_metric_no_user_id`
- `test_create_metric_no_sensitive_keys`
- `test_metric_response_fields`

All 15 tests in that file pass without mocks. The test payloads (`heart_rate=72`) trigger no alerts, so `evaluate_metric_risks` returns `[]` for these inputs.

---

## Regression Coverage

### New: `test_risk_engine_uuid_hygiene.py` (8 tests)

| Test | Validates |
|------|-----------|
| `TestMetricRisksUUIDHygiene::test_metric_str_uuid_no_crash` | str UUID does not crash on SQLite |
| `TestMetricRisksUUIDHygiene::test_metric_alert_user_id_is_uuid` | RiskAlert.user_id is a UUID object after coercion |
| `TestMetricRisksUUIDHygiene::test_metric_uuid_object_still_works` | UUID object input still works |
| `TestMetricRisksUUIDHygiene::test_metric_alert_user_id_matches` | Coerced UUID value matches original |
| `TestNoAlertForNormalMetrics::test_no_alert_for_normal_heart_rate` | Normal heart rate → no alerts |
| `TestNoAlertForNormalMetrics::test_none_profile_returns_no_bmi_alert` | `profile=None` → no BMI alert |
| `TestLabItemRisksUUIDHygiene::test_lab_str_uuid_no_crash` | Lab path str UUID does not crash |
| `TestLabItemRisksUUIDHygiene::test_lab_alert_user_id_is_uuid` | Lab RiskAlert.user_id is UUID |

---

## Test Results

| Suite | Result |
|-------|--------|
| `test_risk_engine_uuid_hygiene.py` | **8/8 passed** |
| `test_metrics_symptoms_response_leakage.py` | **15/15 passed** |
| `test_postgresql_parity.py` | **11/11 passed** |
| `make runtime-smoke` (Stage 1–4) | **113 passed, 2 skipped** |
| Full backend suite | **949 passed, 2 skipped** |

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/risk_engine.py` | Added `import uuid`, str→UUID coercion in `_make_alert`, updated type annotations |
| `backend/tests/test_risk_engine_uuid_hygiene.py` | **NEW** — 8 regression tests |
| `backend/tests/test_metrics_symptoms_response_leakage.py` | Removed 4 stale `unittest.mock.patch` blocks |

---

## Security Impact

- **Attack surface**: None changed. No new endpoints, no auth changes.
- **Data integrity**: Prevents silent type mismatch between callers and ORM. UUID values are now guaranteed correct type before persistence.
- **Cross-database parity**: SQLite and PostgreSQL both persist `RiskAlert` without crash or silent coercion.
