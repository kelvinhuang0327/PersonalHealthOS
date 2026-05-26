# P84 — Report / Symptom → Daily Recommendation Lane Discovery

**Date:** 2026-05-26  
**Classification:** `P84_REPORT_SYMPTOM_DAILY_RECOMMENDATION_DISCOVERY_READY`  
**Preceding task:** P83 Actions Page Contract Local Guard (`e14ada3`)

---

## 1. Current Implemented Flow Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  REPORT PATH                                                                │
│                                                                             │
│  User uploads file (/platform/documents)                                   │
│      ↓  POST /documents/upload  → MedicalDocument (parse_status=pending)  │
│  User clicks Parse                                                          │
│      ↓  POST /documents/{id}/parse                                         │
│         → extract_text() (PDF/OCR)                                         │
│         → parse_lab_items() → LabReportItem rows                           │
│         → evaluate_lab_item_risks() → RiskAlert rows                       │
│         → MedicalDocument.parse_status = 'parsed'                          │
│  User reviews + confirms (PUT /documents/{id}/confirm)                     │
│      ↓  MedicalDocument.parse_status = 'confirmed'                         │
│         cache_invalidate(dashboard:{user_id}:)  ← signals dashboard       │
│                                                                             │
│  build_evidence_bundle()                                                    │
│      ↓  queries LabReport + LabReportItem (abnormal_flag IS NOT NULL)      │
│         queries RiskAlert (status='active')                                 │
│         → lab_report_items[]  (evidence_level='A', confidence≈0.75)        │
│         → risk_alerts[]       (evidence_level='B', confidence=0.85)        │
│         → lab_abnormalities[] (detect_lab_abnormalities bridge)            │
│                                                                             │
│  get_action_recommendations()                                               │
│      ↓  scores candidates from risk_alerts + lab_abnormalities            │
│         adds why_now, evidence_sources, evidence_summary, priority         │
│         → recommendations[]: lab-sourced with source_type='lab_report_item'│
│                               or source_type='lab_abnormality'             │
│                                                                             │
│  generate_daily_health_summary()                                            │
│      ↓  derives topRisk from risk_alerts → _derive_top_risk()             │
│         "健檢報告顯示 {item_name} 數值標記為異常" (why_now, line 805)      │
│         missing_data: "健檢報告（或無異常項目）" when lab_report_items=[]  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  SYMPTOM PATH                                                               │
│                                                                             │
│  User enters symptom (/platform/symptoms)                                  │
│      ↓  POST /symptoms                                                      │
│         → parse_temporal_symptom() → estimated_start_date,                 │
│           estimated_duration_days, temporal_source, confidence_score       │
│         → SymptomLog row (with temporal fields)                             │
│                                                                             │
│  build_evidence_bundle()                                                    │
│      ↓  queries SymptomLog (last 90 days)                                  │
│         → symptoms[] (< 30 days old, evidence_level='C', confidence=0.7)  │
│         → long_term_symptoms[] (duration>30 days OR >30 days ago)          │
│         → symptom_timeline[] (build_symptom_timeline)                      │
│         → symptom_patterns[] (detect_symptom_patterns)                     │
│         missing_data: "症狀記錄" when symptom_rows=[]                      │
│                                                                             │
│  get_action_recommendations()                                               │
│      ↓  source_priority: symptom=50, symptom_pattern=65                   │
│         symptom-sourced recs appear when no higher-priority source exists  │
│                                                                             │
│  generate_daily_health_summary()                                            │
│      ↓  _derive_top_risk: falls through to long_term_symptoms (severity≥6) │
│         missing_data hint: "症狀記錄" → link to /platform/symptoms         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  DAILY ASSISTANT UI (GET /health-assistant/daily-summary)                  │
│                                                                             │
│  DailyAssistantEntry (frontend component)                                  │
│      ↓  getDailySummary() → { topRisk, biggestChange, todayAction,        │
│                               whyNow, confidence, missingData?,            │
│                               encouragement?, escalation? }                │
│         getOutcomeFeedback(7) → outcome streak                             │
│                                                                             │
│  Displayed fields with evidence disclosure:                                 │
│    topRisk       → shown in "今日最需關注" card                            │
│    whyNow        → shown under top recommendation (line 309 of component)  │
│    confidence    → → RecommendationTrustBlock (amber/green banner)         │
│    missingData[] → shown with links to correct page (fully implemented)    │
│    evidence_summary → shown in decision-recommendation-layer.tsx           │
│    evidence_sources → tags in health-assistant-panel.tsx                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Confirmed Links: Report → Risk / Recommendation / Daily Assistant

