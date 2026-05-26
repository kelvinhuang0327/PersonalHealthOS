# P88 — Evidence Traceability Discovery Report

**Status**: COMPLETE — discovery only, no code changes  
**Authored**: P88 investigation session  
**Scope**: Read-only audit of backend service code + frontend component rendering  
**Commits planned**: `docs(product): P88 evidence traceability discovery`

---

## 1. Investigation Question

> "What is the smallest safe way to make recommendations / Daily Assistant outputs traceable to their evidence sources?"

Acceptance criteria:
- A user looking at a recommendation can understand *where* that recommendation came from
- Preferably without modifying the backend API schema
- Without broad selector inflation or new AI/LLM behaviour

---

## 2. Current Evidence Traceability Map

### 2a. Evidence Bundle — `GET /health-assistant/evidence-bundle`

All evidence items are **fully traceable** at the data layer. Every item carries:

| Field | Always present | Notes |
|---|---|---|
| `source_type` | ✅ | `"symptom"`, `"health_metric"`, `"lab_report_item"`, `"risk_alert"`, `"insight"`, `"action"` |
| `source_id` | ✅ | UUID string of the originating DB row |
| `evidence_level` | ✅ | `"A"` (lab), `"B"` (metric / alert / insight), `"C"` (symptom) |
| `recency` | ✅ | `"today"` \| `"this_week"` \| `"this_month"` \| `"older"` |
| `summary` | ✅ | Human-readable one-liner |

Lab report items additionally carry:

| Field | Notes |
|---|---|
| `report_id` | UUID of the parent `LabReport` row |
| `report_date` | e.g. `"2026-01-15"` — date the lab was performed |
| `item_name` | e.g. `"空腹血糖"` |
| `value_num` / `value_text` | the measured value |
| `abnormal_flag` | `"H"`, `"L"`, `"C"`, etc. |
| `unit` | measurement unit |
| `ref_range` | reference range string |

This is **evidence level A**, the richest traceability data in the system.

### 2b. Recommendations — `GET /health-assistant/recommendations`

`get_action_recommendations()` (`health_assistant_service.py:583`) returns each recommendation with:

| Field | Present | Rendered in UI |
|---|---|---|
| `source_type` | ✅ | ❌ overridden to `'recommendation'` in frontend mapping |
| `source_id` | ✅ | ❌ not rendered |
| `evidence_sources` | ✅ list of `{type, id, summary}` | ❌ not rendered |
| `evidence_summary` | ✅ computed one-liner | ✅ rendered as FileText badge |
| `data_insufficiency_reason` | ✅ when C-level evidence | ✅ rendered as amber warning |
| `why_now` | ✅ narrative string | ✅ rendered as bullet list (after wrapping to `[string]`) |

**Example `evidence_summary` values produced by the backend:**

```
健檢報告（2026-01-15）：空腹血糖 = 6.8 mmol/L，旗標 H
風險警示：高血壓風險（warning，本週觸發）
自述症狀（C 級）：頭痛，嚴重度 7/10，估計已持續 3 天
AI 洞察：睡眠品質下降（高嚴重度，本月）
```

### 2c. Daily Health Summary — `GET /health-assistant/daily-summary`

`generate_daily_health_summary()` (`health_assistant_service.py:1143`) returns:

| Field | Type | Traceable |
|---|---|---|
| `topRisk` | derived narrative string | ❌ no `source_type`/`source_id` |
| `biggestChange` | derived narrative string | ❌ no `source_type`/`source_date` |
| `todayAction` | derived from top recommendation | ❌ no source backlink |
| `whyNow` | narrative string from top rec's `why_now` | ❌ no source type label |
| `confidence` | float 0–1 | ✅ rendered as % in UI |
| `missingData` | list of missing category strings | ✅ rendered with fill-in links |

The daily summary intentionally collapses evidence into narrative strings. Source identity is **explicitly dropped** by design at this layer.

### 2d. Frontend Rendering

#### `DecisionRecommendationLayer` (`app/components/platform/decision-recommendation-layer.tsx`)

Currently renders (per recommendation card):
- Source type icon + label from `SOURCE_META[item.source_type]`
- Priority badge
- Evidence level badge (A/B)
- `item.why_now` bullets (up to 2)
- `item.next_action` italic text
- `item.evidence_summary` as FileText badge ✅ **already visible**
- `item.data_insufficiency_reason` as amber warning ✅ **already visible**
- `item.trust` as `<RecommendationTrustBlock>`

#### `daily-assistant-entry.tsx`

Currently renders:
- `topRec.title` + `topRec.why_now` text
- `trust` block (level + limitations)
- `missingData` hints with links to fill-in pages
- `summary.whyNow` narrative text
- Confidence % signal
- Encouragement message

---

## 3. Where Source Identity Is Preserved

