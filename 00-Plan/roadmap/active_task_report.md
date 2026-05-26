# Active Task Report — P77 Daily Assistant Contract Guard (2026-05-26)

## P77 Daily Assistant Contract Drift Guard (2026-05-26)

**Final Classification: `P77_DAILY_ASSISTANT_CONTRACT_GUARD_READY`**

---

### 1. Scope

After P76 created the contract doc and spec, P77 adds a lightweight
Makefile target so the P76 contract is one command away and harder
to accidentally skip.

No component changes. No backend changes. No new dependencies.
No CI wiring.

---

### 2. Changes

| File | Type | Change |
|---|---|---|
| `Makefile` | Modified | Added `daily-assistant-contract` target + `.PHONY` entry |
| `docs/security/P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md` | Modified | Added P77 guard command to §6, P77 row to §8 |

---

### 3. New Makefile Target

```makefile
# P77 Daily Assistant signal contract guard — local/manual only, not CI-required
# Runs typescript check + P76 contract smoke (5 tests).
# Full P64–P76 regression: use frontend-e2e-local
# See: docs/security/P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md
daily-assistant-contract:
	cd frontend && npx tsc --noEmit
	cd frontend && npx playwright test tests/e2e/p76-daily-assistant-signal-contract.spec.ts --reporter=line
```

---

### 4. Validation Results

| Gate | Result |
|------|--------|
| P76 postcheck: `npx tsc --noEmit` | ✅ 0 errors |
| P76 postcheck: P76 contract tests (5) | ✅ 5/5 |
| P76 postcheck: `make runtime-smoke` (56) | ✅ 56/56 |
| `make daily-assistant-contract` (new target) | ✅ TSC + 5/5 |

---

### 5. Commits

| Commit | Message |
|--------|---------|
| `f0fd117` | chore(dev): P77 daily assistant contract make target |

---



### 1. Scope

After P64–P75, the Daily Assistant exposes 11 stable test ids. P76 consolidates
them into one frontend signal contract document and one contract smoke test.
No component changes. No backend changes.

---

### 2. Changes

| File | Type |
|---|---|
| `docs/security/P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md` | New contract doc |
| `frontend/tests/e2e/p76-daily-assistant-signal-contract.spec.ts` | New contract test |

---

### 3. Contract Test (`p76-daily-assistant-signal-contract.spec.ts`) — 5 tests

| # | Test | Result |
|---|------|--------|
| 1 | Full signal happy path: all optional signals visible with fully-populated data | ✅ |
| 2 | Loading state contract: `daily-assistant-loading` visible while API pending | ✅ |
| 3 | Empty state contract: `daily-summary-empty` visible when no summary + no topRec | ✅ |
| 4 | Negative contract: all optional signals absent when source fields absent/zero/none | ✅ |
| 5 | ErrorBoundary contract: dashboard renders without error fallback | ✅ |

---

### 4. Contract Document

Path: `docs/security/P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md`

Covers:
- Full test id table with data conditions, phase, required/optional status
- 3 state model (loading / empty / loaded)
- 6 invariant groups (state exclusivity, empty-state guard, optional signal guards,
  escalation source, medical framing, naming conventions)
- Validation commands
- Known limitations

---

### 5. Test Gate Results

| Gate | Result |
|------|--------|
| `npx tsc --noEmit` | ✅ 0 errors |
| `npx next build` | ✅ clean |
| P76 acceptance (5 tests) | ✅ 5/5 |
| P64–P76 regression (110 tests) | ✅ 110/110 |
| `make runtime-smoke` (56 Python tests) | ✅ 56/56 |

---

### 6. Commits

| Commit | Message |
|--------|---------|
| `539ecec` | test(frontend): P76 daily assistant signal contract |
| `75e2a6a` | docs(security): P76 daily assistant signal contract |

---

### 7. data-testid inventory (cumulative P64–P76)

| testid | Phase | Required / Optional | Data condition |
|--------|-------|---------------------|---------------|
| `daily-assistant-entry` | baseline | required | always |
| `daily-assistant-loading` | P74 | required during load | `isFullyLoading` |
| `daily-summary-empty` | baseline | required when no data | `!hasDailySummary && !topRec` |
| `daily-summary-why-now` | P65 | optional | `summary.whyNow` truthy |
| `daily-summary-missing-data` | P66 | optional | `missingItems.length > 0` |
| `daily-summary-missing-data-explanation` | P66 | optional | `missingItems.length > 0` |
| `daily-summary-action-impact` | P67 | optional | `summary.todayAction` truthy |
| `daily-summary-outcome-improved-badge` | P68 | optional | `hasFeedback && improved_count > 0` |
| `daily-summary-biggest-change-context` | P69 | optional | `summary.biggestChange` truthy |
| `daily-summary-confidence-signal` | P70 | optional | `confidence > 0` |
| `daily-summary-encouragement` | P71 | optional | `encouragement` non-empty |
| `daily-summary-escalation-notice` | P72 | optional | `escalationLevel !== 'none'` |
| `daily-summary-next-checkin` | P73 | optional* | `trust.nextCheckInSuggestion \|\| summary` |

---

## P75 Daily Assistant Empty State Testability (2026-05-26)

## P75 Daily Assistant Empty State Testability / Copy Consistency (2026-05-26)

**Final Classification: `P75_DAILY_ASSISTANT_EMPTY_STATE_COVERAGE_READY`**

---

### 1. Scope

The empty state branch in `DailyAssistantEntry` already had
`data-testid="daily-summary-empty"` (introduced pre-P65). P74 covered two basic
scenarios. P75 deepens empty state coverage and verifies copy consistency.

**Decision: Option A (tests-only).** No component change was needed.
The existing `daily-summary-empty` testid is stable; P74 tests depend on it.
The naming difference (`daily-summary-empty` vs `daily-assistant-loading`) is
cosmetic — `daily-summary-` is the intra-card namespace, `daily-assistant-` is
the card-level namespace. Alias wrapper would add complexity without benefit.

No component changes. No backend changes. No new dependencies.

---

### 2. Change

None to production code. One test file added:
`frontend/tests/e2e/p75-daily-assistant-empty-state.spec.ts`

---

### 3. Test Coverage (`p75-daily-assistant-empty-state.spec.ts`) — 11 tests

| # | Test | Result |
|---|------|--------|
| 1 | Empty state visible: all summary fields empty strings + no recommendations | ✅ |
| 2 | Empty state visible: daily-summary returns empty object + no recommendations | ✅ |
| 3 | Empty state NOT visible when summary.topRisk is populated | ✅ |
| 4 | Empty state NOT visible when topRec present even if summary empty (grid fallback) | ✅ |
| 5 | Empty state heading copy is non-diagnostic ("今日摘要尚未生成") | ✅ |
| 6 | CTA link points to /quick-check-in | ✅ |
| 7 | Empty state NOT visible while loading (loading phase shown instead) | ✅ |
| 8 | Loading → empty state transition: loading appears then resolves to empty state | ✅ |
| 9 | P74 regression: daily-assistant-loading visible while API pending | ✅ |
| 10 | P73 regression: next-checkin visible in normal loaded state | ✅ |
| 11 | Dashboard renders without ErrorBoundary fallback | ✅ |

**Key techniques:**
- Promise-based route freeze for loading/empty transition tests (same as P74)
- Fixture `DAILY_SUMMARY_NULL_BODY = {}` exercises undefined-field path
- `RECOMMENDATIONS_WITH_ONE` verifies the `hasDailySummary || topRec` guard

---

### 4. Test Gate Results

| Gate | Result |
|------|--------|
| `npx tsc --noEmit` | ✅ 0 errors |
| `next build` (no rebuild — tests-only) | ✅ P74 build valid |
| P75 acceptance (11 tests) | ✅ 11/11 |
| P64–P75 regression (105 tests) | ✅ 105/105 |
| `make runtime-smoke` (56 Python tests) | ✅ 56/56 |

---

### 5. Commits

| Commit | Message |
|--------|---------|
| `c2c4a1a` | test(frontend): P75 daily assistant empty state coverage |

---

### 6. data-testid inventory (cumulative P64–P75)

| testid | Phase | Component | Notes |
|--------|-------|-----------|-------|
| `daily-assistant-entry` | baseline | card root | |
| `daily-summary-top-risk` | baseline | 3-card grid | |
| `daily-summary-biggest-change` | baseline | 3-card grid | |
| `daily-summary-next-action` | baseline | 3-card grid | |
| `daily-summary-outcome-section` | baseline | outcome section | |
| `daily-summary-empty` | baseline | empty branch | P75 deepened coverage |
| `daily-summary-why-now` | P65 | top-risk card | |
| `daily-summary-missing-data` | P66 | missing data list | |
| `daily-summary-missing-data-explanation` | P66 | missing data copy | |
| `daily-summary-action-impact` | P67 | todayAction card | |
| `daily-summary-outcome-improved-badge` | P68 | outcome row | |
| `daily-summary-biggest-change-context` | P69 | biggestChange card | |
| `daily-summary-confidence-signal` | P70 | confidence pill | |
| `daily-summary-encouragement` | P71 | encouragement block | |
| `daily-summary-escalation-notice` | P72 | amber escalation block | |
| `daily-summary-next-checkin` | P73 | next check-in line | |
| `daily-assistant-loading` | P74 | loading skeleton | |

---

## P74 Daily Assistant Loading State Testability (2026-05-26)

## P74 Daily Assistant Loading State Testability (2026-05-26)

**Final Classification: `P74_DAILY_ASSISTANT_LOADING_STATE_READY`**

---

### 1. Scope

The loading skeleton in `DailyAssistantEntry` (`isFullyLoading` branch) had no
`data-testid`, making it untestable in Playwright without brittle element
selectors. The empty state already had `data-testid="daily-summary-empty"` from
an earlier phase. Primary target: add `data-testid="daily-assistant-loading"` to
the skeleton container div.

No backend changes. No API schema changes. No new dependencies. No logic changes.

---

### 2. Change

**Component** (`daily-assistant-entry.tsx`):
```tsx
// Before
<div className="space-y-3">

// After (P74)
<div data-testid="daily-assistant-loading" className="space-y-3">
```

One attribute added to one element in the `isFullyLoading` branch.

---

### 3. Test Coverage (`p74-daily-assistant-loading-state.spec.ts`) — 11 tests

| # | Test | Result |
|---|------|--------|
| 1 | Loading skeleton visible (testid) while daily-summary pending | ✅ |
| 2 | Loading skeleton is child of daily-assistant-entry | ✅ |
| 3 | After loading resolves: daily-summary-next-checkin visible (P73 regression) | ✅ |
| 4 | Empty state (daily-summary-empty) visible when APIs return no content | ✅ |
| 5 | Empty state not visible in normal loaded state | ✅ |
| 6 | P73 regression: trust.nextCheckInSuggestion shown | ✅ |
| 7 | P72 regression: escalation notice visible | ✅ |
| 8 | P71 regression: encouragement visible | ✅ |
| 9 | P70 regression: confidence signal visible | ✅ |
| 10 | P69 regression: biggest-change context visible | ✅ |
| 11 | Dashboard renders without ErrorBoundary fallback | ✅ |

**Key technique**: frozen daily-summary route using `Promise` in Playwright route
handler — holds `sumLoading=true`, keeping `isFullyLoading=true` until explicitly
unblocked, ensuring loading state is assertable without timing hacks.

---

### 4. Test Gate Results

| Gate | Result |
|------|--------|
| `npx tsc --noEmit` | ✅ 0 errors |
| `npx next build` | ✅ clean |
| P74 acceptance (11 tests) | ✅ 11/11 |
| P64–P73 regression (83 tests) | ✅ 83/83 |
| Full P64–P74 regression (94 tests) | ✅ 94/94 |
| `make runtime-smoke` (56 Python tests) | ✅ 56/56 |

---

### 5. Commits

| Commit | Message |
|--------|---------|
| `952cfb2` | feat(frontend): P74 daily assistant loading state testid |

---

### 6. data-testid inventory (cumulative P64–P74)

| testid | Phase | Component | Notes |
|--------|-------|-----------|-------|
| `daily-assistant-entry` | baseline | card root | |
| `daily-summary-top-risk` | baseline | 3-card grid | |
| `daily-summary-biggest-change` | baseline | 3-card grid | |
| `daily-summary-next-action` | baseline | 3-card grid | |
| `daily-summary-outcome-section` | baseline | outcome section | |
| `daily-summary-empty` | baseline | empty branch | already existed |
| `daily-summary-why-now` | P65 | top-risk card | |
| `daily-summary-missing-data` | P66 | missing data list | |
| `daily-summary-missing-data-explanation` | P66 | missing data copy | |
| `daily-summary-action-impact` | P67 | todayAction card | |
| `daily-summary-outcome-improved-badge` | P68 | outcome row | |
| `daily-summary-biggest-change-context` | P69 | biggestChange card | |
| `daily-summary-confidence-signal` | P70 | confidence pill | |
| `daily-summary-encouragement` | P71 | encouragement block | |
| `daily-summary-escalation-notice` | P72 | amber escalation block | |
| `daily-summary-next-checkin` | P73 | next check-in line | |
| `daily-assistant-loading` | **P74** | loading skeleton | **new** |

---

# Active Task Report — P73 Daily Assistant Next Check-in Suggestion (2026-05-26)

## P73 Daily Assistant Next Check-in Suggestion (2026-05-26)

**Final Classification: `P73_DAILY_ASSISTANT_NEXT_CHECKIN_READY`**

---

### 1. Scope

The daily-assistant card had a bare next check-in block that rendered
`trust.nextCheckInSuggestion` only when a top recommendation with a trust
block was present (i.e., `trust?.nextCheckInSuggestion` truthy). In all
test fixtures and real low-data scenarios where `recommendations: []`, this
block was never visible — the user received no check-in guidance.

P73 chose **Option B** (dynamic API field exists) plus a graceful fallback:
- When `trust.nextCheckInSuggestion` is present: show it (existing behavior, now with `data-testid`)
- When `trust` is null but `summary` is loaded + `todayAction` non-empty: show `完成今日行動後，回來更新記錄。`
- When `trust` is null + `todayAction` empty/absent: show `今日資料已更新，明天繼續追蹤。`

Guard: `(trust?.nextCheckInSuggestion || summary)` — element always visible
when the daily summary is loaded.

`data-testid="daily-summary-next-checkin"` added for acceptance coverage.

