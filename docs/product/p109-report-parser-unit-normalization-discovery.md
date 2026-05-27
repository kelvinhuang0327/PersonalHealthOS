# P109 — Report Parser Unit Field Normalization at Ingest: Discovery

**Date:** 2026-05-27
**Classification:** `P109_BACKEND_NORMALIZED_UNIT_FIELD_RECOMMENDED`
**Branch:** `main`
**Preceded by:** P108 (frontend-only `normalizeUnitForCompare()`)

---

## 1. Pre-flight Result

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD | attached ✅ |
| P108 commit `a229d1c` | present ✅ |
| Dirty files | Only governance/roadmap files (CEO-Decision.md, CTO-Analysis.md, roadmap.md) ✅ |

---

## 2. Parser and Ingest Flow Map

```
PDF / image bytes
      │
      ▼
extract_text()                          ← report_parser.py:72
      │ raw_text (str)
      ▼
parse_lab_items(raw_text, gender)       ← report_parser.py:157
      │
      ├── GENERIC_LINE_PATTERN.match()  ← regex group(3) captures unit token
      │       unit = (match.group(3) or '').strip() or None   ← line 171
      │       *** NO normalization applied here ***
      │
      ├── normalize_item_name(raw_name) ← name alias resolution (ALIAS_MAP)
      │
      ├── parse_reference_range()       ← parses ref range string
      │
      └── returns list[dict] with keys:
              item_name, item_code, value_num, value_text,
              unit ← raw captured string, untouched
              ref_range, ref_low, ref_high, range_source,
              abnormal_flag, parser_confidence

      │ list[dict]
      ▼
documents.py: parse_document() endpoint ← documents.py:113-118
      │
      │  for row in extracted:
      │      item = LabReportItem(report_id=report.id, **row)
      │      db.add(item)
      │
      ▼
LabReportItem.unit column               ← entities.py:168
      String(30) — stores whatever parser returned, verbatim
      *** NO normalization at ingest ***

      │ item.unit (raw string)
      ▼
GET /documents/lab-history              ← documents.py:379
      │  'unit': item.unit              ← raw string passed to frontend
      ▼
Frontend: normalizeUnitForCompare()     ← lab-unit-normalization.ts:16
      *** Only safety net for alias comparison ***
```

---

## 3. Current Unit Handling Behavior

### 3.1 GENERIC_LINE_PATTERN unit capture

The regex at `report_parser.py:41-46` captures unit via:
```
([A-Za-z/%\.μµ]+)?
```

- `μ` (U+03BC, Greek mu) and `µ` (U+00B5, micro sign) are both in the character class.
- The captured group is stripped of whitespace but **not normalized**.
- A PDF reporting `μmol/L` stores `μmol/L`; a PDF reporting `µmol/L` stores `µmol/L`; a PDF with OCR rendering `umol/L` stores `umol/L` — three distinct strings for the same unit.
- `IU/L` stores as `IU/L`; `U/L` stores as `U/L` — two distinct strings.

### 3.2 Name normalization exists, unit normalization does not

`normalize_item_name()` at `report_parser.py:84` resolves item name aliases via `ALIAS_MAP` (e.g., `GPT` → `ALT`). No parallel function exists for unit strings.

### 3.3 Ingest path is a blind pass-through

`parse_document()` at `documents.py:115-118` unpacks the parser dict directly into `LabReportItem(**row)`. The `unit` key is never touched between parser output and DB write.

### 3.4 Reference range lookup uses unit passively

`infer_reference_range()` at `report_parser.py:121` accepts `unit` and may fall back to `ref_unit = rule.get('unit') or unit`. If the stored unit is `IU/L` but the config file has `U/L`, the reference range is still resolved by item name (not unit), so this is not a correctness risk — but it reveals that unit is already treated as a secondary hint.

### 3.5 Frontend is the only current normalization point

`normalizeUnitForCompare()` in `frontend/lib/lab-unit-normalization.ts` handles:
- `IU/L` → `U/L` (and lowercase variants)
- Unicode `μ` / `µ` prefix → ASCII `u`
- Trim + lowercase

