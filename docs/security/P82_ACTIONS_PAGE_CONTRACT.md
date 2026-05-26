# P82 — Actions Page Frontend Contract

**Phase:** P82 Actions Page Contract Consolidation  
**Date:** 2026-05-26  
**Status:** READY  
**Classification:** `P82_ACTIONS_PAGE_CONTRACT_READY`

---

## 1. Purpose

This document defines the stable frontend contract for the `/platform/actions` page
recommendation history, feedback loop, and snooze surfaces after P80–P81.

It serves as a reference for:
- Future developers adding or modifying Actions page sections
- CI/CD gates to detect accidental removal of key testids
- Reviewer checklist for any PR touching `frontend/app/platform/actions/`
  or `frontend/app/components/platform/`

---

## 2. Scope

- **Route**: `/platform/actions` only  
- **Layer**: Frontend (Next.js, App Router)  
- **No backend/API changes** — all contract tests are fully mocked  
- **No business logic changes**

---

## 3. Stable Test IDs

| Test ID | Phase | User-Visible Meaning | Data Condition | Required / Optional | Regression Spec |
|---------|-------|----------------------|----------------|----------------------|-----------------|
| `actions-loading` | P80 | Loading skeleton while dashboard API pending | `loading === true` (before `getDashboard` resolves) | **Required** | p80-actions-recommendation-smoke |
| `actions-page` | P80 | Loaded page root (ErrorBoundary inner wrapper) | `loading === false` | **Required** | p80-actions-recommendation-smoke, p81-actions-feedback-snooze-smoke, p82-actions-page-contract |
| `actions-feedback-loop` | P81 | Section 4 "行動效果回饵" — completed actions feedback card grid | `grouped.completed.length > 0` (actions with `status: 'done'`) | **Optional** — renders only when done actions exist | p81-actions-feedback-snooze-smoke, p82-actions-page-contract |
| `actions-snoozed-section` | P81 | 稍後提醒 — snoozed actions section inside status board | `grouped.snoozed.length > 0` (actions with `status: 'snoozed'`) | **Optional** — renders only when snoozed actions exist | p81-actions-feedback-snooze-smoke, p82-actions-page-contract |
| `recommendation-history-card` | P62 | Recommendation outcome history timeline | `historyData !== null` (outcome-feedback API returns data) | **Optional** — renders only when outcome history exists | p80-actions-recommendation-smoke, p81-actions-feedback-snooze-smoke, p82-actions-page-contract |
| `history-summary-bar` | P62 | Summary bar inside recommendation history card | `historyData !== null` | **Optional** | p80-actions-recommendation-smoke |

### Grouping logic reference (from `actions/page.tsx` useMemo)

```typescript
const completed = [...actions.filter((a) => a.status === 'done')].sort(...)
const snoozed   = actions.filter((a) => a.status === 'snoozed')
```

- `actions-feedback-loop` visible ↔ `status: 'done'` actions in API response  
- `actions-snoozed-section` visible ↔ `status: 'snoozed'` actions in API response  
- Both sections can co-exist on the same page  

---

## 4. Invariants

The following behavioral guarantees must hold after any PR touching the Actions page:

### 4.1 State Separation

- The page **must** distinguish loading state from loaded state.  
  `actions-loading` is present while `getDashboard` is pending.  
  `actions-page` is present after `getDashboard` resolves (success or failure).  
  These two states are **mutually exclusive**.

### 4.2 Recommendation History

- `recommendation-history-card` **must** render when `getOutcomeFeedback` returns non-null data.  
- `recommendation-history-card` **must not** render when `getOutcomeFeedback` fails or returns null.  
- An API failure on outcome feedback **must not** crash the page — `actions-page` must remain visible.

### 4.3 Feedback Loop Section

- `actions-feedback-loop` **must** render only when at least one `status: 'done'` action exists.  
- `actions-feedback-loop` content must not imply medical diagnosis.  
- `actions-feedback-loop` must not be rendered when `grouped.completed` is empty.

### 4.4 Snooze Section