| Step | API / Service | Implemented? |
|------|---------------|:------------:|
| Upload file | `POST /documents/upload` | ✅ |
| Parse (OCR + rule extraction) | `POST /documents/{id}/parse` → `parse_lab_items()` | ✅ |
| Generate `RiskAlert` from abnormal items | `evaluate_lab_item_risks()` during parse | ✅ |
| User confirms document | `PUT /documents/{id}/confirm` → `cache_invalidate` | ✅ |
| `LabReportItem` flows into evidence bundle | `build_evidence_bundle()` — `lab_report_items` key, evidence_level=A | ✅ |
| `RiskAlert` flows into recommendations | `get_action_recommendations()` — source_priority=100 | ✅ |
| Lab abnormality bridge → recommendations | `detect_lab_abnormalities()` + source_priority=75 | ✅ |
| Lab-sourced `why_now` in recommendation | Line 805: `"健檢報告顯示 {item_name} 數值標記為異常"` | ✅ |
| `topRisk` in daily summary from risk_alerts | `_derive_top_risk()` — risk_alerts first priority | ✅ |
| Missing-data hint → `/platform/documents` | `DailyAssistantEntry` `MISSING_DATA_LINKS` | ✅ |

**Confirmed gap:** Document `confirmed_data` field (user-edited corrections from `PUT /confirm`) is stored in `MedicalDocument.confirmed_data` JSON blob but **is NOT fed back into `LabReportItem` rows or `RiskAlert` rows**. The parse pipeline runs once at parse time; confirmed corrections do not regenerate lab items. Corrections are invisible to the evidence bundle.

---

## 3. Confirmed Links: Symptoms → Recommendation / Daily Assistant

| Step | API / Service | Implemented? |
|------|---------------|:------------:|
| Create symptom log | `POST /symptoms` → `SymptomLog` | ✅ |
| Temporal fields extracted | `parse_temporal_symptom()` → `estimated_start_date`, `estimated_duration_days`, `temporal_source`, `confidence_score` | ✅ |
| Symptoms in evidence bundle | `build_evidence_bundle()` — `symptoms` / `long_term_symptoms` / `symptom_timeline` / `symptom_patterns` | ✅ |
| Symptom-sourced recommendations | `get_action_recommendations()` — source_priority=50/65 | ✅ |
| Long-term symptom → daily `topRisk` | `_derive_top_risk()` for severity ≥ 6 | ✅ |
| Missing-data hint → `/platform/symptoms` | `DailyAssistantEntry` `MISSING_DATA_LINKS` | ✅ |
| Duration category → `estimated_duration_days` | `duration_map` in `symptoms.py` create endpoint | ✅ |

**Confirmed gap:** The `symptoms` page UI captures `duration_category` (4 options), but there is **no UI feedback** telling the user how many symptoms were used by the last Daily Assistant run, or what `temporal_source` / `confidence_score` was assigned. The evidence is consumed silently.

---

## 4. Missing Links / Unknowns