This is applied at comparison time only. Raw `item.unit` is displayed as-is.

---

## 4. Storage and Display Safety Assessment

| Question | Finding |
|---|---|
| Does changing `unit` from `IU/L` → `U/L` hide original report wording? | **Yes** — if `unit` is the only field. Users see their lab report's original wording in the ParsedItems drawer; changing the stored unit would silently alter displayed text. |
| Does changing `μmol/L` → `umol/L` affect display? | **Yes** — same risk. A user who uploaded a PDF showing `μmol/L` would see `umol/L` in the UI. |
| Is changing only `unit` in-place safe for existing DB rows? | **No** — retroactive migration of existing `LabReportItem` rows would alter historical display strings with no audit trail. |
| Would normalization affect `ref_range` string? | **Yes** — `ref_range` is formatted with unit suffix (e.g., `>=0.9 U/L`). If `unit` is normalized in-place, `ref_range` would not change (it is built at parse time), creating inconsistency. |
| Is there a `display_unit` / `canonical_unit` split today? | **No** — only one `unit` column exists in `LabReportItem`. |

**Conclusion:** In-place mutation of `unit` at ingest or via migration is **not safe** without a dual-field schema.

---

## 5. Recommended P110 Architecture

### Option Comparison

| Option | Description | Safety | Complexity | Recommended |
|---|---|---|---|---|
| **A: Keep parser raw; frontend helper only** | Status quo. Frontend `normalizeUnitForCompare()` is the sole normalization layer. | Safe | None | No — DB drift will worsen over time; future backend queries (grouping, analytics) will fail on unit mismatch |
| **B: Parser canonicalizes `unit` field in-place** | Parser writes normalized value to the single `unit` column. | Unsafe — raw display string lost | Low | No — loses original wording |
| **C: Add `normalized_unit` field; preserve raw `unit`** | Schema adds `normalized_unit String(30)` to `LabReportItem`. Parser writes canonical form there; `unit` remains raw. | Safe — raw preserved | Medium (migration needed) | **YES — Recommended** |
| **D: Backend helper for comparison only; no storage change** | A Python `normalize_unit_for_compare()` used at query time in `get_lab_history` or analytics. No schema change. | Safe | Low | Partial — solves backend grouping without DB change, but does not prevent future drift or simplify indexing |

### P110 Recommendation: Option C

Add `normalized_unit` to `LabReportItem` schema and populate it at parse time alongside raw `unit`.

**Why Option C:**
- Raw `unit` is preserved for display — no UX regression.
- `normalized_unit` can be used for grouping, trending, and backend comparisons without frontend workarounds.
- Eliminates reliance on frontend as the only normalization gate.
- Enables future backend analytics (e.g., aggregate all `u/l` enzyme results) without ambiguity.
- `ref_range` display inconsistency is avoided since `unit` remains unchanged.
- A Alembic migration is required but low-risk: nullable column, backfilled on next parse.

**Normalization rules for `normalized_unit` (mirrors P108 frontend):**

| Input | Normalized |
|---|---|
| `IU/L` | `U/L` |
| `iu/l` | `U/L` |
| `μmol/L` (U+03BC) | `umol/L` |
| `µmol/L` (U+00B5) | `umol/L` |
| `mg/dL` | `mg/dL` (unchanged) |
| `mmol/L` | `mmol/L` (unchanged) |

Canonical form: preserve original case (e.g., `U/L` not `u/l`) after alias substitution — display-safe and consistent with lab conventions.

---

## 6. Backend Test Plan for P110

If P110 implements Option C, the following unit tests should be added to `backend/tests/test_report_parser_stage2.py`:

### 6.1 Unit normalization function tests

```python
# test that a new normalize_unit() helper produces canonical forms
@pytest.mark.parametrize("raw,expected", [
    ("IU/L",    "U/L"),
    ("iu/l",    "U/L"),
    ("IU/l",    "U/L"),
    ("μmol/L",  "umol/L"),   # U+03BC
    ("µmol/L",  "umol/L"),   # U+00B5
    ("umol/L",  "umol/L"),   # already canonical
    ("mg/dL",   "mg/dL"),    # must remain unchanged
    ("mmol/L",  "mmol/L"),   # must remain unchanged
    ("U/L",     "U/L"),      # already canonical
    (None,      None),        # null passthrough
    ("",        None),        # empty → None
])
def test_normalize_unit(raw, expected):
    assert normalize_unit(raw) == expected
```