- `actions-snoozed-section` **must** render only when at least one `status: 'snoozed'` action exists.  
- `actions-snoozed-section` must not imply push notification delivery unless explicitly supported.  
- `actions-snoozed-section` must not be rendered when `grouped.snoozed` is empty.

### 4.5 Medical Overclaiming Guard

The following phrases **must not** appear anywhere on the rendered Actions page:

| Prohibited Phrase | Reason |
|-------------------|--------|
| `建議有效` | Implies certainty of recommendation effectiveness |
| `改善健康` | Implies guaranteed health improvement |
| `治療有效` | Medical treatment claim |
| `已證明有效` | Clinical proof claim |
| `醫療診斷` | Medical diagnosis claim |

### 4.6 Playwright Mock Rule

- Use `route.fulfill({ status: 500, json: { detail: '...' } })` to simulate API failure.  
- **Never** use `route.fulfill({ json: null })` — causes Playwright route hang (discovered P80).

---

## 5. Section Overlap Map

```
/platform/actions
├── Loading state
│   └── [actions-loading]  ← while getDashboard pending
├── Loaded state root
│   └── [actions-page]
│       ├── Status board grid (xl:grid-cols-3)
│       │   ├── Todo Card
│       │   ├── In-progress Card
│       │   ├── Completed Card (up to 5)
│       │   ├── [actions-snoozed-section]  ← optional: snoozed.length > 0
│       │   └── Dismissed Card            ← optional: dismissed.length > 0
│       ├── Section 4 Feedback Loop
│       │   └── [actions-feedback-loop]   ← optional: completed.length > 0
│       └── Section 5 History Timeline
│           └── [recommendation-history-card]  ← optional: historyData !== null
│               └── [history-summary-bar]
```

---

## 6. Validation Commands

Run after any PR touching `/platform/actions` or related components:

```bash
# Contract smoke (P82)
cd frontend && npx playwright test tests/e2e/p82-actions-page-contract.spec.ts --reporter=line

# Targeted regression (P80 + P81)
cd frontend && npx playwright test \
  tests/e2e/p80-actions-recommendation-smoke.spec.ts \
  tests/e2e/p81-actions-feedback-snooze-smoke.spec.ts \
  --reporter=line

# Adjacent feedback / snooze behavior
cd frontend && npx playwright test \
  tests/e2e/p55-action-feedback-loop.spec.ts \
  tests/e2e/p56-recommendation-feedback-persistence.spec.ts \
  tests/e2e/p57-snooze-persistence.spec.ts \
  --reporter=line

# Daily Assistant contract
make daily-assistant-contract

# Backend smoke (must never be broken by frontend changes)
make runtime-smoke
```

---

## 7. Coverage Gaps / Known Limitations

| Gap | Status | Risk |
|-----|--------|------|
| `actions-feedback-loop` inner `ActionFeedbackCard` items — no testids on individual cards | Known gap | Low — outer section is gated |
| `decision-recommendation-layer` has zero testids | Known gap | Low — P55 covers button behavior |
| `actions-snoozed-section` does not verify future vs past `snoozed_until` in UI | Known gap | Low — grouping useMemo only checks status field |
| Loading state test requires `freezeDashboard` async coordination | Inherent Playwright pattern | Low — pattern established in P80 |

---

## 8. Change History

| Phase | Change | Files |
|-------|--------|-------|
| P62 | Added `recommendation-history-card`, `history-summary-bar` testids | recommendation-history-card.tsx |
| P80 | Added `actions-loading`, `actions-page` testids; wrote recommendation smoke | actions/page.tsx, p80-actions-recommendation-smoke.spec.ts |
| P81 | Added `actions-snoozed-section`, `actions-feedback-loop` testids; wrote feedback/snooze smoke | actions/page.tsx, p81-actions-feedback-snooze-smoke.spec.ts |
| P82 | Contract consolidation doc + contract smoke test | docs/security/P82_ACTIONS_PAGE_CONTRACT.md, p82-actions-page-contract.spec.ts |
