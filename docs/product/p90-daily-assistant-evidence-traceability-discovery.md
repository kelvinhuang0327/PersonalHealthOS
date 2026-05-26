# P90 — Daily Assistant Evidence Traceability Discovery

**Date**: 2026-05-26  
**Classification**: `P90_FRONTEND_ONLY_DAILY_TRACEABILITY_READY`  
**Investigator**: CTO Agent  
**Scope**: Discovery only — no backend schema changes, no code committed in P90.

---

## 1. Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD | `e1418d6` (P89 report) ✅ |
| Dirty files | governance-only (CEO-Decision.md, CTO-Analysis.md, active_task.md, roadmap.md) ✅ |

---

## 2. Baseline Gate Results

| Gate | Tests | Result |
|---|---|---|
| `actions-page-contract` | 4 | ✅ PASS |
| `documents-confirmed-data-contract` | 4 | ✅ PASS |
| `documents-page-contract` | 4 | ✅ PASS |
| `symptoms-page-contract` | 4 | ✅ PASS |
| `daily-assistant-contract` | 5 | ✅ PASS |
| `runtime-smoke` | 56 | ✅ PASS |

---

## 3. Current Daily Assistant Traceability Map

### 3.1 Backend — `generate_daily_health_summary` return shape

File: `backend/app/services/health_assistant_service.py` (line 1143)

```python
result = {
    "person_id":    person_id,            # str
    "generated_at": _NOW().isoformat(),    # str
    "topRisk":      top_risk,              # str — narrative
    "biggestChange": biggest_change,       # str — narrative
    "todayAction":  today_action,          # str — copied from rec["title"]
    "whyNow":       why_now,               # str — copied from rec["why_now"]
    "confidence":   confidence,            # float 0.20–0.95
}
# optionally added:
result["missingData"]  = missing_data      # list[str]
result["encouragement"] = encouragement   # str
result["escalation"]   = device_escalation # dict
```

**Source fields NOT present in the daily-summary response**:
- `source_type` — absent
- `source_id` — absent
- `evidence_summary` — absent
- `evidence_sources` — absent

**How `todayAction` / `whyNow` are derived** (`_derive_today_action_and_why`, line ~1295):

```python
for rec in recommendations:          # top recommendation from get_action_recommendations()
    if not rec.get("is_tracking") and rec.get("source_type") not in ("missing_data",):
        return rec.get("title"), rec.get("why_now")
```

The recommendation object *has* `source_type`, `source_id`, `evidence_summary` — but `_derive_today_action_and_why` extracts only `title` + `why_now`. The source identity is **discarded at this layer**.

### 3.2 Frontend Type — `DailyHealthSummary`

File: `frontend/lib/api.ts` (line 138)

```typescript
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
}
```

Confirmed: **no `source_type`, `source_id`, `evidence_summary`, or `evidence_sources` in the type**.

### 3.3 Frontend Component — `DailyAssistantEntry`

File: `frontend/app/components/platform/daily-assistant-entry.tsx`

The component fetches two streams:
1. `summary` — from `api.getDailySummary()` → `DailyHealthSummary` (narrative strings only, no source refs)
2. `topRec` — from `data?.recommendations?.[0]` → `Recommendation` (from parent, full type)

**`Recommendation` interface** (from `health-assistant-panel.tsx`):

```typescript
export interface Recommendation {
  title: string
  why_now: string
  priority: 'high' | 'medium' | 'low'
  source_type: string       // ← present
  source_id?: string        // ← present
  evidence_summary?: string // ← present
  evidence_sources: EvidenceSource[]
  trust?: RecommendationTrust
  data_insufficiency_reason?: string
  // ...
}
```

The `topRec` block rendered in `DailyAssistantEntry` (line ~295):

```tsx
{topRec && (
  <div className="rounded-xl bg-white border border-slate-100 p-3">
    <div className="flex items-start justify-between gap-2 mb-2">
      <div className="min-w-0">
        <p className="text-xs font-semibold text-slate-800">{topRec.title}</p>
        <p className="mt-0.5 text-[11px] text-slate-500 leading-relaxed">
          {topRec.why_now}
        </p>
        {/* evidence_summary is NOT rendered here ← gap */}
      </div>
      <Link href="/platform/actions">行動 →</Link>
    </div>
    {trust && <RecommendationTrustBlock trust={trust} showLimitations />}
  </div>
)}
```

`topRec.evidence_summary` exists in scope but is **not rendered**.

---

## 4. Source Identity: Preserved vs Lost

