# P94 — DailyHealthSummary Per-Card Evidence Refs

**Status**: DONE  
**Commit**: `81a5228`  
**Date**: 2025-07-14  
**Branch**: `main`  
**Preceded by**: P93 `cec22df` (daily summary structured evidence refs discovery)

---

## Objective

Add optional `topRiskRef`, `biggestChangeRef`, `todayActionRef` evidence ref fields to the
`DailyHealthSummary` API response and render conservative mini-badges in each of the three
3-grid cards on the Daily Assistant panel. No new endpoints. No LLM behavior. Non-breaking.

---

## Problem Statement (from P93)

`generate_daily_health_summary` returned 7 narrative strings with **zero source provenance**.
All three `_derive_*` helpers had the winning source identity available internally, but
discarded it at the return boundary. End-users had no way to trace why a card showed a
specific risk, change, or action.

---

## Design Decisions

### Non-breaking contract
All three new response fields are **optional**. Existing clients unaware of these fields
continue to work without change. The P76 Playwright contract mock has no ref fields
and still passes — adding optional TypeScript fields is backward-compatible.

### Tuple return pattern
All three `_derive_*` helpers now return tuples instead of plain strings:
- `_derive_top_risk` → `tuple[str, dict[str, Any] | None]`
- `_derive_biggest_change` → `tuple[str, dict[str, Any] | None]`
- `_derive_today_action_and_why` → `tuple[str, str, dict[str, Any] | None]`

`generate_daily_health_summary` unpacks and conditionally sets the ref fields.

### source_id: None for health_metric trends
`_derive_biggest_change` trend path spans multiple metric records, not a single UUID winner.
`source_id` is explicitly set to `None` — the `source_type` alone is sufficient context.

### No `href` for risk_alert, health_metric, outcome
No dedicated navigation pages exist for these source types. `EVIDENCE_SOURCE_META` now
includes label-only entries for `health_metric`, `outcome`, `recommendation`. The `ExternalLink`
icon only renders when the `source_type` has an `href` in the map.

---

## Files Changed

### Backend

| File | Change |
|---|---|
| `backend/app/services/health_assistant_service.py` | 4 functions: `_derive_top_risk`, `_derive_biggest_change`, `_derive_today_action_and_why`, `generate_daily_health_summary` — all updated to return/unpack tuples with optional ref dicts |
| `backend/tests/test_daily_summary_service.py` | 17 `_derive_*` unit tests updated: unpack tuples, assert `source_type` / `source_id` / `None` |

### Frontend

| File | Change |
|---|---|
| `frontend/lib/api.ts` | Added `DailySummaryEvidenceRef` type + 3 optional fields to `DailyHealthSummary` |
| `frontend/lib/evidence-source-meta.ts` | Added `health_metric`, `outcome`, `recommendation` label-only entries |
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Added mini-badge `<div>` to each of the 3 grid cards (`daily-summary-top-risk`, `daily-summary-biggest-change`, `daily-summary-next-action`) |
| `frontend/tests/e2e/p94-daily-summary-3grid-evidence-refs.spec.ts` | New spec — 4 tests (T1–T4) validating badge visibility and link presence |

---

## Evidence Ref Schema

```typescript
type DailySummaryEvidenceRef = {
  source_type: string   // e.g. "risk_alert", "outcome", "health_metric", "insight"
  source_id?: string    // UUID of winning source record (null for trend-based)
  summary?: string      // human-readable label from the source
}
```

---

## Per-source-type Ref Behaviour

| Source type | Badge label | Navigation link |
|---|---|---|
| `risk_alert` | summary field or `查看風險提醒` | ✗ (no page yet) |
| `health_metric` | summary field or `健康指標數據` | ✗ (no page yet) |
| `outcome` | summary field or `健康成效紀錄` | ✗ (no page yet) |
| `insight` / `recommendation` | summary field or `行動建議來源` | ✗ (no page yet) |
| `lab_report_item` | summary field or `查看健檢報告` | ✓ → `/platform/documents` |
| `lab_abnormality` | summary field or `查看健檢報告` | ✓ → `/platform/documents` |
| `symptom` / `long_term_symptom` | summary field or `查看症狀紀錄` | ✓ → `/platform/symptoms` |

---

## Test Results

### Backend (pytest)
```
31 passed in 0.89s
```

### TypeScript
```
npx tsc --noEmit — clean (0 errors)
```

### Next.js build
```
Build complete — 0 errors, 0 warnings
```

### Playwright (P94 + P76)
```
9 passed (8.9s)
  4 P76 contract tests — all green
  4 P94 badge tests (T1–T4) — all green
```

### Makefile gates (all 6)
```
daily-assistant-contract         4 passed
actions-page-contract            3 passed, 4 warnings
documents-confirmed-data-contract  41 passed, 2 skipped, 4 warnings
documents-page-contract          29 passed, 4 warnings
symptoms-page-contract           57 passed, 4 warnings
runtime-smoke                    56 passed, 4 warnings
```

---

## What Was NOT Changed

- `frontend/lib/trust-type-guards.ts` — `isDailyHealthSummary` only asserts required fields; optional ref fields require no guard update
- `frontend/tests/e2e/p76-daily-assistant-signal-contract.spec.ts` — P76 mock has no ref fields; optional field additions are backward-compatible
- No new API endpoints
- No LLM prompt changes
- No CI wiring

---

## Classification

`P94_3GRID_EVIDENCE_REFS_DONE` — All 3 cards have refs, all gates pass.
