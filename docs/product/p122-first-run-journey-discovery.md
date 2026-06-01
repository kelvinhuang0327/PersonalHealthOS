# P122 — First-Run Journey Discovery (2026-06-01)

## Scope And Guardrails
- Task: Discovery/spec only (no runtime implementation).
- Goal: Define a minimal executable first-run contract that stitches existing surfaces only.
- Source of truth: repository source code and existing contract tests (not stale P120 narrative claims).

## Phase 0 Pre-flight (PASS)
- Repo root: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS`
- Branch: `main`
- Git dir: `.git` (not worktree)
- P120 commit `9413929` present in `git log --oneline -8`
- Dirty/untracked state checked and matched known governance/runtime artifacts only:
  - modified governance files: `00-Plan/roadmap/CEO-Decision.md`, `00-Plan/roadmap/CTO-Analysis.md`, `00-Plan/roadmap/active_task.md`, `00-Plan/roadmap/roadmap.md`
  - known untracked: `backend/test-results/`, `frontend/tests/e2e/p118-suppression-reason-badge-contract.spec.mjs`, `node_modules/`, root `package.json`, root `package-lock.json`
- STOP conditions: not triggered.

## 1. Four-Capability Surface Inventory (Route / Component / Contract / Data Flow)

### A) Report Import + Confirmation (Documents)
- Route: `/platform/documents`
- Main page/component:
  - `frontend/app/platform/documents/page.tsx`
  - `ParsedItemsDrawer` in `frontend/app/components/platform/parsed-items-drawer.tsx`
- Frontend contract/data calls:
  - `api.listDocuments()` -> `GET /api/v1/documents`
  - `uploadDocument(category, file)` -> `POST /api/v1/documents/upload`
  - `api.parseDocument(id)` -> `POST /api/v1/documents/{id}/parse`
  - `api.getDocumentParsedItems(id)` -> `GET /api/v1/documents/{id}/parsed-items`
  - `api.confirmDocument(id, payload)` -> `PUT /api/v1/documents/{id}/confirm`
- Backend surface:
  - `backend/app/api/documents.py`
- Existing guard/contract tests:
  - `frontend/tests/e2e/p85-documents-page-contract.spec.ts`
  - `frontend/tests/e2e/p87-documents-confirmed-data-refeed.spec.ts`
  - `frontend/tests/e2e/p97-documents-evidence-deep-link.spec.ts`

### B) Historical Symptom Input (Symptoms)
- Route: `/platform/symptoms`
- Main page/component:
  - `frontend/app/platform/symptoms/page.tsx`
- Frontend contract/data calls:
  - `api.createSymptom(payload)` -> `POST /api/v1/symptoms`
  - `api.listSymptoms()` -> `GET /api/v1/symptoms`
  - `api.listMetrics()` -> `GET /api/v1/metrics` (for abnormal-date heatmap overlays)
- Backend surface:
  - `backend/app/api/symptoms.py`
- Existing guard/contract tests:
  - `frontend/tests/e2e/p86-symptoms-page-contract.spec.ts`

### C) Integrated Symptom Page + Daily Assistant Entry (Dashboard)
- Route: `/platform/dashboard`
- Main page/components:
  - `frontend/app/platform/dashboard/page.tsx`
  - `DailyAssistantEntry` in `frontend/app/components/platform/daily-assistant-entry.tsx`
  - `HealthAssistantPanel` in `frontend/app/components/platform/health-assistant-panel.tsx`
- Frontend contract/data calls:
  - `api.getDashboard()` -> `GET /api/v1/dashboard`
  - `api.getRecommendations()` -> `GET /api/v1/health-assistant/recommendations`
  - `api.getDailySummary()` -> `GET /api/v1/health-assistant/daily-summary`
  - `api.getOutcomeFeedback(7)` -> `GET /api/v1/health-assistant/outcome-feedback`
- Backend surface:
  - `backend/app/api/dashboard.py`
  - `backend/app/api/health_assistant.py`
- Existing guard/contract tests:
  - `frontend/tests/e2e/p76-daily-assistant-signal-contract.spec.ts`
  - `frontend/tests/e2e/p91-daily-assistant-evidence-badge.spec.ts`
  - `frontend/tests/e2e/p94-daily-summary-3grid-evidence-refs.spec.ts`

### D) Action Execution / Recommendation Surface (Actions)
- Route: `/platform/actions`
- Main page/components:
  - `frontend/app/platform/actions/page.tsx`
  - `DecisionRecommendationLayer` in `frontend/app/components/platform/decision-recommendation-layer.tsx`
- Frontend contract/data calls:
  - `api.getRecommendations()` -> `GET /api/v1/health-assistant/recommendations`
  - `api.getActions()` -> `GET /api/v1/actions`
  - `api.createAction(payload)` -> `POST /api/v1/actions`
  - `api.getOutcomeFeedback(30)` -> `GET /api/v1/health-assistant/outcome-feedback`
- Backend surface:
  - `backend/app/api/actions.py`
  - `backend/app/api/health_assistant.py`
- Existing guard/contract tests:
  - `frontend/tests/e2e/p82-actions-page-contract.spec.ts`
  - `frontend/tests/e2e/p80-actions-recommendation-smoke.spec.ts`
  - `frontend/tests/e2e/p89-actions-evidence-traceability.spec.ts`

## 2. New-User Journey Gap Diagnosis (Current State)

### Verified
- No dedicated route exists for onboarding/first-run/welcome (`/platform/onboarding`, `/platform/first-run`, `/platform/welcome` absent).
- There is an existing `OnboardingWizard` modal in `frontend/app/platform/layout.tsx` + `frontend/app/components/platform/onboarding-wizard.tsx`, but it currently covers profile/goals/first-metric only.

### Missing Connection (Activation Gap)
- The current onboarding modal does not bind completion to:
  - document upload + parsed confirmation completion,
  - symptom submission completion,
  - daily assistant recommendation/action completion.
- There is no explicit stepper/progress contract that guides users through:
  - report import -> parsed review/confirm -> symptom input -> daily recommendation action.
- Existing surfaces are strong individually, but activation path is implicit and discoverability-dependent.

## 3. Minimal First-Run Journey Contract (Existing Surfaces Only)

## Entry
- Primary entry: `/platform/dashboard` (`DailyAssistantEntry` block).
- Navigation targets must remain existing pages only:
  - `/platform/documents`
  - `/platform/symptoms`
  - `/platform/dashboard`
  - `/platform/actions`

## Step Definition (4-step minimal)
1. Step A: Report Import/Confirm
   - Route: `/platform/documents`
   - Completion signal (existing contract): any document with `parse_status = confirmed` or confirmed-data summary visible.
2. Step B: Symptom Input
   - Route: `/platform/symptoms`
   - Completion signal (existing contract): symptom list has >= 1 row for current person.
3. Step C: Daily Assistant Insight Visible
   - Route: `/platform/dashboard`
   - Completion signal (existing contract): `DailyAssistantEntry` not in empty state (`daily-summary-empty` absent or top recommendation available).
4. Step D: Recommendation To Action
   - Route: `/platform/actions`
   - Completion signal (existing contract): at least one tracked/todo/in_progress action from recommendation source, or explicit done action.

## Required States Per Step

### Empty state
- No confirmed report + no symptom + no assistant summary + no action.
- UX contract: show first incomplete step CTA only (no fake completion).

### Missing-data state
- Assistant has recommendation but `missing_data` indicates absent evidence (filtered for non-trivial items already implemented in `DailyAssistantEntry`).
- UX contract: show data-gap explanation and direct user to missing surface route.

### Completed state
- All A-D steps satisfy completion signals.
- UX contract: journey card collapses into "journey complete" summary and keeps deep links for revisit.

## Transition Rules (no new backend)
- A->B after document confirm.
- B->C after symptom entry and dashboard refresh.
- C->D when recommendation appears and user adds/starts action.
- D->steady-state when first action is done or tracking started.

## 4. P121 Suppression-Reason Gap Placement And Severity

## Where It Lands In Journey
- Gap location: Step C and Step D evidence explainability layer (Daily Assistant and Actions evidence).
- Root cause in source: `backend/app/services/health_assistant_service.py` builds `lab_report_items` with filter `LabReportItem.abnormal_flag.isnot(None)`, which excludes suppressed rows where flag is `None` and reason is important.

## Severity For First-Run
- Classification: fast-follow, non-blocking for first-run activation.
- Rationale:
  - First-run contract success criterion is user activation path completion, not suppression-reason explainability completeness.
  - Existing surfaces still support A->B->C->D completion with current contracts.
  - P114 already reduced high-risk false abnormal behavior; remaining issue is confidence/explainability quality, not journey viability.

## 5. Final Classification And Next Lane

## Discovery Classification
- `can-implement-minimally`

## Final Classification
- `P122_FIRST_RUN_JOURNEY_DISCOVERY_READY`

## Next Implementation Lane
- `P121 Backend Evidence Bundle Suppression Reason Propagation` (already CEO approved; remains next after P122)

## Minimal Implementation File List (Proposed, no changes made in P122)
- `frontend/app/components/platform/daily-assistant-entry.tsx`
  - Add first-run journey progress block (step CTA + state badges) using existing routes.
- `frontend/lib/first-run-journey.ts` (new)
  - Pure state-derivation helper from existing payloads (documents/symptoms/summary/actions).
- `frontend/app/platform/dashboard/page.tsx`
  - Mount minimal first-run journey entry panel above/near Daily Assistant section.
- `frontend/tests/e2e/p122-first-run-journey-contract.spec.ts` (new)
  - Mocked contract for empty/missing/completed transitions and CTA routing.

## Test Strategy For The Lane (Cost-aware)
- Keep existing contracts as safety net:
  - `make documents-page-contract`
  - `make symptoms-page-contract`
  - `make daily-assistant-contract`
  - `make actions-page-contract`
  - `make report-symptom-recommendation-contract`
- Add one focused P122 contract spec only; avoid full baseline reruns if no backend change.

## Governance Notes
- No runtime code changed in this task.
- No backend/schema/API expansion performed.
- No branch/worktree operations performed.
- P120 stale claim "lab_report_items includes abnormal_flag_reason" was not reused as truth for Daily Assistant path decisions; source code verification was used.