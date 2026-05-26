# P93 — DailyHealthSummary Structured Evidence Refs Discovery

**Date**: 2026-05-26
**Classification**: `P93_BACKEND_SCHEMA_GAP_CONFIRMED`
**Investigator**: CTO Agent
**Scope**: Discovery only — no backend schema changes, no code committed in P93.

---

## 1. Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD | `587e452` (P92 report) ✅ |
| Dirty files | governance-only (CEO-Decision.md, CTO-Analysis.md, active_task.md, roadmap.md) ✅ |

---

## 2. Baseline Gates (before)

| Gate | Tests | Result |
|---|---|---|
| `daily-assistant-contract` | 4 | ✅ PASS |
| `actions-page-contract` | 3 | ✅ PASS |
| `documents-confirmed-data-contract` | 41 + 2 skipped | ✅ PASS |
| `documents-page-contract` | 29 | ✅ PASS |
| `symptoms-page-contract` | 57 | ✅ PASS |
| `runtime-smoke` | 56 | ✅ PASS |

---

## 3. DailyHealthSummary Generation Map

### 3.1 Call graph (`generate_daily_health_summary`)

```
generate_daily_health_summary(db, user_id, person_id)
  │
  ├── build_evidence_bundle()
  │     ├── symptoms, long_term_symptoms        [source_type=symptom,       source_id=UUID]
  │     ├── health_metrics                      [source_type=health_metric, source_id=UUID]
  │     ├── lab_report_items                    [source_type=lab_report_item, source_id=UUID]
  │     ├── risk_alerts                         [source_type=risk_alert,    source_id=UUID]
  │     ├── outcomes                            [source_type=outcome,       source_id=UUID]
  │     └── device_escalation                  [no source_id — computed signal]
  │
  ├── get_action_recommendations()
  │     └── recommendations[]                  [source_type, source_id, evidence_summary all present]
  │
  ├── _derive_top_risk(risk_alerts, recs, long_term_syms, missing, escalation)
  │     → returns str only ← source discarded
  │
  ├── _derive_biggest_change(outcomes, health_metrics)
  │     → returns str only ← source discarded
  │
  ├── _derive_today_action_and_why(recommendations, escalation)
  │     → returns (str, str) only ← source discarded
  │
  └── result = {topRisk, biggestChange, todayAction, whyNow, confidence, ...}
        → 7 narrative strings — zero source references
```

### 3.2 `_derive_top_risk` priority chain and source availability

| Priority | Source data | source_type | source_id | Navigation? |
|---|---|---|---|---|
| 1st | `risk_alerts[max severity]` | `risk_alert` | ✅ UUID | ❌ No `/risk-alerts` page yet |
| 2nd | `device_escalation` urgent/warning | — | ❌ None | ❌ Computed signal |
| 3rd | `recommendations[0]` (high, not missing_data) | `lab_report_item` / `symptom` / etc | ✅ UUID | ✅ via `EVIDENCE_SOURCE_META` |
| 4th | `long_term_symptoms[0]` (severity ≥ 6) | `symptom` | ✅ UUID | ✅ `/platform/symptoms` |
| 5th | `recommendations[0]` (any) | any | ✅ UUID | ✅ via `EVIDENCE_SOURCE_META` |
| 6th | missing_data count ≥ 3 | — | ❌ None | ❌ Fallback string |
| 7th | no-risk fallback | — | ❌ None | ❌ Fallback string |

### 3.3 `_derive_biggest_change` priority chain and source availability

| Priority | Source data | source_type | source_id | Navigation? |
|---|---|---|---|---|
| 1st | `outcomes[max abs delta]` | `outcome` | ✅ UUID | ❌ No outcome detail page |
| 2nd | `health_metrics` trend (4 metric types) | `health_metric` | ✅ UUID | ❌ No metrics page |
| 3rd | fallback "無明顯數據變化" | — | ❌ None | ❌ |

**Note**: `biggestChange` source types (`outcome`, `health_metric`) have no user-facing navigation page. A `summary` label can be included in the ref, but `href` would be absent from `EVIDENCE_SOURCE_META`. The badge will show label-only, no link — which is still valuable for transparency.

### 3.4 `_derive_today_action_and_why` priority chain and source availability

