# P40 – PostgreSQL Parity Smoke

**Status:** `P40_POSTGRESQL_PARITY_VERIFIED`
**Date:** 2026-05-24
**Branch:** `main`
**HEAD at completion:** _(see git log)_

---

## Objective

Verify that the SQLAlchemy ORM layer functions correctly against a real
PostgreSQL 16 database.  All prior hardening tests (P13–P38) used SQLite
in-memory with `StaticPool`; this task provides evidence that production-path
behaviour (UUID, TIMESTAMPTZ, JSONB, FK cascade) works correctly.

---

## Environment

| Item | Value |
|---|---|
| PostgreSQL version | 16 (Docker `postgres:16`, also local Homebrew PG) |
| Python | 3.9.6 |
| SQLAlchemy | (see `requirements.txt`) |
| psycopg2 | bundled in `.venv` |
| Test database | `health_insights_test` on `127.0.0.1:5432` |
| Schema applied | `database/schema.sql` + all 9 migrations (001–009) |
| Connection string | `postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/health_insights_test?gssencmode=disable&sslmode=disable` |

### Setup Notes

There are two PostgreSQL processes on port 5432:
- Local Homebrew PostgreSQL (PID 2512) — `127.0.0.1:5432` — used by tests
- Docker container `health-insights-postgres-local` — `0.0.0.0:5432`

The local PostgreSQL is the primary connection target for Python tests.
macOS GSSAPI Kerberos must be bypassed with `?gssencmode=disable&sslmode=disable`
in the DSN; this is safe in a local dev context.

---

## Test Results

Test file: `backend/tests/test_postgresql_parity.py`

```
============================= test session starts ==============================
collected 11 items

tests/test_postgresql_parity.py ...........                              [100%]

============================== 11 passed in 0.54s ==============================
```

| # | Test | Class | Verdict |
|---|---|---|---|
| T1a | `test_select_one` | TestConnectivity | ✅ PASS |
| T1b | `test_uuid_extension` | TestConnectivity | ✅ PASS |
| T1c | `test_expected_tables_exist` | TestConnectivity | ✅ PASS |
| T2a | `test_insert_user_with_uuid_pk` | TestUserORM | ✅ PASS |
| T2b | `test_user_created_at_is_timestamptz` | TestUserORM | ✅ PASS |
| T3a | `test_insert_person_profile_uuid_fk` | TestPersonProfileORM | ✅ PASS |
| T4a | `test_insert_health_metric` | TestHealthMetricORM | ✅ PASS |
| T5a | `test_risk_alert_with_uuid_object_succeeds` | TestRiskAlertUUIDCoercion | ✅ PASS |
| T5b | `test_risk_alert_with_str_uuid_r4_behavior` | TestRiskAlertUUIDCoercion | ✅ PASS (coercion — see R4 below) |
| T6a | `test_delete_user_cascades_metric` | TestFKCascade | ✅ PASS |
| T7a | `test_jsonb_roundtrip` | TestJSONBColumn | ✅ PASS |

---

## R4 – UUID Coercion Verdict

**Risk:** `risk_engine._make_alert()` receives `user_id` as a `str` (callers
pass `str(current_user.id)`) but `RiskAlert.user_id` is
`Column(UUID(as_uuid=True), ...)`.

**Probe (T5b):** Passing a string UUID to the column on PostgreSQL succeeded —
psycopg2 coerces the string to the native PostgreSQL UUID type internally.

**Verdict:** R4 is a **latent type smell, not a runtime crash** on PostgreSQL.

| Backend | Behaviour |
|---|---|
| SQLite (StaticPool) | `StatementError: 'str' object has no attribute 'hex'` ← crash |
| PostgreSQL 16 / psycopg2 | String silently coerced — insert succeeds |

**Recommendation:** The fix (pass `UUID` object instead of `str`) remains
recommended to:
1. Fix the SQLite crash (relevant for CI runs and new test authors)
2. Align with the `UUID(as_uuid=True)` ORM contract
3. Prevent breakage if psycopg2 is replaced with psycopg3 (async driver) which
   has stricter type enforcement

**Scope:** Deferred to P41 (single-line fix in `metrics.py`, `documents.py`
plus annotation update in `risk_engine.py`).

---

## Other Findings

| Area | Finding | Severity |
|---|---|---|
| GSSAPI on macOS | Local psql/psycopg2 requires `gssencmode=disable` in DSN for local dev | Low / Dev-only |
| Dual PG on port 5432 | Homebrew PG binds before Docker; test suite must use local PG | Low / Known |
| schema.sql vs migrations | Two CREATE INDEX statements in schema.sql reference `ai_summaries` before that table is created; harmless (IF EXISTS equivalent via migrations). | Low / Cosmetic |
| JSONB account_settings | Round-trip correct — dict preserved faithfully | ✅ OK |
| TIMESTAMPTZ created_at | Server default applied by PostgreSQL correctly | ✅ OK |
| ON DELETE CASCADE | Verified with expire_all() to bypass ORM identity-map cache | ✅ OK |

---

## SQLite Baseline (unchanged)

```
make runtime-smoke
  Stage 1 (health):          3 passed, 4 warnings
  Stage 2 (security-smoke):  29 passed, 2 skipped, 4 warnings
  Stage 3 (config-smoke):    24 passed, 4 warnings
  Stage 4 (validation-smoke): 57 passed, 4 warnings
Total: 113 passed, 2 skipped  ✅ unchanged
```

---

## Classification

`P40_POSTGRESQL_PARITY_VERIFIED`

All 11 parity tests pass. No regressions in the SQLite suite.
Production path (UUID, TIMESTAMPTZ, JSONB, FK cascade) works correctly.
R4 is confirmed non-crashing on PostgreSQL (latent type smell only).

---

## Next Recommended Tasks

| Task | Description |
|---|---|
| P41 | Fix R4: pass UUID object (not str) to `evaluate_metric_risks` / `evaluate_lab_item_risks` callers |
| P42 | Add Makefile `postgres-smoke` target wrapping `test_postgresql_parity.py` |
| P43 | Resolve dual-PG port conflict documentation in `docs/DEVELOPMENT.md` |