| Layer | Field | Status |
|---|---|---|
| Backend `get_action_recommendations()` | `source_type`, `source_id`, `evidence_summary` | ✅ Returned |
| Backend `generate_daily_health_summary()` | `source_type`, `source_id`, `evidence_summary` | ❌ Not forwarded |
| `DailyHealthSummary` API type | `source_type`, `source_id`, `evidence_summary` | ❌ Not defined |
| `Recommendation` type (topRec) | `source_type`, `source_id`, `evidence_summary` | ✅ Present |
| `DailyAssistantEntry` component | renders `topRec.evidence_summary` | ❌ Not rendered |
| `DailyAssistantEntry` component | `topRec.source_type` in scope | ✅ Available |

**Critical finding**: The Daily Assistant component already holds `topRec` with `source_type` and `evidence_summary`. These fields are available in the component — they are simply **not yet rendered**.

---

## 5. Whether Frontend-Only Traceability Is Possible

**Yes. Frontend-only Option A is fully viable.**

The `topRec` object in `DailyAssistantEntry` already contains:
- `topRec.source_type` — e.g., `'lab_report_item'`, `'symptom'`, `'recommendation'`
- `topRec.evidence_summary` — e.g., `'健檢報告（2026-01-15）：空腹血糖 = 6.8 mmol/L，旗標 H'`

Using the same `SOURCE_LINK` pattern from P89:

```typescript
const SOURCE_LINK = {
  lab_report_item:   { label: '查看健檢報告', href: '/platform/documents' },
  lab_abnormality:   { label: '查看健檢報告', href: '/platform/documents' },
  symptom:           { label: '查看症狀紀錄', href: '/platform/symptoms' },
  long_term_symptom: { label: '查看症狀紀錄', href: '/platform/symptoms' },
}
```

Adding an `evidence_summary` badge + conditional source-page link after `topRec.why_now` requires:
- ~10 lines of JSX inside `DailyAssistantEntry`
- No new API calls
- No backend schema change
- No new dependencies (FileText, ExternalLink, Link already used in related components)

---

## 6. Investigation Q&A

### Q1: What exactly does `generate_daily_health_summary` return?

7 narrative string fields + optional `missingData`, `encouragement`, `escalation`. No source references whatsoever. `todayAction` = `rec["title"]`, `whyNow` = `rec["why_now"]` — source identity discarded.

### Q2: Are there any structured fields like source_type, source_id, evidence_refs?

No. The daily-summary endpoint returns only narrative copy. This confirms P88 Gap G5.

### Q3: Is `whyNow` traceable?

No. It is a string copy of the top recommendation's `why_now` field. The source that generated that `why_now` (lab report, symptom, etc.) is not attached.

### Q4: What does `DailyHealthSummary` type include?

9 fields: `person_id`, `generated_at`, `topRisk`, `biggestChange`, `todayAction`, `whyNow`, `confidence`, and optional `missingData`, `encouragement`, `escalation`. No source fields.

### Q5: Is any existing traceability field stripped or ignored?

Yes — the `Recommendation` interface (used for `topRec`) has `source_type`, `source_id`, `evidence_summary` — but `DailyAssistantEntry` renders only `title` and `why_now` from `topRec`. `evidence_summary` is ignored.

### Q6: Where are whyNow, todayAction rendered?

- `whyNow` → "今日最重要風險" grid card, `data-testid="daily-summary-why-now"` (line ~255)
- `todayAction` → "今日主要行動" grid card, `data-testid="daily-summary-next-action"` (line ~270)
- `topRec.why_now` + `topRec.title` → top recommendation card (line ~295)
- `topRec.evidence_summary` → **not rendered anywhere**

### Q7: Could Daily Assistant reuse P89 source traceability directly?

Yes — the `topRec` block is the ideal injection point. It's independent from the 3-grid daily-summary cards which use `DailyHealthSummary` strings (no source refs available there).

---

## 7. Minimal P91 Recommendation

### Option A — Frontend-only: render `topRec.evidence_summary` + source link ⭐ RECOMMENDED

**Location**: `frontend/app/components/platform/daily-assistant-entry.tsx`, inside the `topRec` block  
**What**: After `<p>{topRec.why_now}</p>`, add the same evidence badge pattern from P89  
**No backend change needed**  
**~10 lines of JSX**  
**Risk: low** — purely additive, renders only when `topRec.evidence_summary` is truthy

```tsx
{topRec.evidence_summary && (
  <div className="mt-1.5 flex items-start gap-1.5 rounded bg-white/60 px-2 py-1 text-[11px] text-slate-500">
    <FileText className="h-3 w-3 flex-shrink-0 mt-0.5" />
    <span className="flex-1">{topRec.evidence_summary}</span>
    {SOURCE_LINK[topRec.source_type] && (
      <Link
        href={SOURCE_LINK[topRec.source_type].href}
        data-testid="p91-daily-source-page-link"
        className="ml-1 flex items-center gap-0.5 shrink-0 text-[11px] text-slate-400 hover:text-blue-600 transition-colors"
      >
        <ExternalLink className="h-2.5 w-2.5" />
        {SOURCE_LINK[topRec.source_type].label}
      </Link>
    )}
  </div>
)}
```