| Priority | Source data | source_type | source_id | evidence_summary | Navigation? |
|---|---|---|---|---|---|
| 1st (override) | `device_escalation` urgent + no actionable recs | — | ❌ None | ❌ None | ❌ |
| 2nd | `recommendations[0]` (non-tracking, not missing_data) | any | ✅ UUID | ✅ String | ✅ via `EVIDENCE_SOURCE_META` |
| 3rd | `recommendations[0]` (tracking) | any | ✅ UUID | ✅ String | ✅ via `EVIDENCE_SOURCE_META` |
| 4th | `recommendations[0]` (any) | any | ✅ UUID | ✅ String | ✅ via `EVIDENCE_SOURCE_META` |
| 5th | default fallback | — | ❌ None | ❌ None | ❌ |

`todayAction` ref is the **highest confidence opportunity** — the winning rec has `source_type`, `source_id`, and `evidence_summary` all populated and merely discarded by the current return-type signature of `_derive_today_action_and_why`.

---

## 4. Source Identity: Preserved vs Lost

### Backend layer

| Data path | Fields | Status |
|---|---|---|
| `build_evidence_bundle()` items | `source_type`, `source_id`, `summary` | ✅ All present per item |
| `get_action_recommendations()` | `source_type`, `source_id`, `evidence_summary` | ✅ All present per rec |
| `_derive_top_risk` return | only `str` | ❌ Source discarded |
| `_derive_biggest_change` return | only `str` | ❌ Source discarded |
| `_derive_today_action_and_why` return | `(str, str)` | ❌ Source discarded |
| `generate_daily_health_summary` result | 7 narrative strings | ❌ Zero source refs |

### Frontend layer

| Location | Fields | Status |
|---|---|---|
| `DailyHealthSummary` TS type (`api.ts:138`) | 9 fields, no source refs | ❌ Not defined |
| `p76-daily-assistant-signal-contract.spec.ts` mocks | No source ref fields | ✅ Non-breaking (optional fields) |
| `test_daily_summary_service.py` asserts | Narrative strings only | ✅ Non-breaking (optional fields) |
| `DailyAssistantEntry` 3-grid cards | Render `summary.*` strings | ❌ No ref available to render |

### Comparison: topRec vs 3-grid cards

| | `topRec` (P91) | 3-grid cards (P93 gap) |
|---|---|---|
| Data source | `Recommendation` object (full) | `DailyHealthSummary` (narrative strings only) |
| `source_type` | ✅ Present | ❌ Not forwarded |
| `evidence_summary` | ✅ Present | ❌ Not forwarded |
| Evidence badge possible today? | ✅ P91 already done | ❌ Requires backend schema change |

---

## 5. Existing Schema — No Hidden Fields

After reading `generate_daily_health_summary` (service lines 1143–1200) and `DailyHealthSummary` TS type (`api.ts:138–149`):

- **No hidden source fields** exist in the current API response
- **No fields are stripped by the frontend** — the TS type faithfully mirrors the backend response
- The existing tests do **not** assert the absence of source ref fields → adding optional `topRiskRef?`, `biggestChangeRef?`, `todayActionRef?` is non-breaking for all existing tests and contract specs

---

## 6. Recommended Evidence Ref Shape

### Type design rationale

**Per-card single ref** (not summary-level array):
- Each `_derive_*` function picks exactly ONE winning item — the ref is always singular
- Per-card naming (`topRiskRef`, `biggestChangeRef`, `todayActionRef`) eliminates "which card does this ref belong to?" ambiguity
- A flat optional ref is simpler than `evidence_refs: EvidenceRef[]` with card discriminators
- Backend stays unaware of frontend routing — `source_type` → `href` mapping handled by `EVIDENCE_SOURCE_META` on the frontend

**Proposed types**:

```typescript
// New — add to frontend/lib/api.ts
export type DailySummaryEvidenceRef = {
  source_type: string      // e.g. 'risk_alert', 'symptom', 'lab_report_item', 'recommendation', 'health_metric', 'outcome'
  source_id?: string       // UUID of the winning record (absent for escalation / fallback paths)
  summary?: string         // brief context text (may be absent for simple fallback paths)
}

// Updated DailyHealthSummary
export type DailyHealthSummary = {
  person_id:    string
  generated_at: string
  topRisk:      string
  biggestChange: string
  todayAction:  string
  whyNow:       string
  confidence:   number
  missingData?: string[]
  encouragement?: string
  escalation?:  EscalationDecision
  // P94 additions — all optional, backward-compatible
  topRiskRef?:       DailySummaryEvidenceRef
  biggestChangeRef?: DailySummaryEvidenceRef
  todayActionRef?:   DailySummaryEvidenceRef
}
```

### EVIDENCE_SOURCE_META additions required

For P94, add two new source types to `frontend/lib/evidence-source-meta.ts`:

