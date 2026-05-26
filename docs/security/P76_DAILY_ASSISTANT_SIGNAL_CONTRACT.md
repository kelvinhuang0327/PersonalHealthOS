# P76 Daily Assistant Signal Contract

**Version**: P76 (2026-05-26)  
**Scope**: Dashboard Daily Assistant Entry component only  
**Component**: `frontend/app/components/platform/daily-assistant-entry.tsx`  
**Status**: Active — do not remove or rename listed test ids without updating this document and the P76 contract test.

---

## 1. Purpose

After P64–P75, the Daily Assistant section of the dashboard exposes **11 stable test ids** covering loading, empty, and loaded states.
This document records the _frontend signal contract_: which ids exist, what data conditions produce them, and which regression spec protects each one.

It serves as a guard against:
- Silent renames of `data-testid` attributes during refactors
- Removal of optional signals without audit
- New logic conditions that bypass existing render guards
- Incorrect medical framing in copy (see Invariants)

This is **not** a backend API contract. No backend or API changes were made in P76.

---

## 2. Scope

| In scope | Out of scope |
|---|---|
| `daily-assistant-entry.tsx` test ids | `backend/app/**` |
| Loading / empty / loaded signal state | API schema changes |
| Conditional signal guards | Other dashboard components |
| P76 contract test | New dependencies |
| This document | New backend endpoints |

---

## 3. Component Signal Model

The component has three mutually exclusive top-level states:

```
┌─────────────────────────────────────────────────────────────────┐
│  isFullyLoading === true                                        │
│  → daily-assistant-loading (skeleton)                           │
├─────────────────────────────────────────────────────────────────┤
│  isFullyLoading === false                                       │
│  ├── hasDailySummary || topRec → 3-card grid                   │
│  │   (loaded state — optional signals may appear)              │
│  └── !hasDailySummary && !topRec → daily-summary-empty         │
└─────────────────────────────────────────────────────────────────┘
```

**Derived values (component source)**:
```typescript
const hasDailySummary = !!(summary?.topRisk || summary?.biggestChange || summary?.todayAction)
const isFullyLoading  = loading || sumLoading
const topRec          = data?.recommendations?.[0] ?? null
const missingItems    = (data?.missing_data ?? []).filter(m => !TRIVIAL_MISSING.has(m))
const hasFeedback     = fbSummary && fbSummary.total_count > 0
```

---

## 4. Stable Test Id Table

| test id | Phase | User-visible meaning | Data condition (render guard) | Required / Optional | Regression spec |
|---|---|---|---|---|---|
| `daily-assistant-entry` | baseline | Card root container | Always rendered | **required** | p64–p76 all specs |
| `daily-assistant-loading` | P74 | Loading skeleton (3 skeleton cards) | `isFullyLoading === true` (`loading prop \|\| sumLoading`) | **required** (during load) | `p74-daily-assistant-loading-state.spec.ts` |
| `daily-summary-empty` | baseline | "今日摘要尚未生成" empty state | `!hasDailySummary && !topRec` | **required** (when no data) | `p75-daily-assistant-empty-state.spec.ts` |
| `daily-summary-why-now` | P65 | "為什麼重要" copy under topRisk card | `summary?.whyNow` truthy | optional | `p65-daily-assistant-why-now-clarity.spec.ts` |
| `daily-summary-biggest-change-context` | P69 | "近 7 天最顯著趨勢" context copy | `summary?.biggestChange` truthy | optional | `p69-daily-assistant-biggest-change-context.spec.ts` |
| `daily-summary-action-impact` | P67 | Tracking continuity copy under todayAction card | `summary?.todayAction` truthy | optional | `p67-daily-assistant-action-impact-clarity.spec.ts` |
| `daily-summary-confidence-signal` | P70 | Confidence percentage pill | `typeof summary?.confidence === 'number' && summary.confidence > 0` | optional | `p70-daily-assistant-confidence-signal.spec.ts` |
| `daily-summary-encouragement` | P71 | 小助手鼓勵 message block | `typeof summary?.encouragement === 'string' && summary.encouragement.trim().length > 0` | optional | `p71-daily-assistant-encouragement.spec.ts` |
| `daily-summary-escalation-notice` | P72 | Amber escalation/watch/warning banner | `summary?.escalation != null && summary.escalation.escalationLevel !== 'none'` | optional | `p72-daily-assistant-escalation-notice.spec.ts` |
| `daily-summary-missing-data-explanation` | P66 | Explanation copy inside missing-data block | `missingItems.length > 0` (non-trivial missing data) | optional | `p66-daily-assistant-missing-data-explanation.spec.ts` |
| `daily-summary-outcome-improved-badge` | P68 | "已改善 N 項" badge in outcome section | `hasFeedback && fbSummary.improved_count > 0` | optional | `p68-daily-assistant-outcome-badge.spec.ts` |
| `daily-summary-next-checkin` | P73 | Next check-in suggestion text | `trust?.nextCheckInSuggestion \|\| summary` (non-null) | optional* | `p73-daily-assistant-next-checkin.spec.ts` |