| Layer | Preserved | Evidence |
|---|---|---|
| Evidence bundle (backend) | ✅ Fully | `source_id`, `report_id`, `report_date`, `item_name` all present |
| Recommendation response (backend) | ✅ Fully | `evidence_sources[]`, `evidence_summary`, `source_type`, `source_id` all in response |
| `evidence_summary` string in UI | ✅ Rendered | FileText badge in DecisionRecommendationLayer |
| `data_insufficiency_reason` in UI | ✅ Rendered | Amber warning when C-level evidence |
| `why_now` narrative in UI | ✅ Rendered | Bullet list explaining the trigger |

---

## 4. Where Source Identity Is Lost

### G1 — `source_type` overridden in frontend mapping (HIGHEST IMPACT)

**File**: `frontend/app/platform/actions/page.tsx` line 113  
**Code**:
```typescript
source_type: 'recommendation',   // ← hardcoded
```
**Effect**: All recommendations from `GET /health-assistant/recommendations` are tagged as `source_type: 'recommendation'` regardless of whether they originated from a lab report item, symptom, or risk alert.  
**Consequence**: `DecisionRecommendationLayer` always shows "系統建議" icon + label, never "風險警示" or context-specific source type. The `SOURCE_META` lookup is effectively broken for these cards.

### G2 — `evidence_sources` array not forwarded or rendered

**Where**: The backend recommendation has `evidence_sources: [{type, id, summary}]`. This is NOT mapped into `UnifiedDecisionItem` and NOT rendered anywhere.  
**Severity**: Low — `evidence_summary` (the pre-computed string) covers most use cases. The IDs in `evidence_sources` would be needed only if implementing "view original source" deep-links.

### G3 — No "view source page" navigation link

**Where**: `DecisionRecommendationLayer` renders `evidence_summary` but provides no link to the underlying data source page.  
**Example gap**: Recommendation says "健檢報告（2026-01-15）：血糖 = 6.8" but there is no link to `/platform/documents`.  
**Severity**: Medium UX — user can read the source reference but cannot navigate to it without knowing the platform layout.

### G4 — Daily Assistant `whyNow` has no source type label

**Where**: `daily-assistant-entry.tsx` renders `summary.whyNow` as plain text.  
**Example gap**: The daily card says "目前有主動風險警示：高血壓風險" but there is no "(來自: 健康指標)" label.  
**Severity**: Low — the risk alert title itself implies the source. Would require backend change to add `whyNow_source_type`.

### G5 — `generate_daily_health_summary` returns no structured source refs (backend layer)

`topRisk`, `biggestChange`, `todayAction`, `whyNow` are narrative strings derived from risk alerts / metrics / recommendations. There is no `topRisk_source_type`, `topRisk_source_id`, or `topRisk_date` in the response.  
**Severity**: Out of P88 scope — requires backend schema change.

---

## 5. Frontend-Only Traceability Assessment

**Answer: YES — frontend-only traceability is achievable for G1 and G3.**

The backend recommendation response already contains everything needed:
- `r.source_type` (the actual originating type: `"lab_report_item"`, `"symptom"`, `"risk_alert"`, etc.)
- `r.evidence_summary` (the human-readable source reference string, already rendered)

**P89 minimal intervention — 2 files, ~10 lines:**

**Fix 1 — Forward actual `source_type` (G1):**  
File: `frontend/app/platform/actions/page.tsx`  
Change line 113 from:
```typescript
source_type: 'recommendation',
```
To:
```typescript
source_type: r.source_type ?? 'recommendation',
```
Effect: DecisionRecommendationLayer will now show the correct source icon ("風險警示" for risk alerts, "AI 洞察" for insights, etc.).

**Fix 2 — Add source-page link to `evidence_summary` badge (G3):**  
File: `frontend/app/components/platform/decision-recommendation-layer.tsx`  
After the `evidence_summary` badge, add a conditional link:

```tsx
{/* P88 G3: source-page navigation link */}
{(item.source_type === 'lab_report_item' || item.source_type === 'lab_abnormality') && (
  <Link href="/platform/documents" className="text-[11px] text-slate-400 hover:text-blue-600 flex items-center gap-0.5 transition-colors">
    <ExternalLink className="h-2.5 w-2.5" />
    查看報告
  </Link>
)}
{(item.source_type === 'symptom' || item.source_type === 'long_term_symptom') && (
  <Link href="/platform/symptoms" className="text-[11px] text-slate-400 hover:text-blue-600 flex items-center gap-0.5 transition-colors">
    <ExternalLink className="h-2.5 w-2.5" />
    查看症狀
  </Link>
)}
```

This requires no backend changes, no new API fields, no new test data.

---

## 6. Risks and Unknowns