```typescript
// Existing entries (P92):
lab_report_item:   { label: '查看健檢報告', href: '/platform/documents' },
lab_abnormality:   { label: '查看健檢報告', href: '/platform/documents' },
symptom:           { label: '查看症狀紀錄', href: '/platform/symptoms' },
long_term_symptom: { label: '查看症狀紀錄', href: '/platform/symptoms' },
risk_alert:        { label: '查看風險提醒' },  // no href yet

// P94 additions (label-only — no navigation page exists):
health_metric:     { label: '健康指標數據' },
outcome:           { label: '健康成效紀錄' },
recommendation:    { label: '行動建議來源' },
```

---

## 7. Minimal P94 Implementation Plan

### Phase A — Backend (~45 LOC)

**File**: `backend/app/services/health_assistant_service.py`

Change 1: `_derive_top_risk` → return `tuple[str, dict | None]`
```python
# Returns (narrative, ref | None)
def _derive_top_risk(...) -> tuple[str, dict | None]:
    if risk_alerts:
        best = max(risk_alerts, key=...)
        ...
        return f"{best['title']}（{sev_label}）", {
            "source_type": "risk_alert",
            "source_id": best.get("source_id"),
            "summary": best.get("title", ""),
        }
    if escalation and esc_level in ("urgent", "warning"):
        return f"裝置健康訊號...", None   # no source_id for device signals
    for rec in recommendations:
        if rec.get("priority") == "high" and ...:
            return rec.get("title"), {
                "source_type": rec["source_type"],
                "source_id": rec.get("source_id"),
                "summary": rec.get("evidence_summary", ""),
            }
    for sym in long_term_symptoms:
        if (sym.get("severity") or 0) >= 6:
            return f"持續症狀...", {
                "source_type": "symptom",
                "source_id": sym.get("source_id"),
                "summary": sym.get("summary", ""),
            }
    ...
    return "目前未偵測到顯著風險", None
```

Change 2: `_derive_biggest_change` → return `tuple[str, dict | None]`
```python
def _derive_biggest_change(...) -> tuple[str, dict | None]:
    if outcomes:
        best = max(outcomes, key=...)
        ...
        return f"{label}{direction} {abs(delta):.1f}...", {
            "source_type": "outcome",
            "source_id": best.get("source_id"),
            "summary": best.get("summary", ""),
        }
    for extractor, label, ...:
        ...
        return f"{label}{direction} {abs(delta):.1f}...", {
            "source_type": "health_metric",
            "source_id": None,    # no single winning metric UUID from trend
            "summary": f"{label} 近期趨勢",
        }
    return "近期無明顯數據變化", None
```

Change 3: `_derive_today_action_and_why` → return `tuple[str, str, dict | None]`
```python
def _derive_today_action_and_why(...) -> tuple[str, str, dict | None]:
    ...
    for rec in recommendations:
        if not rec.get("is_tracking") and ...:
            return rec.get("title"), rec.get("why_now"), {
                "source_type": rec["source_type"],
                "source_id": rec.get("source_id"),
                "summary": rec.get("evidence_summary", ""),
            }
    ...
    return default_action, default_why, None
```

Change 4: `generate_daily_health_summary` — unpack tuples, conditionally add refs
```python
top_risk, top_risk_ref = _derive_top_risk(...)
biggest_change, biggest_change_ref = _derive_biggest_change(...)
today_action, why_now, today_action_ref = _derive_today_action_and_why(...)
...
if top_risk_ref:
    result["topRiskRef"] = top_risk_ref
if biggest_change_ref:
    result["biggestChangeRef"] = biggest_change_ref
if today_action_ref:
    result["todayActionRef"] = today_action_ref
```

### Phase B — Backend tests (~20 LOC)

**File**: `backend/tests/test_daily_summary_service.py`

All `_derive_*` helper tests must unpack tuples:
```python
# Before:
result = _derive_top_risk([alert], [], [], [])
assert "血壓偏高" in result

# After:
narrative, ref = _derive_top_risk([alert], [], [], [])
assert "血壓偏高" in narrative
assert ref is not None
assert ref["source_type"] == "risk_alert"
```

Integration test `test_daily_summary_full_data` would gain:
```python
assert result.get("todayActionRef") is not None or result.get("topRiskRef") is not None
```

### Phase C — Frontend type (~8 LOC)

**File**: `frontend/lib/api.ts`
- Add `DailySummaryEvidenceRef` type
- Add optional `topRiskRef?`, `biggestChangeRef?`, `todayActionRef?` to `DailyHealthSummary`

**File**: `frontend/lib/trust-type-guards.ts`
- `isDailyHealthSummary` guard: optional fields → no required assertion change

