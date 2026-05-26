# P79 Daily Assistant Next Lane Decision

**Version**: P79 (2026-05-26)
**Scope**: Post P64–P78 Daily Assistant micro-polish — lane selection
**Status**: Decision — stop Daily Assistant micro-signals, move to Actions/Recommendations lane

---

## 1. Current Closure State

P64–P78 is **fully committed** on `main`. All validation gates pass.

| Gate | Result |
|------|--------|
| `make daily-assistant-contract` (TSC + 5 contract tests) | ✅ PASS |
| `make runtime-smoke` (56 Python backend tests) | ✅ PASS |
| Governance dirty files | governance-only ✅ |
| Contract doc (`P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md`) | up-to-date ✅ |
| Makefile target (`daily-assistant-contract`) | live, local/manual ✅ |

---

## 2. What P64–P78 Completed

| Phase | Deliverable |
|-------|-------------|
| P64 | Daily Assistant summary quality recovery — 3-card grid testids, safe outcome/missing-data copy |
| P65 | `daily-summary-why-now` contextual signal |
| P66 | `daily-summary-missing-data`, `daily-summary-missing-data-explanation` |
| P67 | `daily-summary-action-impact` (tracking continuity copy) |
| P68 | `daily-summary-outcome-improved-badge` |
| P69 | `daily-summary-biggest-change-context` |
| P70 | `daily-summary-confidence-signal` |
| P71 | `daily-summary-encouragement` |
| P72 | `daily-summary-escalation-notice` |
| P73 | `daily-summary-next-checkin` |
| P74 | `daily-assistant-loading` skeleton testid |
| P75 | Empty-state test depth (11 tests, no component change) |
| P76 | Signal contract doc + 5-test contract smoke spec |
| P77 | `make daily-assistant-contract` Makefile guard |
| P78 | "When to run" discoverability table in contract doc §6 |

**Total**: 13 testids documented, 6 invariant groups, local/manual guard in place.

---

## 3. Current Contract Guard Status

```
make daily-assistant-contract
```
- TypeScript check + 5 contract smoke tests
- Runtime: ~5 seconds
- Local/manual only
- Not wired to CI (intentional — no CI infrastructure exists in this repo)
- Trigger guidance documented in `docs/security/P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md §6`

**Assessment**: Guard is sufficient. No further guard work is justified now.

---

## 4. Contract Gap Audit

Checked the P76 contract test against the full testid inventory:

| Area | Status |
|------|--------|
| Loading state exclusivity | ✅ covered (test 2) |
| Empty state guard | ✅ covered (test 3) |
| All 9 optional signals visible in full data | ✅ covered (test 1) |
| All optional signals absent in no-data | ✅ covered (test 4) |
| ErrorBoundary safety | ✅ covered (test 5) |
| Grid card testids (`top-risk`, `biggest-change`, `next-action`) | inherently covered by test 1 state |
| `daily-summary-missing-data` co-render with explanation | covered in P66 spec; not a P76 gap |
| `daily-summary-outcome-unknown` | covered in P75 spec; not a P76 gap |

**Verdict**: No missing invariants found. **Do not add tests to P76 contract spec.**

---

## 5. Decision: Stop Daily Assistant Micro-Polish

**Decided: STOP adding Daily Assistant micro-signals.**

Reasons:
1. All 13 testids are documented and tested. The component has no unlabeled visible state transitions.
2. Signal inflation risk — each new signal requires P76 contract update, spec update, Makefile knowledge update. ROI decreases with each addition.
3. The roadmap P1 clearly states: _"Keep recommendation history, outcome feedback, and trust UI consistent across Dashboard and Actions."_ This is the next product-value work.
4. P64–P78 has fully served the Daily Assistant micro-polish lane.

---

## 6. Recommended Next Lane

**P80: Recommendation History / Actions Page Consistency Smoke**

### Rationale
- P55–P63 built outcome feedback, snooze persistence, and recommendation history card. These foundations are in production but have **no cross-page E2E smoke** confirming the Actions page (`/platform/actions`) renders recommendation history consistently.
- The roadmap explicitly names this: _"Keep recommendation history, outcome feedback, and trust UI consistent across Dashboard and Actions."_ (roadmap P1)
- P4 (Report-to-Action browser journey) is also a candidate, but requires more setup (report upload flow). Actions page consistency is lower friction and higher immediate trust value.

### P80 Scope (bounded)
- Read `frontend/app/` — inspect the Actions page component for existing testids
- If testids exist: write a mocked Playwright smoke for Actions page (recommendation history card visible, feedback states, snooze state)
- If testids are absent: add the minimum required testids + mocked smoke
- No backend changes
- No new API endpoints
- `make runtime-smoke` must remain green

### P80 Explicit Non-Scope
- Daily Assistant component (`daily-assistant-entry.tsx`) — do not touch
- Backend test changes
- New auth flow
- CI wiring

---

## 7. Risks if Continuing Daily Assistant Micro-Polish

| Risk | Severity |
|------|----------|
| Signal inflation — contract doc and spec grow unsustainably | Medium |
| Diminishing product value per signal added | High |
| Workers forget which lane they are on | Medium |
| P76 contract guard becomes expensive to maintain | Low (currently) → Medium (if >20 testids) |

---

## 8. Risks if Moving to P80 Too Early

| Risk | Mitigation |
|------|-----------|
| Actions page testids do not exist → P80 requires component changes | Acceptable — adding testids is low-risk and follows P64–P73 precedent |
| Actions page Playwright mock requires complex fixture setup | Use same `addInitScript` + `page.route` pattern already established |
| `make daily-assistant-contract` might break if Actions page renders Daily Assistant | Unlikely — components are independent; guard scope is fixed to P76 spec file |

---

## 9. Validation Commands

```bash
# Required after any future Daily Assistant component edit
make daily-assistant-contract

# Required before any commit
cd frontend && npx tsc --noEmit

# Required before any commit (backend)
make runtime-smoke

# Full P64–P78 regression (only when changing behavior or fixtures)
make frontend-e2e-local

# P80 — once implemented
cd frontend && npx playwright test tests/e2e/p80-actions-recommendation-smoke.spec.ts --reporter=line
```

---

## 10. Exact Next 24h Prompt

See `00-Plan/roadmap/active_task_report.md` P79 block for the copy-paste prompt.