### 6.2 Parser integration: normalized_unit populated

```python
def test_parse_lab_items_normalized_unit_iu_l():
    items = parse_lab_items("ALT 32 IU/L", gender=None)
    item = next(i for i in items if i['item_name'] == 'ALT')
    assert item['unit'] == 'IU/L'              # raw preserved
    assert item['normalized_unit'] == 'U/L'    # canonical stored

def test_parse_lab_items_normalized_unit_unicode_mu():
    items = parse_lab_items("Uric Acid 380 μmol/L", gender=None)
    item = next(i for i in items if 'Uric' in item['item_name'])
    assert item['unit'] == 'μmol/L'
    assert item['normalized_unit'] == 'umol/L'

def test_parse_lab_items_normalized_unit_mg_dl_unchanged():
    items = parse_lab_items("Glucose 110 mg/dL 70-99", gender='male')
    item = next(i for i in items if i['item_name'] == 'Glucose')
    assert item['unit'] == 'mg/dL'
    assert item['normalized_unit'] == 'mg/dL'  # no alias applied

def test_parse_lab_items_normalized_unit_mmol_unchanged():
    items = parse_lab_items("LDL 4.5 mmol/L", gender=None)
    item = next(i for i in items if i['item_name'] == 'LDL')
    assert item['unit'] == 'mmol/L'
    assert item['normalized_unit'] == 'mmol/L'

def test_parse_lab_items_no_unit_normalized_unit_none():
    items = parse_lab_items("ALT 32", gender=None)
    if items:
        item = items[0]
        assert item.get('normalized_unit') is None
```

### 6.3 mg/dL and mmol/L are NOT converted into each other

```python
def test_mg_dl_and_mmol_l_are_not_aliased():
    mg = normalize_unit("mg/dL")
    mmol = normalize_unit("mmol/L")
    assert mg != mmol, "mg/dL and mmol/L must never normalize to the same value"
```

---

## 7. Risks and Unknowns

| Risk | Severity | Mitigation |
|---|---|---|
| Alembic migration adds nullable `normalized_unit` column — low risk but requires review | Low | Nullable; no default needed; existing rows get `NULL` until re-parsed |
| Existing historical rows will have `NULL` `normalized_unit` until documents are re-parsed | Medium | Backend comparison/grouping must treat `NULL` as "use frontend fallback"; document in API contracts |
| Frontend `normalizeUnitForCompare()` and backend `normalize_unit()` must stay in sync | Medium | Define a single canonical alias table in a shared doc; test both sides against same examples |
| `ref_range` string includes raw unit suffix (e.g., `>=0.9 U/L`) — inconsistency if `unit` changed in-place | High | Avoided entirely by Option C — `unit` remains raw |
| OCR may produce non-UTF8 or corrupted unit strings | Low | `GENERIC_LINE_PATTERN` already limits to `[A-Za-z/%\.μµ]+`; normalization should handle `None` gracefully |
| Future unit aliases (e.g., `ng/mL` vs `ng/ml`) are not covered | Low | `normalize_unit()` can be extended; P109 scope is alias-only, not conversion |

---

## 8. Validation Table

| Gate | Result |
|---|---|
| `make lab-trend-comparison-contract` (7 tests) | PASS |
| `make lab-trend-report-date-contract` (4 tests) | PASS |
| `make documents-confirmed-data-contract` (4 tests) | PASS |
| `make documents-page-contract` (4 tests) | PASS |
| `make report-symptom-recommendation-contract` (5 tests) | PASS |
| `make documents-evidence-deeplink-contract` (4 tests) | PASS |
| `make daily-summary-evidence-contract` (4 tests) | PASS |
| `make daily-assistant-contract` (5 tests) | PASS |
| `make actions-page-contract` (4 tests) | PASS |
| `make symptoms-page-contract` (4 tests) | PASS |
| `make runtime-smoke` (56 tests) | PASS |
| Backend code changes | NOT RUN — P109 is docs-only |
| Frontend code changes | NOT RUN — P109 is docs-only |