### Phase D — Frontend UI (~30 LOC)

**File**: `frontend/app/components/platform/daily-assistant-entry.tsx`

Each 3-grid card gets a conditional mini-badge. Pattern identical to P91 evidence badge but smaller (the 3-grid cards are compact):

```tsx
{/* Inside daily-summary-top-risk card, after topRisk text */}
{summary?.topRiskRef && (
  <div className="mt-1.5 flex items-center gap-1 text-[10px] text-slate-400">
    <FileText className="h-2.5 w-2.5 flex-shrink-0" />
    <span className="flex-1 truncate">{summary.topRiskRef.summary || '依據健康數據'}</span>
    {EVIDENCE_SOURCE_META[summary.topRiskRef.source_type]?.href && (
      <Link href={EVIDENCE_SOURCE_META[summary.topRiskRef.source_type]!.href!}
        data-testid="p94-top-risk-ref-link"
        className="shrink-0 text-slate-400 hover:text-blue-600">
        <ExternalLink className="h-2.5 w-2.5" />
      </Link>
    )}
  </div>
)}
```

Same pattern for `biggestChangeRef` (`data-testid="p94-biggest-change-ref-link"`) and `todayActionRef` (`data-testid="p94-today-action-ref-link"`).

**File**: `frontend/lib/evidence-source-meta.ts`
- Add `health_metric`, `outcome`, `recommendation` entries (label-only, no `href`)

### Phase E — New Playwright tests (~30 LOC)

**File**: `frontend/tests/e2e/p94-daily-summary-3grid-evidence-refs.spec.ts`

```
T1: topRiskRef source_type=risk_alert → badge visible in top-risk card, no link (risk_alert has no href)
T2: todayActionRef source_type=lab_report_item → badge visible in next-action card, link to /platform/documents
T3: biggestChangeRef source_type=health_metric → badge visible in biggest-change card, no link
T4: no refs in response → no badges in any 3-grid card
```

**Contract mock update**: `DAILY_SUMMARY_FULL` in `p76-daily-assistant-signal-contract.spec.ts` gains optional ref fields (non-breaking since contract test asserts signals not field presence).

**Makefile gate**: `daily-assistant-contract` already covers the component — no new gate target needed.

---

## 8. Risks / Unknowns

| Risk | Severity | Mitigation |
|---|---|---|
| `_derive_*` return type change → unpack in tests | Medium | Mechanical update — all tests in `test_daily_summary_service.py` use direct calls to helpers |
| `biggestChange` has no navigation page | Medium | `href` absent for `health_metric`/`outcome` in EVIDENCE_SOURCE_META → badge shows summary label only, no link. Transparent and not misleading |
| `topRisk` from `device_escalation` has no `source_id` | Low | Return `None` ref for escalation path → `topRiskRef` absent → no badge. Graceful |
| `todayActionRef` partially overlaps P91 `topRec` badge | Low | Different card slot, different user intent. `todayAction` is in the 3-grid; `topRec` is a separate card below. Both serve independent user attention points |
| Medical overclaiming if ref labels make system appear diagnostic | Low | Labels use "參考依據" / "健康數據" framing only, same as P89/P91 |
| `_derive_biggest_change` health_metric trend has no single UUID | Low | Set `source_id: None` for trend-based refs — `summary` text still provides transparency |
| Risk alert has no `/platform/risk-alerts` navigation page | Medium | `risk_alert` entry in EVIDENCE_SOURCE_META has no `href` (existing P92 design) — badge shows label only. Can add href in future when risk page ships |

---

## 9. Validation Table

| Gate | Tests | Result |
|---|---|---|
| `daily-assistant-contract` | 4 | ✅ PASS |
| `actions-page-contract` | 3 | ✅ PASS |
| `documents-confirmed-data-contract` | 41 + 2 skipped | ✅ PASS |
| `documents-page-contract` | 29 | ✅ PASS |
| `symptoms-page-contract` | 57 | ✅ PASS |
| `runtime-smoke` | 56 | ✅ PASS |
| Code changes in P93 | — | None — discovery only |
| TSC | — | Not needed (no code change) |

---

## 10. Next 24h Executable Prompt