> *`daily-summary-next-checkin` renders whenever the component is in the loaded state and either `trust.nextCheckInSuggestion` is set or `summary` is non-null. In practice it is visible in almost all loaded states.

**Additional context ids** (not covered in this contract table but present in component):

| test id | Notes |
|---|---|
| `daily-summary-top-risk` | Grid card, always visible in loaded state if `hasDailySummary \|\| topRec` |
| `daily-summary-biggest-change` | Grid card, same condition |
| `daily-summary-next-action` | Grid card, same condition |
| `daily-summary-outcome-section` | Visible when `hasFeedback === true` |
| `daily-summary-missing-data` | Visible when `missingItems.length > 0`; co-renders with `daily-summary-missing-data-explanation` |
| `daily-summary-outcome-unknown` | Visible when `tracking_count > 0 || insufficient_data_count > 0` |

---

## 5. Invariants

The following invariants MUST hold across all future changes to `daily-assistant-entry.tsx`:

### 5.1 State exclusivity
- `daily-assistant-loading` and `daily-summary-empty` MUST NOT be visible at the same time.
- `daily-assistant-loading` and any loaded-state signal MUST NOT be visible at the same time.
- `daily-summary-empty` MUST NOT be visible when `hasDailySummary === true` OR `topRec !== null`.

### 5.2 Empty state guard
- Empty state MUST only render when **both** `hasDailySummary === false` AND `topRec === null`.
- If a top recommendation exists (even with no summary), the 3-card grid renders instead.

### 5.3 Optional signals: absent when source is absent/empty/zero/none
- `daily-summary-why-now` MUST be hidden when `summary.whyNow` is falsy or absent.
- `daily-summary-biggest-change-context` MUST be hidden when `summary.biggestChange` is falsy.
- `daily-summary-action-impact` MUST be hidden when `summary.todayAction` is falsy.
- `daily-summary-confidence-signal` MUST be hidden when `confidence === 0` or absent.
- `daily-summary-encouragement` MUST be hidden when `encouragement` is absent, empty, or whitespace.
- `daily-summary-escalation-notice` MUST be hidden when `escalation` is null/undefined OR `escalationLevel === 'none'`. Do NOT use a `should_escalate` boolean.
- `daily-summary-missing-data-explanation` MUST be hidden when `missing_data` is empty or contains only TRIVIAL_MISSING items.
- `daily-summary-outcome-improved-badge` MUST be hidden when `improved_count === 0` or `total_count === 0`.

### 5.4 Escalation level source
- Escalation MUST use `escalationLevel` field (values: `'none'`, `'watch'`, `'warning'`, `'urgent'`).
- Do NOT invent a `should_escalate` boolean or any other escalation trigger field.

### 5.5 Medical framing
- No signal MUST imply medical diagnosis, treatment certainty, or clinical confirmation.
- Copy that reads "已改善" refers to user-reported feedback, not clinical outcomes.
- The disclaimer "這是使用者回饋，不是醫療效果證明" must remain in the outcome section.

### 5.6 Naming conventions
- Card-level test ids use prefix `daily-assistant-` (e.g. `daily-assistant-entry`, `daily-assistant-loading`).
- Intra-card signal test ids use prefix `daily-summary-` (e.g. `daily-summary-why-now`).
- Do not mix prefixes within a new signal without updating this document.