---

## 9. Files Changed

| File | Action |
|---|---|
| `docs/product/p109-report-parser-unit-normalization-discovery.md` | Created — this document |
| `00-Plan/roadmap/active_task_report.md` | Updated — P109 entry appended |

---

## 10. Known Limitations

- P109 is discovery-only. No backend normalization was implemented.
- Existing `LabReportItem` rows in production have raw unit strings. Backfill strategy for `normalized_unit` is deferred to P110.
- `normalizeUnitForCompare()` handles prefix-level mu substitution (`^μ` / `^µ`). A unit like `g/μmol` (where mu is mid-string) would not be normalized by the current frontend helper; the same limit applies to any P110 backend port.
- The alias list (IU/L ↔ U/L, μ ↔ u) matches P108 scope. Other potential aliases (e.g., `kU/L` vs `IU/L`) are not covered and were not evaluated in P109.

---

## 11. Next 24h Executable Prompt

```text
[每次交接開頭] — Governance Header

## Required Output
- next 24h prompt（只針對 prompt 內容可以直接複製貼上，整個 prompt 用 text 包起來）
- 目前狀況是怎樣？有問題嗎？接下來我們要處理什麼？CTO agent 5 行內摘要
- 目前狀況是怎樣？有問題嗎？接下來我們要處理什麼？CEO agent 5 行內摘要

# Branch Governance (MANDATORY)
## Canonical Repo
/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS
## Canonical Branch
main
## Rules
- Do NOT create a new branch
- Do NOT create a new worktree
- Do NOT checkout another branch
- Do NOT clone another repo
- Do NOT use detached HEAD

New branch requires explicit authorization: YES create new branch for <reason>

---

# Required Pre-flight
git rev-parse --show-toplevel
git branch --show-current
git status --short
git log --oneline -8

---

# STOP Conditions
If:
- repo is not /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS
- branch is not main
- detached HEAD detected
- unrelated dirty files exist outside expected governance/report files
- P109 report commit is missing
- any baseline gate fails before implementation

THEN:
- STOP immediately
- Do NOT modify code
- Report current repo + branch + issue

---

# Merge Governance
If merge is clean: proceed directly, run post-merge verification, report commit hash, tests, final classification.
If merge has conflict: STOP, report conflict files, do not auto-resolve unless instructed.

---

# Task: P110 — Backend normalized_unit Field for LabReportItem

## Goal
Implement Option C from P109 discovery:
- Add `normalized_unit` (String(30), nullable) to `LabReportItem` entity and schema.
- Add `normalize_unit(raw: str | None) -> str | None` helper in `report_parser.py`.
- Populate `normalized_unit` in `parse_lab_items()` output dict.
- Pass `normalized_unit` through the ingest path (`parse_document()`) to the DB.
- Expose `normalized_unit` in `ParsedItemResponse`, `ParsedItemPreview`, and `lab-history` API response.
- Add Alembic migration (nullable column, no default — existing rows left NULL).
- Add backend unit tests for `normalize_unit()` and integration in `parse_lab_items()`.

## Context
P109 (docs/product/p109-report-parser-unit-normalization-discovery.md) concluded:
- Parser captures `unit` verbatim; no normalization exists at ingest.
- Single `unit` column; changing it in-place would lose original display wording.
- Recommended: Option C — add `normalized_unit` field alongside raw `unit`.
- P108 frontend `normalizeUnitForCompare()` must remain as fallback for historical NULL rows.
- Alias rules: IU/L → U/L; μ/µ prefix → u; mg/dL and mmol/L are NOT aliased to each other.

## Required Baseline Validation
Before implementation:
make lab-trend-comparison-contract
make lab-trend-report-date-contract
make documents-confirmed-data-contract
make documents-page-contract
make report-symptom-recommendation-contract
make documents-evidence-deeplink-contract
make daily-summary-evidence-contract
make daily-assistant-contract
make actions-page-contract
make symptoms-page-contract
make runtime-smoke

If any fail, STOP.

## Scope
Allowed:
- backend/app/services/report_parser.py — add normalize_unit(), update parse_lab_items()
- backend/app/models/entities.py — add normalized_unit column to LabReportItem
- backend/app/schemas/documents.py — add normalized_unit to ParsedItemResponse, ParsedItemPreview
- backend/app/api/documents.py — pass normalized_unit in lab-history and parsed-items responses
- backend/alembic/versions/ — add migration for normalized_unit column
- backend/tests/test_report_parser_stage2.py — add tests from P109 test plan (section 6)

Not allowed:
- Do NOT modify frontend runtime code
- Do NOT normalize existing DB rows (backfill) — leave historical NULLs
- Do NOT implement real unit conversion (mg/dL ↔ mmol/L)
- Do NOT add Makefile targets
- Do NOT wire CI
- Do NOT create branch/worktree
- Do NOT stage unrelated governance dirty files

## normalize_unit() Specification
Input → Output (canonical form preserves recognizable case, not lowercase):
  "IU/L"   → "U/L"
  "iu/l"   → "U/L"
  "IU/l"   → "U/L"
  "μmol/L" → "umol/L"   (U+03BC)
  "µmol/L" → "umol/L"   (U+00B5)
  "umol/L" → "umol/L"   (already canonical)
  "mg/dL"  → "mg/dL"    (unchanged)
  "mmol/L" → "mmol/L"   (unchanged)
  "U/L"    → "U/L"      (already canonical)
  None     → None
  ""       → None

## Required Validation After Implementation
make lab-trend-comparison-contract
make lab-trend-report-date-contract
make documents-confirmed-data-contract
make documents-page-contract
make report-symptom-recommendation-contract
make documents-evidence-deeplink-contract
make daily-summary-evidence-contract
make daily-assistant-contract
make actions-page-contract
make symptoms-page-contract
make runtime-smoke
cd backend && python -m pytest tests/test_report_parser_stage2.py -v

## Commit Rules
Stage only:
- backend/app/services/report_parser.py
- backend/app/models/entities.py
- backend/app/schemas/documents.py
- backend/app/api/documents.py
- backend/alembic/versions/<new_migration>.py
- backend/tests/test_report_parser_stage2.py
- 00-Plan/roadmap/active_task_report.md

Commit message: feat(backend): P110 normalized_unit field at ingest for LabReportItem

## Final Classification
Use one of:
- P110_BACKEND_NORMALIZED_UNIT_FIELD_READY
- P110_BLOCKED_BY_PRE_FLIGHT
- P110_BLOCKED_BY_CONTRACT_REGRESSION
- P110_BLOCKED_BY_MIGRATION_ERROR
```

---

## 12. CTO Agent 5-Line Summary

P109 discovery confirmed the parser captures unit strings verbatim — no normalization exists between OCR output and DB storage. The single `LabReportItem.unit` column stores raw strings (e.g., `IU/L`, `μmol/L`, `µmol/L`) with no alias resolution. In-place mutation of `unit` is unsafe because it is used for display; Option C (add nullable `normalized_unit` field) is the correct architecture. P108 frontend `normalizeUnitForCompare()` remains a valid fallback for historical NULL rows. P110 should implement `normalize_unit()` in `report_parser.py`, populate `normalized_unit` at parse time, and expose it in API responses.

---

## 13. CEO Agent 5-Line Summary

Health reports store unit strings exactly as they appear in PDFs — meaning the same unit (`IU/L` vs `U/L`, `μmol/L` vs `umol/L`) can be stored differently across documents. P108 patched this at the display layer; P109 confirms the root cause is in the data storage layer. The recommended fix (P110) adds a second `normalized_unit` field to the database — keeping the original wording visible to users while giving the system a clean, consistent value for comparisons and trend analysis. No existing data is altered; only newly-parsed documents get the normalized value. This is a low-risk, high-value data quality improvement that reduces long-term maintenance burden on the frontend.