```
[每次交接開頭] — Governance Header

Repo: /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS  Branch: main
HEAD must be: <P93 report commit>
Dirty allowed: CEO-Decision.md, CTO-Analysis.md, active_task.md, roadmap.md only

# Task: P94 — DailyHealthSummary Per-Card Evidence Refs Implementation

## Context

P93 confirmed:
- generate_daily_health_summary returns 7 narrative strings, zero source refs
- All three _derive_* helpers have the winning source available but discard it
- todayAction ref is highest-confidence: winning rec.source_type + evidence_summary present
- biggestChange ref source_type = outcome or health_metric — no navigation page → label-only badge
- topRisk ref varies by priority path — risk_alert, recommendation, symptom, or None

## Scope

### Backend
- backend/app/services/health_assistant_service.py
  - _derive_top_risk → return (str, dict | None)
  - _derive_biggest_change → return (str, dict | None)
  - _derive_today_action_and_why → return (str, str, dict | None)
  - generate_daily_health_summary → unpack tuples, add topRiskRef/biggestChangeRef/todayActionRef to result
- backend/tests/test_daily_summary_service.py
  - Update all _derive_* helper tests to unpack tuples
  - Add assertions on ref.source_type for key paths

### Frontend
- frontend/lib/api.ts → add DailySummaryEvidenceRef type + 3 optional fields to DailyHealthSummary
- frontend/lib/evidence-source-meta.ts → add health_metric, outcome, recommendation entries (no href)
- frontend/lib/trust-type-guards.ts → isDailyHealthSummary guard (no required field assertions needed)
- frontend/app/components/platform/daily-assistant-entry.tsx → add mini-badge to each 3-grid card
- frontend/tests/e2e/p94-daily-summary-3grid-evidence-refs.spec.ts → 4 tests (T1–T4)

### Not allowed in P94
- Do NOT add fake refs when source is unavailable (always use None / absent)
- Do NOT add navigation href for health_metric, outcome, risk_alert (no pages exist)
- Do NOT modify contract mock assertions (only add optional fields to DAILY_SUMMARY_FULL)
- Do NOT modify DailyHealthSummary required fields

## Baseline gates

make daily-assistant-contract actions-page-contract documents-confirmed-data-contract documents-page-contract symptoms-page-contract runtime-smoke

If any fail, STOP.

## Validation

cd backend && python -m pytest tests/test_daily_summary_service.py -v
cd frontend && npx tsc --noEmit
cd frontend && npx playwright test p94 p76 --reporter=line
make daily-assistant-contract runtime-smoke

## Commits

Commit 1 (code):
  git add backend/app/services/health_assistant_service.py \
          backend/tests/test_daily_summary_service.py \
          frontend/lib/api.ts \
          frontend/lib/evidence-source-meta.ts \
          frontend/lib/trust-type-guards.ts \
          frontend/app/components/platform/daily-assistant-entry.tsx \
          frontend/tests/e2e/p94-daily-summary-3grid-evidence-refs.spec.ts
  git commit -m "feat: P94 DailyHealthSummary per-card evidence refs"

Commit 2 (report):
  git add docs/product/p94-*.md 00-Plan/roadmap/active_task_report.md
  git commit -m "docs(report): P94 daily summary 3-grid evidence refs report"

## Classification

- P94_3GRID_EVIDENCE_REFS_DONE — all 3 cards have refs, all tests pass
- P94_PARTIAL_DONE — todayAction and topRisk done, biggestChange label-only
- P94_BLOCKED_BY_CONTRACT_REGRESSION — if any gate fails before or after
```

---

## 11. CTO 10-Line Summary

P93 discovery complete. Gap confirmed: `generate_daily_health_summary` returns 7 narrative strings with zero source references — all three private `_derive_*` helpers discard the winning source identity at their return boundary. Source data IS available at generation time for all three cards: `topRisk` winner is a `risk_alert` (UUID) or `recommendation` (source_type + source_id); `biggestChange` winner is an `outcome` or `health_metric` (source_id available but no navigation page); `todayAction` winner is the top `recommendation` with `source_type`, `source_id`, and `evidence_summary` all populated — the highest confidence and lowest risk fix. No hidden fields exist in the current API response; adding optional `topRiskRef?`, `biggestChangeRef?`, `todayActionRef?` is non-breaking for all existing tests and the p76 contract spec. The recommended P94 plan is: change the three `_derive_*` helpers to return `(str, dict | None)` tuples (~45 LOC backend), add optional ref fields to `DailyHealthSummary` TS type (~8 LOC), add `health_metric`/`outcome`/`recommendation` label-only entries to `EVIDENCE_SOURCE_META`, and render mini-badges in the 3-grid cards (~30 LOC JSX). `biggestChange` and `risk_alert` refs will show label-only (no href — no navigation page), while `todayAction` and `topRisk` (when sourced from a lab/symptom rec) will show a full source-page link via the existing `EVIDENCE_SOURCE_META` pattern. All 6 baseline gates pass. No code changes in P93.