### Option B — Backend adds `evidence_refs` to daily-summary response

- Requires modifying `generate_daily_health_summary` to forward `source_type` + `evidence_summary` from the top recommendation
- Requires updating `DailyHealthSummary` frontend type
- Requires new Playwright contract test update
- Risk: medium — affects the daily-assistant contract spec
- **Not needed for P91 if Option A suffices**

### Option C — Use Actions page only; Daily Assistant stays narrative

- Acceptable if daily assistant is considered a "narrative entry" only
- Users would navigate to `/platform/actions` to see source traceability
- **Loses the opportunity to surface evidence in the first touchpoint**

### Option D — Docs only, no implementation yet

- Viable if other priorities take precedence
- **Discovery is complete; P91 is unblocked if chosen**

---

## 8. Risks / Unknowns

| Risk | Severity | Notes |
|---|---|---|
| `topRec` absent (no recommendations) | Low | Component already handles `topRec` null gracefully |
| `topRec.evidence_summary` absent | Low | Badge is conditional on truthiness — safe |
| `SOURCE_LINK` defined in two files | Low | Minor duplication vs. extracting to shared lib; extract in P92+ if needed |
| `whyNow` grid card has no source ref | Medium | `summary.whyNow` is a copy without source — cannot add source link there without Option B |
| `topRisk` / `biggestChange` have no source | Medium | Narrative only — requires Option B to add source attribution to 3-grid cards |
| Daily assistant contract spec may need update | Low | Existing P76 spec does not assert absence of evidence_summary — adding it is non-breaking |

---

## 9. Validation Table (Post-Investigation)

| Gate | Tests | Result |
|---|---|---|
| `actions-page-contract` | 4 | ✅ PASS |
| `documents-confirmed-data-contract` | 4 | ✅ PASS |
| `documents-page-contract` | 4 | ✅ PASS |
| `symptoms-page-contract` | 4 | ✅ PASS |
| `daily-assistant-contract` | 5 | ✅ PASS |
| `runtime-smoke` | 56 | ✅ PASS |
| Code changes in P90 | — | None |
| TSC | — | Not needed (no code change) |

---

## 10. Next 24h Executable Prompt

```
P91 — Daily Assistant Top Recommendation Evidence Badge

Context: P90 confirmed that `DailyAssistantEntry` already holds `topRec`
(type `Recommendation`) with `source_type`, `source_id`, `evidence_summary`.
These are not rendered. P89's SOURCE_LINK pattern applies directly.

Task: Add evidence_summary badge + source-page link to the `topRec` block
in `frontend/app/components/platform/daily-assistant-entry.tsx`.

Scope:
- Add SOURCE_LINK constant (same 4 entries as P89: lab_report_item,
  lab_abnormality, symptom, long_term_symptom)
- Add FileText + ExternalLink imports (from lucide-react, already in project)
- After `<p>{topRec.why_now}</p>`, add conditional evidence badge matching
  the P89 pattern (data-testid="p91-daily-source-page-link")
- Create new Playwright test file:
  frontend/tests/e2e/p91-daily-assistant-evidence-badge.spec.ts
  - T1: topRec.source_type = 'lab_report_item' → badge visible, link to /platform/documents
  - T2: topRec.source_type = 'symptom' → badge visible, link to /platform/symptoms
  - T3: topRec.source_type = 'recommendation' → badge visible, no source-page link
  - T4: topRec.evidence_summary absent → no badge rendered

Baseline gates: make daily-assistant-contract actions-page-contract runtime-smoke
Build: cd frontend && npx next build
Commit: feat(frontend): P91 daily assistant top-rec evidence badge
Commit: docs(report): P91 evidence badge report

Do NOT modify DailyHealthSummary API type.
Do NOT modify backend.
Do NOT extract SOURCE_LINK to shared lib in P91 (defer to P92+).
```

---

## 11. CTO 10-Line Summary

P90 discovery complete. `generate_daily_health_summary` returns 7 narrative strings with no source references — Gap G5 confirmed. However, the frontend component (`DailyAssistantEntry`) already holds the full `Recommendation` object (`topRec`) with `source_type`, `source_id`, and `evidence_summary` in scope — these are simply not rendered. The evidence badge added in P89 can be applied identically to the `topRec` block in Daily Assistant with ~10 lines of JSX, zero backend changes, zero new API calls, and zero schema modifications. Option A is safe, additive, and fully unblocked. The 3-grid cards (`topRisk`, `biggestChange`, `todayAction`) remain narrative-only since they use `DailyHealthSummary` strings where source identity is not available — that would require Option B (backend schema addition) deferred to P92+. All 6 baseline gates pass. P91 is the recommended next slice.