| Risk | Likelihood | Mitigation |
|---|---|---|
| `SOURCE_META` in `DecisionRecommendationLayer` does not have an entry for `lab_report_item` or `long_term_symptom` → falls back to `recommendation` style | Confirmed (see code: only `alert`, `insight`, `recommendation`, `trend`, `action` defined) | Add entries for `lab_report_item`, `lab_abnormality`, `long_term_symptom`, `symptom` to `SOURCE_META` |
| `why_now` on backend recommendation is a `str`, but `UnifiedDecisionItem.why_now` expects `string[]` | Known — already handled in mapping (`[String(r.why_now)]`) | No change needed |
| `evidence_sources` IDs are `LabReportItem.id`, NOT `document_id` — "view source document" deep-link by ID is not directly possible without extra API call | Confirmed | Use page-level link (`/platform/documents`) not item-level deep-link |
| Fixing G1 (`source_type`) may change icon/style of existing recommendation cards — visual regression | Low (controlled by `SOURCE_META` defaults) | Add `SOURCE_META` entries; Playwright E2E for the new source types |

---

## 7. Validation Table

| Validation | Status |
|---|---|
| `build_evidence_bundle`: `lab_report_item` has `report_date`, `report_id`, `item_name` | ✅ Confirmed (lines 316–358, `health_assistant_service.py`) |
| `_build_recommendation_from_candidate`: returns `evidence_summary`, `source_type`, `source_id`, `evidence_sources` | ✅ Confirmed (lines 790–960, `health_assistant_service.py`) |
| `actions/page.tsx` maps `r.evidence_summary` → `UnifiedDecisionItem.evidence_summary` | ✅ Confirmed (line 130) |
| `actions/page.tsx` maps `r.data_insufficiency_reason` → `UnifiedDecisionItem.data_insufficiency_reason` | ✅ Confirmed (line 131) |
| `DecisionRecommendationLayer` renders `evidence_summary` as FileText badge | ✅ Confirmed (lines 123–128) |
| `DecisionRecommendationLayer` renders `data_insufficiency_reason` as amber warning | ✅ Confirmed (lines 131–135) |
| `actions/page.tsx` line 113: `source_type` hardcoded to `'recommendation'` | ✅ Confirmed — **this is Gap G1** |
| No "view source page" link exists for lab/symptom recommendation source types | ✅ Confirmed — **this is Gap G3** |
| `generate_daily_health_summary` returns no `source_type` field | ✅ Confirmed (lines 1186–1205, returns only narrative strings) |

---

## 8. Next Executable Prompt (P89)

```
P89 — Evidence Source Label Fix

SCOPE: Frontend-only. 2 files. ~12 lines. No backend changes. No new API.

CONSTRAINT: Do NOT modify backend. Do NOT add new API calls. Do NOT inflate test selectors.
Pass all 6 baseline gates before and after (make runtime-smoke + 5 contract targets).

FILE 1: frontend/app/platform/actions/page.tsx
- Line ~113: change `source_type: 'recommendation',` → `source_type: r.source_type ?? 'recommendation',`
- Also forward: `source_id: r.source_id ? String(r.source_id) : (r.action_id ? String(r.action_id) : `ha_rec_${r.rule_id ?? i}`),`

FILE 2: frontend/app/components/platform/decision-recommendation-layer.tsx
- Add SOURCE_META entries for: `lab_report_item`, `lab_abnormality`, `long_term_symptom`, `symptom`
- After the evidence_summary FileText badge, add conditional source-page link:
  • If source_type in ['lab_report_item', 'lab_abnormality'] → Link to /platform/documents, text "查看報告"
  • If source_type in ['symptom', 'long_term_symptom'] → Link to /platform/symptoms, text "查看症狀"

DELIVERABLES:
1. Updated files committed
2. Updated active_task_report.md with P89 block
3. TSC pass: npx tsc --noEmit
4. All 6 baseline gates green

COMMIT: feat(actions): P89 evidence source-type label and page link
```

---

## 9. CTO 10-Line Summary

Evidence traceability data exists end-to-end in the backend — every recommendation already carries `source_type`, `source_id`, `evidence_summary` (a human-readable one-liner), and `data_insufficiency_reason`. Two of these fields (`evidence_summary`, `data_insufficiency_reason`) are already rendered in the `DecisionRecommendationLayer` component.

The primary gap is a **one-line bug** in `actions/page.tsx`: `source_type` is hardcoded to `'recommendation'`, discarding the actual originating type (`"lab_report_item"`, `"symptom"`, `"risk_alert"`) returned by the backend. This prevents the correct source icon from appearing.

The secondary gap is the absence of a **source-page navigation link** — users can read "健檢報告（2026-01-15）：血糖 6.8" but cannot click to navigate to `/platform/documents`. Since deep-linking to a specific document by LabReportItem UUID is not directly possible without an extra API call, a page-level link (`/platform/documents`) is the safe minimum.

Daily Assistant traceability is a backend-layer gap (narrative strings, no structured refs) — out of P88 scope.

**Recommended P89 slice**: Fix `source_type` forwarding (1 line) + add `SOURCE_META` entries + add conditional source-page link in `DecisionRecommendationLayer`. Estimated: 2 files, ~12 lines, no backend changes, no new API, fully testable with existing Playwright mocks.