| # | Gap | Category | Impact |
|---|-----|----------|--------|
| G1 | `confirmed_data` corrections (from `PUT /confirm`) not re-fed into `LabReportItem` → evidence bundle uses original parsed values | Data freshness | Medium — user expects corrections to affect recommendations |
| G2 | No UI disclosure in Daily Assistant or Actions page showing "this recommendation came from your lab report uploaded on DATE" with a back-link | Evidence traceability | Medium — trust gap |
| G3 | No UI on `/platform/symptoms` page showing "used by Daily Assistant" or "confidence_score assigned" | Evidence traceability | Low — invisible feedback loop |
| G4 | `/platform/documents` page has zero `data-testid` attributes — no Playwright smoke coverage of the upload → parse → confirm flow | Testability | Medium — core path untestable without backend |
| G5 | `/platform/symptoms` page has zero `data-testid` attributes — no Playwright smoke coverage | Testability | Low — mocked tests would require adding testids first |
| G6 | No backend test asserting that `confirmed=True` document's `confirmed_data` flows into the next evidence bundle call | Correctness | Unknown — gap G1 may silently exist |
| G7 | `DailyHealthSummary` response has no `evidence_sources` key — unlike recommendations, the summary card does not expose which data type (report vs symptom vs metric) drove `topRisk` | Frontend transparency | Low-Medium |

---

## 5. Smallest Next Implementation Recommendation

**Recommended next slice: P85 — Documents Page Testid Surface + Upload→Parse Contract Smoke**

### Why this slice?
- The documents page is the **entry point** for the report path, yet has zero testids and zero Playwright coverage.
- Adding a small testid surface (upload form, parse button, confirm button, parse-status indicator) unblocks mocked contract testing without requiring a live backend.
- This directly mirrors what P80/P82 did for the Actions page.
- **No backend changes required** — the API surface for upload/parse/confirm is already complete.

### Scope for P85
1. Add 4–6 `data-testid` attributes to `frontend/app/platform/documents/page.tsx`:
   - `documents-page` (page root — required)
   - `documents-loading` (skeleton state — required)
   - `document-upload-form` (upload section — required)
   - `document-list` (document list — required)
   - `document-parse-btn` (parse trigger — optional, on each card)
   - `document-confirm-btn` (confirm trigger — optional, on each card)
2. Write a 4-test mocked Playwright contract spec (`p85-documents-page-contract.spec.ts`):
   - Test 1: Page renders with document list (mocked `GET /documents`)
   - Test 2: Loading state visible while API frozen
   - Test 3: API failure safe — empty list, no crash
   - Test 4: Medical overclaim guard (no prohibited phrases)
3. Add `make documents-page-contract` to Makefile (same pattern as P83)
4. Update `docs/security/` with contract doc

### NOT recommended for P85
- Fixing G1 (confirmed_data → LabReportItem feedback loop) — requires careful backend logic, not bounded enough
- Adding evidence source back-links in Daily Assistant (G2/G7) — requires design decision on UI surface
- Symptom page testids (G5) — can follow in P86

---

## 6. Validation Table

| Command | Result |
|---------|--------|
| `make actions-page-contract` (4 tests) | ✅ PASS |
| `make daily-assistant-contract` (5 tests) | ✅ PASS |
| `make runtime-smoke` (56 Python tests) | ✅ PASS |
| `cd frontend && npx tsc --noEmit` | NOT RUN (no code changes) |
| Playwright spec for documents | NOT RUN (no documents spec exists yet — P85 scope) |
| Playwright spec for symptoms | NOT RUN (no symptoms spec exists yet — P86 scope) |

---

## 7. Risk Table

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| G1: `confirmed_data` corrections ignored by evidence bundle | Medium | Confirmed | P85+ scope: add re-parse or correction-apply endpoint |
| Lab items only flow when `abnormal_flag IS NOT NULL` — normal results invisible to assistant | Low | Confirmed by code | Known design choice; acceptable for MVP |
| `cache_invalidate` on confirm clears dashboard cache, but evidence bundle may be re-fetched before new risk alerts are created (race) | Low | Theoretical | Cache TTL is short; no evidence of production issue |
| No `data-testid` on documents/symptoms pages — regressions undetectable by Playwright | Medium | Active | P85 addresses documents; P86 symptoms |
| Symptom temporal extraction runs NLP on free-text `note` field — confidence can be 0.0 for structured inputs | Low | By design | `confidence_score` shown as evidence_level='C' |