---

## 6. Validation Commands

### P64–P76 full regression
```bash
cd frontend && npx playwright test \
  tests/e2e/p76-daily-assistant-signal-contract.spec.ts \
  tests/e2e/p75-daily-assistant-empty-state.spec.ts \
  tests/e2e/p74-daily-assistant-loading-state.spec.ts \
  tests/e2e/p73-daily-assistant-next-checkin.spec.ts \
  tests/e2e/p72-daily-assistant-escalation-notice.spec.ts \
  tests/e2e/p71-daily-assistant-encouragement.spec.ts \
  tests/e2e/p70-daily-assistant-confidence-signal.spec.ts \
  tests/e2e/p69-daily-assistant-biggest-change-context.spec.ts \
  tests/e2e/p68-daily-assistant-outcome-badge.spec.ts \
  tests/e2e/p67-daily-assistant-action-impact-clarity.spec.ts \
  tests/e2e/p66-daily-assistant-missing-data-explanation.spec.ts \
  tests/e2e/p65-daily-assistant-why-now-clarity.spec.ts \
  tests/e2e/p64-daily-assistant-summary-quality.spec.ts \
  --reporter=line
```

### TypeScript check
```bash
cd frontend && npx tsc --noEmit
```

### P77 contract guard (one-command shortcut)
```bash
make daily-assistant-contract
```
Runs TypeScript check + P76 contract smoke (5 tests). Local/manual only — not wired into CI.

### When to run `make daily-assistant-contract`

| Trigger | Action |
|---------|--------|
| Before editing `daily-assistant-entry.tsx` | Run guard first — confirm baseline is green |
| After adding / renaming any `data-testid` in that component | Run guard to catch contract drift |
| After changing signal data conditions (`hasDailySummary`, `topRec`, `isFullyLoading`, etc.) | Run guard + update this contract doc |
| After modifying fixtures in any P64–P76 spec | Run guard to confirm cross-spec consistency |
| Full P64–P76 regression | Use `make frontend-e2e-local` (all specs, ~2 min) |

Do **not** run this as a branch-protection gate — it is a developer-facing local sanity check only.

### Backend smoke
```bash
make runtime-smoke
```

---

## 7. Known Limitations

1. `daily-summary-next-checkin` has a very broad render condition (shows whenever `summary` is non-null). It is documented as optional* but is practically always visible in the loaded state.
2. `daily-summary-missing-data` and `daily-summary-missing-data-explanation` always co-render; they are not independently controllable.
3. The `daily-assistant-entry` card root has no explicit loading-complete gate of its own — it relies on child state transitions.
4. TRIVIAL_MISSING exclusion list (`風險警示（目前無主動警示）`, `健康洞察（建議先執行健康分析）`) is hardcoded in the component. Changes to this list affect `daily-summary-missing-data` visibility.

---

## 8. Change History

| Phase | Change | Author |
|---|---|---|
| P64 | Daily summary 3-card grid, basic testids | CTO Agent |
| P65 | `daily-summary-why-now` | CTO Agent |
| P66 | `daily-summary-missing-data`, `daily-summary-missing-data-explanation` | CTO Agent |
| P67 | `daily-summary-action-impact` | CTO Agent |
| P68 | `daily-summary-outcome-improved-badge` | CTO Agent |
| P69 | `daily-summary-biggest-change-context` | CTO Agent |
| P70 | `daily-summary-confidence-signal` | CTO Agent |
| P71 | `daily-summary-encouragement` | CTO Agent |
| P72 | `daily-summary-escalation-notice` | CTO Agent |
| P73 | `daily-summary-next-checkin` | CTO Agent |
| P74 | `daily-assistant-loading` | CTO Agent |
| P75 | Deepened empty-state coverage (tests-only) | CTO Agent |
| P76 | This contract document + `p76-daily-assistant-signal-contract.spec.ts` | CTO Agent |
| P77 | `make daily-assistant-contract` guard target (Makefile + doc update) | CTO Agent |