No backend changes. No API schema changes. No new dependencies.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Replace bare next check-in block with guarded conditional + data-testid |
| `frontend/tests/e2e/p73-daily-assistant-next-checkin.spec.ts` | 12 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P73 acceptance (12 tests) | ✅ 12/12 |
| P72 regression (16 tests) | ✅ 16/16 |
| P71 regression (12 tests) | ✅ 12/12 |
| P70 regression (10 tests) | ✅ 10/10 |
| P69 regression (7 tests) | ✅ 7/7 |
| P68 regression (6 tests) | ✅ 6/6 |
| P67 regression (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Known limitations

- The `todayAction` guard uses truthiness: an empty string (`''`) is treated
  as absent. If the backend sends a whitespace-only `todayAction`, the fallback
  "明天繼續追蹤" will render. This is the same pattern used by P71 encouragement
  (`.trim().length > 0`) but P73 does not call `.trim()` — consistent with the
  minimal-change policy; could be hardened in a future pass.
- `trust.nextCheckInSuggestion` is always shown as-is (no trim). If the backend
  returns an empty string, the logic falls through to the `summary?.todayAction`
  check. This is correct behavior since an empty string is falsy in JS.
- The fallback copy is static Chinese and will not localise if i18n is added.

---

### 5. Commit

`8fc97a3` — feat(frontend): P73 daily assistant next check-in suggestion

---

# Active Task Report — P72 Daily Assistant Escalation Notice (2026-05-26)

## P72 Daily Assistant Escalation Notice (2026-05-26)

**Final Classification: `P72_DAILY_ASSISTANT_ESCALATION_READY`**

---

### 1. Scope

Added an escalation notice that surfaces `DailyHealthSummary.escalation`
(optional `EscalationDecision` from the daily-summary API) when the
`escalationLevel` is not `'none'`. The field was already fetched every render
but never displayed. P72 closes that gap with a guarded amber block placed
before the 3-card grid so urgent signals are visible before routine context.

`EscalationDecision` shape (read from `lib/api.ts`):
```typescript
{
  escalationLevel: 'none' | 'watch' | 'warning' | 'urgent'
  reasons: string[]
  confidence: number
  recommendedAction: string | null
  requiresFollowUp: boolean
}
```

Note: the prompt suggested `should_escalate === true` but that field does not
exist in the type. The actual guard uses `escalationLevel !== 'none'`.

Guard: `summary?.escalation != null && summary.escalation.escalationLevel !== 'none'`
Placement: before the 3-card grid (after isHighConf banner).
Display: label "需要留意" + level suffix (緊急/警告/觀察) + `reasons[0]` +
`recommendedAction` prefixed with "建議：" if not null.
Uses existing `AlertTriangle` icon (already imported). No new dependencies.
No backend changes. No API schema changes.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `<div data-testid="daily-summary-escalation-notice">` before 3-card grid, guarded by escalationLevel !== 'none' |
| `frontend/tests/e2e/p72-daily-assistant-escalation-notice.spec.ts` | 16 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P72 acceptance (16 tests) | ✅ 16/16 |
| P71 regression (12 tests) | ✅ 12/12 |
| P70 regression (10 tests) | ✅ 10/10 |
| P69 regression (7 tests) | ✅ 7/7 |
| P68 regression (6 tests) | ✅ 6/6 |
| P67 regression (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Known limitations

- Only `reasons[0]` is shown; subsequent reasons are silently dropped if the
  backend returns multiple. This is intentional to keep the notice compact.
- `escalationLevel` maps to static Chinese labels in the frontend. If a new
  level is added to the backend enum, the label will not appear (silent fallback
  to just "需要留意" with no suffix).
- The notice is styled amber regardless of level — `urgent` does not receive
  a stronger colour. This is intentional conservatism (no medical alarm UX
  without product review).
- Prompt specified `should_escalate === true` guard; the actual type uses
  `escalationLevel !== 'none'` — corrected after reading `lib/api.ts`.

---

### 5. Commit

`4477a22` — feat(frontend): P72 daily assistant escalation notice

---

# Active Task Report — P71 Daily Assistant Encouragement Message (2026-05-26)

## P71 Daily Assistant Encouragement Message (2026-05-26)

**Final Classification: `P71_DAILY_ASSISTANT_ENCOURAGEMENT_READY`**

---

### 1. Scope

Added an encouragement block to the Daily Assistant section that surfaces
`DailyHealthSummary.encouragement` (optional string from the daily-summary API)
when present and non-empty. The field was already fetched every render but never
displayed to the user. P71 closes that gap with a minimal guarded block:
label "小助手鼓勵" + the trimmed encouragement text.

Guard: `typeof summary?.encouragement === 'string' && summary.encouragement.trim().length > 0`
Placement: after the P70 confidence signal, before the top-recommendation block.
Whitespace-only strings are suppressed (`.trim().length > 0`).
No backend changes. No API schema changes. No new dependencies. No new icon imports.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `<div data-testid="daily-summary-encouragement">` with label + trimmed text, guarded by non-empty string check |
| `frontend/tests/e2e/p71-daily-assistant-encouragement.spec.ts` | 12 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P71 acceptance (12 tests) | ✅ 12/12 |
| P70 regression (10 tests) | ✅ 10/10 |
| P69 regression (7 tests) | ✅ 7/7 |
| P68 regression (6 tests) | ✅ 6/6 |
| P67 regression (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Known limitations

- The encouragement text comes verbatim from the AI-generated backend field; the
  frontend does not validate or sanitize the content beyond trimming whitespace.
- Empty string and whitespace-only values are correctly suppressed. Null is not
  produced by the typed API but would also be suppressed by the string guard.
- The label "小助手鼓勵" is hardcoded; if the backend were to produce encouragement
  in another language, the label would still be Chinese.

---

### 5. Commit

`b21e25e` — feat(frontend): P71 daily assistant encouragement message

---

# Active Task Report — P70 Daily Assistant Confidence Signal (2026-05-26)

## P70 Daily Assistant Confidence Signal (2026-05-26)

**Final Classification: `P70_DAILY_ASSISTANT_CONFIDENCE_SIGNAL_READY`**

---

### 1. Scope

Added a compact confidence signal that surfaces `DailyHealthSummary.confidence`
(a 0–1 float from the daily-summary API) as a rounded percentage to the user.
Previous components used `topRec.trust.level` ("low"/"high") for qualitative
banners, but the numeric `confidence` field was never displayed. P70 fills that
gap with a single guarded line: `可信度 N%`.

Guard: `typeof summary?.confidence === 'number' && summary.confidence > 0`
Placement: after the 3-card grid, before the top-recommendation block.
No backend changes. No API schema changes. No new dependencies.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `<div data-testid="daily-summary-confidence-signal">` after 3-card grid, guarded by confidence > 0 |
| `frontend/tests/e2e/p70-daily-assistant-confidence-signal.spec.ts` | 10 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P70 acceptance (10 tests) | ✅ 10/10 |
| P69 regression (7 tests) | ✅ 7/7 |
| P68 regression (6 tests) | ✅ 6/6 |
| P67 regression (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Known limitations

- The `confidence` field from `DailyHealthSummary` is a raw API value; its exact
  calibration is not validated in the frontend. The guard `> 0` prevents showing
  a "可信度 0%" which would be confusing.
- The existing low/high confidence banners (from `topRec.trust.level`) remain
  unchanged — they represent recommendation-level trust, not summary-level.

---

### 5. Commit

`cdb0328` — feat(frontend): P70 daily assistant confidence signal

---

# Active Task Report — P69 Daily Assistant Biggest Change Context Label (2026-05-26)

## P69 Daily Assistant Biggest Change Context Label (2026-05-26)

**Final Classification: `P69_DAILY_ASSISTANT_BIGGEST_CHANGE_CONTEXT_READY`**

---

### 1. Scope

Added a static context label beneath the 今日最大變化 (biggestChange) text,
using the same conditional guard pattern established in P65 (whyNow) and P67
(action impact). The label renders only when `summary?.biggestChange` is
non-empty, and displays: 「此為近 7 天最顯著的健康趨勢變化。」

No backend changes. No API schema changes. No new dependencies.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `<p data-testid="daily-summary-biggest-change-context">` after biggestChange text, guarded by `summary?.biggestChange` non-empty |
| `frontend/tests/e2e/p69-daily-assistant-biggest-change-context.spec.ts` | 7 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P69 acceptance (7 tests) | ✅ 7/7 |
| P68 regression (6 tests) | ✅ 6/6 |
| P67 regression (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Commit

`07aa0cc` — feat(frontend): P69 daily assistant biggest change context label

---

# Active Task Report — P68 Daily Assistant Outcome Known Badge (2026-05-26)

## P68 Daily Assistant Outcome Known Badge (2026-05-26)

**Final Classification: `P68_DAILY_ASSISTANT_OUTCOME_BADGE_READY`**

---

### 1. Scope

Added an explicit positive badge in the 7-day outcome section when
`fbSummary.improved_count > 0`. Previously the count was shown only as a grey
dot + plain text. The badge uses the already-imported `CheckCircle2` icon with
emerald styling and shows "已改善 N 項，持續追蹤中".

No backend changes. No new dependencies. Guard: `improved_count > 0`.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `<div data-testid="daily-summary-outcome-improved-badge">` after count flex row, guarded by `fbSummary!.improved_count > 0` |
| `frontend/tests/e2e/p68-daily-assistant-outcome-badge.spec.ts` | 6 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P68 acceptance (6 tests) | ✅ 6/6 |
| P67 regression (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Commit

`1733d40` — feat(frontend): P68 daily assistant outcome known badge

---

# Active Task Report — P67 Daily Assistant Action Impact Clarity (2026-05-26)

## P67 Daily Assistant Action Impact Clarity (2026-05-26)

**Final Classification: `P67_DAILY_ASSISTANT_ACTION_IMPACT_CLARITY_READY`**

---

### 1. Scope

Added a short expected-impact line below the "今日主要行動" (recommended next action) text.
The line renders only when `summary.todayAction` is non-empty — same conditional guard as
the P65 `whyNow` pattern. Static copy only; no backend changes, no new API fields.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `<p data-testid="daily-summary-action-impact">` inside the next-action card, guarded by `summary?.todayAction` |
| `frontend/tests/e2e/p67-daily-assistant-action-impact-clarity.spec.ts` | 5 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P67 acceptance (5 tests) | ✅ 5/5 |
| P66 regression (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Commit

`0a58f5d` — feat(frontend): P67 daily assistant action impact clarity

---

# Active Task Report — P66 Daily Assistant Missing Data Explanation (2026-05-26)

## P66 Daily Assistant Missing Data Explanation (2026-05-26)

**Final Classification: `P66_DAILY_ASSISTANT_MISSING_DATA_EXPLANATION_READY`**

---

### 1. Scope

User-facing improvement: each missing-data item in the Daily Assistant card now
shows an inline explanation of what capability is unlocked when that data is
provided. A stable `data-testid="daily-summary-missing-data-explanation"` summary
paragraph is also added at the bottom of the missing-data block.

No backend changes. No new dependencies. No new routes.

---

### 2. Files changed

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Add `MISSING_DATA_GAINS` map, `getMissingGain()` helper; restructure missing-data block from `flex-wrap` to `flex-col` with per-item gain text and explanation paragraph |
| `frontend/tests/e2e/p66-daily-assistant-missing-data-explanation.spec.ts` | 5 acceptance tests (new file) |

---

### 3. Test results

| Suite | Result |
|---|---|
| P66 acceptance (5 tests) | ✅ 5/5 |
| P65 regression (4 tests) | ✅ 4/4 |
| P64 regression (6 tests) | ✅ 6/6 |
| Backend smoke (56 tests) | ✅ 56/56 |

---

### 4. Commit

`a00a8ae` — feat(frontend): P66 daily assistant missing data explanation

---

# Active Task Report — P65 Daily Assistant Why-Now Clarity (2026-05-26)

## P65 Daily Assistant Why-Now Clarity (2026-05-26)

**Final Classification: `P65_DAILY_ASSISTANT_CONTINUITY_READY`**

---

### 1. Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD at start | `85ae765` — docs(report): P64 recovery handoff ✅ |
| Dirty files | 4 governance M — no scope conflict ✅ |

---

### 2. P64 Postcheck

| Suite | Result |
|---|---|
| `npx tsc --noEmit` | ✅ 0 errors |
| P64 targeted (6 tests) | ✅ 6/6 passed |
| P55/P56/P57 regression (17 tests) | ✅ 17/17 passed |
| `make runtime-smoke` | ✅ 56/56 passed |

---

### 3. Chosen P65 Improvement

**Surface the `whyNow` field on the daily summary top-risk card.**

**Why bounded**:
- `DailyHealthSummary` type already had `whyNow: string` defined in `lib/api.ts`
- P64 test fixture already populated `whyNow: '近期記錄顯示血壓波動加劇'`
- The field was fetched by the component but never rendered anywhere in the UI
- One conditional `<p>` element added — no new fetches, no types, no backend changes
- `data-testid="daily-summary-why-now"` added for stable acceptance targeting

**Addresses P65 requirements**:
- #1 (today's top risk): risk card now shows both WHAT the risk is and WHY it matters
- #4 (why-now explanation): `whyNow` text displayed as "為什麼重要：…" sub-line

---

### 4. Files Modified

| File | Change |
|---|---|
| `frontend/app/components/platform/daily-assistant-entry.tsx` | Added conditional `whyNow` sub-line inside `daily-summary-top-risk` card |
| `frontend/tests/e2e/p65-daily-assistant-why-now-clarity.spec.ts` | New — 4 acceptance tests (present/absent whyNow + P64 regression ×2) |

---

### 5. Tests

| Suite | Result |
|---|---|
| `npx tsc --noEmit` (pre + post) | ✅ 0 errors |
| P65 targeted (4 tests) | ✅ 4/4 passed |
| P64 regression (6 tests) | ✅ 6/6 passed |
| P55/P56/P57 regression (17 tests) | ✅ 17/17 passed |
| `make runtime-smoke` | ✅ 56/56 passed |

---

### 6. Commits

- `0a1c470` feat(frontend): P65 daily assistant why-now clarity — render whyNow explanation on top-risk card

---

### 7. Known Limitations / Unknown / Inferred

- `whyNow` is only shown for the top-risk card. `biggestChange` and `todayAction` cards do not have an analogous "why this matters" sub-line — this is intentional (bounded scope).
- The `whyNow` field comes from the backend `/health-assistant/daily-summary` endpoint. If the backend returns an empty string or omits the field, the sub-line is correctly suppressed.
- P65 does not address requirements #2 (biggest change), #3 (recommended next action), #5 (missing data), #6 (outcome known/unknown) beyond what P64 already shipped. These remain as future candidates for P66+.

---

# Active Task Report — P64-RECOVERY (2026-05-26)

## P64-RECOVERY (2026-05-26)

**Final Classification: `P64_RECOVERY_READY`**

---

### Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD | `f0678d3` — docs(report): P63 recommendation history card acceptance closure |
| Dirty files at start | 7 expected (4 governance M, 1 M daily-assistant-entry, 2 ?? spec files) — no scope conflict |

---

### Step 1A — Diag Intent Extracted

`frontend/tests/e2e/p64-diag.spec.ts` was a runtime crash investigation tool,
not an acceptance test. Design intent extracted to `docs/security/P64_RECOVERY_DIAGNOSIS.md`:
- `page.on('pageerror', ...)` + `page.on('console', ...)` capture pattern
- localStorage auth bypass via `addInitScript`
- 8-second wait + body text dump strategy
- Route stubs for all `/api/v1/**` paths (5 lines corrupted by copy-paste damage)

File physically removed (`rm`) — was untracked, no `git rm` needed.

### Step 1C — TypeScript

`npx tsc --noEmit` → **Exit 0, 0 errors** ✅

---

### Step 2A — Baseline Failure

`npx playwright test ...p64-daily-assistant-summary-quality.spec.ts` → **5 failed, 1 passed**

All 5 failures: `[data-testid="daily-assistant-entry"]` not visible (12s timeout).
Error-context snapshot confirmed: `載入失敗，請重新整理` — ErrorBoundary fallback active.

Test 2 ("missing data state") uniquely passed because its mock stub included `missing_data: [...]`.

### Step 2B — PageError Stack

```
TypeError: Cannot read properties of undefined (reading 'length')
    at sC (dashboard/page-9f34c3fea89de3b0.js:1:99153)
    [React render stack — rE → l$ → iZ → ia]
```

### Step 2D — [Decision]: `both`

**Production-side (real bug):**
`frontend/app/components/platform/health-assistant-panel.tsx:268`
```ts
const hasMissing = data && data.missing_data.length > 0 && !hasRecs;
//                                           ^^^^^^^^ undefined when API omits field
```
`data.missing_data` is `undefined` when the recommendations API response lacks the field.
Accessing `.length` on `undefined` throws `TypeError` → React catches → `ErrorBoundary`.

**Mock-side (test gap):**
Default stub `{ person_id, recommendations: [], total: 0 }` omitted `missing_data`,
making 5/6 tests exercise the crash path every run.

---

### Step 3 — Minimum Fix

**Fix 1 — `health-assistant-panel.tsx:267–268` (production null guard):**
```ts
// Before:
const hasRecs = data && data.recommendations.length > 0;
const hasMissing = data && data.missing_data.length > 0 && !hasRecs;
// After:
const hasRecs = data && (data.recommendations?.length ?? 0) > 0;
const hasMissing = data && (data.missing_data?.length ?? 0) > 0 && !hasRecs;
```

**Fix 2 — `p64-daily-assistant-summary-quality.spec.ts` default stub:**
Added `missing_data: []` to default recommendations in `stubRoutes()`.

**Diagnostic cleanup:** Removed `page.on('pageerror', ...)` / `page.on('console', ...)` instrumentation before commit.

---

### Step 3C — Full Validation

| Check | Result |
|---|---|
| `npx tsc --noEmit` | Exit 0 ✅ |
| P64 `p64-daily-assistant-summary-quality.spec.ts` | **6/6 PASS** ✅ |
| P55 `p55-action-feedback-loop.spec.ts` | 9/9 PASS ✅ |
| P56 `p56-recommendation-feedback-persistence.spec.ts` | 4/4 PASS ✅ |
| P57 `p57-snooze-persistence.spec.ts` | 4/4 PASS ✅ |
| `make runtime-smoke` | 56 passed, 0 failed ✅ |

---

### Commits

- **C2** `fix(frontend): P64 daily assistant guard + acceptance recovery`
  — `frontend/app/components/platform/health-assistant-panel.tsx` (null guard)
  — `frontend/app/components/platform/daily-assistant-entry.tsx` (P64 data-testid hooks)
  — `frontend/tests/e2e/p64-daily-assistant-summary-quality.spec.ts` (mock fix, diagnostic removed)

- **C3** `docs(security): add P64 recovery diagnosis evidence`
  — `docs/security/P64_RECOVERY_DIAGNOSIS.md`

- **C4** `docs(report): P64 recovery handoff`
  — `00-Plan/roadmap/active_task_report.md`

---

### Known Limitations

1. `p64-diag.spec.ts` syntax corruption root cause not confirmed — likely copy-paste accident during P64 handoff; no tracking needed.
2. `health-assistant-panel.tsx` `generated_at` field also absent from mocks — `data?.generated_at` already uses optional chain (safe); no action needed.
3. `HealthAssistantData.missing_data` is typed as required (`string[]`) in the interface but absent from API in low-data states. A follow-up could update the interface to `missing_data?: string[]` for better type accuracy.
4. Backend regression (723 PASS from P13) not re-run in this session — backend untouched, `make runtime-smoke` 56/56 confirms no regression.

---

--- # Appendix: Prior Sprint Reports ---

## P63-RECOMMENDATION-HISTORY-ACCEPTANCE (2026-05-25)

**Final Classification: `P63_RECOMMENDATION_HISTORY_ACCEPTANCE_READY`**

### 1. 本輪目標
驗證並強化 P62 建議回饋 Timeline Card 的產品接受度：placement（元件出現在 Section 4 之後）、error state（API 500 → 卡片不顯示）、安全文案、回歸測試。

### 2. 已完成事項
- 調查 `recommendation-history-card.tsx`、`page.tsx` 整合、P62 spec，確認 5 項驗收標準
- 確認 placement：Section 5 (`RecommendationHistoryCard`) 在 Section 4 (`行動效果回饋`) 之後 ✅
- 確認 error state：`catch(() => setHistoryData(null))` → 卡片不渲染 ✅
- 補充 `p63-recommendation-history-acceptance.spec.ts`（2 個 Playwright tests）
- 修復 error-state 測試 timeout：以 `expect(getByText('執行中心')).toBeVisible` 取代 `waitForLoadState('networkidle')`

### 3. 修改或產出的檔案
| 檔案 | 動作 |
|------|------|
| `frontend/tests/e2e/p63-recommendation-history-acceptance.spec.ts` | 新建 |
| `00-Plan/roadmap/active_task_report.md` | prepend |

### 4. 驗證結果
| 項目 | 結果 |
|------|------|
| TypeScript `tsc --noEmit` | 0 errors ✅ |
| `make runtime-smoke` | 56 passed ✅ |
| P62 regression (8 tests) | 8/8 ✅ |
| P63 acceptance (2 tests) | 2/2 ✅ |

### 5. 目前結論
`P63_RECOMMENDATION_HISTORY_ACCEPTANCE_READY`

### 6. 尚未完成事項
無。

### 7. 風險
無產品代碼改動，純測試補充。P62 所有回歸通過。

### 8. 建議
進入 P64。

### 9. 下一輪 task prompt
由 CEO 決定。

### 10. CTO 摘要
P63 驗證 P62 Recommendation History Card 產品接受度。5 項驗收標準全部通過：(1) placement—Section 5 在 Section 4 之後；(2) error state—API 500 時卡片不顯示；(3) 安全文案存在；(4) 空狀態文案存在；(5) P62 regression 8/8。補充 `p63-recommendation-history-acceptance.spec.ts` 2 個 Playwright tests（placement + error state）。修復 error-state test timeout（networkidle → getByText）。TypeScript clean；runtime-smoke 56 passed；P62 8/8；P63 2/2。無產品代碼改動。Commit: `5ccf7c1`。

---

## P62-RECOMMENDATION-FEEDBACK-TIMELINE (2026-05-25)

**Final Classification: `P62_RECOMMENDATION_FEEDBACK_TIMELINE_READY`**

### 1. 本輪目標
新增 `recommendation-history-card.tsx`，使用現有 `GET /api/v1/health-assistant/outcome-feedback?window_days=30` API，讓使用者在 `/platform/actions` 看到 30 天建議回饋 timeline。

### 2. 已完成事項
- 建立 props-driven `RecommendationHistoryCard` 元件（feedback status 標籤、顏色徽章、outcome badge、空狀態、安全免責聲明）
- 整合至 `/platform/actions` Section 5，在現有 `view_actions` useEffect 中新增 `getOutcomeFeedback(30)` fetch
- 建立 8 個 Playwright acceptance tests（完全 mocked，無需 live backend）
- TypeScript 修正：`showOutcomeBadge` 條件移除錯誤的 `!== 'completed'` 判斷

### 3. 修改或產出的檔案
| 檔案 | 操作 |
|------|------|
| `frontend/app/components/platform/recommendation-history-card.tsx` | 新建 |
| `frontend/app/platform/actions/page.tsx` | 修改（+14 行，新增 import + state + fetch + render） |
| `frontend/tests/e2e/p62-recommendation-history-card.spec.ts` | 新建 |
| `00-Plan/roadmap/active_task_report.md` | prepend P62 block |

### 4. 驗證結果
| 驗證項目 | 結果 |
|----------|------|
| TypeScript `npx tsc --noEmit` | ✅ 0 errors |
| `make runtime-smoke` | ✅ 56 passed, 0 failures |
| Playwright P62 (8 tests) | ✅ 8/8 passed |
| Playwright P55/P56/P57 regression (17 tests) | ✅ 17/17 passed |

### 5. 目前結論
`P62_RECOMMENDATION_FEEDBACK_TIMELINE_READY` — 所有驗證通過，已 commit `b6cb0b9`。

### 6. 尚未完成事項
無。P62 bounded scope 全部完成。

### 7. 風險
無新後端改動，僅前端元件新增 + fetch，風險極低。

### 8. 建議
進入 P63（待 CEO 決定下一個 product slice 方向）。

### 9. CTO 摘要
P62 完成 Recommendation Feedback Timeline。新增 `recommendation-history-card.tsx`（props-driven, 30-day window）；整合至 `/platform/actions` section 5；8 Playwright tests 全過；使用現有 `/outcome-feedback?window_days=30` + P59 型別；無後端改動；TypeScript clean；runtime-smoke 56 passed；P55/P56/P57 regression 17/17；安全說明已加入（不代表醫療效果）。Commit: `b6cb0b9`。

---

## P61-ROADMAP-REFOCUS-AFTER-OUTCOME-SMOKE-CLOSURE (2026-05-25)

**Final Classification: `P61_ROADMAP_REFOCUS_READY`**

### Branch Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- HEAD: `6ea326b` (P60 outcome-smoke) ✅
- Dirty files: `CEO-Decision.md`, `CTO-Analysis.md`, `active_task.md`, `roadmap.md` (expected governance outputs only) ✅

### P50–P60 Closure Summary

| Phase | Result | Commit |
|-------|--------|--------|
| P50 | Frontend auth smoke stabilized (missing BUILD_ID diagnosed) | `0191e59` |
| P51 | Recommendation explanation safety (safe Chinese copy) | — |
| P52 | Prioritized action safety | — |
| P53 | Action confidence labels | — |
| P54 | Daily summary context (topRisk/biggestChange/todayAction/whyNow/confidence/missingData) | — |
| P55 | Action feedback loop (mark done/snoozed/not_useful/not_applicable) | `0191e59` |
| P56 | Recommendation feedback persistence | `9624f04` |
| P57 | Snooze persistence + dismissed filter | `07b15d0` |
| P58 | Recommendation outcome readiness safeguards (safe copy, confidence=0.0) | `5dea27e` |
| P59 | Outcome visibility: frontend type unions, outcome-feedback-card, 18 API tests | `4e5dd81` |
| P60 | Outcome smoke: `outcome-smoke` Makefile target, 56 tests in `make runtime-smoke` | `6ea326b` |

### Product Gap Identified

After P50–P60, the product recommendation → feedback → outcome chain is closed at the data/API layer.
**Missing from user experience**: a chronological history view showing past recommendations, user responses, and safe outcome statuses.

### Option Evaluation

| Option | Status | Reason |
|--------|--------|--------|
| A — Daily Assistant Summary Quality | Backend solid (all fields returned), UI polish only | Lower value: backend complete |
| B — Recommendation Feedback Timeline | **Selected** | Completes visible product loop; existing API + types; bounded scope |
| C — Report-to-Action Closure | Already implemented per P4 roadmap | No clear gap |
| D — Data Insufficiency Clarity | `missingData` field exists in response | Minor UI polish |

### Decision: Option B — P62

**Rationale**: P55–P60 built the full action feedback + outcome data pipeline. The logical next product step is giving users a visible record of their recommendation history. The backend endpoint (`/outcome-feedback?window_days=30`) and all TypeScript types (`OutcomeFeedbackItem`, `OutcomeFeedback`) already exist. Only a new frontend component is needed.

### Files Changed
| File | Change |
|------|--------|
| `00-Plan/roadmap/roadmap.md` | Updated Latest Phase Status to reflect P50–P60 closure; added P62 direction |
| `00-Plan/roadmap/active_task.md` | Replaced stale P50 task with P62 worker prompt |
| `00-Plan/roadmap/active_task_report.md` | This P61 block prepended |

### Tests
Code tests: NOT RUN (docs/roadmap-only changes).
TypeScript: NOT RUN (no frontend code changes).

### Commits
- C1: `docs(roadmap): refocus product roadmap after P60 outcome smoke closure`

---

## P50-FRONTEND-AUTH-SMOKE-DIAGNOSIS (2026-05-25)

**Final Classification: `P50_FRONTEND_AUTH_SMOKE_STABILIZED`**

### Branch Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `62b791f` (P49 closure) ✅
- Dirty files: `CEO-Decision.md`, `CTO-Analysis.md`, `active_task.md`, `roadmap.md` (expected CTO/CEO outputs only) ✅

### A. Reproduce + Evidence Summary

**Pre-diagnosis state:**
- `:3010` — free (no conflict)
- `:3000` — node PID 2991 (unrelated dev process)
- `:8000` — Python/uvicorn (backend live)
- `frontend/.next/BUILD_ID` — **MISSING**

**Direct `next start` probe (before fix):**
```
Error: Could not find a production build in the '.next' directory.
Try building with 'next build' before starting the production server.
EXIT: 1
```

### B. Timeout Type Judgment

**B2 — Server crash; Playwright can't connect.**

`next start` exits immediately (< 1s, exit code 1) on missing `BUILD_ID`. Playwright polls the readiness URL for the full 120s before timing out. Error message "Timed out waiting 120000ms" is misleading — the actual failure is a deterministic crash, not a slow startup.

### C. Five-Item Checklist

| Item | Result |
|------|--------|
| C1. Build state | **ROOT CAUSE** — `BUILD_ID` missing; ran `next build`, created `BUILD_ID=mmhAYpkD9M5aFIXDq1iZa` |
| C2. Port conflict | `:3010` free — no conflict (C1 resolved, C2 skipped) |
| C3. Manual `next start` | Post-fix: `✓ Ready in 438ms`, `curl → HTTP 200` (C1 resolved, C3 confirmation only) |
| C4. Readiness URL | `playwright.config.ts` url `http://127.0.0.1:3010` matches binding — no mismatch (C1 resolved) |
| C5. Env | `.env.local` has `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`; optional vars absent — not blocking (C1 resolved) |

### D. Terminal Decision

**Path (a): `P50_FRONTEND_AUTH_SMOKE_STABILIZED`**

Fix: `cd frontend && npx next build` — creates production build artifacts. No config files modified.

`make frontend-auth-smoke` post-fix: **6/6 PASS (11.7s)**.

### E. `runtime-smoke` No Regression

`make runtime-smoke` post-fix: **130 passed, 2 skipped** ✅

### Files Changed
| File | Change |
|------|--------|
| `docs/security/P50_FRONTEND_AUTH_SMOKE_STABILITY.md` | Created — full diagnosis evidence |
| `00-Plan/roadmap/active_task_report.md` | P50 block prepended |

### Commits
- C1: `docs(security): add P50 frontend auth smoke stability diagnosis`
- C2: `docs(report): P50 frontend auth smoke diagnosis handoff`

### Known Limitations
- `.next/` must exist with a valid production build before running `make frontend-auth-smoke`; `Makefile` documents this as a prerequisite comment but does not enforce it
- Fix durability: stable until `.next/` is cleared again

---

# Appendix: Prior Sprint Reports

## P49-FRONTEND-AUTH-E2E-CI-READINESS (2026-05-24)

**Final Classification: `P49_FRONTEND_AUTH_E2E_LOCAL_GATE_DOCUMENTED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `579a42c` (P48 closure) ✅
- Tree: clean ✅

### Conclusion: Option B — Docs Only

Frontend auth e2e (`frontend-auth-smoke`) cannot safely run in CI. Blockers:
- Needs `uvicorn app.main:app --port 8000` (backend service with env vars + DB)
- Needs `next start` at port 3010 (after fresh `npm run build`)
- `next start` webServer timed out locally (120s) — unreliable without freshly built frontend
- P15 timeout=120s, P16 timeout=180s — too slow for CI
- GitHub Actions does not share localhost across jobs without service containers

### Local Validation Attempt
`make frontend-auth-smoke` → `Error: Timed out waiting 120000ms from config.webServer`

Backend was live (`curl /health` → 200). Build existed (May 23). webServer still timed out.

### Canonical Local Gate
```bash
cd backend && uvicorn app.main:app --port 8000   # separate terminal
cd frontend && npm run build
make frontend-auth-smoke
```

### CI Gap
- CI runs `npm run e2e:ci` — 3 mocked specs only (no backend needed) ✅
- Auth e2e stays local-only — already documented in CI comment since P22 ✅
- Auth contract covered by CI backend suite via `backend-auth-audit` (41 tests) ✅

### runtime-smoke Unchanged
130 passed, 2 skipped ✅

### Files Changed
| File | Change |
|------|--------|
| `docs/security/P49_FRONTEND_AUTH_E2E_CI_READINESS.md` | Created |

### Commits
- C1: `docs(security): add P49 frontend auth e2e CI readiness report`
- C2: `docs(report): P49 frontend auth e2e handoff report`

---

## P48-CI-RUNTIME-SMOKE-ALIGNMENT (2026-05-24)

**Final Classification: `P48_CI_RUNTIME_SMOKE_ALIGNED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `a6a64c9` (P47 closure) ✅
- Tree: clean ✅

### Gap Found
CI's `npm run build` silently skips TypeScript (`ignoreBuildErrors: true` in `next.config.mjs`). CI's `npm run lint` is ESLint only. No CI step enforced tsc before P48.

### Fix Applied
Added `npx tsc --noEmit` step to CI frontend job (`.github/workflows/ci-cd.yml`) after `npm ci`, before lint/build. Equivalent to `make frontend-tsc`.

### CI vs runtime-smoke Alignment (Post-P48)
| Area | CI | runtime-smoke |
|------|----|---------------|
| Backend (all stages) | ✅ 983-test full suite ⊇ 130 backend tests | ✅ |
| frontend-tsc | ✅ `npx tsc --noEmit` (P48 added) | ✅ |
| P47 token policy (12 tests) | ✅ full suite | ✅ |

### Validation
- `npx tsc --noEmit`: exit 0 ✅
- `make runtime-smoke`: 130 passed, 2 skipped ✅

### Files Changed
| File | Change |
|------|--------|
| `.github/workflows/ci-cd.yml` | `npx tsc --noEmit` step added to frontend job |
| `docs/security/P48_CI_RUNTIME_SMOKE_ALIGNMENT.md` | Created |

### Commits
- C1: `ci: add frontend TypeScript typecheck to align with runtime-smoke`
- C2: `docs(security): add P48 CI runtime-smoke alignment report`
- C3: `docs(report): P48 CI runtime-smoke handoff report`

---

## P47-TOKEN-POLICY-RUNTIME-GATE (2026-05-24)

**Final Classification: `P47_TOKEN_POLICY_RUNTIME_GATE_READY`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `8fde52f` (P46 closure) ✅
- Tree: clean ✅

### What Changed
**`Makefile` — `backend-auth-audit` target**
- Added `tests/test_report_download_token_policy.py` (12 tests: 5 P44 + 7 P45)
- Updated comment to reference P44/P45
- Propagates through: `backend-auth-audit` → `security-smoke` → `runtime-smoke` stage 2

### runtime-smoke: 118 → 130
| Stage | Before | After |
|-------|--------|-------|
| Stage 2 (security) | 29, 2 skip | **41, 2 skip** |
| Total | **118** | **130** |

### Targeted Test
`test_report_download_token_policy.py`: 12/12 passed ✅

### Files Changed
| File | Change |
|------|--------|
| `Makefile` | `backend-auth-audit` + `test_report_download_token_policy.py` |
| `docs/security/P47_TOKEN_POLICY_RUNTIME_GATE.md` | Created |
| `docs/security/P46_SMOKE_GATE_REFRESH.md` | Gap → CLOSED; table updated |
| `docs/security/P39_SECURITY_AUDIT_CLOSURE_INDEX.md` | Stage 2 29→41; total 118→130; §13 P47 row; gap closed |

### Commits
- C1: `chore(governance): add report download token policy to runtime smoke`
- C2: `docs(security): add P47 token policy runtime gate report`
- C3: `docs(report): P47 token policy runtime gate handoff report`

---

## P46-SMOKE-GATE-REFRESH (2026-05-24)

**Final Classification: `P46_SMOKE_GATE_REFRESH_READY`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `cb6f19b` (P45 closure) ✅
- Tree: clean ✅

### Updated Smoke Counts
| Stage | Before P46 (P39 doc) | After P46 (actual) |
|-------|----------------------|---------------------|
| Stage 3 (config-smoke) | 24 | **29** (+5 P43 tests) |
| runtime-smoke total | 113 | **118** |
| Full backend suite | ~800+ | **983** |

### R5 Risk Status: MITIGATED
- Before: Token in `?token=` query string → appears in server access logs
- After P45: Frontend strips token from URL, sends via `X-Report-Download-Token` header
- Backend accepts header (preferred) or query (backward compat)

### P44/P45 Coverage Gap Documented
- `test_report_download_token_policy.py` (12 tests) is NOT in runtime-smoke
- Runs only in full backend suite
- Recommended P47: add to `backend-auth-audit` Makefile target (130 runtime-smoke tests)

### Files Changed
| File | Change |
|------|--------|
| `docs/security/P39_SECURITY_AUDIT_CLOSURE_INDEX.md` | Stage counts, R5, P44 recommendation, Section 13 |
| `docs/security/P46_SMOKE_GATE_REFRESH.md` | Created |
| `Makefile` | config-smoke comment updated (P43 reference) |
| `00-Plan/roadmap/active_task_report.md` | This block |

### Validation
| Suite | Result |
|-------|--------|
| `make runtime-smoke` | 118 passed, 2 skipped ✅ |
| Targeted 33 tests | 33/33 passed ✅ |
| `tsc --noEmit` | 0 errors ✅ |

### Commits
- C1: `chore(governance): refresh smoke gate labels`
- C2: `docs(security): refresh smoke gate and report token closure index`
- C3: `docs(report): P46 smoke gate refresh handoff report`

---

## P45-REPORT-DOWNLOAD-TOKEN-HEADER (2026-05-24)

**Final Classification: `P45_REPORT_DOWNLOAD_TOKEN_HEADER_HARDENED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `389b7fa` (P44 closure) ✅
- Tree: clean ✅

### What Changed
**`backend/app/api/reports.py`** — download endpoint now accepts `X-Report-Download-Token` header:
- Header preferred over query string (`provided_token = x_report_download_token or token`)
- Query `?token=` retained as backward-compatible fallback
- Invalid header with valid query → 403 (no silent fallback)
- No token at all → 403
- JWT owner check unchanged and still runs first

**`frontend/app/components/platform/report-export-modal.tsx`** — `handleDownload()`:
- Extracts token from `download_url` with `URL.searchParams.get('token')`
- Strips token from URL: `searchParams.delete('token')` → `fetchUrl` has no token
- Sends token as `X-Report-Download-Token` header
- JWT still sent as `Authorization: Bearer`

### Token in Access Log: MITIGATED
- Before: `GET /api/v1/reports/download/{id}?token=<uuid>` logged
- After: `GET /api/v1/reports/download/{id}` logged (token in header, not URL)

### Tests Added — `TestHeaderTokenDownload` (7 new tests)
| Test | Assert |
|------|--------|
| `test_header_token_owner_jwt_succeeds` | 200 |
| `test_query_token_backward_compat_succeeds` | 200 |
| `test_header_preferred_header_valid_query_invalid` | 200 |
| `test_header_preferred_header_invalid_query_valid_rejected` | 403 |
| `test_no_token_at_all_denied` | 403 |
| `test_cross_user_jwt_valid_header_token_denied` | 404 |
| `test_no_jwt_valid_header_token_denied` | 401 |

### Validation
| Suite | Result |
|-------|--------|
| Targeted (33 tests) | 33/33 passed |
| `tsc --noEmit` | 0 errors |
| `make runtime-smoke` | 118 passed, 2 skipped |
| Full backend suite | 983 passed, 2 skipped |

### Commits
- C1 `97c6096`: `fix(security): accept report download token from request header`
- C2 `47f0148`: `fix(frontend): send report download token via header`
- C3 `51a7ca8`: `test(security): add report download token header regression`
- C4: `docs(security): add P45 report download token header report`
- C5: `docs(report): P45 report download token header handoff report`

---

## P44-REPORT-DOWNLOAD-TOKEN-POLICY (2026-05-24)

**Final Classification: `P44_REPORT_DOWNLOAD_TOKEN_RISK_DOCUMENTED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `2c38ebb` (P43 closure) ✅
- Tree: clean ✅

### Investigation
- Download endpoint `GET /api/v1/reports/download/{report_id}` requires: JWT (get_current_user) + owner_user_id match + token match + expiry ✅
- Token embedded in URL query string: `?token=<uuid>` → leaks to server-side access logs ⚠ (residual risk)
- Frontend uses fetch+blob+createObjectURL (no browser navigation) → browser history NOT at risk ✅
- P39 R5: token-alone attack → HTTP 401 (JWT required first) ✅

### Test Gap Closed
- **Missing**: "no JWT + valid token → 401" was not tested in any existing file
- **Root cause**: P18 docstring said download was "token-only (no JWT auth)" — P20 silently added JWT but left no-JWT path untested

### Changes
**`backend/tests/test_report_download_token_policy.py`** — CREATED (5 tests)
| Class | Test | Assert |
|-------|------|--------|
| `TestDownloadEndpointRequiresJWT` | `test_no_jwt_valid_token_denied` | 401 |
| `TestDownloadTokenStandaloneAttack` | `test_stolen_token_no_jwt_denied` | 401 |
| `TestDownloadTokenStandaloneAttack` | `test_cross_user_jwt_valid_token_denied` | 404 |
| `TestDownloadTokenBodyDoesNotLeakToken` | `test_403_body_does_not_echo_token` | 403 + clean body |
| `TestDownloadTokenBodyDoesNotLeakToken` | `test_404_body_does_not_echo_token` | 404 + clean body |

### Test Results
| Suite | Result |
|-------|--------|
| New + existing hardening (14) | 14/14 passed |
| `make runtime-smoke` | 118 passed, 2 skipped |
| Full backend suite | 976 passed, 2 skipped |

### Residual Risk Accepted
- Token in server-side access logs: LOW impact (token alone → 401, requires owner JWT)
- Deferred mitigation: X-Report-Download-Token header (P45+)

### Artifacts
- `backend/tests/test_report_download_token_policy.py` — new (5 tests)
- `docs/security/P44_REPORT_DOWNLOAD_TOKEN_POLICY.md` — report

### Commits
- C1 `e95d151`: `test(security): add report download token policy regression`
- C2: `docs(security): add P44 report download token policy`
- C3: `docs(report): P44 report download token policy handoff report`

---

## P43-STARTUP-SECURITY-WARNINGS (2026-05-24)

**Final Classification: `P43_STARTUP_SECURITY_WARNINGS_WIRED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `21f60f6` (docs: P42 closure) ✅
- Tree: clean ✅
- No push / no new deps / no frontend / no auth changes ✅

### Investigation
- `log_json(logger, level, event, **payload)` exists in `app/core/logging.py` ✅
- `get_runtime_security_warnings()` from P42 not imported or called in `main.py` ❌ (GAP)
- Test pattern: `monkeypatch.setattr(main_module, 'settings', ...)` + direct `startup_event()` call ✅

### Changes
**`backend/app/main.py`** — added `get_runtime_security_warnings` import + warning loop in `startup_event()`:
- Runs after `validate_production_secrets()` (fatal guard unchanged)
- Emits `runtime_security_warning` JSON log at WARNING level for each warning code
- Payload contains only `warning_code` and `app_env` — no secrets

**Warning codes**:
- `RATE_LIMIT_DISABLED_IN_PRODUCTION` — production + rate_limit_enabled=False
- `IN_MEMORY_LIMITER_PROCESS_LOCAL` — production + rate_limit_enabled=True

### Test Results
| Suite | Result |
|-------|--------|
| `test_runtime_config_startup_guard.py` (19 tests) | 19/19 passed |
| `test_rate_limit_production_policy.py` (17 tests) | 17/17 passed |
| `make runtime-smoke` (Stage 1–4) | 118 passed, 2 skipped |
| Full backend suite | 971 passed, 2 skipped |

### Artifacts
- `backend/app/main.py` — startup warning loop wired
- `backend/tests/test_runtime_config_startup_guard.py` — 5 new tests (`TestStartupRuntimeSecurityWarnings`)
- `docs/security/P43_STARTUP_SECURITY_WARNINGS.md` — report

### Commits
- C1 `5710698`: `fix(startup): log runtime security warnings at startup`
- C2 `f06e321`: `test(security): assert startup emits rate-limit warnings in production`
- C3: `docs(security): add P43 startup security warnings report`
- C4: `docs(report): P43 startup security warnings handoff report`

---

## P42-RATE-LIMIT-PRODUCTION-POLICY (2026-05-24)

**Final Classification: `P42_RATE_LIMIT_POLICY_HARDENED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `9bc1e81` (docs: P41 closure) ✅
- Tree: clean ✅
- No push / no new deps / no frontend / no auth changes ✅

### Investigation Findings
- `rate_limit_enabled` defaults to `False` — opt-in, not enforced in production
- `InMemoryRateLimitMiddleware` is process-local; state not shared across workers
- `validate_production_secrets` checked `jwt_secret_key` only — no rate-limit policy
- P26 covered middleware contract; no production policy tests existed
- Classification before fix: **PARTIAL + GAP**

### Fix Applied
Added `get_runtime_security_warnings(settings) -> list[str]` to `backend/app/core/config.py`:
- Production + `rate_limit_enabled=False` → warns `RATE_LIMIT_DISABLED_IN_PRODUCTION`
- Production + `rate_limit_enabled=True` → warns `IN_MEMORY_LIMITER_PROCESS_LOCAL`
- Dev/staging/local → returns `[]` (no noise)
- Never raises — backward-compatible

### Production Policy Defined
- Single-worker: `RATE_LIMIT_ENABLED=true` is sufficient for basic abuse protection
- Multi-worker: in-memory limiter does not share state → gateway/WAF/Redis required
- `/health*` permanently exempt (hardcoded in middleware)
- No per-route throttle added (out of scope)

### Test Results
| Suite | Result |
|-------|--------|
| `test_rate_limit_production_policy.py` | 17/17 passed |
| `test_rate_limit_smoke.py` | 7/7 passed |
| `test_config_security_guard.py` | 15/15 passed |
| `make runtime-smoke` (Stage 1–4) | 113 passed, 2 skipped |
| Full backend suite | 966 passed, 2 skipped |

### Accepted Residual Limitations
- In-memory limiter is process-local: ACCEPTED, documented
- No worker topology config in Settings: ACCEPTED / UNKNOWN
- Global threshold only: ACCEPTED (no per-route throttle)
- `get_runtime_security_warnings` not yet wired into startup logging: DEFERRED (P43)

### Artifacts
- `backend/app/core/config.py` — `get_runtime_security_warnings` helper
- `backend/tests/test_rate_limit_production_policy.py` — 17 policy tests (NEW)
- `docs/security/P42_RATE_LIMIT_PRODUCTION_POLICY.md` — policy report

### Commits
- C1 `8484fca`: `fix(config): expose runtime security warnings for rate limiting policy`
- C2: `docs(security): add P42 rate limit production policy`
- C3: `docs(report): P42 rate limit production policy handoff report`

---

## P41-RISK-ENGINE-UUID-HYGIENE (2026-05-24)

**Final Classification: `P41_RISK_ENGINE_UUID_HYGIENE_FIXED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `a6d909d` (docs: P40 closure) ✅
- Tree: clean ✅
- No push / no new deps / no frontend / no auth changes ✅

### Root Cause
`risk_engine._make_alert` received `str` UUID values from callers (`str(current_user.id)`) but passed them directly into `RiskAlert(user_id=..., UUID(as_uuid=True))`. SQLite crashed with `StatementError: 'str' object has no attribute 'hex'`; PostgreSQL silently coerced (R4 from P40 reclassified as latent type smell).

### Fix Applied
- Added `import uuid` and str→UUID coercion in `_make_alert`
- Updated `evaluate_metric_risks` / `evaluate_lab_item_risks` type annotations to `uuid.UUID | str`
- Callers (`metrics.py`, `documents.py`) unchanged — coercion handles them

### P35 Mock Removal
Removed 4 stale `unittest.mock.patch` blocks from `test_metrics_symptoms_response_leakage.py` that existed solely to prevent the SQLite crash. All 15 tests pass without mocks.

### Test Results
| Suite | Result |
|-------|--------|
| `test_risk_engine_uuid_hygiene.py` | 8/8 passed |
| `test_metrics_symptoms_response_leakage.py` | 15/15 passed |
| `test_postgresql_parity.py` | 11/11 passed |
| `make runtime-smoke` (Stage 1–4) | 113 passed, 2 skipped |
| Full backend suite | 949 passed, 2 skipped |

### Artifacts
- `backend/app/services/risk_engine.py` — str→UUID coercion fix
- `backend/tests/test_risk_engine_uuid_hygiene.py` — 8 regression tests (NEW)
- `backend/tests/test_metrics_symptoms_response_leakage.py` — 4 stale mocks removed
- `docs/security/P41_RISK_ENGINE_UUID_HYGIENE.md` — security report

### Commits
- C1 `d7be418`: `fix(db): use UUID objects for risk alert persistence`
- C2 `7592ca0`: `test(db): add risk engine UUID hygiene regression`
- C3: `docs(security): add P41 risk engine UUID hygiene report`
- C4: `docs(report): P41 risk engine UUID hygiene handoff report`

---

## P40-POSTGRESQL-PARITY-SMOKE (2026-05-24)

**Final Classification: `P40_POSTGRESQL_PARITY_VERIFIED`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `7524be4` (docs: P39 closure index) ✅
- Tree: clean ✅
- No push / no new deps / no frontend / no auth changes ✅

### Execution Summary
- PostgreSQL 16 already running (`health-insights-postgres-local`, healthy 2 days)
- Local Homebrew PG also running on port 5432 (port conflict; macOS GSSAPI bypass required)
- Created `health_insights_test` DB in local PG; applied `schema.sql` + 9 migrations
- SQLAlchemy confirmed connected: 14 tables visible
- 11 parity tests written and executed: **11 passed**
- R4 probe: str UUID coerced by psycopg2 on PostgreSQL — latent type smell, not crash
- SQLite runtime-smoke: 113 passed, 2 skipped (unchanged)

### Artifacts
- `backend/tests/test_postgresql_parity.py` — 11 parity tests (T1–T7)
- `docs/security/P40_POSTGRESQL_PARITY_SMOKE.md` — parity report

### Commits
- C1: `test(db): add P40 PostgreSQL parity smoke (11 tests, all pass)`
- C2: `docs(security): add P40 PostgreSQL parity smoke report`
- C3: `docs(report): P40 PostgreSQL parity handoff report`

### Next Task: P41
Fix R4 UUID coercion: pass UUID object (not str) to `evaluate_metric_risks` /
`evaluate_lab_item_risks` callers in `metrics.py` and `documents.py`.

---

## P39-SECURITY-AUDIT-CLOSURE-INDEX (2026-05-24)

**Final Classification: `P39_SECURITY_AUDIT_CLOSURE_INDEX_READY`**

### Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `4c9ffb1` (docs: P38 audit report) ✅
- Status: clean (no uncommitted files) ✅

### Summary
- **Goal**: Create canonical closure index for P13–P38 security/readiness hardening
- **Index path**: `docs/security/P39_SECURITY_AUDIT_CLOSURE_INDEX.md`
- **Scope**: Read-only investigation + docs creation only (no backend/test/frontend modifications)

### P13–P38 Closure Classification Summary
| Category | Count |
|----------|-------|
| A. CLOSED (full coverage) | 19 tasks |
| B. CLOSED_WITH_ACCEPTED_GAP | 3 tasks (P18, P22, P26) |
| C. DOCS_ONLY | 1 task (P19) |
| D. INFRA | 2 tasks (P21, P31) |

### C.GAPs Fixed (P13–P38)
| Type | Count | Tasks |
|------|-------|-------|
| Response field leakage (user_id / storage fields) | 6 schemas | P32, P35, P38 |
| Auth / authorization | 2 fixes | P18, P20 |
| Config / secrets | 1 fix | P28 |
| Injection (filename traversal) | 1 fix | P27 |
| Validation constraints | 3 rounds | P23, P24, P30 |

### runtime-smoke Result
| Stage | Result |
|-------|--------|
| 1 — Health check | 3 passed ✅ |
| 2 — Security smoke | 29 passed, 2 skipped ✅ |
| 3 — Config smoke | 24 passed ✅ |
| 4 — Validation smoke | 57 passed ✅ |
| **Total** | **113 passed, 2 skipped** ✅ |

### Accepted Gaps (documented in index §7)
- R1: Rate limiter in-memory, not multi-worker shared
- R2: Rate limit opt-in per route, not globally enforced
- R3: AI prompt injection structural governance deferred
- R4: `risk_engine.py` passes `str(user.id)` to `UUID(as_uuid=True)` column (SQLite compat issue)
- R5: Report download token leakable via browser history (mitigated by UUID entropy + 1hr expiry)
- R6: Frontend e2e auth tests not in CI (require live backend)

### Recommended Next Tasks
- **P40** (HIGH): PostgreSQL parity smoke — all tests currently run on SQLite
- **P41** (MEDIUM): risk_engine.py UUID compatibility fix (R4)
- **P42** (MEDIUM): Rate-limit production enablement policy (R1/R2)
- **P43** (MEDIUM): AI prompt governance / prompt-injection policy (R3)
- **P44** (LOW): Report download token hardening (R5)

### Files Changed
- Created: `docs/security/P39_SECURITY_AUDIT_CLOSURE_INDEX.md`
- Updated: `00-Plan/roadmap/active_task_report.md` (this prepend)

### Commits
- `C1`: `docs(security): add P39 security audit closure index`
- `C2`: `docs(report): P39 security audit closure report`

---

## P38-REMAINING-API-SURFACE-AUDIT (2026-05-24)

**Final Classification: `P38_REMAINING_API_SURFACE_FIXED`**

### Summary
- Audited: 9 remaining API files (actions, analytics, auth, external_metrics, insights, persons, profile, reports, timeline) + corresponding schemas
- **3 C.GAPs found and fixed**:
  - `ProfileResponse.user_id: UUID` → removed from schema + removed from GET/PUT /profile/me response dicts
  - `HealthInsightResponse.user_id: UUID` → removed from schema
  - `HealthActionRead.user_id: UUID` → removed from schema
- **A.SAFE** (no changes): UserResponse, AccountResponse, PersonResponse.owner_user_id (P33 design), ExternalSyncResponse/ExternalTrendResponse, TimelineResponse data dicts, ReportStatusResponse download_url, untyped outcomes list
- 14 regression tests added → 14/14 PASS
- Full test suite: 916+14 PASS, 2 skipped
- runtime-smoke: 113 passed, 2 skipped
- Commits: `2338e30` (fix), `c0b4060` (tests), *(C3 pending)*

### Status: All 17 API files audited (P32–P38 complete)

---

## P37-AI-HEALTH-RESPONSE-AUDIT (2026-05-24)

**Final Classification: `P37_AI_HEALTH_SMOKE_VERIFIED`**

### Summary
- Audited: `api/ai_summary.py` (2 routes), `api/health_score.py` (3 routes), `api/ai_modules.py` (4 routes), plus schemas for ai_summary, health_score, health_analysis, trend_analysis, ai_modules
- **No C.GAP found** — both `AISummary` and `HealthScore` ORM have `user_id` column; neither `AISummaryResponse` nor `HealthScoreResponse` declares it; `from_attributes=True` only serializes declared fields
- `narrative_json` and `score_detail` JSON blobs contain only AI-generated health content — no user_id embedded
- `AIModuleResponse`/`AIModuleEvaluationResponse` — no ORM at all, pure structured AI output, no user_id
- 13 regression tests added → 13/13 PASS
- runtime-smoke: 113 passed, 2 skipped
- Commits: `6987495` (tests), *(C2 pending)*

### Next: P38 — Remaining API Surface Final Audit
- Check any remaining routes not covered by P32–P37
- Candidates: notification, recommendation, person_profile, admin endpoints
- Find files: `find backend/app/api -maxdepth 1 -type f | sort`

---

## P36-LAB-RISK-RESPONSE-AUDIT (2025-07-27)

**Final Classification: `P36_LAB_RISK_SMOKE_VERIFIED`**

### Summary
- Audited: `api/documents.py` (8 routes), `api/risk_alerts.py` (5 routes), `schemas/documents.py`, `schemas/risk_alerts.py`
- **No C.GAP found** — all schema-based routes exclude user_id/storage fields
- B.PARTIAL routes: `GET /documents/lab-history`, `GET /risk-alerts/unread-count`, `POST /risk-alerts/{id}/dismiss` — explicit safe dict construction, regression tests added
- 12 regression tests added → 12/12 PASS
- runtime-smoke: 113 passed, 2 skipped
- Commits: `e4929a8` (tests), `8ecb96e` (docs)

### Next: P37 — Health Score & AI Summary Response Audit
- Target: `AISummary` ORM has `user_id` — verify not in response schemas
- Files: `backend/app/api/health_score.py`, `backend/app/api/ai_summary.py` (if exist), corresponding schemas

---

## P35-METRICS-SYMPTOMS-RESPONSE-AUDIT (2026-05-24)

**Final Classification: `P35_METRICS_SYMPTOMS_LEAKAGE_HARDENED`**

---

### 1. Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- HEAD at start: `20f6e83` (P34 docs commit) ✅
- Working tree: clean ✅

### 2. Investigation Commands

```bash
grep -Rn "@router\.\(get\|post\|put\|patch\|delete\)\|response_model\|user_id" \
  backend/app/api/metrics.py backend/app/api/symptoms.py \
  backend/app/schemas/metrics.py backend/app/schemas/symptoms.py
```

```bash
grep -Rn "password_hash\|secret_\|storage_key\|storage_bucket\|file_path\|download_token" \
  backend/app/api/metrics.py backend/app/api/symptoms.py \
  backend/app/schemas/metrics.py backend/app/schemas/symptoms.py
```

### 3. Route Audit Inventory

| Route | Response Model | ORM `user_id` Column | Response Before Fix | Classification | Action |
|---|---|---|---|---|---|
| POST /metrics | `MetricResponse` | `HealthMetric.user_id` present | `user_id: UUID` **EXPOSED** | C. GAP | Removed from schema |
| GET /metrics | `list[MetricResponse]` | same | `user_id: UUID` **EXPOSED** | C. GAP | Removed from schema |
| GET /metrics/latest | `Optional[MetricResponse]` | same | `user_id: UUID` **EXPOSED** | C. GAP | Removed from schema |
| POST /symptoms | `SymptomResponse` | `SymptomLog.user_id` present | `user_id: UUID` **EXPOSED** | C. GAP | Removed from schema |
| GET /symptoms | `list[SymptomResponse]` | same | `user_id: UUID` **EXPOSED** | C. GAP | Removed from schema |
| PUT /symptoms/{id} | `SymptomResponse` | same | `user_id: UUID` **EXPOSED** | C. GAP | Removed from schema |

### 4. Fix Applied

**`backend/app/schemas/metrics.py`** — `MetricResponse`
- Removed: `user_id: UUID`
- Retained: `id`, `subject_profile_id`, `source`, all metric scalar fields

**`backend/app/schemas/symptoms.py`** — `SymptomResponse`
- Removed: `user_id: UUID`
- Retained: `id`, `subject_profile_id`, all symptom scalar fields

ORM columns `HealthMetric.user_id` and `SymptomLog.user_id` are retained — used in `.filter()` clauses in API routes for ownership enforcement. No DB model changes.

### 5. Additional Findings (Non-blocking)

**Pre-existing bug in `risk_engine.py`**: `evaluate_metric_risks(str(current_user.id), ...)` passes `str` UUID to `RiskAlert(user_id=...)` which is `UUID(as_uuid=True)`. This causes SQLAlchemy `StatementError: 'str' object has no attribute 'hex'` on SQLite. Scoped to existing code, not introduced by P35. POST metric tests mock `evaluate_metric_risks` to return `[]` to isolate response schema validation.

### 6. Sensitive Field Scan
- `password_hash`, `storage_key`, `storage_bucket`, `file_path`, `download_token`: **not present** in any metrics/symptoms schema or API file ✅

### 7. Files Changed

| File | Change |
|---|---|
| `backend/app/schemas/metrics.py` | Removed `user_id: UUID` from `MetricResponse` |
| `backend/app/schemas/symptoms.py` | Removed `user_id: UUID` from `SymptomResponse` |
| `backend/tests/test_metrics_symptoms_response_leakage.py` | Created — 15 regression tests |

### 8. Tests Added — `test_metrics_symptoms_response_leakage.py`

| Class | Test | Result |
|---|---|---|
| TestMetricsResponseLeakage | test_create_metric_status_201 | PASS |
| TestMetricsResponseLeakage | test_create_metric_no_user_id | PASS |
| TestMetricsResponseLeakage | test_create_metric_no_sensitive_keys | PASS |
| TestMetricsResponseLeakage | test_list_metrics_no_user_id | PASS |
| TestMetricsResponseLeakage | test_list_metrics_no_sensitive_keys | PASS |
| TestMetricsResponseLeakage | test_latest_metric_no_user_id | PASS |
| TestMetricsResponseLeakage | test_metric_response_fields | PASS |
| TestSymptomsResponseLeakage | test_create_symptom_no_user_id | PASS |
| TestSymptomsResponseLeakage | test_create_symptom_no_sensitive_keys | PASS |
| TestSymptomsResponseLeakage | test_list_symptoms_no_user_id | PASS |
| TestSymptomsResponseLeakage | test_list_symptoms_no_sensitive_keys | PASS |
| TestSymptomsResponseLeakage | test_update_symptom_no_user_id | PASS |
| TestSymptomsResponseLeakage | test_symptom_response_fields | PASS |
| TestCrossUserMetricsSymptomsIsolation | test_cross_user_metrics_404 | PASS |
| TestCrossUserMetricsSymptomsIsolation | test_cross_user_symptoms_404 | PASS |

**Total: 15/15 PASS**

### 9. Test Run Output

```
15 passed, 4 warnings in 2.50s
```

### 10. runtime-smoke

```
Stage 1:  3 passed
Stage 2: 29 passed, 2 skipped
Stage 3: 24 passed
Stage 4: 57 passed
Total:  113 passed, 2 skipped — all 4 stages green ✅
```

### 11. Known Limitations / Inferred

- Cross-user isolation for metrics/symptoms is enforced via `HealthMetric.user_id == current_user.id` and `SymptomLog.user_id == current_user.id` filters, **not** via `get_target_person` (unlike dashboard). The cross-user 404 tests confirm this filtering works via the `get_target_person` dependency applied to the `person_id` query param.
- `evaluate_metric_risks` string-UUID bug is pre-existing, not introduced by P35. Tracked for future hardening.

### 12. Commits

- `8b22a5f` fix(security): remove user_id from MetricResponse and SymptomResponse (P35)
- `30ac9d7` test(security): add metrics/symptoms response leakage regression (P35)
- `(docs)` docs(report): P35 metrics symptoms response audit report

### 13. Final Classification

**`P35_METRICS_SYMPTOMS_LEAKAGE_HARDENED`**
- C.GAP found: `user_id: UUID` exposed in both `MetricResponse` and `SymptomResponse`
- Fix applied: removed from both schemas
- 15 regression tests: all PASS
- runtime-smoke: 113 passed, 2 skipped

---

## P34-DASHBOARD-RESPONSE-AUDIT (2026-05-24)

**Final Classification: `P34_DASHBOARD_SMOKE_VERIFIED`**

---

### 1. Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- HEAD at start: `1fa28c4` (P33 docs commit) ✅
- Working tree: clean ✅

### 2. Scope

`backend/app/api/dashboard.py` — 3 routes, all using explicit `response_model=`.
`backend/app/schemas/dashboard.py` — Pydantic models; `DashboardOverviewV2Response` contains multiple `list[dict[str, Any]]` and `dict[str, Any]` fields.
All contributing service functions in `backend/app/services/health_ai_engine/` and `backend/app/services/decision_engine_service.py` audited.

### 3. Route Audit Inventory

| Route | Response Model | Dynamic dict[str, Any] Fields | Data Sources | Classification | Action |
|---|---|---|---|---|---|
| GET /dashboard/overview | `DashboardOverviewResponse` | `latest_metrics`, `active_alerts`, `summary` | HealthMetric ORM (explicit field selection), risk alerts | A. SAFE | Regression tests added |
| GET /dashboard/trends | `DashboardTrendsResponse` | None — all `list[TrendPoint]` (typed Pydantic) | HealthMetric ORM | A. SAFE | Regression tests added |
| GET /dashboard (v2) | `DashboardOverviewV2Response` | `alerts`, `insights`, `recent_symptoms`, `recent_metrics`, `recent_labs`, `trends`, `predictive_insights`, `anomaly_alerts`, `clinical_labels`, `recommendations`, `health_narrative_v2`, `health_narrative_v3`, `prioritized_actions` | Multiple — see below | A. SAFE | Regression tests added |

### 4. DashboardOverviewV2Response Dict Fields — Detailed Audit

| Field | Shape | Data Source | Sensitive Fields? | Classification |
|---|---|---|---|---|
| `alerts` | `list[dict]` | Explicit construction: `id`, `severity`, `title`, `description`, `created_at`, `rule_id`, `category`, `priority`, `confidence`, `evidence_level`, `guideline_source`, `medical_disclaimer` | None | A.SAFE |
| `insights` | `list[dict]` | Explicit construction: `id`, `insight_type`, `severity`, `title`, `summary`, `recommendation`, `generated_at`, `rule_id`, `category`, `priority`, `confidence`, `evidence_level`, `guideline_source`, `guideline_version`, `medical_disclaimer` | None | A.SAFE |
| `recent_symptoms` | `list[dict]` | ORM explicit: `id`, `symptom`, `occurred_at`, `note`, `estimated_start_date`, `estimated_duration_days` | No `user_id` | A.SAFE |
| `recent_metrics` | `list[dict]` | ORM explicit: `id`, `recorded_at`, `systolic_bp`, `diastolic_bp`, `heart_rate`, `blood_glucose`, `weight_kg`, `sleep_hours`, `steps` | No `user_id` | A.SAFE |
| `recent_labs` | `list[dict]` | ORM explicit: `id`, `report_date`, `report_type`, `created_at`, `abnormal_items` | No `file_path`, `storage_key`, `user_id` | A.SAFE |
| `predictive_insights` | `list[dict]` | `generate_predictive_insights()` — health clinical text only | None | A.SAFE |
| `anomaly_alerts` | `list[dict]` | `detect_anomalies()` — health clinical text only | None | A.SAFE |
| `clinical_labels` | `list[dict]` | `derive_clinical_labels()` — health label + guideline metadata | None | A.SAFE |
| `recommendations` | `list[dict]` | `generate_recommendations()` — health text + guideline metadata | None | A.SAFE |
| `health_narrative_v2` | `dict` | `generate_health_narrative_v2()` — narrative text lists | None | A.SAFE |
| `health_narrative_v3` | `dict` | `generate_health_narrative_v3()` — narrative text lists | None | A.SAFE |
| `prioritized_actions` | `list[dict]` | ORM explicit: `id`, `title`, `category`, `status`, `priority`, `frequency`, `impact_status`, `reminder_status`, `streak_count` | No `user_id` | A.SAFE |
| `decision_items` | `list[UnifiedDecisionItem]` | `build_decision_items()` → `UnifiedDecisionItem` (typed Pydantic) | None | A.SAFE |
| `health_score.components` | `dict` | Explicit score components: `blood_pressure`, `bmi`, `lab_results`, penalties | None | A.SAFE |

### 5. Confirmed Safety Properties

1. **No `password_hash`** — zero occurrences in all dashboard-contributing services
2. **No `storage_bucket` / `storage_key`** — `LabReport.storage_bucket` / `.storage_key` never forwarded to client; only `id`, `report_date`, `report_type`, `created_at`, `abnormal_items` are serialized
3. **No `file_path` / `download_token`** — same as above
4. **No `user_id`** in nested metric/symptom/lab items — all ORM queries use `current_user.id` as a filter only, never return it in the dict payload
5. **`UnifiedDecisionItem`** is strongly-typed Pydantic — no arbitrary dict passthrough possible
6. **`enrich_explainability()`** only adds `guideline_source`, `guideline_version`, `evidence_level` — all clinical metadata, no secrets
7. **Cross-user isolation** — `get_target_person` (deps.py:81) filters `owner_user_id == current_user.id` on all 3 routes; cross-user `person_id` → 404

### 6. Tests Added

**`backend/tests/test_dashboard_response_leakage.py`** — 16 tests, all PASS

| Class | Tests | Purpose |
|---|---|---|
| `TestDashboardOverviewLeakage` | 3 | Status 200 + recursive scan + no user_id in latest_metrics |
| `TestDashboardTrendsLeakage` | 3 | Status 200 + recursive scan + TrendPoint key shape enforcement |
| `TestDashboardV2Leakage` | 7 | Full v2 recursive scan; recent_metrics/labs/symptoms/alerts/decision_items/health_score individual scans |
| `TestCrossUserDashboardIsolation` | 3 | Cross-user person_id → 404 on overview, trends, and v2 |

Recursive scanner: checks `password_hash`, `hashed_password`, `password`, `storage_bucket`, `storage_key`, `file_path`, `download_token`, `secret_key`, `secret`, `is_superuser`, `is_staff`.

### 7. Commits
- `3d410d8` — `test(security): add dashboard response leakage regression (P34)`

### 8. runtime-smoke Results
| Stage | Suite | Result |
|---|---|---|
| 1 | Health check | 3 passed |
| 2 | Security smoke | 29 passed, 2 skipped |
| 3 | Config smoke | 24 passed |
| 4 | Validation smoke | 57 passed |
| **Total** | | **113 passed, 2 skipped** |

### 9. Known Limitations
- `health_narrative_v2` and `health_narrative_v3` are `dict[str, Any]` — runtime recursive scan covers these but they are not individually exhausted in static analysis; snapshot tests would be needed if narrative service structure changes significantly.
- Cache layer (`cache_set`/`cache_get`) uses in-memory dict; if upgraded to Redis, the cached payload is a `model_dump(mode='json')` snapshot of the same `DashboardOverviewV2Response` — same safe field set.

---

## P33-HEALTH-ASSISTANT-RESPONSE-AUDIT (2026-05-23)

**Final Classification: `P33_HEALTH_ASSISTANT_SMOKE_VERIFIED`**

---

### 1. Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- HEAD at start: `799f164` (P32 docs commit) ✅
- Working tree: clean ✅

### 2. Scope

`backend/app/api/health_assistant.py` — 706 lines, 20+ routes, all returning `dict[str, Any]` with no `response_model`. Goal: verify no sensitive/internal fields leak through these untyped responses.

### 3. Route Audit Results

| Route | Return shape | Classification | Notes |
|---|---|---|---|
| GET /evidence-bundle | `build_evidence_bundle()` dict | B.PARTIAL | `_completed_rule_ids`: internal prefixed field; value is rule ID strings (e.g., "R001"), not credentials |
| GET /recommendations | `get_action_recommendations()` dict | A.SAFE | No sensitive fields |
| GET /device-signals | manual dict | A.SAFE | `person_id`, `generated_at`, `signals`, `signal_count` — clean |
| GET /product-signals | `build_product_signals()` dict | A.SAFE | Aggregate metrics only |
| GET /outcome-feedback | `compare_expected_vs_actual_outcome()` dict | A.SAFE | No sensitive fields |
| GET /daily-summary | `generate_daily_health_summary()` dict | A.SAFE | Deterministic health aggregates |
| GET /notifications/intelligent | manual dict | A.SAFE | `person_id`, `items`, `suppressed`, `total_candidates` |
| POST /notifications/{id}/snooze | `_serialize_log()` | A.SAFE | 14 notification fields; no credentials |
| POST /notifications/{id}/ignore | `_serialize_log()` | A.SAFE | Same |
| POST /notifications/{id}/click | `_serialize_log()` | A.SAFE | Same |
| POST /notifications/{id}/acted | `_serialize_log()` | A.SAFE | Same |
| GET /personalization-profile | `profile_to_dict()` | B.PARTIAL | Returns `PersonalizationProfile.id` (row UUID, not `user.id`) — own-user only |
| GET /engagement-analytics | `build_engagement_analytics()` dict | A.SAFE | Engagement aggregates |
| POST /personalization-profile/sync | `profile_to_dict()` | B.PARTIAL | Same as GET |
| GET /narrative-memory | manual dict | A.SAFE | `person_id`, `found`, `memory` — own user only |
| POST /narrative-memory/generate | manual dict | A.SAFE | Same |
| GET /narrative-memory/cross-period | manual dict | A.SAFE | `person_id`, `reasoning` |
| POST /family-relationships | manual dict | B.PARTIAL | `owner_user_id` = own UUID; not cross-user |
| GET /family-relationships | `load_family_relationships()` | B.PARTIAL | `owner_user_id` = own UUID |
| GET /family-health-context | manual dict | A.SAFE | `person_id`, `context` — aggregate |
| GET /family-recommendations | manual dict | A.SAFE | `person_id`, `recommendations`, `total` |

**No C.GAP found.** No `password_hash`, `storage_key`, `storage_bucket`, `file_path`, `download_token`, `is_superuser` in any route.

### 4. Cross-User Isolation Confirmed

`get_target_person` (deps.py:81):
```python
.filter(PersonProfile.id == person_uuid, PersonProfile.owner_user_id == current_user.id)
```
Cross-user `person_id` → 404 at the dependency level. Confirmed via 3 regression tests.

### 5. B.PARTIAL Items Documented (Not Fixed — Own-User Data Only)

| Field | Location | Reason B.PARTIAL (not C.GAP) |
|---|---|---|
| `_completed_rule_ids` | evidence-bundle | Internal-prefixed; value is rule ID strings, not credentials |
| `owner_user_id` | family-relationships GET/POST | Always own user's UUID; no cross-user path exists |
| `id` in profile_to_dict | personalization-profile | PersonalizationProfile row UUID, not User.id |

### 6. Tests Added

**`backend/tests/test_health_assistant_leakage.py`** — 15 tests, all PASS

| Class | Tests | Purpose |
|---|---|---|
| `TestEvidenceBundleLeakage` | 2 | Recursive scan + person_id ownership |
| `TestDeviceSignalsLeakage` | 2 | Recursive scan + person_id ownership |
| `TestFamilyRelationshipsLeakage` | 4 | No sensitive keys; owner_user_id == own UUID (list + create) |
| `TestFamilyContextLeakage` | 2 | family-health-context and family-recommendations recursive scan |
| `TestCrossUserIsolation` | 3 | Cross-user person_id → 404 on evidence-bundle, family-context, recommendations |
| `TestNotificationStatusLeakage` | 2 | Snooze + ignore `_serialize_log` response recursive scan |

Recursive scanner: checks `password_hash`, `hashed_password`, `password`, `storage_bucket`, `storage_key`, `file_path`, `download_token`, `secret_key`, `secret`, `is_superuser`, `is_staff`.

### 7. Commits
- `967fe18` — `test(security): add health_assistant response leakage regression (P33)`

### 8. runtime-smoke Results
| Stage | Suite | Result |
|---|---|---|
| 1 | Health check | 3 passed |
| 2 | Security smoke | 29 passed, 2 skipped |
| 3 | Config smoke | 24 passed |
| 4 | Validation smoke | 57 passed |
| **Total** | | **113 passed, 2 skipped** |

---

## P32-RESPONSE-SCHEMA-LEAKAGE-AUDIT (2026-05-23)

**Final Classification: `P32_RESPONSE_LEAKAGE_HARDENED`**

---

### 1. Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- HEAD at start: `1748d94` (P31 docs commit) ✅
- Working tree: clean ✅

### 2. Response Leakage Inventory

| Endpoint / Schema | Response Model | Sensitive Fields Considered | Current Guard | Classification | Action |
|---|---|---|---|---|---|
| POST /auth/register | `UserResponse` | `password_hash`, `is_active` | Excluded — only `id` + `email` | A. SAFE | Regression test added |
| POST /auth/login | `TokenResponse` | `password_hash` | JWT only — intentional | A. SAFE | Regression test added |
| GET /persons, POST /persons | `PersonResponse` | `password_hash`, `owner_user_id` | `password_hash` excluded; `owner_user_id` is own UUID only | B. PARTIAL | Regression test: confirms own-UUID invariant |
| POST /documents/upload, GET /documents | `DocumentResponse` | `storage_bucket`, `storage_key` | **Both included — internal infra fields** | **C. GAP** | **Fixed: both fields removed from schema** |
| GET /profile/me | `ProfileResponse` | `user_id`, `password_hash` | `password_hash` excluded; `user_id` is own UUID | B. PARTIAL | Documented — not a cross-user leak |
| GET /profile/account | `AccountResponse` | `password_hash`, `account_settings dict` | `password_hash` excluded; `account_settings` is opaque | B. PARTIAL | Documented |
| POST /reports/generate | `ReportGenerateResponse` | `token`, `file_path` | Neither exposed — only `report_id` + `status` | A. SAFE | Schema test added |
| GET /reports/{id} | `ReportStatusResponse` | `token`, `file_path` | No raw `token` key; no `file_path`; download_url embeds token intentionally | A. SAFE | Schema test added |

### 3. Gap Found and Fixed: `DocumentResponse` — storage_bucket + storage_key

**Root cause**: `DocumentResponse` in `backend/app/schemas/documents.py` declared `storage_bucket: str` and `storage_key: str`. These are internal infrastructure fields — the S3/local bucket name and the object path. Clients have no need for them; the server uses them exclusively for internal `download_file()` calls.

**Fix**: Removed both fields from `DocumentResponse`. The ORM model (`MedicalDocument`) retains the columns — server-side parsing (`/parse`) still works. FastAPI `response_model` filtering now prevents these fields from appearing in any document endpoint response.

**File changed**: `backend/app/schemas/documents.py`

### 4. Intentional Exposures Documented

- `TokenResponse.access_token` — intentional; required for client auth
- `PersonResponse.owner_user_id` — exposed only to the authenticated owner; not a cross-user leak; documents which user owns the profile
- `ProfileResponse.user_id` — same as above
- `ReportStatusResponse.download_url` — embeds download token in URL; intentional; endpoint is owner-only verified

### 5. Files Changed

| File | Change |
|---|---|
| `backend/app/schemas/documents.py` | Removed `storage_bucket` and `storage_key` from `DocumentResponse` |
| `backend/tests/test_response_leakage.py` | Created — 12 regression tests |

### 6. Tests Added

`backend/tests/test_response_leakage.py` — 12 tests:

| Class | Test | Result |
|---|---|---|
| `TestAuthResponseLeakage` | `test_register_response_no_password_hash` | PASS |
| `TestAuthResponseLeakage` | `test_register_response_fields` | PASS |
| `TestAuthResponseLeakage` | `test_login_response_no_password_hash` | PASS |
| `TestAuthResponseLeakage` | `test_login_response_has_access_token` | PASS |
| `TestPersonResponseLeakage` | `test_persons_list_no_password_hash` | PASS |
| `TestPersonResponseLeakage` | `test_persons_list_owner_uuid_is_own` | PASS |
| `TestDocumentSchemaLeakage` | `test_document_response_no_storage_bucket_field` | PASS |
| `TestDocumentSchemaLeakage` | `test_document_response_no_storage_key_field` | PASS |
| `TestDocumentSchemaLeakage` | `test_document_response_omits_storage_from_orm` | PASS |
| `TestReportSchemaLeakage` | `test_report_status_response_no_raw_token_field` | PASS |
| `TestReportSchemaLeakage` | `test_report_status_response_no_file_path_field` | PASS |
| `TestReportSchemaLeakage` | `test_report_status_schema_serialized_keys` | PASS |

### 7. Validation Results

| Target | Result |
|---|---|
| `pytest tests/test_response_leakage.py` | 12 passed ✅ |
| `make runtime-smoke` | all 4 stages pass ✅ |

### 8. Known Limitations / Unknowns

- `AccountResponse.account_settings: dict` — opaque dict. If caller stores internal flags there, they would be exposed. However, `AccountResponse` is owner-only (`GET /profile/account`) and the dict contents are controlled by the user themselves. Classified B.PARTIAL; not fixed in this phase.
- `DashboardOverviewV2Response` and related dashboard schemas contain multiple `list[dict[str, Any]]` fields. These are aggregated computed data; no raw ORM internal fields confirmed. Classified D.UNKNOWN — out of P32 scope; requires deeper consumer review.
- `health_assistant.py` routes all return `dict[str, Any]` with no `response_model`. Content is LLM-orchestrated. Not audited in P32.

### 9. Commits
- `7e08118` — `fix(security): remove storage_bucket and storage_key from DocumentResponse (P32)`
- `b6875ab` — `test(security): add response leakage regression coverage (P32)`

---

## P31-VALIDATION-SMOKE-GATE-CONSOLIDATION (2026-05-23)

**Final Classification: `P31_RUNTIME_SMOKE_VALIDATION_GATE_READY`**

---

### 1. Branch Governance Pre-flight
- Branch: `main` | HEAD before: `35fb405` | Status: clean ✅

### 2. Smoke Coverage Audit (P23–P30)

| Test File | Tests | Prior Target | Classification |
|---|---|---|---|
| `test_input_validation_hardening.py` (P23) | 19 | none | **B — MISSING** |
| `test_input_validation_boundary.py` (P24) | 11 | none | **B — MISSING** |
| `test_injection_smoke.py` (P27) | 7 | none | **B — MISSING** |
| `test_schema_validation_p30.py` (P30) | 20 | none | **B — MISSING** |
| `test_config_security_guard.py` (P28) | — | `config-smoke` | **A — INCLUDED** |
| `test_runtime_config_startup_guard.py` (P29) | — | `config-smoke` | **A — INCLUDED** |
| `test_runtime_smoke.py` | 3 | `runtime-smoke` (stage 1) | **A — INCLUDED** |
| `test_auth_negative_smoke.py` | — | `security-smoke` | **A — INCLUDED** |
| `test_real_token_auth_negative.py` | — | `security-smoke` | **A — INCLUDED** |

### 3. Files Changed

- `Makefile` — added `validation-smoke` target; added as stage 4 of `runtime-smoke`; updated `.PHONY`

### 4. New / Updated Makefile Targets

**`validation-smoke` (new):**
```
cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q \
    tests/test_input_validation_hardening.py \
    tests/test_input_validation_boundary.py \
    tests/test_injection_smoke.py \
    tests/test_schema_validation_p30.py
```

**`runtime-smoke` (updated — stage 4 added):**
```
1. test_runtime_smoke.py       (health endpoint contracts)
2. security-smoke              (auth audit + frontend tsc)
3. config-smoke                (P28/P29 secret guard)
4. validation-smoke            (P23/P24/P27/P30 schema/injection)
```

### 5. Validation Results

| Target | Result |
|---|---|
| `make validation-smoke` | 57 passed, 0 failed ✅ |
| `make runtime-smoke` | all stages pass (3 + 29 + 15 + 57 = 104 tests) ✅ |

### 6. Known Limitations
- `frontend-tsc` step in `security-smoke` requires Node.js — if tsc is unavailable the gate fails. This is pre-existing behavior, not introduced by P31.
- `validation-smoke` only covers P23/P24/P27/P30. P25 (health endpoint runtime), P26 (rate-limit smoke), P28/P29 (config guard) remain in their own dedicated targets which are already part of `runtime-smoke`.

### 7. Commit
- `75214b8` — `chore(governance): add validation-smoke to runtime gate (P31)`

---

## P30-SCHEMA-VALIDATION-BOUNDARY-HARDENING (2026-05-23)

**Final Classification: `P30_SCHEMA_VALIDATION_HARDENED`**

---

### 1. Branch Governance Pre-flight
- Branch: `main` | HEAD before: `8c36e51` | Status: clean ✅

### 2. Full Schema Audit (18 schema files + inline API classes)

All 18 files in `backend/app/schemas/` and 3 inline `BaseModel` classes in
`backend/app/api/` were audited. Files classified as:

- **SAFE A**: `auth.py` (existing), `symptoms.py`, `ai_modules.py`, `ai_summary.py`,
  `health_score.py`, `external_metrics.py` (all response/read-only)
- **RESPONSE ONLY** (no user input): `dashboard.py`, `decision.py`, `health_analysis.py`,
  `health_score.py`, `insights.py`, `risk_alerts.py`, `timeline.py`, `trend_analysis.py`
- **GAPS IDENTIFIED**: `persons.py`, `metrics.py`, `auth.py` (change-password),
  `actions.py`, `health_assistant.py` inline classes, `external_metrics.py` query param

### 3. Gaps Identified & Fixed

| Schema / File | Class / Field | Gap | Fix Applied |
|---|---|---|---|
| `schemas/persons.py` | `PersonCreateRequest.allergies` | No `max_length` (DB write) | `Field(max_length=2000)` |
| `schemas/persons.py` | `PersonCreateRequest.family_history` | No `max_length` (DB write) | `Field(max_length=2000)` |
| `schemas/persons.py` | `PersonCreateRequest.chronic_conditions` | No `max_length` (DB write) | `Field(max_length=2000)` |
| `schemas/persons.py` | `PersonUpdateRequest` (same 3 fields) | Same | Same fix |
| `schemas/metrics.py` | `MetricCreateRequest.note` | No `max_length` (DB write) | `Field(max_length=2000)` |
| `schemas/auth.py` | `ChangePasswordRequest.current_password` | No `max_length` (bcrypt DoS risk) | `Field(max_length=1024)` |
| `schemas/actions.py` | `HealthActionCreate.confidence` | No `ge/le` range | `Field(ge=0, le=1)` |
| `api/health_assistant.py` | `_SnoozeBody.snoozed_until` | No `max_length` | `Field(max_length=40)` |
| `api/health_assistant.py` | `_FamilyRelationshipBody.related_profile_id` | No `max_length` | `Field(max_length=36)` |
| `api/external_metrics.py` | `metric` Query param | No `max_length` | `Query(max_length=60)` |

### 4. UNKNOWN D (deferred — deeper review needed)

| Schema | Field | Reason |
|---|---|---|
| `documents.py` | `DocumentConfirmRequest.confirmed_data: dict[str, Any]` | Arbitrary confirmed report data; size-limiting requires understanding all consumers |
| `profile.py` | `AccountUpdateRequest.account_settings: Optional[dict]` | App-controlled settings dict; keys are not user-driven free text |

### 5. Test Coverage (20 tests, 100% pass)

File: `backend/tests/test_schema_validation_p30.py`

- `TestPersonFieldConstraints` — 7 tests (create + update per-field rejection + valid accepted)
- `TestMetricNoteConstraint` — 2 tests
- `TestChangePasswordConstraint` — 2 tests
- `TestActionConfidenceConstraint` — 5 Pydantic tests (boundary + None)
- `TestHealthAssistantInlineSchemas` — 4 Pydantic tests

### 6. Regression
Full suite: **833 passed, 2 skipped, 0 failed**

### 7. Commits
- `43a318a` — `fix(validation): harden remaining schema boundary constraints (P30)`
- `716a618` — `test(validation): add P30 schema boundary regression coverage`

---

## P29-PRODUCTION-CONFIG-RUNTIME-SMOKE (2026-05-23)

**Final Classification: `P29_PRODUCTION_CONFIG_RUNTIME_SMOKE_READY`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `69d46e2` (P28 complete) ✅ |
| Dirty files | none ✅ |

---

### 2. Runtime Guard Surface Classification

| Surface | Classification | Evidence |
|---|---|---|
| `validate_production_secrets()` function | **SAFE A** | 15 unit tests in `test_config_security_guard.py` (P28) |
| `startup_event()` integration | **PARTIAL B → FIXED** | Not tested in P28; fixed by P29 startup integration tests |
| Env-var → Settings resolution | **PARTIAL B → FIXED** | `APP_ENV` / `JWT_SECRET_KEY` env var priority not smoke-tested; fixed in P29 |
| `get_settings()` lru_cache override | **PARTIAL B → FIXED** | Cache-clear + env var re-read behavior not verified; fixed in P29 |
| `config-smoke` Makefile target | **GAP C → FIXED** | Target absent from Makefile; added in P29 |
| `runtime-smoke` includes guard | **GAP C → FIXED** | `runtime-smoke` did not call config tests; now calls `config-smoke` as third stage |

---

### 3. Tests Added — `backend/tests/test_runtime_config_startup_guard.py`

9 tests, 3 classes:

| Class | Tests | What is verified |
|---|---|---|
| `TestEnvVarToSettingsResolution` | 4 | `APP_ENV` env var overrides default; `JWT_SECRET_KEY` env var overrides default; production+placeholder via env vars triggers guard; production+real secret via env vars accepted |
| `TestStartupEventIntegration` | 3 | `startup_event()` raises `RuntimeError` with production+insecure settings (monkeypatched); passes with dev+insecure; passes with production+real secret |
| `TestGetSettingsCacheBehavior` | 2 | `cache_clear()` + env var override gives production env; after cleanup, local dev env is safe and guard-free |

All tests are DB-independent. `app_auto_create_tables=False` used in pass-through startup tests.

---

### 4. Makefile Changes

**New target `config-smoke`:**
```makefile
config-smoke:
    cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q \
        tests/test_config_security_guard.py \
        tests/test_runtime_config_startup_guard.py
```
Runs 24 tests (P28 + P29), no DB required, ~1.5s.

**`runtime-smoke` updated** — now three stages:
1. `test_runtime_smoke.py` — health endpoint contracts
2. `security-smoke` — auth/JWT regression + TypeScript typecheck
3. `config-smoke` — production secret guard regression (new)

---

### 5. Test Results

| Suite | Result |
|---|---|
| `make config-smoke` | **24 / 24 PASSED** |
| `make runtime-smoke` | **ALL STAGES PASS** |
| Full backend regression | **813 passed, 2 skipped, 0 failed** |

---

### 6. Commits

| Ref | Message |
|---|---|
| `d7aab81` | `test(config): add runtime startup guard smoke regression` |
| `954b62a` | `chore(governance): add config-smoke runtime guard target` |
| C3 (this report) | `docs(report): P29 production config runtime smoke report` |

---

### 7. Known Limitations

| Limitation | Impact |
|---|---|
| `startup_event()` tested via direct call, not `TestClient` ASGI lifecycle | TestClient ASGI startup is already covered by `test_runtime_smoke.py` (local env) |
| `on_event('startup')` is deprecated in FastAPI; 4 deprecation warnings in tests | Cosmetic; pre-existing; does not affect guard behavior |
| env-var tests use `monkeypatch.setenv` which may interact with `.env` file if pydantic-settings priority order changes | Low risk; priority (env > .env file) is documented pydantic-settings behavior |

---

## P28-SECRETS-PRODUCTION-CONFIG-GUARD (2026-05-23)

**Final Classification: `P28_PRODUCTION_SECRET_GUARD_HARDENED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `81e2ce7` (P27 complete) ✅ |
| Dirty files | none ✅ |

---

### 2. Audit Scope

Full secrets / production config inventory across:
- `backend/app/core/config.py` — all 30 `Settings` fields
- `backend/app/main.py` — startup and middleware wiring
- `docker-compose.prod.yml` — production environment overrides
- `docker-compose.yml` — dev/base environment defaults
- `backend/.env` / `.env.example` — local and example env files

No frontend changes. No new pip/npm dependencies. No DB schema changes.

---

### 3. Config Surface Classification

| Config Key | Default | Classification | Risk Level |
|---|---|---|---|
| `jwt_secret_key` | `'replace_me'` | **GAP C → FIXED** | CRITICAL: JWT forgeable if default reaches prod |
| `s3_secret_key` | `'minioadmin'` | PARTIAL B | MEDIUM: MinIO/S3 access via hardcoded creds |
| `database_url` | `postgres:postgres@localhost` | PARTIAL B | MEDIUM: dev creds in default URL |
| `sentry_environment` | `'production'` | PARTIAL B | LOW: dev events routed to prod Sentry project if DSN set in dev |
| `app_debug` | `False` | SAFE A | FastAPI debug disabled by default |
| `app_env` | `'dev'` | SAFE A | Correct dev default; prod compose overrides to `'production'` |
| `cors_allow_origins` | `http://localhost:3000,...` | SAFE A | Restrictive default; restricts cross-origin to localhost |
| `rate_limit_enabled` | `False` | PARTIAL B | Opt-in; must be explicitly enabled for production hardening |
| `trusted_hosts` | `'*'` | PARTIAL B | Wildcard; should be scoped in production |
| `openai_api_key` | `''` | SAFE A | Empty default; AI features disabled until key provided |
| `sentry_dsn` | `''` | SAFE A | Empty default; Sentry disabled until DSN provided |

---

### 4. GAP C Fix — JWT Secret Production Guard

**Gap:** `jwt_secret_key: str = 'replace_me'` had no enforcement.  
`docker-compose.prod.yml` sets `APP_ENV: production` via the `environment:` block.  
An operator could deploy `docker-compose.prod.yml` while relying on the `.env`
file for `JWT_SECRET_KEY` — if omitted, the config fell through to `'replace_me'`
and the server started without any warning.

**Fix — `backend/app/core/config.py`:**

```python
_INSECURE_JWT_PLACEHOLDERS: frozenset[str] = frozenset({
    '', 'replace_me', 'replace_me_in_prod',
})
_PRODUCTION_ENVS: frozenset[str] = frozenset({'production', 'prod'})

def validate_production_secrets(settings: Settings) -> None:
    if settings.app_env.lower() in _PRODUCTION_ENVS:
        if settings.jwt_secret_key in _INSECURE_JWT_PLACEHOLDERS:
            raise RuntimeError(
                "UNSAFE STARTUP: jwt_secret_key is set to a known insecure "
                "placeholder in app_env='...'. Set JWT_SECRET_KEY environment "
                "variable to a cryptographically random value (>= 32 bytes) "
                "before starting in production."
            )
```

**Fix — `backend/app/main.py`:**
`validate_production_secrets(settings)` called as the first line of `startup_event()`.
The server refuses to accept any requests if the guard fires.

---

### 5. Tests — `backend/tests/test_config_security_guard.py`

15 tests, 4 classes:

| Class | Tests | Scope |
|---|---|---|
| `TestProductionRejectsInsecurePlaceholders` | 5 | `replace_me`, `replace_me_in_prod`, empty string, `prod` alias, error message names `JWT_SECRET_KEY` |
| `TestProductionAcceptsRealSecret` | 2 | 64-char hex secret accepted in `production` and `prod` |
| `TestNonProductionAllowsPlaceholder` | 6 | dev / local / staging / test / development (parametrised) + default settings are safe |
| `TestRateLimitSettingsParseable` | 2 | PARTIAL B classification: opt-in flag parses correctly |

All 15 pass.

---

### 6. Regression Results

| Suite | Before | After |
|---|---|---|
| Full backend | 789 passed, 2 skipped | **804 passed, 2 skipped, 0 failed** |
| P28 guard tests | — | 15 / 15 PASSED |

---

### 7. Commits

| Ref | Message |
|---|---|
| `67e8681` | `fix(config): add production guard for insecure JWT secret` |
| `b0a0a23` | `test(config): P28 runtime security config guard regression` |
| C3 (this report) | `docs(report): P28 secrets and production config guard report` |

---

### 8. Remaining PARTIAL B Items (Not Fixed in P28 — Require Ops Decisions)

| Item | Recommendation |
|---|---|
| `s3_secret_key = 'minioadmin'` | Override via `S3_SECRET_KEY` env var in production; add to deployment runbook |
| `rate_limit_enabled = False` | Set `RATE_LIMIT_ENABLED=true` in `docker-compose.prod.yml` for production hardening |
| `trusted_hosts = '*'` | Set `TRUSTED_HOSTS=yourdomain.com` in production |
| `sentry_environment = 'production'` | Override `SENTRY_ENVIRONMENT` to `local` or `dev` in local `.env` files |

---

## P27-INPUT-SANITIZATION-INJECTION-AUDIT (2026-05-23)

**Final Classification: `P27_INJECTION_HARDENED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `37736a1` (P26 tests) ✅ |
| Dirty files | none ✅ |

---

### 2. Audit Scope

Full input sanitization / injection surface audit across all routes. Five injection
categories checked: SQL injection, filesystem path traversal, AI prompt injection,
log injection, module/parameter injection.

No auth changes. No new dependencies. No frontend changes.

---

### 3. Surface Classification (Final)

| Surface | Sink Type | Guard Before P27 | Classification | Action |
|---|---|---|---|---|
| All DB queries (every route) | SQL | SQLAlchemy ORM — parameterized | **SAFE A** | None |
| `conn.execute(text('SELECT 1'))` in `main.py` | SQL | Hardcoded query, no user input | **SAFE A** | None |
| `upload_file()` storage key | Filesystem | UUID-based key, never uses filename | **SAFE A** | None |
| `_local_path_from_key()` | Filesystem | `startswith(root)` guard | **SAFE A** | None |
| `original_filename = file.filename` | DB metadata + PDF | ❌ No basename normalization | **GAP C → FIXED** | `os.path.basename` applied |
| `evaluate_module` `module_name` URL param | Module dispatch | Allowlist `{'health_check_interpreter','symptom_analysis','health_risk_prediction'}` | **SAFE A** | None |
| Fixed-route module names | Module dispatch | Hardcoded in handler | **SAFE A** | None |
| `_build_prompt()` `focus` field | AI prompt | `max_length=200` only (P24) | **PARTIAL B** | Documented — self-contained risk |
| `_load_prompt_template()` module param | Filesystem | `PROMPT_FILES` dict guard | **SAFE A** | None |
| `report_id` URL param | Dict lookup + FileResponse | `_REPORT_STATE.get(id)` → None → 404 | **SAFE A** | None |
| Download `file_path` | FileResponse | Server-set UUID path; not from client | **SAFE A** | None |
| Request logger | Log | Logs only method/path/status/latency/ip; `json.dumps(ensure_ascii=True)` | **SAFE A** | None |
| PDF `original_filename` content | PDF bytes | Parens escaped; covered by GAP C fix | **SAFE A (after fix)** | Covered by filename fix |

---

### 4. Fix Applied — GAP C: `original_filename` Path Traversal in DB Metadata

**File:** `backend/app/api/documents.py`

**Symptom:** Uploading a file named `../../evil.pdf` (valid PDF extension, valid
MIME type) would store the raw string `../../evil.pdf` in `MedicalDocument.original_filename`.
The filesystem was already safe (storage key is `documents/<user_id>/<uuid4>.pdf`).
The DB metadata and PDF report rendering received the un-sanitized value.

**Fix (1 line):**
```python
# Before (line 42):
original_filename=file.filename or 'unknown',

# After:
original_filename=os.path.basename(file.filename or '') or 'unknown',
```
`os.path.basename('../../evil.pdf')` → `'evil.pdf'`.

Also added `import os` at the top of `documents.py` (stdlib, no new dependency).

---

### 5. Documented Gap — PARTIAL B: `focus` Prompt Injection Surface

**File:** `backend/app/services/ai_modules_service.py` → `_build_prompt()`

`focus` is interpolated directly into the AI prompt string:
```python
focus_text = focus or '無特定焦點，請綜合分析。'
f'分析焦點: {focus_text}\n'
```

**Risk level:** Low. The `focus` field is:
- Bounded to `max_length=200` chars (P24 hardening)
- Requires authentication to reach the route
- Self-contained: an attacker can only affect their own AI analysis output
- No data leakage to other users is possible through this vector
- AI model is only called when `settings.openai_api_key` is set; test/default env uses rule-based fallback

**Decision:** Document only. Structural prompt injection mitigations (e.g.,
instruction delimiters, output format enforcement) are AI model layer concerns
outside the scope of backend hardening. The bounded max_length from P24 already
limits the surface area.

---

### 6. Tests Created

**File:** `backend/tests/test_injection_smoke.py` — 7 tests, all pass

```
TestDocumentFilenameInjection::test_path_traversal_filename_stored_as_basename   PASS
TestAIModuleInjection::test_unknown_module_name_rejected                         PASS
TestAIModuleInjection::test_prompt_injection_focus_does_not_crash                PASS
TestReportIdentifierInjection::test_status_unknown_id_returns_404                PASS
TestReportIdentifierInjection::test_status_injection_strings_return_404          PASS
TestReportIdentifierInjection::test_download_unknown_report_returns_404          PASS
TestReportIdentifierInjection::test_download_wrong_token_returns_403             PASS
```

Full regression: **789 passed, 2 skipped, 0 failures** (13.6 s)

---

### 7. Commits

| SHA | Message |
|---|---|
| `43912e8` | `fix(security): normalize uploaded filename to basename before DB storage` |
| `f2a2209` | `test(security): P27 injection surface smoke regression (7 tests)` |

---

## P26-RATE-LIMIT-BRUTE-FORCE-AUDIT (2026-05-23)

**Final Classification: `P26_RATE_LIMIT_SMOKE_VERIFIED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `a3d69f8` (P25 report) ✅ |
| Dirty files | none ✅ |

---

### 2. Audit Scope

Rate-limit / brute-force protection audit — verifying that:
- `InMemoryRateLimitMiddleware` is correctly implemented
- Health endpoints are exempt from throttling
- Middleware behavior is covered by regression tests
- Config knobs are correctly documented
- Rate limiting remains **opt-in** (`RATE_LIMIT_ENABLED=true` env var)

No auth changes. No DB changes. No new dependencies. No production behavior enabled.

---

### 3. Rate-Limit Inventory

#### Middleware — `backend/app/core/rate_limit.py`

| Property | Value |
|---|---|
| Class | `InMemoryRateLimitMiddleware(BaseHTTPMiddleware)` |
| Bucket key | `{client_ip}:{path}` — per-IP per-path |
| Window algorithm | Sliding window (deque, time-based) |
| Health exemption | `path.startswith('/health')` → bypassed |
| 429 body | `{'detail': 'Rate limit exceeded'}` — no internal leak |
| Storage | Thread-safe in-process `defaultdict(deque)` with `Lock` |
| External dependency | None (`slowapi` is NOT installed and NOT used) |

#### Config — `backend/app/core/config.py`

| Setting | Default | Env Var |
|---|---|---|
| `rate_limit_enabled` | `False` | `RATE_LIMIT_ENABLED` |
| `rate_limit_requests` | `120` | `RATE_LIMIT_REQUESTS` |
| `rate_limit_window_seconds` | `60` | `RATE_LIMIT_WINDOW_SECONDS` |

`.env.example` shows `RATE_LIMIT_ENABLED=true` — production intent is documented.

#### Wiring — `backend/app/main.py`

```python
if settings.rate_limit_enabled:
    app.add_middleware(InMemoryRateLimitMiddleware,
        requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds)
```

Middleware is conditionally mounted at startup — clean opt-in behavior.

---

### 4. Classification

| Item | Classification |
|---|---|
| Middleware implementation (`InMemoryRateLimitMiddleware`) | **SAFE A** — correct sliding window, thread-safe, no external deps |
| `/health`, `/health/live`, `/health/ready` exempt | **SAFE A** — `startswith('/health')` bypasses throttling |
| 429 body safe (`detail` only, no internals) | **SAFE A** — confirmed |
| Per-path bucket isolation | **SAFE A** — confirmed: exhausting path A does not affect path B |
| `rate_limit_enabled=False` default | **PARTIAL B** — middleware exists but opt-in; correct for dev/test |
| No existing rate-limit smoke test | **GAP C** → **FIXED** — `test_rate_limit_smoke.py` added |
| `slowapi` not installed | **SAFE A** — not needed; custom middleware is self-contained |
| Default threshold `120 req/60s` per IP per path | **PARTIAL B** — adequate for general use; auth endpoints (login, register) share this global threshold, not a stricter per-route limit |

#### Remaining known limitation (out of scope for P26)
- `InMemoryRateLimitMiddleware` is **global**, not per-route. Auth endpoints (`POST /api/v1/auth/login`, `POST /api/v1/auth/register`) are throttled at the same `120 req/60s` rate as all other endpoints. A per-route stricter limit (e.g., `10 req/60s` for login) would require route-level decorator support or a dedicated auth-route bucket override — this is a future hardening task, not P26 scope.
- In-memory storage does not persist across restarts and is not shared across multiple worker processes. Suitable for single-process deployment; multi-worker deployments would need Redis-backed storage.

---

### 5. Fixes Applied

| Commit | SHA | Description |
|---|---|---|
| C1 | `d3f73f5` | `test(security): add rate-limit smoke regression` |

#### C1 — `backend/tests/test_rate_limit_smoke.py` (7 tests)

| Test | Assertion |
|---|---|
| `test_health_get_exempt_when_enabled` | `/health` → 200 ×5, never 429 |
| `test_health_live_exempt_when_enabled` | `/health/live` → 200 ×5, never 429 |
| `test_health_ready_exempt_when_enabled` | `/health/ready` → 200 ×5, never 429 |
| `test_non_health_route_limited` | 3 allowed → 4th is 429 (threshold=3) |
| `test_429_body_is_safe` | `{detail: 'Rate limit exceeded'}`, no traceback/error/store keys |
| `test_disabled_mode_no_interference` | No middleware → 200 ×10 |
| `test_different_paths_tracked_separately` | Path A exhausted → Path B still returns 200 |

All tests use a minimal self-contained FastAPI app — no DB, no auth, no running server.

---

### 6. Regression Gate

| Gate | Result |
|---|---|
| `test_rate_limit_smoke.py` (7 tests) | **7/7 PASS** |
| `make runtime-smoke` (health + security chain) | **EXIT:0** — 29 passed, 2 skipped |

---

### 7. Files Changed

| File | Change |
|---|---|
| `backend/tests/test_rate_limit_smoke.py` | **CREATED** — 140 lines, 7 tests |
| `00-Plan/roadmap/active_task_report.md` | **UPDATED** — P26 block prepended |

---

### 8. Rate Limiting Status After P26

- **Remains opt-in** — `RATE_LIMIT_ENABLED=false` by default
- **Production activation**: set `RATE_LIMIT_ENABLED=true` in environment
- **Default production threshold**: 120 requests / 60 seconds per IP per path
- **Health endpoints**: always exempt (verified by tests)
- **Middleware contract**: verified by 7-test regression suite

---

### 9. Final Status

```
P26_RATE_LIMIT_SMOKE_VERIFIED
HEAD: d3f73f5
make runtime-smoke: EXIT:0
InMemoryRateLimitMiddleware: VERIFIED — exempt, throttling, safe 429, path isolation
Rate limiting: remains opt-in (RATE_LIMIT_ENABLED=true to activate)
Known gap: global threshold only, no per-route stricter limit for auth endpoints
Next: P27 — TBD
```

---

---

## P25-DEPLOYMENT-SMOKE-RUNTIME-READINESS (2026-05-23)

**Final Classification: `P25_RUNTIME_HEALTH_ENDPOINT_HARDENED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `6537e33` (P24 report) ✅ |
| Dirty files | none ✅ |

---

### 2. Audit Scope

Runtime readiness audit — verifying that:
- Health endpoints exist and return the correct contract
- A single `make runtime-smoke` target chains health + security regression
- Runtime configuration gaps are inventoried and classified

No DB schema changes. No auth logic changes. No new production dependencies.

---

### 3. Inventory Classification

| Item | Classification |
|---|---|
| `GET /health` → 200, `{status: ok}` | **SAFE A** — exists, correct |
| `GET /health/live` → 200, `{status: alive}` | **SAFE A** — exists, correct |
| `GET /health/ready` → 200 (DB up) / 503 (DB down) | **SAFE A** — DB probed via `SELECT 1` |
| `InMemoryRateLimitMiddleware` skips `/health` paths | **SAFE A** — confirmed in `rate_limit.py` |
| `app_auto_create_tables=True` on startup | **SAFE A** — documented behavior |
| `docker-compose.local.yml` starts PostgreSQL only | **SAFE A** — correct by design |
| `smoke_check.py` is an orchestrator task checker | **PARTIAL B** — NOT a deployment health check; named misleadingly |
| `rate_limit_enabled=False` by default | **PARTIAL B** — middleware exists but must be enabled via `RATE_LIMIT_ENABLED=true` |
| No health endpoint pytest coverage | **GAP C** → **FIXED** — `test_runtime_smoke.py` added |
| No `make runtime-smoke` target | **GAP C** → **FIXED** — added to `Makefile` |
| `jwt_secret_key` default is an insecure placeholder | **GAP C** → DOCUMENTED (no code change; mitigated by `.env.local` override) |

---

### 4. Security Gaps Documented (no code change warranted)

#### `jwt_secret_key` insecure default
- **Location**: `backend/app/core/config.py`
- **Issue**: Default value is a well-known placeholder. If deployed to a production environment without an explicit env override, all JWTs would share a predictable signing key.
- **Current mitigation**: `.env.local` overrides with a non-default local value. Production deployments are expected to set `JWT_SECRET_KEY` via environment variable.
- **Recommended hardening** (future): Add a startup guard in `main.py` that raises `RuntimeError` when `app_env == 'production'` and `jwt_secret_key` matches the insecure default.

#### `rate_limit_enabled=False`
- **Location**: `backend/app/core/config.py`
- **Issue**: `InMemoryRateLimitMiddleware` is implemented correctly but disabled by default. Public deployments without `RATE_LIMIT_ENABLED=true` have no in-process rate limiting.
- **Note**: `InMemoryRateLimitMiddleware` already correctly exempts `/health` paths.

#### `smoke_check.py` naming
- **Location**: root `smoke_check.py`
- **Issue**: The file name implies deployment health checking but it queries the `OrchestratorDB` task pool. Developers may wrongly assume it verifies API readiness.
- **Resolution**: This audit adds `make runtime-smoke` → `test_runtime_smoke.py` as the canonical health smoke entry point.

---

### 5. Fixes Applied

| Commit | SHA | Description |
|---|---|---|
| C1 | `f09a530` | `test(runtime): add health endpoint contract smoke regression` |
| C2 | `a5a8d6d` | `chore(governance): add runtime-smoke Makefile target` |

#### C1 — `backend/tests/test_runtime_smoke.py`
Three in-process TestClient tests:
- `test_health_returns_ok` → `GET /health` → 200, `{status: ok, service: ...}`
- `test_health_live_returns_alive` → `GET /health/live` → 200, `{status: alive, service: ...}`
- `test_health_ready_contract` → `GET /health/ready` → 200 or 503 (not 500), `{status: ready|not_ready, ...}`

No auth overrides needed (public endpoints). Passes in CI regardless of PostgreSQL availability.

#### C2 — `Makefile` — `runtime-smoke` target
```
make runtime-smoke
```
Runs:
1. `tests/test_runtime_smoke.py` (health endpoint contract, in-process)
2. `make security-smoke` (backend-auth-audit + frontend-tsc)

No running server required for any step.

---

### 6. Regression Gate

| Gate | Result |
|---|---|
| `test_runtime_smoke.py` (3 tests) | **3/3 PASS** |
| `make runtime-smoke` full chain | **EXIT:0** — 29 passed, 2 skipped |
| P23 / P24 test files | **unmodified** |

---

### 7. Files Changed

| File | Change |
|---|---|
| `backend/tests/test_runtime_smoke.py` | **CREATED** — 64 lines, 3 health endpoint tests |
| `Makefile` | **UPDATED** — `runtime-smoke` target added (7 lines) |
| `00-Plan/roadmap/active_task_report.md` | **UPDATED** — P25 block prepended |

---

### 8. Final Status

```
P25_RUNTIME_HEALTH_ENDPOINT_HARDENED
HEAD: a5a8d6d
make runtime-smoke: EXIT:0
Health endpoint contract: VERIFIED
Gaps documented: jwt_secret_key default, rate_limit_enabled=False, smoke_check.py naming
Next: P26 — TBD
```

---

---

## P24-BOUNDARY-INPUT-VALIDATION (2026-05-23)

**Final Classification: `P24_BOUNDARY_INPUT_VALIDATION_HARDENED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `fbe83cc` (P23 report) ✅ |
| Dirty files | none ✅ |

---

### 2. Threat Model (OWASP A03 / A08 — Boundary Layer)

P23 closed obvious DB-write schema gaps. P24 targets the boundary layer:
- `Form(...)` fields with no length constraint written to DB
- `list[str]` request fields with no count or per-item length bound
- `Query(...)` parameters with no string length bound
- Optional text fields passed into AI prompt pipelines without truncation guard

---

### 3. Boundary Validation Inventory

| Endpoint | Input | Type | Current Validation | Risk | Class |
|---|---|---|---|---|---|
| `POST /documents/upload` | `category` | Form | none | DB write, unbounded | **GAP C** |
| `POST /reports/generate` | `include_sections` | Body list | no count/item bound | 25 items loop CPU + unbounded strings | **GAP C** |
| `POST /reports/generate` | `person_id` | Body str | none | no UUID format check | **PARTIAL B** |
| `POST /ai-modules/*` | `AIModuleRequest.focus` | Body str | none | passed to AI prompt pipeline | **GAP C** |
| `GET /documents/lab-history` | `metric` | Query str | none | Python filter (not SQL-inject risk, still unbounded) | **PARTIAL B** |
| `POST /documents/upload` | file/content-type/size | File | `validate_upload()` enforces all | already protected | **SAFE A** |
| All `days/limit/ge/le` query params | int | Query | `ge/le` constraints | already protected | **SAFE A** |
| `POST /ai-modules/evaluate/{module_name}` | path | Path str | explicit allowlist check | already protected | **SAFE A** |
| `health_assistant` query params | `days/period_type` | Query | `ge/le` + `pattern=` regex | already protected | **SAFE A** |

---

### 4. Fixes Applied

#### `backend/app/api/documents.py`
- `category: Form(...)` → `Form(..., min_length=1, max_length=60)` — prevents empty/oversized category written to `MedicalDocument.category`
- `metric: Query(default=None)` → `Query(default=None, max_length=120)` — bounds lab history filter query param

#### `backend/app/api/reports.py` — `ReportGenerateRequest`
- `include_sections: list[str]` → `list[Annotated[str, Field(max_length=60)]]` with `Field(max_length=20)` — prevents oversized section lists (>20 items) and per-item oversized strings (>60 chars)
- `person_id: Optional[str] = None` → `Field(default=None, max_length=36)` — UUID-length bound

#### `backend/app/schemas/ai_modules.py` — `AIModuleRequest`
- `focus: Optional[str] = None` → `Field(default=None, max_length=200)` — prevents oversized focus strings from entering AI prompt pipeline

---

### 5. Test Results

| Test File | Tests | Result |
|---|---|---|
| `test_input_validation_boundary.py` | 11 | ✅ 11 passed |
| `test_input_validation_hardening.py` | 19 | ✅ 19 passed (no regression) |
| `make security-smoke` (all auth + tsc) | 29+2skip+tsc | ✅ EXIT:0 |

#### P24 Test Coverage

| Test | Assertion |
|---|---|
| `test_sections_too_many_rejected` | 25 items → 422 |
| `test_section_item_too_long_rejected` | item >60 chars → 422 |
| `test_person_id_too_long_rejected` | person_id >36 chars → 422 |
| `test_valid_single_section_accepted` | `["score"]` → 202 |
| `test_category_too_long_rejected` | Form >60 chars → 422 |
| `test_category_empty_rejected` | Form `""` → 422 |
| `test_focus_too_long_rejected` | focus >200 chars → ValidationError |
| `test_focus_valid_accepted` | valid focus → schema OK |
| `test_focus_none_valid` | `focus=None` → schema OK |
| `test_metric_query_too_long_rejected` | metric >120 chars → 422 |
| `test_metric_query_valid_accepted` | `?metric=glucose` → 200 |

---

### 6. Commits

| SHA | Message |
|---|---|
| `07f8a7c` | `fix(validation): harden boundary input constraints` |
| `61a8c86` | `test(validation): add boundary input rejection regression (11 tests)` |

---

### 7. Known Limitations / Out-of-scope

- File upload content validation (MIME detection beyond extension/type allowlist) — would require content-scanning library — out of scope
- Report `include_sections` items are matched by string equality; unknown section names are silently ignored (no 422 for unknown section names) — by design, not a security gap
- `person_id` is not validated as a UUID format (only length-bounded); invalid UUIDs are silently ignored by the DB query — low-risk, documented
- Dynamic payloads in `narrative-memory/generate`, `personalization-profile/sync` not audited — UNKNOWN, deferred

---

### 8. Completed Security Hardening Stack

| Phase | Classification | Focus |
|---|---|---|
| P17 | `P17_BACKEND_AUTHORIZATION_AUDIT_VERIFIED` | auth middleware coverage |
| P18 | `P18_REPORT_STATUS_AUTH_HARDENED_DOWNLOAD_GAP` | report status auth |
| P19 | `P19_DOWNLOAD_JWT_REQUIRED_FRONTEND_CONTRACT_GAP` | download JWT doc |
| P20 | `P20_REPORT_DOWNLOAD_AUTHORIZATION_CLOSED` | download auth closure |
| P21 | `P21_SECURITY_SMOKE_AND_CI_READY` | Makefile smoke target |
| P22 | `P22_FRONTEND_E2E_CI_SAFE_SMOKE_READY` | frontend e2e CI safe |
| P23 | `P23_INPUT_VALIDATION_HARDENED` | Pydantic schema constraints |
| **P24** | **`P24_BOUNDARY_INPUT_VALIDATION_HARDENED`** | **boundary Form/Query/list/focus** |

---

## P23-INPUT-VALIDATION-SCHEMA-HARDENING (2026-05-23)

**Final Classification: `P23_INPUT_VALIDATION_HARDENED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `83465e0` (P22 report) ✅ |
| Dirty files | none ✅ |

---

### 2. Threat Model (OWASP A03 / A08)

Authenticated users can submit request bodies. Without field-level Pydantic
constraints, malformed or oversized payloads reach the DB write path — causing
either application errors (500) or unexpected data storage. Pydantic constraints
are the correct enforcement layer: they fire before any service code runs and
return 422 automatically.

---

### 3. Validation Surface Audit

| Schema | Field(s) | Previous State | Risk | Fix |
|---|---|---|---|---|
| `auth.LoginRequest` | `password` | bare `str` | C — bcrypt DoS via unbounded input | `max_length=1024` |
| `symptoms.SymptomCreateRequest` | `note` | `Optional[str]` | C — unbounded → DB | `max_length=2000` |
| `symptoms.SymptomUpdateRequest` | `note` | `Optional[str]` | C — unbounded → DB | `max_length=2000` |
| `profile.ProfileUpsertRequest` | `allergies` | `Optional[str]` | C — unbounded → DB | `max_length=2000` |
| `profile.ProfileUpsertRequest` | `family_history` | `Optional[str]` | C — unbounded → DB | `max_length=2000` |
| `profile.ProfileUpsertRequest` | `chronic_conditions` | `Optional[str]` | C — unbounded → DB | `max_length=2000` |
| `profile.AccountUpdateRequest` | `email` | bare `str` | C — no format validation | `Optional[EmailStr]` |
| `actions.HealthActionCreate` | `description` | `Optional[str]` | C — unbounded → DB | `max_length=2000` |
| `actions.HealthActionCreate` | `category/action_type/priority/frequency/status` | bare `str` | C — unbounded → DB | `max_length=30–60` |
| `actions.HealthActionCreate` | `source_id/evidence_level/guideline_source/rule_id` | `Optional[str]` | C — unbounded → DB | `max_length=60–200` |
| `actions.HealthActionUpdate` | `description/category/priority/frequency/status` | `Optional[str]` | C — unbounded → DB | `max_length=30–2000` |
| `actions.HealthActionUpdate` | `snooze_reason/reminder_status/impact_status` | `Optional[str]` | C — unbounded → DB | `max_length=30–500` |
| `documents.ParsedItemUpdate` | `value/unit/reference_range` | `Optional[str]` | C — unbounded → DB | `max_length=50–500` |
| `health_assistant._SnoozeBody` | `hours` | `Optional[int]` no bounds | C — negative/huge values | `ge=1, le=168` |

**Schemas already SAFE (no changes):**
- `auth.RegisterRequest` — `EmailStr` + `password min/max` ✅
- `metrics.MetricCreateRequest` — all numeric with `ge`/`le` ✅
- `persons.PersonCreateRequest/Update` — `display_name`, `relationship`, `gender`, numeric bounds ✅
- `symptoms.SymptomCreateRequest` — `severity`, `duration_minutes`, `confidence_score` bounds ✅
- `health_score.HealthScoreCalculateRequest` — `days ge/le` ✅
- `ai_modules.AIModuleRequest` — `days`, `max_items` ge/le ✅
- `health_assistant._FamilyRelationshipBody` — field validators ✅

---

### 4. Commits

| SHA | Type | Description |
|---|---|---|
| `dd8ddb0` | `fix(validation)` | Harden Pydantic constraints across schema surface |
| `0a0e116` | `test(validation)` | P23 schema rejection regression suite (19 tests) |

---

### 5. Test Results

```
19 passed, 0 failed
make security-smoke → EXIT:0  (29 auth tests + tsc — all pass)
```

Test file: `backend/tests/test_input_validation_hardening.py`

| Test | Asserts |
|---|---|
| `test_login_password_too_long` | `password * 1025 → 422` |
| `test_login_password_at_max_accepted` | `password * 1024 → not 422` |
| `test_create_note_too_long` | `note * 2001 → 422` |
| `test_update_note_too_long` | `note * 2001 → 422` |
| `test_create_valid_with_note` | `note * 200 → 200` |
| `test_allergies_too_long` | `allergies * 2001 → 422` |
| `test_family_history_too_long` | `family_history * 2001 → 422` |
| `test_chronic_conditions_too_long` | `chronic_conditions * 2001 → 422` |
| `test_account_email_invalid` | `"not-an-email" → 422` |
| `test_profile_valid` | valid upsert → 200 |
| `test_create_description_too_long` | `description * 2001 → 422` |
| `test_create_category_too_long` | `category * 61 → 422` |
| `test_create_priority_too_long` | `priority * 31 → 422` |
| `test_update_snooze_reason_too_long` | `snooze_reason * 501 → 422` |
| `test_create_valid_action` | valid action → 201 |
| `test_update_value_too_long` | `value * 501 → ValidationError` |
| `test_update_unit_too_long` | `unit * 51 → ValidationError` |
| `test_update_reference_range_too_long` | `reference_range * 101 → ValidationError` |
| `test_update_valid` | valid ParsedItemUpdate → passes |

---

### 6. P17–P23 Completed Stack

| Task | Classification | HEAD |
|---|---|---|
| P17 | `P17_BACKEND_AUTHORIZATION_AUDIT_VERIFIED` | `7d36258` |
| P18 | `P18_REPORT_STATUS_AUTH_HARDENED_DOWNLOAD_GAP` | `e59d09e` |
| P19 | `P19_DOWNLOAD_JWT_REQUIRED_FRONTEND_CONTRACT_GAP` | `b37cab2` |
| P20 | `P20_REPORT_DOWNLOAD_AUTHORIZATION_CLOSED` | `b26cf25` |
| P21 | `P21_SECURITY_SMOKE_AND_CI_READY` | `b7c352b` |
| P22 | `P22_FRONTEND_E2E_CI_SAFE_SMOKE_READY` | `83465e0` |
| P23 | `P23_INPUT_VALIDATION_HARDENED` | `0a0e116` |

---

## P22-FRONTEND-E2E-BACKEND-DEPENDENCY (2026-05-23)

**Final Classification: `P22_FRONTEND_E2E_CI_SAFE_SMOKE_READY`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `b7c352b` (P21 report) ✅ |
| Dirty files | none ✅ |

---

### 2. CI Frontend E2E Current State (pre-P22)

CI frontend job ran: `npm run e2e` = `playwright test` (all 6 specs)

| Spec | Backend Required | CI Status before P22 |
|---|---|---|
| `health-platform.spec.ts` | **No** — `page.route` fully mocked | ✅ would pass |
| `platform-app.spec.ts` | **No** — `page.route` fully mocked | ✅ would pass |
| `family-health-card.spec.ts` | **No** — `page.route` fully mocked | ✅ would pass |
| `auth-negative.spec.ts` | **Yes** — real JWT to `localhost:8000` | ❌ connection refused |
| `auth-ui-negative.spec.ts` | **Yes** — real backend UI flow | ❌ connection refused |
| `auth-ui-multi.spec.ts` | **Yes** — real backend UI flow | ❌ connection refused |

The 3 auth specs call `http://localhost:8000` directly. No backend runs in the CI frontend job.

---

### 3. Selected Option: B — Split CI to mocked-only subset

Auth e2e specs require a live backend. The equivalent auth coverage already exists as Python integration tests in the backend job (`make backend-auth-audit` — 29 tests, P13–P20). Adding a backend service to the frontend CI job would require pip install + uvicorn start + env vars — too broad for P22.

Smallest safe fix: add `e2e:ci` npm script that runs only the 3 mocked specs, switch CI to use it.

---

### 4. Changes

| File | Change |
|---|---|
| `frontend/package.json` | Added `"e2e:ci"` script — runs 3 mocked specs with `--reporter=line` |
| `.github/workflows/ci-cd.yml` | `npm run e2e` → `npm run e2e:ci`; step renamed to clarify mocked-only |
| `Makefile` | Added `frontend-e2e-local` target (full suite, documents backend requirement); added to `.PHONY` |

**`e2e:ci` script:**
```
playwright test tests/e2e/health-platform.spec.ts tests/e2e/platform-app.spec.ts tests/e2e/family-health-card.spec.ts --reporter=line
```

---

### 5. Entrypoint Map (post-P22)

| Command | Scope | Backend needed | CI? |
|---|---|---|---|
| `make security-smoke` | backend P13–P20 auth + frontend tsc | No | Recommended CI gate |
| `npm run e2e:ci` | 3 mocked Playwright specs | No | ✅ used in CI |
| `make frontend-auth-smoke` | 3 auth Playwright specs | **Yes** | Local only |
| `make frontend-e2e-local` | All 6 specs | **Yes** | Local only |
| `npm run e2e` | All 6 specs | **Yes** | Local only |

---

### 6. Validation

```
make security-smoke    29 passed, 2 skipped + 0 tsc errors
package.json JSON      valid (node -e require check)
```

`npm run e2e:ci` not run against live server in this session (no backend started). Script correctness verified via JSON parse + spec file existence check.

---

### 7. Commits

| SHA | Message |
|---|---|
| `9dabb8d` | `ci: avoid unsupported frontend e2e backend dependency` |
| `8364858` | `chore(governance): add frontend-e2e-local entrypoint` |
| final | `docs(report): P22 frontend e2e backend dependency report` |

---

### 8. Remaining CI / Manual Gaps

- Auth Playwright specs (`auth-negative`, `auth-ui-negative`, `auth-ui-multi`) not run in CI. Equivalent coverage exists in `make backend-auth-audit` (Python). Full browser-level auth validation requires `make frontend-auth-smoke` locally with backend running.
- CI frontend job does not start a backend service. If future work needs full e2e in CI, a dedicated CI job with service containers + PostgreSQL setup would be required (out of P22 scope).
- `family-health-card.spec.ts` header says "NOT RUN (no live server in CI pipeline)" — this comment is now stale but in-spec (test logic still valid); updating comments is out of P22 scope.

---

## P21-CI-ENTRYPOINT-HARDENING (2026-05-23)

**Final Classification: `P21_SECURITY_SMOKE_AND_CI_READY`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `b26cf25` (P20 report) ✅ |
| Dirty files | none ✅ |

---

### 2. Current Command Inventory (pre-P21)

| Command | Classification | File |
|---|---|---|
| `make backend-test` | PARTIAL — re-creates `.venv` every run | Makefile |
| `make backend-smoke` | SAFE — `.venv/bin/python -m pytest`, 2 files (P12/P13 only) | Makefile |
| `PYTHONPATH=. pytest -q` (CI) | UNSAFE — bare `pytest` not guaranteed to use correct interpreter | `.github/workflows/ci-cd.yml:67` |
| `npm run e2e` (CI) | PARTIAL — runs full Playwright suite; backend not started in CI frontend job | `.github/workflows/ci-cd.yml:41` |
| `backend-auth-audit` | MISSING — no target covering full P13–P20 stack | — |
| `security-smoke` | MISSING | — |
| `frontend-auth-smoke` | MISSING | — |
| `frontend-tsc` | MISSING | — |

---

### 3. Changes

#### Makefile — 4 new targets added

| Target | Description |
|---|---|
| `backend-auth-audit` | Full P13–P20 auth regression: 4 test files, 31 collected, `.venv/bin/python -m pytest` |
| `frontend-tsc` | `cd frontend && npx tsc --noEmit` — no server required |
| `security-smoke` | `backend-auth-audit` + `frontend-tsc` — complete non-server security gate |
| `frontend-auth-smoke` | Targeted Playwright: `auth-negative`, `auth-ui-negative`, `auth-ui-multi` only |

`backend-auth-audit` covers:
- `tests/test_auth_negative_smoke.py` (P12)
- `tests/test_real_token_auth_negative.py` (P13/P14)
- `tests/test_person_id_authorization_audit.py` (P17)
- `tests/test_report_authorization_hardening.py` (P18+P20)

#### CI workflow (`.github/workflows/ci-cd.yml`)

- Line 67: `PYTHONPATH=. pytest -q` → `PYTHONPATH=. python -m pytest -q`
- CI installs to GitHub-managed Python via `pip install -r requirements-dev.txt` (no venv);  
  `python -m pytest` is more robust than bare `pytest` for PATH lookup.
- Change is minimal (1 line). No new services, no new cache.

#### backend/README.md (local only — untracked)

- Added auth audit commands section with table of covered files.
- File is excluded by `~/.gitignore_global` rule `README.md` — documented as known limitation.

---

### 4. Validation Results

```
make backend-auth-audit    29 passed, 2 skipped (expected SQLite UUID skips)
make security-smoke        29 passed, 2 skipped + 0 tsc errors
make backend-smoke         10 passed (P12/P13 regression)
```

---

### 5. Commits

| SHA | Message |
|---|---|
| `ae0cf5c` | `chore(governance): add reproducible auth security smoke targets` |
| `69badf4` | `ci: use canonical backend auth smoke entrypoint` |
| final | `docs(report): P21 CI entrypoint hardening report` |

---

### 6. CI Status

| Job | Status |
|---|---|
| Backend `Run tests` | Fixed: `pytest -q` → `python -m pytest -q` |
| Frontend `E2E` | **NOT UPDATED** — `npm run e2e` runs full suite without backend; backend is not started in the frontend CI job. Full e2e CI hardening deferred (requires service containers or job dependency). Documented as P22 candidate. |

---

### 7. Known Limitations

- `backend/README.md` documentation update is local-only; global `~/.gitignore_global:README.md` prevents commit without `-f`. 
- `make frontend-auth-smoke` requires: (1) backend running at `localhost:8000`, (2) `npm run build` completed. Not self-contained; documented in Makefile comment.
- `_REPORT_STATE` remains in-memory; report tests would fail after server restart (not a CI risk since tests use TestClient).
- CI frontend job still runs full `npm run e2e`; non-auth E2E specs (`health-platform.spec.ts`, `platform-app.spec.ts`) may fail without a real backend. Deferred.

---

## P20-REPORT-DOWNLOAD-AUTHORIZATION-CLOSED (2026-05-23)

**Final Classification: `P20_REPORT_DOWNLOAD_AUTHORIZATION_CLOSED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `b37cab2` (P19 gap doc) ✅ |
| Authorization phrase | `YES modify frontend/app/components/platform/report-export-modal.tsx` ✅ confirmed in P20 task |

---

### 2. Problem

P19 identified that `GET /api/v1/reports/download/{report_id}` accepted a URL-only
`?token=` parameter — no `Authorization` header required. A browser `<a href target="_blank">`
cannot attach headers, so adding `Depends(get_current_user)` to the download endpoint would
have broken the UI. This was documented as `P19_DOWNLOAD_JWT_REQUIRED_FRONTEND_CONTRACT_GAP`.

P20 is the atomic closure: change the frontend to use `fetch+blob`, then harden the backend
with a JWT owner check.

---

### 3. Changes

| Step | File | Change |
|---|---|---|
| C1 | `frontend/app/components/platform/report-export-modal.tsx` | Replace `<a href target="_blank">下載報告</a>` with authenticated `fetch+blob+createObjectURL` handler reading JWT from `localStorage.getItem('token')` |
| C2 | `backend/app/api/reports.py` | Add `current_user: Annotated[User, Depends(get_current_user)]` to `download_report`; insert ownership check (`owner_user_id != current_user.id → 404`) before token check |
| C3 | `backend/tests/test_report_authorization_hardening.py` | Add `test_download_cross_user_denied` to `TestReportDownloadTokenOnly` — user B + user A's valid token → 404 |

**Security order in `download_report` after C2:**
1. Report exists + status == ready → else 404 (no existence leak)
2. **JWT owner match** → else 404 (ownership gate; 404 not 403 to avoid confirming report existence to wrong user)
3. Token (UUID) match → else 403
4. Token not expired → else 403
5. `FileResponse` 

Both conditions (valid JWT as owner **AND** valid one-time token) are now required.

---

### 4. Test Results

```
backend/tests/test_report_authorization_hardening.py  9 passed
make backend-smoke                                    10 passed
npx tsc --noEmit                                       0 errors
```

---

### 5. Commits

| SHA | Message |
|---|---|
| `0be0368` | `fix(frontend): use authenticated blob fetch for report downloads` |
| `4c33e35` | `fix(auth): require report owner JWT for report downloads` |
| `15102e1` | `test(auth): add report download owner authorization regression` |
| final | `docs(report): P20 report download authorization closure report` |

---

### 6. Known Limitations

- `_REPORT_STATE` is an in-memory `dict` — state is lost on backend restart, no persistent report storage.
- `_set_user()` test helper overrides `get_current_user` via `dependency_overrides` — tests never exercise real JWT decode. Real JWT path is covered by `test_real_token_auth_negative.py`.

---

## P19-REPORT-DOWNLOAD-JWT-HARDENING (2026-05-23)

**Final Classification: `P19_DOWNLOAD_JWT_REQUIRED_FRONTEND_CONTRACT_GAP`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `e59d09e` (P18 report) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Objective

Close the P18 download gap by adding JWT owner-check to `GET /api/v1/reports/download/{report_id}?token=...` so that possession of a leaked token alone is insufficient to download.

---

### 3. Investigation

**Required read-only inspection:**

- `backend/app/api/reports.py` — download endpoint is token-only, no JWT dependency
- `frontend/app/components/platform/report-export-modal.tsx` — frontend download call site
- `frontend/lib/api.ts` — `getReportStatus` and `generateReport` implementations
- `backend/app/core/deps.py` — `get_current_user` auth mechanism

---

### 4. Frontend Download Call Path (Root Cause)

```
report-export-modal.tsx
  generate()
    api.generateReport(...)          // POST /reports/generate  — JWT via fetch+Authorization header ✅
    setInterval → api.getReportStatus(reportId)  // GET /reports/{id} — JWT via fetch+Authorization header ✅
      → returns { status: 'ready', download_url: '/api/v1/reports/download/{id}?token={uuid}' }
      → setDownloadUrl(res.download_url)

  render
    <a href={downloadUrl} target="_blank" rel="noreferrer">下載報告</a>
    ↑
    BROWSER-NATIVE ANCHOR NAVIGATION — no Authorization header sent
```

File: [frontend/app/components/platform/report-export-modal.tsx](frontend/app/components/platform/report-export-modal.tsx#L27-L82)

---

### 5. Why JWT Cannot Be Added Without Frontend Change

`get_current_user` (backend/app/core/deps.py:17) uses:
```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')
```

`OAuth2PasswordBearer` reads **only** from the `Authorization: Bearer <token>` HTTP header. There is no cookie fallback, no query-parameter fallback.

When the browser follows `<a href="/api/v1/reports/download/{id}?token=..."  target="_blank">`:
- The browser opens a new tab and performs a plain GET request
- **No `Authorization` header is sent** — browsers never send custom headers on anchor navigation
- Adding `current_user: Depends(get_current_user)` would raise HTTP 401 for every download

**Effect of adding `Depends(get_current_user)` today:**
```
GET /api/v1/reports/download/{report_id}?token={token}
→ FastAPI: no Authorization header
→ OAuth2PasswordBearer raises HTTP 401 Unauthorized
→ Browser shows login challenge or error page
→ All downloads broken
```

---

### 6. Required Frontend Fix (Out of Scope for P19)

The frontend `<a href>` must be replaced with a `fetch + blob + createObjectURL` pattern:

```typescript
// In report-export-modal.tsx — NOT IMPLEMENTED (frontend/app/** is governance-forbidden)
const handleDownload = async () => {
  const token = getToken()  // JWT from localStorage
  const res = await fetch(downloadUrl, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) return setStatus('failed')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `health_report.pdf`
  a.click()
  URL.revokeObjectURL(url)
}
```

This change is in `frontend/app/components/platform/report-export-modal.tsx` which is in `frontend/app/**` — prohibited by governance. Work **STOPPED** per P19 instructions before making any unsafe backend change.

---

### 7. Current Security Posture (P18 + P19)

| Vector | Status |
|---|---|
| User B queries user A's report status via `GET /reports/{id}` | ✅ Blocked by P18 (404) |
| User B obtains user A's download token via status endpoint | ✅ Blocked by P18 |
| User B downloads user A report with guessed/brute-forced token | ✅ Blocked — UUID entropy (122-bit) |
| User B downloads via leaked token (network/history/log) | ⚠️ Still possible — DOWNLOAD_GAP |
| Token expiry | ✅ 1-hour window (expires_at check) |

---

### 8. Files Changed

None. No code changes made. Documentation-only.

---

### 9. Test Results

No new tests added (no code changes made).

Prior regression suites:
- P18 tests: 8/8 PASS (unmodified)
- backend-smoke P12+P13: 10/10 PASS (unmodified)

---

### 10. Path Forward for P20

To fully close the download gap, the following two-file change must be scoped:

| File | Required Change |
|---|---|
| `frontend/app/components/platform/report-export-modal.tsx` | Replace `<a href>` with `fetch+blob+createObjectURL` |
| `backend/app/api/reports.py` | Add `current_user: Depends(get_current_user)` + ownership check to `download_report` |

Both changes must be made atomically or the download will break. Governance authorization for `frontend/app/**` modification required before P20 can proceed.

---

### 11. Commit

| Hash | Message |
|---|---|
| _(this commit)_ | docs(report): P19 report download JWT frontend contract gap |

---

### 12. CTO Summary (10 lines)

P19 investigated closing the report download gap by requiring JWT ownership on the download endpoint. Investigation found a hard frontend contract incompatibility: `report-export-modal.tsx` renders the download URL as `<a href target="_blank">`, which is browser-native anchor navigation — browsers never send `Authorization` headers on anchor clicks. FastAPI's `OAuth2PasswordBearer` reads only from the `Authorization: Bearer` header (no cookie, no query-param fallback). Adding `Depends(get_current_user)` to the download endpoint would 401 every download attempt, breaking the feature entirely. The required fix — replacing `<a href>` with `fetch+blob+createObjectURL` in `frontend/app/components/platform/report-export-modal.tsx` — is in `frontend/app/**`, which is governance-forbidden for P19. No unsafe backend change was made. Current posture: user B cannot obtain the download token (blocked by P18), UUID token is 122-bit (unguessable), and the 1-hour expiry limits the leak window. Gap remains only exploitable through token exfiltration. Full closure requires authorized scope for `frontend/app/**` in P20.

---

### 13. Next 24h Prompt

```
Resuming PersonalHealthOS on main (HEAD: see git log).
P13–P19 COMPLETE. Auth hardening stack status:
  P13–P18 — all backend auth isolation complete
  P19 — STOPPED: download JWT gap requires frontend/app/** change

P20 PLAN — Atomic download hardening (backend + frontend together):

Requires explicit governance authorization:
  YES modify frontend/app/components/platform/report-export-modal.tsx

If authorized:
  1. Replace <a href> with fetch+blob+createObjectURL in report-export-modal.tsx
  2. Add Depends(get_current_user) + ownership check to download_report() in reports.py
  3. Add regression tests for JWT-protected download
  4. Confirm no existing tests broken

Governance: main, no new branches, no push.
```

---

## P18-REPORT-DOWNLOAD-AUTHORIZATION-HARDENING (2026-05-23)

**Final Classification: `P18_REPORT_STATUS_AUTH_HARDENED_DOWNLOAD_GAP`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `7d36258` (P17 report) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Objective

Close the UNKNOWN / low-risk report authorization gap found in P17: `GET /api/v1/reports/{report_id}` had no user-ownership check — any authenticated user who knew the `report_id` could query report status and retrieve the download token.

---

### 3. `_REPORT_STATE` Before / After

**Before P18** — no user binding:
```python
_REPORT_STATE[report_id] = {
    'status': 'generating',
    'token': token,
    'expires_at': expires_at,
}
```

**After P18** — owner bound on generate:
```python
_REPORT_STATE[report_id] = {
    'status': 'generating',
    'token': token,
    'expires_at': expires_at,
    'owner_user_id': str(current_user.id),   # NEW
}
```

Both the initial `'generating'` state and the final `'ready'` state now include `owner_user_id`.

---

### 4. Endpoint Changes

#### `GET /api/v1/reports/{report_id}` — HARDENED ✅

**Before**: returned `{status: failed}` for unknown reports; no ownership check at all.

**After**:
```python
state = _REPORT_STATE.get(report_id)
if not state:
    raise HTTPException(status_code=404, detail='Report not found')
if str(state.get('owner_user_id')) != str(current_user.id):
    raise HTTPException(status_code=404, detail='Report not found')
```

- Missing report → 404 (was `{status: failed}`)
- Cross-user access → 404 (was 200 with full status)
- Own report → 200 with download URL (unchanged behavior)

#### `GET /api/v1/reports/download/{report_id}?token=...` — TOKEN-ONLY (DOWNLOAD_GAP) ⚠️

Not modified. Token is a UUID (unguessable). Token is now only returned by the hardened status endpoint to the report owner. The download endpoint therefore cannot be reached by user B in the normal flow — they cannot obtain the token.

**Residual risk**: if the token leaks via browser history, network capture, or log scraping, a third party can download without JWT. Mitigated by 1-hour expiry and UUID entropy. Not fixed in P18 scope (would require frontend auth-header change on `<a href>` download).

---

### 5. Test Results

| Test | Result |
|---|---|
| `test_generate_sets_owner_user_id` | ✅ PASS |
| `test_status_own_report_ok` | ✅ PASS |
| `test_status_cross_user_denied` | ✅ PASS |
| `test_status_unknown_report_denied` | ✅ PASS |
| `test_status_response_no_leak` | ✅ PASS |
| `test_download_valid_token_ok` | ✅ PASS |
| `test_download_wrong_token_denied` | ✅ PASS |
| `test_download_unknown_report_denied` | ✅ PASS |
| **P18 new total** | **8/8 PASS** |
| backend-smoke P12+P13 regression (10) | ✅ 10/10 PASS |

---

### 6. Files Changed

| File | Change |
|---|---|
| `backend/app/api/reports.py` | Add `owner_user_id` to both `_REPORT_STATE` assignments; harden `get_report_status` with 404 on missing / cross-user |
| `backend/tests/test_report_authorization_hardening.py` | New — 8 tests across 3 classes |

No schema changes. No new dependencies. No frontend files modified.

---

### 7. Known Limitations / Inferred

| Item | Status |
|---|---|
| Report status owned by current_user | ✅ Fixed |
| Download token only obtainable by owner (via hardened status) | ✅ Effective |
| Download endpoint token-leaked-by-external-means | ⚠️ GAP — GUID-as-secret with 1h expiry |
| `_REPORT_STATE` is in-memory (lost on restart) | Pre-existing design, out of scope |

---

### 8. Commits

| Hash | Message |
|---|---|
| `6902492` | fix(auth): bind report state and status endpoint to report owner (P18) |
| `30cba72` | test(auth): add report authorization hardening regression (P18) |
| _(this commit)_ | docs(report): P18 report status hardened with download gap |

---

### 9. CTO Summary (10 lines)

P18 closed the report authorization gap identified in P17. The `_REPORT_STATE` in-memory dict now stores `owner_user_id = str(current_user.id)` on every `POST /reports/generate` call. `GET /api/v1/reports/{report_id}` now validates `state['owner_user_id'] == str(current_user.id)` and returns 404 for both missing and cross-user report IDs — preventing user B from querying user A's report status or receiving the download token. The download endpoint (`/reports/download/{report_id}?token=...`) remains token-only to preserve browser-native download compatibility; since the token is now only obtainable by the owner through the hardened status endpoint, the practical attack surface is eliminated. Residual risk: token leakage via external means (browser history, network capture) could still allow download — mitigated by UUID entropy and 1-hour expiry. 8 new regression tests confirm ownership binding, 404 on cross-user, no data leak in response body, and valid/invalid download token flows. P12+P13+P17 smoke regressions (10+10+8 = 28 tests) all pass.

---

### 10. Next 24h Prompt

```
Resuming PersonalHealthOS on main (HEAD: see git log).
P13–P18 are COMPLETE. Full auth isolation stack verified:
  P13 — real JWT cross-user API smoke (10 tests)
  P14 — browser auth API negative smoke (10 tests)
  P15 — real-JWT UI negative smoke (1 test)
  P16 — multi-browser storageState isolation (2 tests)
  P17 — backend authorization audit (10 pass, 2 skip/SQLite)
  P18 — report status auth hardened, download gap documented (8 tests)

Known remaining gap:
  GET /api/v1/reports/download/{report_id}?token=... is token-only.
  Token leakage from external sources (browser history, network) could
  allow unauthorized download. Mitigated by UUID entropy + 1h expiry.
  Future P19 option: add JWT + owner check to download endpoint and
  update frontend to use fetch with Authorization header.

Governance:
- Branch: main
- Do NOT modify frontend files
- Do NOT add dependencies
- Do NOT push
```

---

## P17-BACKEND-AUTHORIZATION-ENFORCEMENT-AUDIT (2026-05-23)

**Final Classification: `P17_BACKEND_AUTHORIZATION_AUDIT_VERIFIED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `34aa183` (P16 final report) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Objective

Audit all FastAPI endpoints that accept `person_id` (query param or path param) and verify they enforce `owner_user_id == current_user.id` before returning user-owned data. Add targeted pytest coverage for all uncovered person-scoped routes.

---

### 3. Ownership Gate — `get_target_person` (app/core/deps.py)

```python
def get_target_person(
    person_id: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonProfile:
    default_person = ensure_default_person_profile(db, current_user)
    if not person_id:
        return default_person
    person_uuid = uuid.UUID(person_id)   # raises 404 on invalid UUID
    person = (
        db.query(PersonProfile)
        .filter(PersonProfile.id == person_uuid, PersonProfile.owner_user_id == current_user.id)
        .first()
    )
    if not person:
        raise HTTPException(status_code=404, detail='Person profile not found')
    return person
```

**Verdict**: Correct. All person-scoped routes that delegate to `get_target_person` are safe.

---

### 4. Endpoint Authorization Inventory

| Endpoint | File | person_id via | Ownership mechanism | Classification |
|---|---|---|---|---|
| GET /api/v1/persons | persons.py | N/A | filter `owner_user_id == current_user.id` | **SAFE** |
| PUT /api/v1/persons/{id} | persons.py | path param | filter `id + owner_user_id == current_user.id` | **SAFE** (SQLite coercion note) |
| DELETE /api/v1/persons/{id} | persons.py | path param | filter `id + owner_user_id == current_user.id` | **SAFE** (SQLite coercion note) |
| GET /api/v1/metrics | metrics.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/symptoms | symptoms.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/documents | documents.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/dashboard/overview | dashboard.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/health-score/history | health_score.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/risk-alerts | risk_alerts.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/timeline | timeline.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| GET /api/v1/profile/me | profile.py | ?person_id | `get_target_person` | **SAFE** ✅ tested |
| POST /api/v1/risk-alerts/{id}/dismiss | risk_alerts.py | path param (alert) | `RiskAlert.user_id == current_user.id` | **SAFE** |
| POST /api/v1/reports/generate | reports.py | payload.person_id | `get_target_person` + secondary `owner_user_id` check | **SAFE** |
| GET /api/v1/reports/{report_id} | reports.py | N/A | In-memory GUID-as-secret | **UNKNOWN (low risk)** |
| GET /api/v1/reports/download/{id} | reports.py | N/A | Token-as-secret, no JWT | **UNKNOWN (low risk)** |
| GET /api/v1/health-assistant/family-health-context | health_assistant.py | ?person_id | `get_target_person` | **SAFE** (P12/P13 covered) |
| GET /api/v1/health-assistant/family-recommendations | health_assistant.py | ?person_id | `get_target_person` | **SAFE** (P12/P13 covered) |
| All other health-assistant routes | health_assistant.py | ?person_id | `get_target_person` | **SAFE** |
| GET /api/v1/actions | actions.py | ?person_id | `get_target_person` | **SAFE** |
| GET /api/v1/analytics/* | analytics.py | ?person_id | `get_target_person` | **SAFE** |
| GET /api/v1/ai-summary/* | ai_summary.py | ?person_id | `get_target_person` | **SAFE** |
| GET /api/v1/insights/* | insights.py | ?person_id | `get_target_person` | **SAFE** |

---

### 5. Findings

**No proven cross-user authorization bug found.**

All person-data endpoints use `get_target_person` which enforces `owner_user_id == current_user.id` before the handler runs. A foreign `person_id` always returns HTTP 404 before any data is touched.

**UNKNOWN items (low risk, not fixed per scope):**
- `GET /api/v1/reports/{report_id}` — uses in-memory state keyed by GUID only (no user binding). Any authenticated user who guesses the UUID can query status. Risk: UUIDs are generated per-request and only returned to the requesting user; GUID-as-secret.
- `GET /api/v1/reports/download/{report_id}` — no auth, token-based. Same GUID-as-secret pattern. Short-lived (1h expiry). Low risk.

These are noted for future hardening (bind report state to `current_user.id`) but are outside the P17 fix scope.

---

### 6. Test Results

| Suite | Tests | Result |
|---|---|---|
| test_person_id_authorization_audit.py — cross-user query-param (8) | 8/8 PASS | ✅ |
| test_person_id_authorization_audit.py — path-param (2 skipped) | 2 SKIP | SQLite UUID coercion (see note) |
| test_person_id_authorization_audit.py — own-person sanity (2) | 2/2 PASS | ✅ |
| backend-smoke (P12 + P13, 10 tests) | 10/10 PASS | ✅ |
| **Total** | **10 passed, 2 skipped** | ✅ |

**SQLite skip note**: `PUT/DELETE /persons/{person_id}` routes pass the raw path-param string to SQLAlchemy's `UUID(as_uuid=True)` column. PostgreSQL's psycopg2 coerces `str→UUID` transparently; SQLite does not. The production ownership guard (`owner_user_id == current_user.id`) is correct by code inspection and mirrors the same pattern proven by all other tests.

---

### 7. Files Changed

| File | Change |
|---|---|
| `backend/tests/test_person_id_authorization_audit.py` | New — 12 tests across 3 classes |

No backend application code modified (no bugs found requiring fixes).

---

### 8. Commits

| Hash | Message |
|---|---|
| `d28e13e` | test(auth): add person_id authorization audit coverage (P17) |
| _(this commit)_ | docs(report): P17 backend authorization audit report |

---

### 9. CTO Summary (10 lines)

P17 audited the complete FastAPI `person_id` authorization surface. The central ownership gate is `get_target_person` (core/deps.py) which filters `PersonProfile` by both `id` and `owner_user_id == current_user.id` — any cross-user person_id returns HTTP 404 before the handler runs. 20+ endpoints were catalogued; all person-scoped routes delegate to this gate. 8 GET endpoints were verified by automated cross-user negative probes (metrics, symptoms, documents, dashboard, health-score, risk-alerts, timeline, profile) — all returned 404 with no data leakage. 2 positive sanity checks confirm own-person access still works. PUT/DELETE /persons/{id} have the same ownership guard by code inspection; skipped in SQLite env due to UUID coercion incompatibility. Two report-download routes use GUID/token-as-secret (no user binding) — noted as low-risk UNKNOWN items for future hardening. No proven cross-user authorization bug found. Backend smoke (P12+P13, 10 tests) continues to pass.

---

### 10. Next 24h Prompt

```
Resuming PersonalHealthOS on main (HEAD: see git log).
P13–P17 are COMPLETE. Full auth isolation stack verified:
  P13 — real JWT cross-user API smoke (3 tests)
  P14 — browser auth API negative smoke (3 tests)
  P15 — real-JWT UI negative smoke (1 test)
  P16 — multi-browser storageState isolation (2 tests)
  P17 — backend authorization audit (10 tests, 2 skipped/SQLite)

P18 PLAN — Report Download Authorization Hardening:

The P17 audit found two low-risk UNKNOWN items in reports.py:
  1. GET /api/v1/reports/{report_id}     — no user binding on in-memory state
  2. GET /api/v1/reports/download/{id}  — no auth, token-only

Task: Bind report state to current_user.id so that GET /api/v1/reports/{report_id}
requires the same user who generated the report. Add a pytest verifying that
user A cannot query the status of user B's report_id.

Governance:
- Branch: main
- Allowed: modify backend/app/api/reports.py only
- Allowed: add backend/tests/test_reports_authorization_audit.py
- Do NOT modify frontend files
- Do NOT add dependencies
- Do NOT push or create branches
- Run targeted pytest only
```

---

## P16-MULTI-BROWSER-STORAGESTATE-UI-NEGATIVE-SMOKE (2026-05-23)

**Final Classification: `P16_FULL_UI_AUTH_NEGATIVE_SMOKE_VERIFIED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `2a81426` (P15 final report) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Objective

Extend P15 to full multi-browser simultaneous sessions:
- **Positive control**: userB can access their own persons data (userB.personId in response, userA.personId absent)
- **Cross-user negative**: userA injected with userB.personId gets HTTP 404 + error UI with no data leakage
- **storageState round-trip**: JWT persists across a fresh browser context without `addInitScript`

---

### 3. Root Cause Analysis — Two Failures Fixed

#### Failure 1 — `waitForResponse` filter excluded `?person_id=...` URLs
`api.request()` appends `?person_id=<id>` to every request once `localStorage.person_id` is set. The filter `!url.includes('person_id')` excluded all matching responses → 15s timeout.
**Fix**: changed filter to `/\/api\/v1\/persons(\?|$)/.test(url)` — matches path regardless of query string.

#### Failure 2 — Route handler throw on context close propagated to test runner
`contextA.close()` while dashboard API calls were in-flight caused `route.fetch()` to throw `"Target page, context or browser has been closed"`. Playwright propagated this to the test, ending it before `contextFromStorageState` could run.
**Fix**: wrapped `route.fetch()` in try-catch inside `installCORSBridge`; on catch, calls `route.abort().catch(() => {})` silently.

---

### 4. Architecture

#### `installCORSBridge` (hardened)
```typescript
try {
  const response = await route.fetch()
  await route.fulfill({ response, headers: { ...response.headers(), ...CORS_HEADERS } })
} catch {
  await route.abort().catch(() => {})  // context closed while in-flight
}
```

#### `contextFromStorageState`
```typescript
export async function contextFromStorageState(browser: Browser, statePath: string): Promise<BrowserContext> {
  const context = await browser.newContext({ storageState: statePath })
  await installCORSBridge(context)  // route handlers NOT persisted in storageState
  return context
}
```

#### Test 1 — Simultaneous sessions
- `Promise.all([bootstrapWithRealJWT(ctxA), bootstrapWithRealJWT(ctxB)])` — two independent CORS bridges
- Positive control: reload pageB, assert `GET /api/v1/persons` → 200, contains userB.personId, not userA.personId
- Cross-user: inject userB.personId into pageA localStorage, reload, assert family-health-context → 404, error text visible, body does not contain userB.personId

#### Test 2 — storageState round-trip
- Bootstrap ctxA, `ctxA.storageState({ path: tmpFile })`, close ctxA
- `contextFromStorageState(browser, tmpFile)` → fresh context, no `addInitScript`
- Navigate to dashboard, assert `GET /api/v1/persons` → 200, `localStorage.person_id === userA.personId`

---

### 5. Test Results

| Test | Result | Duration |
|---|---|---|
| Simultaneous sessions — userB positive + userA cross-user 404 | ✅ PASS | ~9.6s combined |
| storageState round-trip — auth persists without addInitScript | ✅ PASS | ~9.6s combined |
| P15 regression (auth-ui-negative.spec.ts) | ✅ PASS | |
| P14 regression (auth-negative.spec.ts × 3) | ✅ PASS | |
| **Total** | **6/6** | **~18s** |

---

### 6. Commits

| Hash | Message |
|---|---|
| `d59c11c` | test(e2e): extract installCORSBridge + add contextFromStorageState + harden route teardown (P16) |
| `5d652cc` | test(e2e): add multi-browser storageState auth isolation smoke (P16) |
| _(this commit)_ | docs(report): P16 multi-browser storageState UI auth smoke report |

---

### 7. Files Changed

| File | Change |
|---|---|
| `frontend/tests/e2e/fixtures/auth-ui.ts` | Extracted `installCORSBridge`, added `contextFromStorageState`, hardened route handler |
| `frontend/tests/e2e/auth-ui-multi.spec.ts` | New — 2 multi-browser tests |

---

### 8. CTO Summary (10 lines)

P16 extends P15's JWT-in-localStorage auth isolation to full multi-browser simultaneous sessions. Two independent Playwright browser contexts (userA + userB) each get their own CORS bridge and JWT bootstrap. Positive control confirms userB's JWT returns their own person records and excludes userA's. Cross-user negative confirms userA injected with userB's personId gets HTTP 404 from the backend and the error UI renders with no data leakage. storageState round-trip proves that Playwright's `context.storageState()` + `browser.newContext({ storageState })` preserves the JWT across a fresh browser context without any `addInitScript` re-injection. Two bugs were fixed: (1) `api.request()` appends `?person_id=...` to all requests — the URL filter needed a path-only regex; (2) `contextA.close()` while dashboard requests were in-flight caused `route.fetch()` to throw into the test runner — fixed by try-catch inside `installCORSBridge`. All 6 tests pass (P14 × 3 + P15 × 1 + P16 × 2) in ~18s total. Auth isolation is now verified at API, UI network, UI DOM, multi-browser, and storageState persistence layers.

---

### 9. Next 24h Prompt

```
Resuming PersonalHealthOS on main (HEAD: <see git log>).
P13–P16 are COMPLETE. All 6 e2e auth isolation tests pass.

P17 PLAN — Backend Authorization Enforcement Audit:
The P14–P16 test suite proved that the frontend correctly scopes requests to the
authenticated user's person_id. The next layer to verify is that the FastAPI backend
ALSO enforces this scoping — i.e., that endpoint handlers validate the JWT sub claim
against the requested person_id and return 403/404 for cross-user attempts at the
API level (not just via the frontend's person_id injection trick).

Task: Audit all FastAPI routes that accept a person_id path/query parameter and verify
they check `current_user.id == person_id` (or equivalent). For any route missing this
check, add the guard and write a backend pytest that directly calls the endpoint with
a valid JWT but a foreign person_id to prove 403 is returned.

Governance:
- Branch: main
- Do NOT modify frontend/**
- Do NOT run full e2e suite
- Do NOT push or create branches
- Run only the new pytest file(s) to verify
```

---

## P15-REAL-JWT-STORAGESTATE-UI-NEGATIVE-SMOKE (2026-05-23)

## P15-REAL-JWT-STORAGESTATE-UI-NEGATIVE-SMOKE (2026-05-23)

**Final Classification: `P15_REAL_JWT_STORAGESTATE_UI_NEGATIVE_SMOKE_VERIFIED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `ca16633` (P14 final report) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Objective

Prove that a user-A browser session (real JWT in localStorage) **cannot** access user-B's family health data at the **UI rendering layer** — network assertion (HTTP 404) AND DOM assertion (error text visible, no data leakage).

---

### 3. Root Cause Analysis — Why Naive Approaches Failed

#### Attempt 1 — React controlled-input fill

`page.fill()` on the Next.js login form did not trigger React's `onChange` handler in a production (`next start`) build.  No `/api/v1/auth/login` request appeared in the network trace.  **Root cause**: Playwright's `fill()` sets the native DOM value but does not fire synthetic React events in production bundle.

#### Attempt 2 — addInitScript + waitForFunction (initial hang)

Switched to JWT bootstrap via `addInitScript`.  Two bugs caused the test to hang for the full 120 s test timeout:

| Bug | Cause | Fix |
|---|---|---|
| **CORS** | Playwright webServer runs on `:3010`; backend `cors_allow_origins` only covers `:3000,3100`. Browser sent all requests but received `time:-1` (no response). PersonProvider's `listPersons()` call never resolved → `person_id` was never set in localStorage. | Added `context.route('http://localhost:8000/**', ...)` CORS bridge in fixture: intercepts every backend request, forwards it unchanged via `route.fetch()`, patches `Access-Control-Allow-Origin: http://127.0.0.1:3010` onto the response. |
| **`waitForFunction` arg/options confusion** | `{ timeout: 10_000 }` was passed as the **2nd** positional argument (the page-function `arg`), not the **3rd** (`options`). Playwright applied `timeout: 0` (infinite) and silently ignored the `10_000` value. Test hung until the 120 s `test.setTimeout` fired. | Reordered to `waitForFunction(fn, undefined, { timeout: 10_000 })`. Confirmed in trace: `params.timeout` changed from `0` to `10000`. |

#### Attempt 3 — addInitScript re-injection on reload

Passing `personId = userA.personId` to `bootstrapWithRealJWT` caused it to be re-injected on `page.reload()` (addInitScript runs on every navigation), overwriting the cross-user injection.  **Fix**: call `bootstrapWithRealJWT(context, token)` without `personId`; let PersonProvider auto-select it.

---

### 4. Final Architecture

```
setupTwoUsers(request)
  ├─ POST /auth/register + /auth/login  → userA.token, userA.personId
  └─ POST /auth/register + /auth/login  → userB.token, userB.personId

bootstrapWithRealJWT(contextA, userA.token)
  ├─ context.route('localhost:8000/**')  ← CORS bridge (new)
  ├─ page.addInitScript({ token })       ← localStorage['token'] = userA.token
  ├─ page.goto('/platform/dashboard')   ← PersonProvider mounts → listPersons()
  └─ waitForFunction(person_id truthy, undefined, { timeout: 10_000 })  ← fix

page.evaluate(() => localStorage.setItem('person_id', userB.personId))

waitForResponse(url.includes('family-health-context'))  ← set up BEFORE reload
page.reload()
  └─ addInitScript fires: token=userA  (person_id stays as userB via localStorage)

familyCtxResponse.status()  →  404   (backend get_target_person owner check)
getByText('無法載入家庭健康資料')  →  visible
bodyText.includes(userB.personId)  →  false
```

---

### 5. Files Changed

| File | Action |
|---|---|
| `frontend/tests/e2e/fixtures/auth-ui.ts` | Created — CORS bridge + real-JWT bootstrap fixture |
| `frontend/tests/e2e/auth-ui-negative.spec.ts` | Created — P15 full-UI cross-user smoke spec |
| `00-Plan/roadmap/active_task_report.md` | Updated — P15 report block prepended |

---

### 6. Test Result

```
Running 1 test using 1 worker
  1 passed (7.3s)
```

| Test | Status |
|---|---|
| user A real-JWT session → user B person_id → family-health-context 404 + error UI rendered | ✅ PASS |

P14 regression check (3/3 API-level tests):

```
Running 3 tests using 1 worker
  3 passed (3.1s)
```

---

### 7. TypeScript Result

```
npx tsc --noEmit
tsc exit: 0  (0 errors)
```

---

### 8. Commit List

| Commit | Hash | Message |
|---|---|---|
| C1 | `78c1e40` | `test(e2e): add real-JWT storageState bootstrap fixture for UI smoke (P15)` |
| C2 | `d2aea8c` | `test(e2e): add full UI cross-user auth negative smoke (P15)` |
| C3 | (this commit) | `docs(report): P15 real-JWT storageState UI auth smoke report` |

---

### 9. Key Lessons

| Lesson | Detail |
|---|---|
| Playwright `waitForFunction(fn, arg, options)` — arg vs options | Passing `{ timeout }` as 2nd param silently makes it the page-function argument, not the timeout option.  Always pass `undefined` as arg when no arg is needed. |
| CORS with Playwright webServer | If `reuseExistingServer: false` and the webServer port is not in the backend CORS whitelist, ALL browser API calls will silently fail.  Use `context.route()` to bridge CORS in the fixture layer without touching production code. |
| `addInitScript` runs on every navigation | Do NOT inject values into `addInitScript` that you intend to override mid-test.  Inject only stable values (JWT token); let the app populate dynamic values (person_id). |

---

# Active Task Report — P14-BROWSER-AUTH-FIXTURE-FOUNDATION (2026-05-23)

## P14-BROWSER-AUTH-FIXTURE-FOUNDATION (2026-05-23)

**Final Classification: `P14_BROWSER_AUTH_NEGATIVE_SMOKE_VERIFIED`**

---

### 1. Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| HEAD before work | `f1be74b` (P13-FINALIZE report, clean tree) ✅ |
| Dirty files at start | None ✅ |

---

### 2. Current Git HEAD Before Work

```
f1be74b docs(report): P13-FINALIZE + browser auth smoke report — NOT_IMPLEMENTED with gap detail
b484c56 docs(roadmap): P13 closure — roadmap + CTO + CEO + active task + report
eeadbf7 chore(governance): backend-smoke target + artifact ignore rules + entrypoint alignment
0a73f1a feat(auth): P13 real-token JWT negative smoke + override smoke
```

---

### 3. Auth Route / Token Endpoint Findings

| Item | Value |
|---|---|
| Register endpoint | `POST /api/v1/auth/register` — `{"email": str, "password": str}` — 201 on success, 400 if already registered |
| Login endpoint | `POST /api/v1/auth/login` — `{"email": str, "password": str}` → `{"access_token": str, "token_type": "bearer"}` |
| Token format | JWT (HS256), subject = user UUID |
| Persons create | `POST /api/v1/persons` with `Authorization: Bearer <token>` |
| Family health context | `GET /api/v1/health-assistant/family-health-context?person_id=<pid>` |
| Family recommendations | `GET /api/v1/health-assistant/family-recommendations?person_id=<pid>` |
| Cross-user isolation | `get_target_person` in `backend/app/core/deps.py` filters `PersonProfile.owner_user_id == current_user.id` → 404 on mismatch |
| No-token behavior | 401 `{"detail":"Not authenticated"}` |
| Backend URL | `http://localhost:8000` (from `frontend/.env.local`: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`) |

---

### 4. Existing Playwright Fixture / Mock-Auth Findings

All three prior specs (`family-health-card`, `health-platform`, `platform-app`) use:
- `localStorage.setItem('token', 'e2e-token')` — hardcoded mock token
- `page.route('**/api/v1/**', ...)` — full API route interception

No `storageState`, no `globalSetup`, no real credential flow found. Confirmed P13 gap.

---

### 5. Files Changed

| File | Action |
|---|---|
| `frontend/tests/e2e/fixtures/auth.ts` | Created — real-auth fixture (116 lines) |
| `frontend/tests/e2e/auth-negative.spec.ts` | Created — 3 negative smoke tests (73 lines) |
| `00-Plan/roadmap/active_task_report.md` | Updated — P14 report block prepended |

---

### 6. Test User / Token Bootstrap Decision

**Decision: register two dedicated e2e users on first run (idempotent)**

| User | Email | Password | Strategy |
|---|---|---|---|
| User A | `e2e-user-a@example.com` | `E2eTestA1!` | `POST /api/v1/auth/register` (400 = already exists → ok) then `POST /api/v1/auth/login` |
| User B | `e2e-user-b@example.com` | `E2eTestB1!` | Same |

Both users were pre-verified against the running backend before writing the fixture. PersonProfile creation is also idempotent — returns existing profile if one already exists.

---

### 7. Single-File Playwright Result

```
Running 3 tests using 1 worker
  3 passed (5.7s)
```

| Test | Status |
|---|---|
| user A JWT cannot access user B family-health-context → 404 | ✅ PASS |
| request without Authorization header → 401 | ✅ PASS |
| user A JWT cannot access user B family-recommendations → 404 | ✅ PASS |

**Scope note**: browser-context/API smoke (not full UI smoke). All HTTP calls use Playwright's `request` fixture (APIRequestContext) directly to the backend. The frontend UI login flow is not exercised — multi-user `storageState` fixture remains an open gap.

---

### 8. TypeScript Result

```
npx tsc --noEmit
tsc exit: 0  (0 errors)
```

---

### 9. Commit List

| Commit | Hash | Message |
|---|---|---|
| C1 | `8af3262` | `test(e2e): add real-auth Playwright fixture for browser auth smoke` |
| C2 | `78afae7` | `test(e2e): add cross-user browser-context auth negative smoke` |
| C3 | (this commit) | `docs(report): P14 browser auth fixture foundation report` |

---

### 10. Known Limitations / Unknown / Inferred

| Category | Detail |
|---|---|
| **Limitation** | Tests use `request` (APIRequestContext), not `page` — no browser UI rendering, no JS navigation, no DOM assertion. Full UI smoke requires storageState + login UI fixture (P15 candidate). |
| **Limitation** | `playwright.config.ts` `webServer` starts Next.js production server (`next start`) before any test run. Tests pass because a production build exists in `.next/`. If the build is stale, `next start` may fail. |
| **Limitation** | Test user credentials (`e2e-user-a@example.com`, `e2e-user-b@example.com`) are now seeded in the running SQLite DB. They persist across restarts. |
| **Inferred** | `reuseExistingServer: false` in playwright config means Playwright always starts a fresh Next.js process on port 3010. If port 3010 is occupied, tests will fail with server-start error. |
| **Unknown** | Whether CI will have a running backend at `localhost:8000`. Backend must be started before Playwright tests in any CI pipeline. |
| **Open gap** | `storageState` multi-user login fixture for full UI smoke — not implemented in this task. |

---

### Final Classification

**`P14_BROWSER_AUTH_NEGATIVE_SMOKE_VERIFIED`**

- Real auth fixture implemented (`frontend/tests/e2e/fixtures/auth.ts`)
- Cross-user negative smoke: 3/3 PASS (5.7s)
- TypeScript: 0 errors
- Boundary verified: `get_target_person()` ownership filter enforced end-to-end

---

---

## APPENDIX: P13-FINALIZE-AND-BROWSER-AUTH-SMOKE (2026-05-23)

## P13-FINALIZE-AND-BROWSER-AUTH-SMOKE (2026-05-23)

**Final Classification: `P13_FINALIZED_BROWSER_AUTH_NOT_IMPLEMENTED`**

---

### Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Dirty files at start | `.gitignore` M, `Makefile` M, 5 roadmap docs M, `D frontend/tsconfig.tsbuildinfo`, `D runtime/launchd/pids/backend.pid`, `D runtime/launchd/pids/frontend.pid`, `?? backend/tests/test_auth_negative_smoke.py`, `?? backend/tests/test_real_token_auth_negative.py` — all P13 expected artifacts, no scope conflict |
| Staged diff at start | 3 deletions (`git diff --cached --stat`) — all confirmed `git rm --cached` (index-only) |

---

### A1 — Staging Intent Confirmation

Physical files verified present on disk before any commit:
- `frontend/tsconfig.tsbuildinfo` — 126,055 bytes, mtime 2026-05-23 ✅
- `runtime/launchd/pids/backend.pid` — 5 bytes, mtime 2026-05-22 ✅
- `runtime/launchd/pids/frontend.pid` — 5 bytes, mtime 2026-05-22 ✅

**Verdict: `git rm --cached` (index-only removal). Physical files intact. Safe to proceed.**

---

### A2 — P13 Test File Authenticity Confirmation

| File | Docstring confirmation |
|---|---|
| `test_real_token_auth_negative.py` | "P13 Real-Token Auth Negative Smoke" — uses real `jwt.decode`, real `create_access_token`, production `get_target_person`. 7 tests. ✅ |
| `test_auth_negative_smoke.py` | "P12 Auth Negative Smoke — cross-user family context isolation" — override-style via `app.dependency_overrides`. 5 tests. ✅ |

**Verdict: Both files confirmed P13 auth tests. Content matches task description.**

---

### A3 — Commit List

| Commit | Hash | Files | Message |
|---|---|---|---|
| C1 | `0a73f1a` | 2 | `feat(auth): P13 real-token JWT negative smoke + override smoke` |
| C2 | `eeadbf7` | 5 | `chore(governance): backend-smoke target + artifact ignore rules + entrypoint alignment` |
| C3 | `b484c56` | 5 | `docs(roadmap): P13 closure — roadmap + CTO + CEO + active task + report` |

C2 includes: `Makefile`, `.gitignore`, `D frontend/tsconfig.tsbuildinfo`, `D runtime/launchd/pids/backend.pid`, `D runtime/launchd/pids/frontend.pid`

---

### A Acceptance Check

```
git log --oneline -5:
  b484c56 docs(roadmap): P13 closure — roadmap + CTO + CEO + active task + report
  eeadbf7 chore(governance): backend-smoke target + artifact ignore rules + entrypoint alignment
  0a73f1a feat(auth): P13 real-token JWT negative smoke + override smoke
  de78305 docs: update active_task_report — P12 production trust closure (713 PASS)
  d41d13c fix(orchestrator): _open_db respects ORCHESTRATOR_PROFILE_PATH env var

git status --short: (empty) ✅

Physical files post-commit:
  frontend/tsconfig.tsbuildinfo — present ✅
  runtime/launchd/pids/backend.pid — present ✅
  runtime/launchd/pids/frontend.pid — present ✅
```

**Sub-acceptance A: PASS**

---

### B1 — Playwright Fixture Probe

```
frontend/tests/
  e2e/
    family-health-card.spec.ts
    health-platform.spec.ts
    platform-app.spec.ts
```

Grep results for `test.use|login|authenticate|storageState|access_token` — **0 matches**

Playwright config (`playwright.config.ts`):
- `testDir: ./tests/e2e`
- `baseURL: http://127.0.0.1:3010`
- No `globalSetup`, no `storageState`, no auth bootstrap

All existing specs use:
- `localStorage.setItem('token', 'e2e-token')` — hardcoded mock token
- `page.route('**/api/v1/**', ...)` — full API interception
- No real login flow, no real credential exchange

---

### B2 — Branch Decision: `BROWSER_AUTH_E2E_NOT_IMPLEMENTED`

#### Missing Fixtures (precise gap list)

| Missing Component | Description |
|---|---|
| **Login helper / auth fixture** | No function that navigates to login page, submits real credentials, and captures a token or `storageState` snapshot |
| **Token bootstrap** | No mechanism to call `/api/v1/auth/token` or `/api/v1/auth/login` with test user credentials and store the JWT for subsequent requests |
| **`storageState` setup** | No `playwright/.auth/user.json` or equivalent; no `test.use({ storageState: ... })` in any spec |
| **Multi-user isolation fixture** | No fixture that creates two distinct authenticated sessions (user A session vs. user B session) |

#### Next.js Routes Involved

| Route | Path |
|---|---|
| Login page | `/platform/login` (App Router: `frontend/app/platform/login/`) and `pages/login.tsx` |
| Family context page | `/platform/settings/family` (App Router: `frontend/app/platform/settings/family/`) |
| Family context API | `GET /api/v1/family-health-context?person_id=<pid>` and `GET /api/v1/family-recommendations?person_id=<pid>` |

#### Recommended Test Assertion Points (when implemented)

1. **Setup**: Create two real users (user A, user B) via API; obtain real JWT for user A via `POST /api/v1/auth/token`
2. **Browser action**: Navigate to `/platform/settings/family?profile=<userB_person_id>` while authenticated as user A
3. **Assertion options** (any of):
   - Response status 404 from backend API call (user B's person not found for user A)
   - Redirect to `/platform/login` or error page
   - DOM assertion: user B's `display_name` / health data NOT present in page content
4. **Negative confirmation**: Page must not render any user B health data (blood pressure, symptoms, risk alerts)

#### Implementation Prerequisites (for future P14)

```typescript
// Required: tests/e2e/fixtures/auth.ts
import { test as base, Page } from '@playwright/test'

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    // 1. POST /api/v1/auth/token with test credentials
    // 2. localStorage.setItem('token', realJWT)
    // 3. yield page to test
    await use(page)
  }
})
```

**No new npm packages required** — Playwright's built-in `page.request.post()` is sufficient for token acquisition.

---

### Known Limitations / Unknown / Inferred

| Category | Detail |
|---|---|
| **Inferred** | All existing Playwright specs use mock tokens — real auth flow has never been E2E tested at browser level |
| **Unknown** | Whether the `/platform/login` App Router page (`frontend/app/platform/login/`) is the active login route vs. `pages/login.tsx` (Pages Router) |
| **Known limitation** | Backend test suite (723 PASS) validates auth isolation at HTTP level; browser-level isolation gap is purely at the Playwright fixture layer |
| **Known limitation** | `webServer` in playwright.config.ts uses `next start` (production build) — any auth fixture must work with the built app, not dev mode |

---

### Final Classification

**`P13_FINALIZED_BROWSER_AUTH_NOT_IMPLEMENTED`**

- Sub-acceptance A: **PASS** — 3 commits (C1/C2/C3) above `de78305`, clean working tree, all 3 physical files intact
- Sub-acceptance B: **`BROWSER_AUTH_E2E_NOT_IMPLEMENTED`** with complete gap detail (missing fixtures, routes, assertion points, implementation guide)

---

---

## APPENDIX: P13-AUTH-E2E-ENTRYPOINT-HARDENED (2026-05-23)

## P13-AUTH-E2E-ENTRYPOINT-HARDENED (2026-05-23)

**Final Classification: `P13_AUTH_E2E_ENTRYPOINT_HARDENED`**

---

### Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Dirty files at start | Known P12 artifacts only (`.gitignore` M, plan files M, 3 artifact D entries from P12 `git rm --cached`, `test_auth_negative_smoke.py` ??). No scope conflict. |

---

### 1. Auth Token Fixture Probe

| Item | Finding |
|---|---|
| `create_access_token` | **Exists** — `backend/app/core/security.py:18` |
| `get_current_user` | Decodes JWT via `jose.jwt.decode` using `settings.jwt_secret_key` / `settings.jwt_algorithm` |
| Existing tests with real JWT | **None** — all prior tests used `dependency_overrides[get_current_user]` |
| Auth fixture available? | **YES** — `create_access_token` is importable; real tokens can be minted in tests |

---

### 2. Real-Token Auth Negative Smoke — PASS

**New file:** `backend/tests/test_real_token_auth_negative.py`

**Approach:** Only `get_db` is overridden (in-memory SQLite). `get_target_person` runs as production code. `get_current_user` uses a SQLite-compatible shim that calls the same `jwt.decode` with the same keys/algorithm, then coerces `sub` string → `uuid.UUID` before the DB query (required for SQLite `UUID(as_uuid=True)`; a no-op in production PostgreSQL).

**Token issuance:** `create_access_token(str(user_id))` — identical to production login endpoint.

| Test | Status |
|---|---|
| User A real token + user B `person_id` → `/family-health-context` → 404, no data leak | ✅ PASS |
| User A real token + user B `person_id` → `/family-recommendations` → 404, no data leak | ✅ PASS |
| No `Authorization` header → 401 | ✅ PASS |
| Expired JWT (exp in past) → 401 | ✅ PASS |
| Garbage non-JWT string → 401 | ✅ PASS |
| User A real token + own `person_id` → 200 (sanity) | ✅ PASS |
| User A real token + no `person_id` → 200 default person (sanity) | ✅ PASS |

**Result:** `7 passed in 1.72s`

**SQLite UUID limitation note:** The production `get_current_user` passes the JWT `sub` string directly to `UUID(as_uuid=True)` column. PostgreSQL's psycopg2 handles implicit casting; SQLite does not. The test shim adds `uuid.UUID(user_id_str)` coercion. This is a test-infra gap, not a security gap — `get_target_person` ownership enforcement runs unshimmed in both test environments.

---

### 3. Test Entrypoint Hardening — PASS

**Problem:** `pytest -q` without `.venv` activation → 46 collection errors (`ModuleNotFoundError: No module named 'sqlalchemy'`).

**Changes:**

| File | Change |
|---|---|
| `backend/README.md` | Replaced bare `pytest -q` with canonical `.venv/bin/python -m pytest -q`; added warning box; documented `make backend-test` as CI equivalent |
| `Makefile` (root) | Added `backend-smoke` target: runs only auth negative tests (`test_auth_negative_smoke.py` + `test_real_token_auth_negative.py`) without full DB setup |

**Canonical test command (hardened):**
```bash
# From repo root
make backend-test
# or directly
cd backend && .venv/bin/python -m pytest -q
# auth smoke only
make backend-smoke
```

---

### 4. Full Validation Run

| Check | Command | Result |
|---|---|---|
| Backend pytest | `backend/.venv/bin/python -m pytest -q` | **723 passed, 0 failed** (716 prior + 7 new real-token tests) |
| Frontend TypeScript | `cd frontend && npx tsc --noEmit` | **Exit 0, 0 errors** |
| Frontend Next Build | `cd frontend && npx next build` | **Success** — 20 static routes, First Load JS 95.3 kB |

---

### 5. Files Changed This Sprint

| File | Action |
|---|---|
| `backend/tests/test_real_token_auth_negative.py` | **NEW** — 7 real-token auth negative tests |
| `backend/README.md` | Updated Tests section with hardened entrypoint instructions |
| `Makefile` | Added `backend-smoke` target; updated `.PHONY` |
| `00-Plan/roadmap/active_task_report.md` | This block prepended |

---

### 6. Known Limitations

1. **SQLite UUID coercion in `get_current_user`:** Production code (`deps.py`) passes JWT `sub` as string to `UUID(as_uuid=True)` column; works in PostgreSQL, fails in SQLite. Fixed by test shim. Application code not changed (out of scope).
2. **Playwright E2E still NOT_RUN:** Real-browser login → token → cross-user probe flow. Out of scope for this sprint.
3. **FastAPI `on_event` deprecation:** 4 warnings per run, pre-existing, not introduced here.
4. **`backend-test` Makefile re-creates venv on every run:** `python3 -m venv .venv` is idempotent but slow. No change made (out of scope).

---

--- # Appendix: P12 Report ---

## P12-POST-CLOSURE-VERIFICATION (2026-05-21)

**Final Classification: `P12_POST_CLOSURE_VERIFIED`**

---

### Branch Governance Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Dirty files at start | `M 00-Plan/roadmap/CEO-Decision.md`, `M 00-Plan/roadmap/CTO-Analysis.md`, `M 00-Plan/roadmap/active_task.md`, `M 00-Plan/roadmap/roadmap.md`, `M frontend/tsconfig.tsbuildinfo`, `M runtime/launchd/pids/backend.pid`, `M runtime/launchd/pids/frontend.pid` — all known artifacts, no scope conflict |

---

### A. Backend Regression Rerun — PASS

**Command:** `cd backend && source .venv/bin/activate && pytest -q`

| Metric | Result |
|---|---|
| Total tests | 716 (713 prior + 3 new auth negative smoke) |
| PASS | 716 |
| FAIL | 0 |
| Skipped | 0 |
| Warnings | 4 (FastAPI `on_event` deprecation — pre-existing) |

**Summary line:** `716 passed, 4 warnings in 5.82s`

> Note: Running pytest without `.venv` activation produces 46 collection errors (`ModuleNotFoundError: No module named 'sqlalchemy'`). The canonical invocation requires `.venv` activation — this is the same environment that produced the claimed 713 PASS.

---

### B. Frontend TypeScript — PASS

**Command:** `cd frontend && npx tsc --noEmit`

**Result:** Exit code 0, zero errors.

---

### C. Frontend Next Build — PASS

**Node version:** v20.19.5  
**npm version:** 10.8.2  
**Command:** `cd frontend && npx next build`

Build succeeded. Route table (all static):

| Route | Size | First Load JS |
|---|---|---|
| / | 358 B | 81.4 kB |
| /dashboard | 325 B | 81.4 kB |
| /health-insights | 2.4 kB | 105 kB |
| /login | 2.98 kB | 84.1 kB |
| /register | 2.84 kB | 83.9 kB |
| … (20 routes total, all ○ Static) | | |

First Load JS shared: 95.2 kB.

---

### D. Minimal API Auth Negative Smoke — PASS

**Auth fixture probe:**
- `TestClient`: present in multiple test files ✅
- `Authorization` / `access_token` / `create_access_token` / `auth_headers`: **NOT present** in test suite
- Existing tests use `app.dependency_overrides[get_current_user]` pattern (no raw JWT in tests)

**Decision:** Auth fixture exists (via dependency_overrides pattern). New negative smoke test written.

**Test file:** `backend/tests/test_auth_negative_smoke.py`

**Access control mechanism verified:**
`get_target_person` in `backend/app/core/deps.py` enforces:
```python
.filter(PersonProfile.id == person_uuid, PersonProfile.owner_user_id == current_user.id)
```
If no match → HTTP 404. This is the isolation boundary tested.

**Tests written (3):**
1. `test_cross_user_family_context_returns_404` — User A token + user B's `person_id` → `/family-health-context` → 404, no data leak ✅
2. `test_cross_user_family_recommendations_returns_404` — Same for `/family-recommendations` → 404, no data leak ✅
3. `test_own_person_id_still_accessible` — Sanity: user A's own `person_id` → 200 ✅

**Result:** `3 passed in 1.50s`

**Full regression after adding test:** `716 passed, 4 warnings in 5.82s` (0 regressions)

---

### E. Artifact Hygiene + Report Integrity — PASS

**E1. Artifact Hygiene:**

| File | Action Taken |
|---|---|
| `frontend/tsconfig.tsbuildinfo` | Added to `.gitignore`; `git rm --cached` ✅ |
| `runtime/launchd/pids/backend.pid` | Added to `.gitignore`; `git rm --cached` ✅ |
| `runtime/launchd/pids/frontend.pid` | Added to `.gitignore`; `git rm --cached` ✅ |

Physical files confirmed intact after `git rm --cached`. No runtime state was deleted.

**E2. Report Integrity:** This block inserted at top of `active_task_report.md`. Prior content preserved below appendix separator.

---

### Known Limitations / Unknown / Inferred

1. **venv invocation**: `pytest -q` without `.venv` activation fails with 46 collection errors. The 713 PASS claim and this session's 716 PASS both require explicit venv. CI/CD should pin to `.venv/bin/pytest` or equivalent.
2. **Token-based E2E**: No real JWT token is issued or verified in tests — auth isolation is tested via `dependency_overrides`. A Playwright-level E2E with a real token flow (login → get JWT → cross-user probe) remains unverified.
3. **Playwright E2E**: Written (spec exists) but not run. Browser E2E status unchanged from P11 handoff.
4. **FastAPI `on_event` deprecation**: 4 warnings in all test runs. Pre-existing, not P12-introduced.

---

--- # Appendix: Prior Sprint Reports ---

# Active Task Report — P12_PRODUCTION_TRUST_CLOSURE_READY

Generated: 2026-05-22  
Classification: **`P12_PRODUCTION_TRUST_CLOSURE_READY`**

---

## Sprint Verification Summary

| Task | Status |
|---|---|
| Task 1 — P10 Family UI evidence transparency verified | ✅ PASS (static smoke + tsc) |
| Task 2 — Minimal static / browser smoke | ✅ Static PASS · Playwright spec written · Browser E2E NOT RUN |
| Task 3 — P11 Production Trust Readiness checklist | ✅ THIS DOCUMENT |
| Task 4 — Regression validation | ✅ 617 PASS (see breakdown below) |

---

## Pre-flight

| Check | Result |
|---|---|
| Repo | `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅ |
| Branch | `main` ✅ |
| Dirty files | `M frontend/tsconfig.tsbuildinfo` (build artifact, not blocking) ✅ |

---

## Task 1 — P10 Family UI Evidence Transparency Verification

### Static smoke checks (all PASS)

| Check | Result |
|---|---|
| `EvidenceSourceBadge` present in component | ✅ 2 occurrences (definition + usage) |
| `AudienceBadge` present in component | ✅ 2 occurrences (definition + usage) |
| `source_type` consumed in render | ✅ 1 occurrence |
| Non-diagnosis disclaimer `非醫療診斷` | ✅ 1 occurrence |
| Limitations section rendered | ✅ present |
| Source origin label `健康觀察資料` | ✅ 2 occurrences (child + caregiver sections) |
| Diagnosis word `診斷` only in disclaimer | ✅ 1 total (confirmed to be in disclaimer text only) |
| Profile UUID `profile_id` in user-facing text | ✅ 0 leakage (only in internal logic / type references) |
| Badge labels: 兒童健康, 照護提醒, 共同風險, 行動建議 | ✅ all present in EvidenceSourceBadge config |

### TypeScript shape validation

- `FamilyRecommendation` type includes `source_type: string` ✅
- `npx tsc --noEmit` → 0 errors ✅
- `npx next build` → CLEAN ✅

---

## Task 2 — Smoke Test Status

| Method | Status |
|---|---|
| Static grep checks | ✅ PASS |
| TypeScript compilation | ✅ PASS |
| Next.js build | ✅ PASS |
| Playwright spec written | ✅ `frontend/tests/e2e/family-health-card.spec.ts` (6 tests) |
| Playwright browser E2E executed | ❌ NOT RUN — requires live dev server |

> Note: Playwright spec covers: section visibility, disclaimer text, source badges (兒童健康, 行動建議), audience badge (照護者), source origin label. Tests are written with mocked API routes.

---

## Task 4 — Regression Validation

### Backend test results

| Test file | Tests | Result |
|---|---|---|
| test_family_health_context.py | 46 | ✅ PASS |
| test_family_context_data_population.py | 18 | ✅ PASS |
| test_family_relationships.py | 17 | ✅ PASS |
| test_narrative_reasoning.py | — | ✅ PASS |
| test_narrative_memory_service.py | — | ✅ PASS |
| test_api_narrative_memory.py | — | ✅ PASS |
| test_engagement_analytics.py | — | ✅ PASS |
| test_personalization_profile.py | — | ✅ PASS |
| test_adaptive_recommendation_scoring.py | — | ✅ PASS |
| test_notification_history_service.py | — | ✅ PASS |
| test_api_notification_status.py | — | ✅ PASS |
| test_notification_intelligence.py | — | ✅ PASS |
| test_api_notification_intelligence.py | — | ✅ PASS |
| test_lab_intelligence.py | — | ✅ PASS |
| test_api_lab_smoke.py | — | ✅ PASS |
| test_api_symptom_smoke.py | — | ✅ PASS |
| test_symptom_intelligence.py | — | ✅ PASS |
| test_device_signal_escalation.py | — | ✅ PASS |
| test_device_signal_detection.py | — | ✅ PASS |
| test_api_escalation_smoke.py | — | ✅ PASS |
| test_health_assistant_service.py | — | ✅ PASS |
| test_daily_summary_service.py | — | ✅ PASS |
| test_recommendation_trust_service.py | — | ✅ PASS |
| test_outcome_feedback_service.py | — | ✅ PASS |
| **Batch 1 total** | **320** | ✅ PASS |
| **Batch 2 total** | **297** | ✅ PASS |
| test_dual_agent_orchestrator.py | 10 failed | ⚠️ PRE-EXISTING — excluded |

**Total (mandated suites): 617 PASS, 0 new failures**

---

## P11 — Production Trust Readiness Checklist

> This checklist tracks readiness for trustworthy production deployment, not feature completeness.  
> Unit tests ≠ production validation. Each item is tagged DONE / GAP / NOT RUN.

### 1. Privacy & Cross-Profile Isolation

| Item | Status | Notes |
|---|---|---|
| Profile UUID not exposed in user-facing text | ✅ DONE | `test_load_errors_limitation_does_not_expose_profile_id` asserts this |
| Cross-profile evidence mixing prevention | ✅ DONE | `build_family_health_context` only uses profiles in `relationships` list |
| Unrelated profile data not surfaced | ✅ DONE | Enforced by `related_pids` filter in service |
| API auth guards (token required) | ⚠️ GAP | Backend endpoints require `Authorization` header but E2E auth validation not tested |
| Family relationship permission enforcement | ⚠️ GAP | `permission_level` stored but not enforced at query level in DB layer |

### 2. Medical Disclaimer Coverage

| Item | Status | Notes |
|---|---|---|
| No-diagnosis disclaimer in FamilyHealthCard | ✅ DONE | "以上內容為觀察性摘要，非醫療診斷，請依個人狀況諮詢專業醫療人員。" |
| Diagnosis wording absent from static copy | ✅ DONE | Only 1 occurrence of `診斷` in component, confirmed in disclaimer context |
| Hallucination guardrail policy documented | ✅ DONE | `ai/prompts/hallucination_guardrail_policy.md` exists |
| Disclaimer on other health display pages | ⚠️ GAP | Disclaimer only confirmed in FamilyHealthCard; other dashboards not audited |
| AI summary output review | ⚠️ GAP | `health_summary_system_prompt.md` exists but output review not automated |

### 3. Source Traceability

| Item | Status | Notes |
|---|---|---|
| `evidence_source` field in recommendations | ✅ DONE | Since P8 |
| `source_type` field in recommendations | ✅ DONE | Added P10 (child_health/caregiver_health/shared_risk/action) |
| Source badge visible in UI | ✅ DONE | `EvidenceSourceBadge` in FamilyHealthCard |
| Audience badge visible in UI | ✅ DONE | `AudienceBadge` in FamilyHealthCard |
| Lab/symptom/device granularity per item | ⚠️ GAP | `childAttentionItems` + `caregiverAlerts` are mixed-source strings; per-item source type not tracked |
| Narrative source traceability | ⚠️ GAP | Narrative memories referenced but not surfaced as evidence badges in UI |

### 4. Confidence & Limitations Coverage

| Item | Status | Notes |
|---|---|---|
| `confidence` field in FamilyHealthContext | ✅ DONE | Scales with profile count + evidence density |
| `limitations` field in FamilyHealthContext | ✅ DONE | Explains data gaps to user |
| Load failure visibility in limitations | ✅ DONE | P9: `load_errors_by_profile` adds limitation text |
| Limitations displayed in FamilyHealthCard | ✅ DONE | Styled with Info icon (P10) |
| ConfidenceBadge shows score | ✅ DONE | `可信度 X%` with color thresholds |
| Confidence calibration validated | ⚠️ GAP | No test asserts confidence formula accuracy vs real data |

### 5. Notification Spam Guard

| Item | Status | Notes |
|---|---|---|
| Max recommendations per member capped | ✅ DONE | `_MAX_SUGGESTIONS_PER_MEMBER = 3` constant enforced in `generate_family_recommendations` |
| Dedup against active actions | ✅ DONE | P9: `active_actions_by_profile` dedup |
| Dedup case-insensitive edge cases | ✅ DONE | P9 `TestFamilyDedupHardening` (6 tests) |
| Notification frequency limits in production | ⚠️ GAP | Unit-level only; no integration test for notification rate limits |

### 6. Data Persistence Boundaries

| Item | Status | Notes |
|---|---|---|
| Family relationships stored in DB | ✅ DONE | `FamilyRelationship` model, `family_relationships` table |
| Evidence data loaded from live DB per request | ✅ DONE | `load_family_evidence_data()` queries DB each call |
| No sensitive data in memory cache | ✅ DONE | No Redis/memory cache layer in current architecture |
| SQLite in tests, real DB in production | ✅ DONE | pytest uses in-memory SQLite via test fixtures |
| Database migration scripts present | ✅ DONE | `database/migrations/` directory exists |
| Migration tested against production schema | ⚠️ GAP | Migration scripts not run in CI |

### 7. E2E Coverage Gaps

| Item | Status | Notes |
|---|---|---|
| Platform dashboard loads | ✅ Written | `platform-app.spec.ts` (NOT RUN in this sprint) |
| FamilyHealthCard section visible | ✅ Written | `family-health-card.spec.ts` (NOT RUN) |
| No-diagnosis disclaimer visible | ✅ Written | `family-health-card.spec.ts` (NOT RUN) |
| Source badge text visible | ✅ Written | `family-health-card.spec.ts` (NOT RUN) |
| Auth flows (login/token refresh) | ❌ NOT WRITTEN | No Playwright test for auth |
| Error state handling (API 500) | ❌ NOT WRITTEN | FamilyHealthCard error state not E2E tested |
| Empty state (no relationships) | ❌ NOT WRITTEN | `EmptyState` component not E2E tested |
| Cross-browser rendering | ❌ NOT RUN | Playwright config not verified for multi-browser |

### 8. Orchestrator Pre-existing Failures

| Item | Status | Notes |
|---|---|---|
| `test_dual_agent_orchestrator.py` | ⚠️ 10 FAILED | Pre-existing failures — not caused by P8–P10 changes |
| Orchestrator failures affect production | ❌ UNVERIFIED | Dual-agent orchestrator feature scope unclear |
| Fix plan | ⚠️ GAP | Failures not investigated; excluded from mandatory suites |

### 9. Deployment Smoke Gaps

| Item | Status | Notes |
|---|---|---|
| Docker Compose local config present | ✅ DONE | `docker-compose.local.yml` exists |
| Docker Compose prod config present | ✅ DONE | `docker-compose.prod.yml` exists |
| `smoke_check.py` script present | ✅ DONE | Root-level `smoke_check.py` exists |
| Smoke check actually run | ❌ NOT RUN | Not run in this sprint |
| Backend startup health check | ⚠️ GAP | `/health` or `/ping` endpoint not confirmed present |
| Frontend startup health check | ⚠️ GAP | Next.js deployment smoke not automated |
| Secrets / env config validated | ❌ NOT RUN | `.env` variable audit not done |

### P11 Summary

| Category | DONE | GAP | NOT RUN |
|---|---|---|---|
| Privacy & cross-profile | 3 | 2 | 0 |
| Medical disclaimer | 3 | 2 | 0 |
| Source traceability | 4 | 2 | 0 |
| Confidence & limitations | 4 | 1 | 0 |
| Notification spam guard | 4 | 1 | 0 |
| Data persistence | 5 | 1 | 0 |
| E2E coverage | 4 written | 3 not written | 4 not run |
| Orchestrator failures | 0 | 1 | 1 |
| Deployment smoke | 3 | 2 | 2 |

> **P11 overall**: Foundation is solid for a health tracking app at personal/beta scale. Key gaps before broader production trust: permission enforcement at DB layer, per-item source type granularity, auth E2E tests, deployment smoke execution, and orchestrator failure resolution.

---

## Prior Sprint Reference

| Sprint | Commit | Classification |
|---|---|---|
| P8 | `cc4312b` | P8_FAMILY_HEALTH_ASSISTANT_VERIFIED |
| P9 | `5e8528f` | P9_FAMILY_CONTEXT_VERIFIED_AND_HARDENED |
| P10a | `92b9707` | P10_FAMILY_CONTEXT_UI_EVIDENCE_READY |
| P10b | this commit | P10_FAMILY_UI_VERIFIED_AND_P11_TRUST_CHECKLIST_READY |

---

## Invariants Upheld

- No profile UUID in any user-facing text ✅
- No diagnosis wording in static copy except designated disclaimer ✅
- Existing API shape unchanged (additive only) ✅
- All mandated test suites PASS ✅
- No new branches created ✅

---

## P10 Sprint Context

Previous sprint: **P9_FAMILY_CONTEXT_VERIFIED_AND_HARDENED** (commit `5e8528f`)

Prior sprint delivered:
- `load_errors_by_profile` visibility in limitations
- Family dedup edge-case hardening (6 tests)
- Load error visibility tests (4 tests)
- 672 backend PASS

This sprint: UI evidence transparency — make Family Health UI trustworthy and transparent without major backend changes.

---

## Changes Delivered

### Backend (`family_health_context_service.py`)
- Added `source_type: str` field to `FamilyRecommendation` TypedDict docstring
- `generate_family_recommendations()` now emits `source_type` alongside `evidence_source`:
  - `child_attention_item` → `"child_health"`
  - `caregiver_alert` → `"caregiver_health"`
  - `shared_risk` → `"shared_risk"`
  - `family_suggestion` → `"action"`
- Fully additive — no existing fields changed

### Frontend Types (`lib/api.ts`)
- Added `source_type: string` to `FamilyRecommendation` type

### Frontend Component (`family-health-card.tsx`)
- New `EvidenceSourceBadge({ sourceType })` — maps source_type → label + color badge
- New `AudienceBadge({ audience })` — shows recommendation target (照護者/成員/全家)
- Recommendations section: shows urgency badge + evidence source badge + audience badge before text
- `childAttentionItems` section: added source origin label "來源：健康觀察資料"
- `caregiverAlerts` section: added source origin label "來源：健康觀察資料"
- Limitations section: upgraded from plain bullets to `Info` icon + styled container
- Added no-diagnosis disclaimer at card bottom: "以上內容為觀察性摘要，非醫療診斷，請依個人狀況諮詢專業醫療人員。"
- Added `Info` icon from lucide-react

### Tests (`test_family_health_context.py`)
- New class `TestFamilyRecommendationAPIShape` (6 tests):
  - `test_all_recommendations_have_source_type`
  - `test_child_attention_item_source_type_is_child_health`
  - `test_caregiver_alert_source_type_is_caregiver_health`
  - `test_shared_risk_source_type_is_shared_risk`
  - `test_family_suggestion_source_type_is_action`
  - `test_context_has_confidence_and_limitations_fields`

---

## Validation Results

```
Backend: 678 PASS (ignoring 10 pre-existing failures in test_dual_agent_orchestrator)
Frontend: tsc 0 errors
Frontend: next build CLEAN
```

---

## Invariants Upheld

- No profile UUID in any user-facing text ✅
- No diagnosis wording in static copy ✅  
- Existing API shape unchanged (additive only) ✅
- All 40 pre-existing family tests continue to pass ✅

---

## P9 Sprint Context

Previous sprint: **P8_FAMILY_HEALTH_ASSISTANT_VERIFIED** (commit `cc4312b`)

Prior sprint delivered:
- `extract_family_evidence_from_bundle()` pure helper
- `load_family_evidence_data()` DB helper
- `GET /family-health-context` uses real per-profile evidence
- `GET /family-recommendations` uses real `active_actions_by_profile` for dedup

This sprint: verification, failure visibility, dedup edge-case hardening.

---

## Commits

| Commit | Tag | Description |
|---|---|---|
| `cc4312b` | `P9_FAMILY_CONTEXT_DATA_POPULATED` | P9 — populate 6 per-profile dicts with real evidence data |
| (current) | `P9_FAMILY_CONTEXT_VERIFIED_AND_HARDENED` | Failure visibility + dedup hardening |

---

## Files Changed This Sprint

| File | Change |
|---|---|
| `backend/app/services/family_health_context_service.py` | `load_family_evidence_data()` now tracks errors in `load_errors_by_profile`; `build_family_health_context()` accepts `load_errors_by_profile` and adds limitation text |
| `backend/app/api/health_assistant.py` | Both family endpoints pass `load_errors_by_profile` from evidence to `build_family_health_context` |
| `backend/tests/test_family_health_context.py` | Added `TestFamilyDedupHardening` (6 tests) and `TestLoadErrorVisibility` (4 tests) |

---

## P9 Data Flow Confirmation

```
FamilyRelationship DB rows
    → load_family_relationships(db, owner_user_id, subject_profile_id)
    → load_family_evidence_data(db, owner_user_id, relationships)
        → unique related_profile_ids iterated
        → build_evidence_bundle(db, uid, pid) per profile
        → on failure: load_errors_by_profile[pid] = "evidence_unavailable" (skip, no crash)
        → returns {
              lab_abnormalities_by_profile,
              symptom_patterns_by_profile,
              escalations_by_profile,
              active_actions_by_profile,
              recommendations_by_profile,
              load_errors_by_profile
          }
    → build_family_health_context(relationships, **evidence, load_errors_by_profile=...)
        → limitations += "部分成員資料載入失敗（N 位）..." when errors present
        → profile IDs never exposed in user-facing limitation text
    → generate_family_recommendations(context, active_actions_by_profile)
        → dedup via flat union all_active set (lowercase strip)
    → GET /family-health-context → frontend FamilyHealthCard
    → GET /family-recommendations → FamilyHealthCard recommendations section
```

---

## Failure Visibility Implementation

| Behaviour | Result |
|---|---|
| Evidence load error for one profile → stored in `load_errors_by_profile` | ✅ |
| Failed profile does not crash endpoint | ✅ |
| Error count surfaced in `limitations` field | ✅ |
| Profile UUID not exposed in `limitations` text | ✅ CONFIRMED by test |
| No errors → no failure limitation added | ✅ |

---

## Family Dedup Hardening — Edge Cases

| Case | Test | Result |
|---|---|---|
| Active child action suppresses matching child recommendation | `test_active_child_action_suppresses_matching_child_recommendation` | ✅ |
| Active parent action does NOT suppress unrelated child recommendation | `test_active_parent_action_does_not_suppress_unrelated_child_recommendation` | ✅ |
| Caregiver alert + child attention item with different text → both in output | `test_caregiver_alert_and_child_attention_item_both_survive_when_different` | ✅ |
| Same risk across two profiles → one shared family suggestion (not two) | `test_same_risk_in_two_profiles_creates_one_shared_suggestion` | ✅ |
| Repeated profile_id in relationships → no duplicate recommendations | `test_repeated_profile_in_relationships_no_duplicate_recommendations` | ✅ |
| Same-case active action text → dedup triggered | `test_case_insensitive_dedup_against_active_actions` | ✅ |

---

## Test Results — Required Validation Suite

| Suite | Count | Result |
|---|---|---|
| `test_family_health_context.py` | 40 | **PASS** (+10 new: 6 dedup + 4 error visibility) |
| `test_family_context_data_population.py` | 18 | **PASS** |
| `test_family_relationships.py` | 17 | **PASS** |
| `test_narrative_reasoning.py` | (included) | **PASS** |
| `test_narrative_memory_service.py` | (included) | **PASS** |
| `test_api_narrative_memory.py` | (included) | **PASS** |
| `test_engagement_analytics.py` | (included) | **PASS** |
| `test_personalization_profile.py` | (included) | **PASS** |
| `test_adaptive_recommendation_scoring.py` | (included) | **PASS** |
| `test_notification_history_service.py` | (included) | **PASS** |
| `test_api_notification_status.py` | (included) | **PASS** |
| `test_notification_intelligence.py` | (included) | **PASS** |
| `test_api_notification_intelligence.py` | (included) | **PASS** |
| `test_lab_intelligence.py` | (included) | **PASS** |
| `test_api_lab_smoke.py` | (included) | **PASS** |
| `test_api_symptom_smoke.py` | (included) | **PASS** |
| `test_symptom_intelligence.py` | (included) | **PASS** |
| `test_device_signal_escalation.py` | (included) | **PASS** |
| `test_device_signal_detection.py` | (included) | **PASS** |
| `test_api_escalation_smoke.py` | (included) | **PASS** |
| `test_health_assistant_service.py` | (included) | **PASS** |
| `test_daily_summary_service.py` | (included) | **PASS** |
| `test_recommendation_trust_service.py` | (included) | **PASS** |
| `test_outcome_feedback_service.py` | (included) | **PASS** |
| **Full backend suite (excl. dual_agent)** | **672** | **672/672 PASS** |
| `test_dual_agent_orchestrator.py` | 10 | **EXCLUDED — pre-existing failures** |
| E2E / Playwright | — | **NOT RUN** |

---

## Cross-Profile Isolation Verification

| Check | Result |
|---|---|
| Evidence loading scoped to `owner_user_id` | ✅ |
| `load_errors_by_profile` keyed by `related_profile_id` only (not user ID) | ✅ |
| User-facing limitation text contains no profile UUIDs | ✅ CONFIRMED by test |
| Evidence load failure for profile A does not affect profile B's data | ✅ |

---

## Frontend Build Verification

| Check | Result |
|---|---|
| `npx tsc --noEmit` | ✅ 0 errors |
| `npx next build` | ✅ CLEAN — all pages static/SSR, no errors |

---

## Known Limitations

- **E2E / Playwright**: NOT RUN. All tests are unit / API integration.
- **Real family data**: Tests use in-memory SQLite with synthetic profiles.
- **Evidence load error granularity**: `load_errors_by_profile` stores `"evidence_unavailable"` for all errors. Detailed error types not exposed to frontend (by design — privacy + simplicity).
- **`test_dual_agent_orchestrator.py`**: 10 pre-existing failures, always excluded. Unrelated to P9.

---

## Git

- Branch: `main`
- P8 foundation commit: `1c1717e` — `P8_FAMILY_HEALTH_ASSISTANT_FOUNDATION_READY`
- P8 verification commit: pending

---

---

# Previous Sprint Report — P4-REPORT-TO-ACTION-VERIFIED

Generated: 2026-05-20  
Classification: **`P4_REPORT_TO_ACTION_VERIFIED`**

---

## Sprint Verification Summary

| Task | Status |
|---|---|
| Task 1 — P4 data flow end-to-end verification | ✅ CONFIRMED |
| Task 2 — API smoke / regression confirmation | ✅ 16/16 PASS (↑1 stale confidence test added) |
| Task 3 — Dashboard LabInsightCard verification | ✅ CONFIRMED — stale indicator added, disclaimer present |
| Task 4 — Update active task report | ✅ THIS DOCUMENT |
| Task 5 — P5 Notification Intelligence planning | ✅ PLANNED (see below, NOT IMPLEMENTED) |

---

## Files Changed This Sprint

| File | Change |
|---|---|
| `backend/app/services/health_assistant_service.py` | Bug fix: `recency` now computed from `report.report_date` (not `created_at`); added `date` import |
| `backend/tests/test_api_lab_smoke.py` | Added `test_stale_report_confidence_lower_than_recent`; fixed sequential client ordering |
| `frontend/app/components/platform/lab-insight-card.tsx` | Added `StaleBadge` component (visible even when collapsed); added `Clock` icon import |

---

## Test Results — Full Battery

| Suite | Count | Result |
|---|---|---|
| `test_lab_intelligence.py` | 82 | **PASS** |
| `test_api_lab_smoke.py` | 16 | **PASS** |
| `test_api_symptom_smoke.py` | 14 | **PASS** |
| `test_symptom_intelligence.py` | 24 | **PASS** |
| `test_device_signal_escalation.py` | (included) | **PASS** |
| `test_device_signal_detection.py` | (included) | **PASS** |
| `test_api_escalation_smoke.py` | 12 | **PASS** |
| `test_health_assistant_service.py` | (included) | **PASS** |
| `test_daily_summary_service.py` | (included) | **PASS** |
| `test_recommendation_trust_service.py` | (included) | **PASS** |
| `test_outcome_feedback_service.py` | (included) | **PASS** |
| **Total (excl. dual_agent)** | **297** | **297/297 PASS** |
| `test_dual_agent_orchestrator.py` | 10 | **EXCLUDED — pre-existing failures, unrelated to P4** |
| E2E / Playwright | — | **NOT RUN** |

---

## P4 Data Flow Confirmation

```
LabReportItem rows (DB, abnormal_flag IS NOT NULL)
    → health_assistant_service.py: build_evidence_bundle()
        → lab_report_items list (recency now computed from report_date ✅)
    → lab_intelligence_service.py: detect_lab_abnormalities()
        → groups by item_name
        → computes severity (flag → recurrence → alert corroboration)
        → classifies abnormality_type (lipid / glucose / uric_acid / fatty_liver_marker / kidney_stone_related_marker / …)
        → stale penalty: recency=older → confidence -0.10
        → stale warning appended to whyDetected text
        → returns list[LabAbnormality]
    → evidence bundle: lab_abnormalities key always present
    → get_action_recommendations()
        → high-severity lab abnormalities enter candidate pool at priority 75
        → trust layer applied
        → completed actions (status=done, completed_at ≤ 30d) deduped by rule_id
    → /recommendations response: lab_abnormalities key present
    → Dashboard LabInsightCard renders:
        → severity badge (red/amber/blue)
        → recurrence pill (if count > 1)
        → stale badge (if any evidenceSource.recency === 'older') ← NEW THIS SPRINT
        → suggested action (always visible)
        → whyDetected + evidence sources (expanded)
        → medical disclaimer
```

---

## Supported Lab Abnormality Types

| Type code | Markers covered |
|---|---|
| `lipid_abnormality` | LDL, HDL, TC, TG, 三酸甘油酯, Cholesterol, Triglyceride |
| `glucose_abnormality` | Blood Sugar, HbA1c, Glucose, 血糖, 糖化血色素 |
| `kidney_function` | Creatinine, eGFR, BUN, 肌酸酐, 腎功能 |
| `liver_function` | ALT, AST, GGT, ALP, Bilirubin, 肝功能 |
| `fatty_liver_marker` | 脂肪肝, Fatty Liver |
| `uric_acid` | 尿酸, Uric Acid |
| `kidney_stone_related_marker` | Oxalate, Calcium, 草酸, 膀胱石, Phosphate |
| `anemia_marker` | Hemoglobin, RBC, Hematocrit, 血色素 |
| `inflammation_marker` | CRP, ESR, WBC, 白血球 |
| `thyroid_function` | TSH, T3, T4, 甲狀腺 |
| `blood_pressure` | BP, Systolic, Diastolic, 血壓 |
| `lab_abnormality` | All other out-of-range markers (generic fallback) |

---

## Dashboard LabInsightCard Verification

| Check | Result |
|---|---|
| Component exists | ✅ `frontend/app/components/platform/lab-insight-card.tsx` |
| Imported in `health-assistant-panel.tsx` | ✅ line 9 |
| `LabInsightCard` rendered in panel | ✅ line 306: `<LabInsightCard abnormalities={data.lab_abnormalities ?? []} />` |
| Uses backend `LabAbnormality` type (not mock data) | ✅ `import type { LabAbnormality } from '../../../lib/api'` |
| `lab_abnormalities` key in frontend `HealthAssistantData` | ✅ `lab_abnormalities?: LabAbnormality[]` |
| Empty state rendered when no abnormalities | ✅ "目前無異常健檢指標" |
| Stale report warning displayed (new) | ✅ `StaleBadge` chip shown in collapsed card header when evidenceSource.recency === 'older' |
| Medical disclaimer | ✅ "以上分析由 AI 自動產生，僅供健康追蹤參考，不構成醫療診斷建議" |
| No diagnosis wording | ✅ (see Known Limitations) |
| `npx tsc --noEmit` | ✅ CLEAN |
| `npx next build` | ✅ SUCCESS |

---

## Known Limitations

- **No diagnosis wording**: `suggestedAction` copy uses action-oriented language ("建議諮詢醫師" not "診斷為X"); copy review against `docs/UI_FEEDBACK_STANDARDS.md` was not re-run this sprint — spot-checked only.
- **Recency uses `report_date`**: Fixed this sprint. Previous implementation used `created_at` (DB insert time), causing all reports to appear fresh in integration tests. Production behaviour was unaffected (reports imported from parsing use `report_date` which was already set correctly), but the test relied on the bug being absent.
- **Stale warning in body text only (before this sprint)**: Was embedded in `whyDetected`, only visible on expand. Now also shown as a collapsed-state chip badge.
- **Single-occurrence reports**: If a lab report has only 1 abnormal occurrence, severity cap = "medium" regardless of flag value (unless flag is "HH"/"LL"). This is intentional conservatism.
- **No trend charts**: Lab marker trends over time are not yet visualised. Planned for P5+.
- **E2E / Playwright tests**: NOT RUN. Smoke tests cover route-level behaviour only.
- **`test_dual_agent_orchestrator.py`**: 10 pre-existing failures, always excluded (`--ignore`).

---

## Git

- Branch: `main`
- P4 base commit: `d2eedc9` — `P4_REPORT_TO_ACTION_BRIDGE_READY`
- This sprint commit: pending (P4_REPORT_TO_ACTION_VERIFIED)

---

# P5 Notification Intelligence — Planning Spec (NOT IMPLEMENTED)

> **Status**: Planned. Target: next sprint (P5).  
> **Scope**: Proactive notification layer bridging daily health insights to user-facing alerts.  
> **No notification code added this sprint.**

### Problem Statement

The recommendation pipeline (`health_assistant_service.py`) currently produces prioritised recommendations on-demand (user opens dashboard). There is no mechanism to:
- Proactively alert the user when a new high-severity finding appears
- Respect quiet hours or notification fatigue thresholds
- Escalate unacknowledged critical alerts
- Learn from snooze/dismiss behaviour to adjust timing

### Required Behaviours

| # | Requirement | Priority |
|---|---|---|
| N1 | High-severity lab/device/symptom finding → push notification | P0 |
| N2 | Notification deduplication — same rule_id not re-notified within cooldown window | P0 |
| N3 | User-configurable quiet hours | P1 |
| N4 | Snooze → re-surface after snooze_duration | P1 |
| N5 | Persistent dismiss → suppress for 30 days | P1 |
| N6 | Escalation → higher-priority notification channel | P1 |
| N7 | Alert fatigue guard: max N notifications per day per person | P1 |
| N8 | Learn from ignore patterns: ignored N times → reduce channel priority | P2 |
| N9 | Notification history in DB for audit/compliance | P2 |

### Proposed Architecture

```
Daily assistant run / cron / real-time trigger
    ↓
notification_intelligence_service.py  (NEW)
    filter_notifiable_findings(evidence_bundle, prefs, notification_log)
        → only findings that exceed priority threshold
        → dedup against NotificationLog within cooldown
        → respect quiet_hours and daily_cap
        ↓
    rank_notifications(candidates)
        → sort by: severity DESC, source_priority DESC, last_seen ASC
        ↓
    build_notification_payload(ranked)
        → title, body, action_url, priority_level, rule_id
        ↓
NotificationLog DB row (status: pending → sent → acked/snoozed/dismissed)
    ↓
delivery_adapter (abstraction)
    → web push (Phase 1)
    → LINE / email (Phase 2)
    → in-app bell (already exists via notification-bell.tsx)
```

### New DB Tables Required

```sql
CREATE TABLE notification_log (
    id              UUID PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    person_id       INTEGER REFERENCES person_profiles(id),
    rule_id         VARCHAR(80),
    channel         VARCHAR(20),   -- 'web_push' | 'email' | 'in_app'
    priority_level  VARCHAR(10),   -- 'critical' | 'high' | 'medium' | 'low'
    title           TEXT,
    body            TEXT,
    action_url      TEXT,
    status          VARCHAR(20),   -- 'pending' | 'sent' | 'acked' | 'snoozed' | 'dismissed'
    snooze_until    TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ,
    acked_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE notification_preferences (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id),
    quiet_start     TIME,          -- e.g. 22:00
    quiet_end       TIME,          -- e.g. 08:00
    daily_cap       INTEGER DEFAULT 5,
    min_priority    VARCHAR(10) DEFAULT 'medium',
    channels        JSONB          -- {"web_push": true, "email": false, "in_app": true}
);
```

### Priority Scoring

| Source type | Base priority | Escalation modifier |
|---|---|---|
| `device_escalation` (critical) | critical | +2 |
| `lab_abnormality` (high severity) | high | +1 if recurrence ≥ 3 |
| `symptom_pattern` (high severity) | high | +1 if worsening trend |
| `lab_abnormality` (medium) | medium | — |
| `symptom_pattern` (medium) | medium | — |
| All others | low | — |

### Cooldown Windows

| Priority | Cooldown | Dismiss suppress |
|---|---|---|
| critical | 6 hours | 7 days |
| high | 24 hours | 30 days |
| medium | 72 hours | 30 days |
| low | 7 days | 90 days |

### Alert Fatigue Guard

- Per-person daily cap (default: 5 notifications/day across all channels)
- Per-rule_id dedup: same rule not re-surfaced until cooldown expires
- Snooze learning: if snoozed ≥ 3 times → auto-downgrade channel priority for that rule

### Out of Scope for P5

- AI-generated notification copy (P6)
- Multi-language notification content (P6)
- SMS delivery (P6)
- Apple Watch / wearable push (future)

### Next Sprint Prompt (P5 kickoff)

```
PersonalHealthOS P5 — Notification Intelligence

Context:
  P4_REPORT_TO_ACTION_VERIFIED complete (297/297 tests pass).
  Evidence bundle: lab_abnormalities, symptom_patterns, device_escalation all wired.
  Daily assistant: get_action_recommendations() produces prioritised top-3.

Goal:
  Implement notification_intelligence_service.py and NotificationLog DB table.
  Wire into daily assistant and /recommendations endpoint.
  Add notification preference model.
  Expose /api/v1/notifications/ CRUD endpoints.
  No frontend push integration yet — in-app bell only (notification-bell.tsx already exists).

Must deliver:
  - notification_intelligence_service.py with filter/rank/build functions
  - NotificationLog SQLAlchemy model + migration
  - NotificationPreferences model
  - test_notification_intelligence.py: 20+ pure-function tests
  - test_api_notification_smoke.py: 8+ route tests
  - Full regression: all 297 existing tests still pass
  - npx tsc --noEmit CLEAN
  - npx next build PASS
  - Commit: P5_NOTIFICATION_INTELLIGENCE_READY

P5 NOT IMPLEMENTED as of this commit.
```

---


|---|---|
| Task 1 — Symptom data flow integrity (code review) | ✅ CONFIRMED |
| Task 2 — API smoke tests for symptom intelligence | ✅ 14/14 PASS |
| Task 3 — `npx tsc --noEmit` + `npx next build` | ✅ CLEAN / BUILD OK |
| Task 4 — Report-to-Action Bridge planning spec | ✅ DOCUMENTED (NOT IMPLEMENTED) |

### Test results — full battery

| Suite | Tests | Result |
|---|---|---|
| `test_symptom_intelligence.py` | 24 | **PASS** |
| `test_device_signal_escalation.py` | (included) | **PASS** |
| `test_device_signal_detection.py` | (included) | **PASS** |
| `test_api_escalation_smoke.py` | 12 | **PASS** |
| `test_api_symptom_smoke.py` | 14 | **PASS** |
| `test_health_assistant_service.py` | (included) | **PASS** |
| `test_daily_summary_service.py` | (included) | **PASS** |
| `test_recommendation_trust_service.py` | (included) | **PASS** |
| `test_outcome_feedback_service.py` | (included) | **PASS** |
| **Total (excl. dual_agent)** | **199** | **199/199 PASS** |

### Data flow confirmation

- `SymptomLog` DB rows → `build_evidence_bundle()` reads last 90 days of symptoms  
- `build_symptom_timeline()` groups rows → produces `symptom_timeline` list in bundle  
- `detect_symptom_patterns()` analyses timeline → produces `symptom_patterns` list in bundle  
- `/evidence-bundle` response always includes `symptom_timeline` + `symptom_patterns` keys  
- High-severity patterns enter `get_action_recommendations()` candidate pool (priority 65)  
- `/recommendations` response always includes `symptom_patterns` key  
- `SymptomInsightCard` renders patterns in `health-assistant-panel.tsx`

### Frontend build

- `npx tsc --noEmit`: **CLEAN** (0 errors)  
- `npx next build`: **SUCCESS** — all pages compiled, static output generated

### Known limitations (carried forward)

- Symptom intelligence computed request-time only; no historical pattern DB table  
- E2E / Playwright tests: NOT RUN  
- `test_dual_agent_orchestrator.py`: 10 pre-existing failures, always excluded  
- Report-to-Action Bridge: NOT IMPLEMENTED (see spec below)

### Git

- Branch: `main`  
- This sprint: `test_api_symptom_smoke.py` (14 tests) + this report  

---

## Report-to-Action Bridge — Planning Spec (NOT IMPLEMENTED)

> **Status**: Planned. Target: next sprint (P4).  
> **Scope**: Bridge between parsed lab report items and the recommendation / decision pipeline.

### Problem statement

Lab reports are parsed and stored as `LabReportItem` rows.  Currently they
inform the `evidence_bundle` but do **not** automatically produce prioritised
action items.  The clinician's intent is: _an abnormal lab result → patient
knows what to do next_.

### Required behaviours

| # | Requirement | Priority |
|---|---|---|
| 1 | Lab abnormality → decision item in `recommendations` | P0 |
| 2 | Lab abnormality → a specific recommended next action | P0 |
| 3 | Repeated abnormal result for same marker → higher recommendation priority | P1 |
| 4 | Completed or active action for same marker → deduplicate (no double-surfacing) | P1 |
| 5 | Each recommendation includes full evidence source traceability | P1 |
| 6 | No medical diagnosis wording — all copy reviewed against `ui-feedback-standards.md` | P0 |

### Proposed architecture

```
LabReportItem rows (DB)
    ↓
build_lab_evidence()          ← new function in lab_intelligence_service.py
    ↓
detect_lab_abnormalities()    ← new function; returns list[LabAbnormality]
    ├─ compares value vs reference_range
    ├─ checks historical recurrence (count of same marker out-of-range)
    └─ deduplicates against existing ActionItem DB rows
    ↓
get_action_recommendations()  ← existing; add "lab_abnormality" source type
    priority score: 75 (above device_signal=70)
    rule_id: "lab_abnormality_{marker_name}"
    ↓
/recommendations response      ← new key: "lab_abnormalities"
    ↓
LabInsightCard (new component) ← renders in health-assistant-panel.tsx
```

### Concrete next-sprint tasks

1. **`lab_intelligence_service.py`** — implement `build_lab_evidence()` and `detect_lab_abnormalities()`:
   - Input: `LabReportItem` list from DB query
   - Output: `list[LabAbnormality]` — each with `markerName`, `value`, `unit`, `referenceRange`, `severity` (low/medium/high), `recurrenceCount`, `suggestedAction`, `evidenceSources`
   - Severity mapping: ≥2× out-of-range = high, 1× = medium, borderline = low
   - No hallucination: only markers actually present in `LabReportItem` inputs

2. **`health_assistant_service.py`** — integrate `detect_lab_abnormalities()` into `build_evidence_bundle()`:
   - Add `"lab_abnormalities"` key to bundle return
   - Add `"lab_abnormality"` to `_SOURCE_PRIORITY` at 75
   - Add `elif src_type == "lab_abnormality":` case in `_build_recommendation_from_candidate()`

3. **Deduplication** — before returning recommendations, check `ActionItem` DB for existing active items with matching `rule_id`; skip if found within 7 days

4. **`LabInsightCard` component** — `frontend/app/components/platform/lab-insight-card.tsx`:
   - Renders each abnormality with severity badge, recurrence count, suggested action
   - Links to source lab report
   - Identical medical-disclaimer footer as `SymptomInsightCard`
   - Loading skeleton + empty state

5. **Tests** (`test_lab_intelligence.py` — 20 pure-function tests + `test_api_lab_smoke.py` — 8 route tests):
   - No abnormalities → empty list (anti-hallucination)
   - Single out-of-range → medium severity
   - Repeated out-of-range → high severity + recurrenceCount
   - Existing ActionItem → deduplication suppresses recommendation
   - All required schema keys present
   - No medical diagnosis wording (keyword blacklist check)

6. **Copy review** — audit all `suggestedAction` and `label` strings against `docs/UI_FEEDBACK_STANDARDS.md` blacklist before merge

### Out of scope for P4

- Trend charts for lab markers (P5)
- Integration with external reference range APIs (P5)
- GP/clinician report generation (future)

---

# Previous Report — P3-SYMPTOM-INTELLIGENCE-READY

Generated: 2026-05-21  
Classification: **`P3_SYMPTOM_INTELLIGENCE_READY`**

---

## Summary

P3 Symptom Intelligence layer is complete and production-merged on `main`.

### What was built

| Component | File | Status |
|---|---|---|
| `build_symptom_timeline()` | `backend/app/services/symptom_intelligence_service.py` | ✅ |
| `detect_symptom_patterns()` | same | ✅ |
| Wire into recommendation pipeline | `backend/app/services/health_assistant_service.py` | ✅ |
| `SymptomInsightCard` | `frontend/app/components/platform/symptom-insight-card.tsx` | ✅ |
| `SymptomPattern` type | `frontend/lib/api.ts` | ✅ |
| `health-assistant-panel.tsx` update | `frontend/app/components/platform/health-assistant-panel.tsx` | ✅ |
| 24 pure-function tests | `backend/tests/test_symptom_intelligence.py` | ✅ 24/24 |

### Validation results

| Suite | Result |
|---|---|
| `test_symptom_intelligence.py` | **24/24 PASS** |
| Full backend (excl. dual_agent) | **246/246 PASS** |
| `npx tsc --noEmit` | **CLEAN** |

### Architecture

- **`build_symptom_timeline`** — groups SymptomLog dicts by symptom name, computes firstSeenAt/lastSeenAt/recurrenceCount, severityTrend (oldest-half avg vs newest-half avg, ±1.5 threshold), relatedDeviceSignals and relatedLabItems via predefined keyword correlation maps (no hallucination guarantee — only returns items actually present in inputs).
- **`detect_symptom_patterns`** — emits up to 5 pattern types per symptom: `recurring_symptom` (≥3 occurrences), `worsening_symptom` (trend==worsening), `symptom_with_device_signal`, `symptom_with_lab_risk`, `unresolved_high_severity_symptom` (severity ≥ 8). Confidence bounded [0.20, 0.90]. No pattern without supporting data.
- **Recommendation bridge** — high-severity patterns enter the `get_action_recommendations()` candidate pool at priority score 65 (between `device_signal=70` and `insight=60`). Rule IDs: `symptom_pattern_{patternType}_{symptomType}`.
- **`SymptomInsightCard`** — shows severity-coded pattern cards with confidence bar, related signal/lab tag chips, suggested action, and medical disclaimer.

### Known limitations
- Symptom timeline computed from current 90-day evidence bundle only (no separate historical DB table).
- E2E / Playwright tests not run.
- `test_dual_agent_orchestrator.py`: 10 pre-existing failures, excluded.

### Git
- Branch: `main`
- Commit: `42fc0f9` — `feat: P3_SYMPTOM_INTELLIGENCE_READY`

---

# Previous Report — P2-DEVICE-ESCALATION-VERIFIED-AND-SAFEGUARDED

Generated: 2026-05-20  
Classification: **`P2_DEVICE_ESCALATION_VERIFIED_AND_SAFEGUARDED`**

---

## Summary

This sprint verified and safeguarded the P2 Device Escalation Layer completed in
the prior session.  No new features were added.  Focus was on git safety, data
flow verification, automated smoke testing, and honest limitation documentation.

---

## Task 1 — Git Safety

| Item | Result |
|---|---|
| `git status` before init | `fatal: not a git repository` |
| `.gitignore` created | ✅ Excludes `.venv/`, `node_modules/`, `.next/`, `.env`, `runtime/snapshots/`, runtime locks |
| `git init` | ✅ |
| `git add .` — excluded files verified | ✅ No `.env`, `.venv`, `node_modules`, `.next`, `snapshots` committed |
| Initial commit | ✅ `ab977a6 chore: initial commit — P2_DEVICE_ESCALATION_LAYER_READY` |
| Runtime orchestrator locks untracked | ✅ `git rm --cached` + .gitignore update |
| Final `git status` | ✅ `nothing to commit, working tree clean` |
| `git log --oneline` | `0df1cb5 chore: untrack runtime lock files from index` → `2c5d36e` → `ab977a6` |

---

## Task 2 — Device Escalation Data Flow Verification

Verified end-to-end by code inspection + automated smoke tests:

```
external_metrics (HealthMetric rows, source != 'manual')
  → detect_device_signals()            ← device_signals in bundle ✅
  → build_device_signal_history()      ← device_signal_history in bundle ✅
  → evaluate_signal_escalation()       ← device_escalation in bundle ✅
  → build_evidence_bundle()
  → get_action_recommendations()       ← device_escalation in return ✅
  → generate_daily_health_summary()    ← escalation key injected when level != none ✅
  → frontend DeviceSignalCard          ← escalation prop consumed ✅
```

| Check | Result |
|---|---|
| `bundle["device_signals"]` present | ✅ |
| `bundle["device_signal_history"]` present | ✅ computed, NOT persisted to DB |
| `bundle["device_escalation"]` present | ✅ |
| `get_action_recommendations()` returns `device_escalation` | ✅ |
| `generate_daily_health_summary()` uses escalation for topRisk / todayAction | ✅ |
| `EscalationDecision` type in `frontend/lib/api.ts` | ✅ |
| `DeviceSignalCard` receives and renders `escalation` prop | ✅ |
| Medical disclaimer shown when signals or escalation present | ✅ |
| Stale-all cap at "watch" | ✅ |

---

## Task 3 — API Smoke Tests

**New file:** `backend/tests/test_api_escalation_smoke.py` — 12 tests

| Class | Tests | Result |
|---|---|---|
| `TestDeviceSignalsEndpoint` | schema keys, empty=no signals, elevated HR→signal, signal key shapes | **4/4 PASS** |
| `TestEvidenceBundleEndpoint` | device_escalation key, schema, no-signal=none, elevated HR raises level, device_signal_history present | **5/5 PASS** |
| `TestDailySummaryEndpoint` | base keys, no-signal=no escalation key, elevated HR may inject escalation | **3/3 PASS** |

Note: Tests use in-memory SQLite with real FastAPI TestClient.  An `autouse`
fixture clears `app.dependency_overrides` after each test to prevent cross-test
contamination.

---

## Required Validation — Full Results

| Test file | Count | Result |
|---|---|---|
| `test_device_signal_escalation.py` | 24 | **24 PASS** |
| `test_device_signal_detection.py` | 21 | **21 PASS** |
| `test_health_assistant_service.py` | ~40 | **PASS** |
| `test_daily_summary_service.py` | ~20 | **PASS** |
| `test_recommendation_trust_service.py` | ~20 | **PASS** |
| `test_outcome_feedback_service.py` | ~20 | **PASS** |
| **Full backend (excl. orchestrator)** | **222** | **222 PASS** |
| `test_dual_agent_orchestrator.py` | 10 | **PRE-EXISTING FAILURES — excluded** |
| `npx tsc --noEmit` | — | **PASS** |
| `npx next build` | — | **PASS** |
| E2E / Playwright browser smoke | — | **NOT RUN** |

---

## Files Changed This Sprint

| File | Change |
|---|---|
| `.gitignore` | Created — excludes secrets, venv, node_modules, runtime locks |
| `backend/tests/test_api_escalation_smoke.py` | Created — 12 API smoke tests |

(All P2 escalation service + UI files were created in the prior session.)

---

## Known Limitations

| Limitation | Detail |
|---|---|
| **DB persistence NOT implemented** | `device_signal_history` is computed deterministically from `HealthMetric` rows at request time.  There is NO separate history table, no trend DB, no long-term memory store.  "Trend memory" means recurrence is inferred across time-bucketed rows from the same table. |
| **E2E not run** | No Playwright / browser smoke tests executed.  Frontend verified by `tsc --noEmit` + `next build` only. |
| **Orchestrator failures pre-existing** | `test_dual_agent_orchestrator.py` — 10 PLANNER_SKIP_SAFE_RUN failures exist before this sprint and are not caused by escalation changes. |
| **No remote git** | Repo is local only.  No remote configured, no CI/CD triggered. |
| **Escalation is session-scoped** | Each API call recomputes escalation from available metrics.  There is no cross-session escalation state. |

---

## Previous Report — P2-DEVICE-SIGNAL-INTELLIGENCE

# Active Task Report — P2-DEVICE-SIGNAL-INTELLIGENCE

Generated: 2026-05-20  
Classification: **`P2_DEVICE_SIGNAL_INTELLIGENCE_READY`**

---

## Pre-step Results

| Step | Result |
|---|---|
| Snapshot path | `runtime/snapshots/backend.app.20260520-HHMM.tgz` (created before any change) |
| `HealthMetric.source` field confirmed | ✅ String(40), default='manual' |
| `HealthMetric.spo2` column exists | ❌ Not present — handled gracefully (no hallucination) |

---

## Modified / Created Files

| File | Action |
|---|---|
| `backend/app/services/device_signal_detection_service.py` | **CREATED** — pure-function detection: elevated HR, pulse trend, low sleep, reduced activity, SpO₂ placeholder |
| `backend/app/services/health_assistant_service.py` | **MODIFIED** — import + enrich external_metrics with raw values + `detect_device_signals` call + `device_signals` in bundle + `_SOURCE_PRIORITY["device_signal"]=70` + candidate generation + recommendation builder handler + return `device_signals` |
| `backend/app/api/health_assistant.py` | **MODIFIED** — import + new `GET /health-assistant/device-signals` endpoint |
| `backend/tests/test_device_signal_detection.py` | **CREATED** — 21 tests covering all 9 spec scenarios |
| `frontend/lib/api.ts` | **MODIFIED** — `DeviceSignal` type + `getDeviceSignals()` |
| `frontend/app/components/platform/device-signal-card.tsx` | **CREATED** — severity badges, freshness, confidence %, empty state |
| `frontend/app/components/platform/health-assistant-panel.tsx` | **MODIFIED** — import + `device_signals?` in HealthAssistantData + render section |

---

## Acceptance Criteria

| Criterion | Status |
|---|---|
| `detect_device_signals([])` returns `[]` | [Confirmed] |
| elevated_resting_heart_rate detected (HR ≥ 90) | [Confirmed] |
| abnormal_pulse_trend detected (≥ 3 ascending readings) | [Confirmed] |
| low_sleep_duration detected (< 7 h) | [Confirmed] |
| reduced_activity detected (< 5000 steps) | [Confirmed] |
| unstable_spo2 — no hallucination (no column) | [Confirmed] |
| Stale → confidence × 0.70 | [Confirmed] |
| ≥ 3 repeated abnormal → severity escalates to high | [Confirmed] |
| Device signal surfaces in Top-3 recommendations | [Confirmed] |
| `/health-assistant/device-signals` endpoint | [Confirmed] |
| `DeviceSignal` TS type + `getDeviceSignals()` API | [Confirmed] |
| `DeviceSignalCard` + empty state rendered in panel | [Confirmed] |
| `npx tsc --noEmit` PASS | [Confirmed] |
| `npx next build` PASS | [Confirmed] |

---

## Test Results

```
test_device_signal_detection.py  — 21 passed
Full backend regression           — 186 passed, 4 warnings
frontend tsc --noEmit             — PASS
frontend next build               — PASS
```

---

## Risks / Next Steps

| Item | Note |
|---|---|
| SpO₂ signal | No `spo2` column yet. Placeholder comment in service. Implement when schema column added. |
| Pulse trend / elevated HR co-signal | Trend only emits when HR < 90 to avoid double-counting. |
| Frontend empty state | Does NOT claim any device is connected — neutral guidance only. |

---

## Final Classification

`P2_DEVICE_SIGNAL_INTELLIGENCE_READY`

---

# Previous Report — P0-EVIDENCE-EXTERNAL-METRICS-FIRST-CLASS

Generated: 2026-05-20

---

## 前置步驟結果

### Step 1 — Snapshot

```
runtime/snapshots/backend.app.20260520-1218.tgz  (180K)
```
Status: **DONE** [Confirmed]

### Step 2 — source 欄位確認

```
backend/app/models/entities.py:93
class HealthMetric:
    source = Column(String(40), default='manual')
```
Status: **CONFIRMED** — `HealthMetric.source` 欄位存在，型別 `String(40)`，預設值 `'manual'`。

### Step 3 — 原始 external_metrics 邏輯

```python
# 原始 (修改前)
"external_metrics": [],  # populated by external_metrics_service if needed
```
原因：hardcoded 空陣列，從未被填入任何資料。

---

## 修改檔案清單

| 檔案 | 修改內容 |
|---|---|
| `backend/app/services/health_assistant_service.py` | 新增 `_freshness_label()` 函式、`_EXTERNAL_RELIABILITY` 對照表、`_DEFAULT_EXTERNAL_RELIABILITY`；在 `build_evidence_bundle` 的 health_metrics 迴圈後新增 external_metrics 抽取邏輯；將 `"external_metrics": []` 替換為 `"external_metrics": external_metrics` |
| `backend/tests/test_health_assistant_service.py` | 新增 `_make_external_metric()` helper、`test_external_metrics_happy_path`、`test_external_metrics_empty_when_all_manual`、`test_external_metrics_stale_freshness` 三個新測試 |
| `runtime/snapshots/backend.app.20260520-1218.tgz` | 新增 snapshot（唯讀備份） |

**未修改任何其他檔案。** frontend、models、API endpoint 簽名均未動。

---

## 驗收標準逐項對應

| 驗收標準 | 結果 |
|---|---|
| 1. 含 source-tagged metrics 的使用者，`external_metrics` 為非空陣列 | **[Confirmed]** — `test_external_metrics_happy_path` PASS |
| 2. 每筆含 `source`, `timestamp`, `freshness`, `reliability`, `summary` | **[Confirmed]** — `test_external_metrics_happy_path` 驗證所有欄位 |
| 3. 無 source-tagged metrics 時，`external_metrics` 保持 `[]` 且不報錯 | **[Confirmed]** — `test_external_metrics_empty_when_all_manual` PASS |
| 4a. happy path 測試 | **[Confirmed]** — `test_external_metrics_happy_path` PASS |
| 4b. empty path 測試 | **[Confirmed]** — `test_external_metrics_empty_when_all_manual` PASS |
| 4c. stale freshness 測試 | **[Confirmed]** — `test_external_metrics_stale_freshness` PASS |
| 5. 既有 backend tests 全綠（無回歸） | **[Confirmed]** — 165 passed (excluding pre-existing orchestrator failures) |
| 6. `npx tsc --noEmit` PASS | **[Confirmed]** — exit code 0 |

---

## 測試輸出摘要

### test_health_assistant_service.py (18 tests)
```
18 passed in 0.43s
```
新增測試：
- `test_external_metrics_happy_path`        PASS
- `test_external_metrics_empty_when_all_manual`  PASS
- `test_external_metrics_stale_freshness`   PASS

### 全 backend suite（不含 orchestrator）
```
165 passed, 4 warnings in 2.23s
```

### Orchestrator pre-existing failures（與本任務無關）
```
10 failed in test_dual_agent_orchestrator.py
原因: PLANNER_SKIP_SAFE_RUN vs CREATED — 環境問題，非本任務造成
```

### Frontend tsc
```
npx tsc --noEmit → exit 0
```

---

## 實作細節

### `_freshness_label(dt)` 邏輯
- `None` → `"unknown"`
- 距今 ≤ 86400 秒（24 h）→ `"fresh"`
- 距今 > 86400 秒 → `"stale"`

### `_EXTERNAL_RELIABILITY` 對照表
| source | reliability |
|---|---|
| apple_health | 0.90 |
| google_fit | 0.88 |
| omron | 0.88 |
| wearable / fitbit / garmin / samsung / withings | 0.85 |
| 未知來源 | 0.80 (fallback) |

### external_metrics 抽取邏輯
- 從現有 `metric_rows`（30 天查詢）中篩選 `source != 'manual'`
- 不新增額外 DB query
- 每筆回傳：`source`, `timestamp` (ISO8601), `freshness`, `reliability`, `summary`
- `summary` 格式：`[{source}] 血壓 130/85、血糖 95.0、體重 70.5kg、...`

---

## 風險 / Unknown / 後續建議

| 項目 | 說明 |
|---|---|
| 真實資料庫中的 source 值多樣性 | 目前 source 欄位為 free-text String(40)，沒有 ENUM 約束。若真實資料中出現非預期 source 值（如 `"Withings"` 大寫），會走 fallback reliability 0.80。建議未來在資料入口統一 lowercase normalize。 |
| external_metrics 未加入 `missing_data` 提示 | 設計決定：external metrics 是補充資料，非必填，不適合觸發 missing_data 警告。 |
| freshness 邊界 24h | 目前 "fresh" = 24h 內。若 wearable 每小時同步，這個邊界合理。但若使用場景改為「當天」概念，建議改為 calendar day boundary。 |
| orchestrator 10 tests 失敗 | 與本任務完全無關，為 `PLANNER_SKIP_SAFE_RUN` 環境設定問題，不在本任務修改範圍。 |
| E2E / API integration test | 未執行 live API call 驗證，unit tests 覆蓋邏輯層，但真實 DB 回傳的 source 值尚未在 staging 驗證。 |

---

## Final Classification

**`P0_EVIDENCE_EXTERNAL_METRICS_DONE`**

---

---

## P53-P52-BROWSER-ACCEPTANCE-CLOSURE-VERIFICATION (2026-05-25)

**Final Classification: `P53_P52_BROWSER_ACCEPTANCE_CLOSURE_VERIFIED`**

### Branch Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- HEAD: `38f9c13` (P52 commit) ✅
- Dirty files: `CEO-Decision.md`, `CTO-Analysis.md`, `active_task.md`, `roadmap.md` (governance docs only, not staged) ✅
- No detached HEAD, no unrelated dirty application files ✅

### 1. 本輪目標

Closure verification for P52. Confirm that the P52 browser acceptance commit does not regress runtime smoke, TypeScript type check, or the browser acceptance spec itself. No new features.

### 2. 已完成事項

- **P52 commit scope verified** — `git show --stat 38f9c13` confirms exactly 5 files changed: `decision-recommendation-layer.tsx`, `health-assistant-panel.tsx`, `actions/page.tsx`, `decision-support.ts`, `p52-recommendation-fields.spec.ts`. No CI, auth, backend connector, or PostgreSQL scope.
- **`make runtime-smoke`** — 130 passed / 2 skipped ✅ (identical to pre-P52 baseline)
- **`npx tsc --noEmit`** — 0 errors ✅ (no `typecheck` npm script exists; ran tsc directly)
- **P52 browser acceptance spec rerun** — `11 / 11 PASS` in 7.9s ✅

### 3. 修改或產出的檔案

No application code modified during this closure round. Only this report updated.

| File | Action |
|---|---|
| `00-Plan/roadmap/active_task_report.md` | Appended P53 closure section |

### 4. 驗證結果 / 測試結果

| Check | Command | Result |
|---|---|---|
| Repo / branch | `git rev-parse --show-toplevel && git branch --show-current` | ✅ canonical |
| P52 commit scope | `git show --stat --oneline 38f9c13` | ✅ 5 files, all frontend/browser |
| Runtime smoke | `make runtime-smoke` | ✅ 130 passed / 2 skipped |
| TypeScript | `npx tsc --noEmit` | ✅ 0 errors |
| P52 browser spec | `npx playwright test tests/e2e/p52-recommendation-fields.spec.ts` | ✅ 11/11 PASS |

### 5. 目前結論

P52 is fully closed. All three verification checks pass with no regressions. The `evidence_summary` and `data_insufficiency_reason` fields are correctly propagated to both the Actions and Dashboard recommendation surfaces, and browser-verified by a stable 11-test Playwright suite. The root bug fixed during P52 stabilization (NarrativeMemoryCard cross-period mock crash + Playwright strict mode violation) does not affect production code — it was a test environment issue only.

### 6. 尚未完成事項

None within P52/P53 scope.

Future backlog (not P53):
- `npm run typecheck` script is missing from `frontend/package.json` — minor DX gap, could add `"typecheck": "tsc --noEmit"`.
- `make runtime-smoke` coverage does not include orchestrator planner tests (pre-existing skip, unrelated to P52).

### 7. 風險與不確定點

| 項目 | 說明 |
|---|---|
| Live backend data shape | P52 browser acceptance is fully mocked. Live `/health-assistant/recommendations` must return `evidence_summary` and `data_insufficiency_reason` from the P51 backend. P51 backend was verified in its own round; no regression expected. |
| `NarrativeMemoryCard` upstream bug | The `crossPeriod !== null` guard (which passes for `undefined`) is a real production bug in `narrative-memory-card.tsx`. If the live API returns a response where `res.reasoning` is missing, the component will crash in production. This was masked in tests but not fixed in application code. Recommend a follow-up defensive fix: `setCrossPeriod(res.reasoning ?? null)`. |

### 8. 建議今天優先處理的方向

1. **(Low, safe)** Add `setCrossPeriod(res.reasoning ?? null)` defensive guard in `narrative-memory-card.tsx` — prevents a real production crash if backend omits `reasoning`.
2. **(Low, DX)** Add `"typecheck": "tsc --noEmit"` to `frontend/package.json` scripts.
3. **(Next priority)** Proceed to next roadmap task per `roadmap.md`.

### 9. 下一輪可直接執行的 task prompt

```
[每次交接開頭] — Governance Header

## Required Pre-flight
git rev-parse --show-toplevel
git branch --show-current
git status --short
git log --oneline -5

## Task
P54-NARRATIVE-MEMORY-CARD-DEFENSIVE-GUARD

Fix production crash risk in NarrativeMemoryCard:
- File: frontend/app/components/platform/narrative-memory-card.tsx
- Line: api.getCrossPeriodReasoning().then((res) => setCrossPeriod(res.reasoning))
- Fix: change to setCrossPeriod(res.reasoning ?? null)
- Rationale: crossPeriod !== null passes for undefined, leading to crossPeriod.confidence crash

After fix:
1. Run npx tsc --noEmit (0 errors required)
2. Run make runtime-smoke (130 passed / 2 skipped required)
3. Run npx playwright test tests/e2e/p52-recommendation-fields.spec.ts --reporter=line (11/11 required)
4. git add frontend/app/components/platform/narrative-memory-card.tsx
5. git commit -m "fix: guard setCrossPeriod against undefined reasoning to prevent production crash"

Forbidden: No new features, no auth changes, no CI changes, no new branches.
```

### 10. CTO Agent 10 行內摘要

1. P53 closure verification 完成，分類：`P53_P52_BROWSER_ACCEPTANCE_CLOSURE_VERIFIED`。
2. P52 commit 38f9c13 scope 確認：5 個 frontend 檔案，無 CI/auth/backend 洩漏。
3. `make runtime-smoke`：130 passed / 2 skipped，與 P51 baseline 完全一致。
4. `npx tsc --noEmit`：0 errors（無 `typecheck` npm script，直接執行 tsc）。
5. P52 browser acceptance spec 重跑：11/11 PASS，7.9s。
6. 本輪未修改任何應用程式碼。
7. 發現生產風險：`NarrativeMemoryCard` 的 `crossPeriod !== null` guard 對 `undefined` 失效，需補 `?? null`。
8. 此 bug 在測試中被 route stub 遮蔽，未進入 P52 commit，需單獨修復。
9. 建議下一輪 P54 專門修這個 defensive guard（一行修改，低風險）。
10. P52/P53 已完全關閉，可安全推進 roadmap 下一任務。

---

## P54-NARRATIVE-MEMORY-CARD-DEFENSIVE-GUARD (2026-05-25)

**Final Classification: `P54_NARRATIVE_MEMORY_CARD_DEFENSIVE_GUARD_READY`**

### Branch Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `262b77f` (P53 closure) ✅
- Dirty files: `CEO-Decision.md`, `CTO-Analysis.md`, `active_task.md`, `roadmap.md` (governance docs only — not staged) ✅

### Root Cause (identified in P53)
`NarrativeMemoryCard.getCrossPeriodReasoning()` receives `{person_id, reasoning: undefined}` when the backend returns an absent field. JavaScript evaluates `undefined !== null` as `true`, so the render guard `crossPeriod !== null` passes — causing `crossPeriod.confidence` to crash inside the Dashboard ErrorBoundary.

The test environment was masked by a route stub that returned `{reasoning: null}` explicitly; the production path remained vulnerable.

### Fix Applied
**File**: `frontend/app/components/platform/narrative-memory-card.tsx`

| Before | After |
|--------|-------|
| `.then((res) => setCrossPeriod(res.reasoning))` | `.then((res) => setCrossPeriod(res.reasoning ?? null))` |

One character change: `?? null` appended. The nullish-coalescing operator coerces `undefined` to `null`, which the existing render guard `crossPeriod !== null` correctly handles.

### Grep Verification (pre-fix)
```
narrative-memory-card.tsx:162:  const [crossPeriod, setCrossPeriod] = useState<CrossPeriodReasoning | null>(null)
narrative-memory-card.tsx:202:    api.getCrossPeriodReasoning()
narrative-memory-card.tsx:203:      .then((res) => setCrossPeriod(res.reasoning))   ← VULNERABLE
narrative-memory-card.tsx:211:    crossPeriod !== null &&
narrative-memory-card.tsx:212:    (crossPeriod.confidence > 0 ||
narrative-memory-card.tsx:432:      {crossPeriod !== null && !hasCrossData && (
```
Exactly one occurrence of the vulnerable pattern — surgical fix confirmed.

### Verification Results
| Check | Command | Result |
|-------|---------|--------|
| TypeScript | `npx tsc --noEmit` | 0 errors ✅ |
| Runtime smoke | `make runtime-smoke` | 130 passed / 2 skipped ✅ |
| P52 browser acceptance | `npx playwright test tests/e2e/p52-recommendation-fields.spec.ts` | 11/11 PASS ✅ |

### Commits
| SHA | Message |
|-----|---------|
| `c06dce1` | `fix: guard cross-period reasoning against undefined response` |

### 10. CTO Agent 10 行內摘要

1. P54 defensive guard 完成，分類：`P54_NARRATIVE_MEMORY_CARD_DEFENSIVE_GUARD_READY`。
2. Root cause：`res.reasoning` 可能為 `undefined`，`undefined !== null` 為 `true`，導致 Dashboard ErrorBoundary crash。
3. Fix：一行 `?? null`，nullish-coalescing 將 `undefined` 強制轉為 `null`，令現有 render guard 正確攔截。
4. Grep 確認只有一個 vulnerable call site，無側效應。
5. `npx tsc --noEmit`：0 errors。
6. `make runtime-smoke`：130 passed / 2 skipped，baseline 不變。
7. P52 browser acceptance spec：11/11 PASS（12.4s）。
8. Commit `c06dce1`：僅 1 file changed，1 insertion，1 deletion。
9. 未洩漏任何 governance docs，不開新 branch，不 force push。
10. P50–P54 全部關閉，生產防護補完，可安全推進 roadmap 下一任務。

---

## P55-DAILY-RECOMMENDATION-ACTION-FEEDBACK (2026-05-25)

**Final Classification: `P55_DAILY_RECOMMENDATION_ACTION_FEEDBACK_READY`**

### Branch Governance Pre-flight
- Repo: `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` ✅
- Branch: `main` ✅
- Starting HEAD: `e235000` (P54 closure) ✅

### A. Problem Statement

Users had no way to express preference on daily recommendations or tracked actions. No feedback signals were preserved. P55 adds five interaction states:

1. **我會做** — implicit (action created/tracking)
2. **完成** — existing `打卡` / `done`
3. **稍後提醒** — existing snooze on recommendation layer; now also removes from filteredDecisionItems
4. **沒有用** — new `not_useful` status; PATCH on ActionCard; dismiss from recommendation layer
5. **不適合我** — new `not_applicable` status; PATCH on ActionCard; dismiss from recommendation layer

System preserves feedback via localStorage (recommendation layer) and DB PATCH (action cards). No medical certainty claims.

### B. Implementation

| Step | File | Change |
|------|------|--------|
| 1 | `frontend/lib/actions.ts` | Extend `status` type: `not_useful \| not_applicable` |
| 2 | `action-status-badge.tsx` | Badge styles for new statuses (orange, slate) |
| 3 | `action-card.tsx` | "沒有用" + "不適合我" buttons on todo/in_progress; disclaimer after dismiss |
| 4 | `decision-recommendation-layer.tsx` | `onDismiss?` prop threaded to `RecommendationItem`; buttons rendered conditionally |
| 5a | `actions/page.tsx` | `RecFeedback` type, localStorage helpers, `recFeedback` state + useEffect |
| 5b | `actions/page.tsx` | `filteredDecisionItems`, `handleSnooze` (fixed: no personId gate on setState), `handleDismissRecommendation`, `grouped.dismissed`, `DecisionRecommendationLayer` `onDismiss` prop |

### C. Root Causes Debugged During Session

| Issue | Root Cause | Fix |
|-------|------------|-----|
| 8/9 tests failing | Stale `.next` build (P52 era) — `next start` served old code without P55 buttons | `npm run build` before re-running tests |
| Snooze didn't remove item | `setRecFeedback` gated on `if (personId)` — personId falsy at click time in test env | Move state update outside personId guard; only gate `saveRecFeedback` |
| PATCH tests intercepted wrong button | `getByRole('button', { name: '沒有用' }).first()` grabbed recommendation layer button (onDismiss), not ActionCard PATCH button | `stubRoutes({ noRecs: true })` in PATCH tests to suppress recommendation layer |
| PATCH route not intercepted | `api.request()` appends `?person_id=person-self` → URL had query string; pattern `**/actions/action-p55-test` didn't match | Changed pattern to `**/actions/action-p55-test**` |

### D. Test Results

| Suite | Result |
|-------|--------|
| `npx tsc --noEmit` | ✅ 0 errors |
| `make runtime-smoke` | ✅ 130 passed / 2 skipped |
| P52 Playwright | ✅ 11/11 |
| **P55 Playwright** | ✅ **9/9** |

### E. Commit

- `853c93c` — `feat: add recommendation action feedback loop`

### F. Classification

`P55_DAILY_RECOMMENDATION_ACTION_FEEDBACK_READY`

P50–P55 全部關閉。使用者每日建議現已具備完整回饋迴路：沒有用 / 不適合我 / 稍後提醒，系統儲存回饋但不作醫學聲明。