---

## 8. Next 24h Executable Prompt

```
[每次交接開頭] — Governance Header (same as P84 header, apply to P85)

# Task: P85 Documents Page Testid Surface + Contract Smoke

## Goal
Add minimal testid surface to `/platform/documents` and write a 4-test
mocked Playwright contract spec, following the exact P80→P82→P83 pattern.
Add `make documents-page-contract` to Makefile.

## Pre-flight (mandatory before any code change)
git rev-parse --show-toplevel  # must be PersonalHealthOS
git branch --show-current      # must be main
git status --short              # governance-only dirty files only
git log --oneline -5            # must see P84 commit at top

make actions-page-contract      # must pass 4/4
make daily-assistant-contract   # must pass 5/5
make runtime-smoke              # must pass 56/56

## Testids to add (frontend/app/platform/documents/page.tsx)
- data-testid="documents-page"          → root div (when not loading)
- data-testid="documents-loading"       → skeleton/loader (when loading=true)
- data-testid="document-upload-form"    → <form> wrapping the upload section
- data-testid="document-list"           → <div> wrapping the documents list

## Spec: frontend/tests/e2e/p85-documents-page-contract.spec.ts
4 tests:
1. Loaded state — documents-page + document-list visible
2. Loading state — documents-loading visible while API frozen
3. API failure safe — page survives GET /documents 500
4. Medical overclaim guard — no prohibited phrases visible

## Makefile target: documents-page-contract
Same pattern as actions-page-contract (TSC + playwright spec)

## Commit rules
- Commit 1: testids + spec + Makefile + contract doc
  "feat(frontend): P85 documents page testid surface + contract smoke"
- Commit 2: active_task_report.md update
  "docs(report): P85 documents page contract report"

## STOP conditions (same as P84)
Same governance rules. Do NOT stage CEO-Decision.md, CTO-Analysis.md,
roadmap.md, active_task.md.

## Final classification options
- P85_DOCUMENTS_PAGE_CONTRACT_READY
- P85_BLOCKED_BY_PRE_FLIGHT
- P85_BLOCKED_BY_CONTRACT_REGRESSION
```

---

## 9. CTO 10-Line Summary

```
P84 Discovery — Report/Symptom→Daily Recommendation Lane

1. Report path is FULLY WIRED: upload→parse→RiskAlert→evidence bundle→
   recommendations→daily summary. evidence_level=A, priority=100.
2. Symptom path is FULLY WIRED: create→temporal parse→evidence bundle→
   symptom_timeline→symptom_patterns→recommendations. evidence_level=C.
3. Daily Assistant consumes both paths deterministically (no LLM) and
   exposes confidence, whyNow, topRisk, missingData hints with page links.
4. Critical gap G1: confirmed_data corrections from PUT /confirm are stored
   but NOT re-fed into LabReportItem rows — evidence bundle uses original
   parse values. Medium impact; not P85 scope.
5. Gap G2: no UI back-link showing "this recommendation came from your
   2026-05-01 lab report" — trust traceability gap.
6. Gap G4/G5: documents and symptoms pages have ZERO data-testid attributes.
   Core report/symptom paths are untestable by Playwright today.
7. Backend test coverage for report→recommendation path is solid
   (test_health_assistant_service.py, test_api_lab_smoke.py).
8. No new backend endpoints needed for P85 — API surface is complete.
9. Smallest safe next slice: P85 = documents page testid surface + 4-test
   mocked contract smoke + make documents-page-contract target.
10. Recommendation: do NOT attempt full report→recommendation E2E live test
    until documents page has stable testid surface (P85 prerequisite).
```

---

## Change History

| Phase | Change | Files |
|-------|--------|-------|
| P84 | Lane discovery report — no code changes | `docs/security/P84_REPORT_SYMPTOM_DAILY_RECOMMENDATION_DISCOVERY.md` |
