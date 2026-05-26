# P64 Recovery Diagnosis

Generated: 2026-05-26
Sprint: P64-RECOVERY
Classification: `P64_RECOVERY_READY`

---

## Step 1A — Extracted Design Intent from `p64-diag.spec.ts`

### File Purpose
`frontend/tests/e2e/p64-diag.spec.ts` was a temporary diagnostic script created to
capture the actual runtime state of Dashboard when the P64 Playwright acceptance tests
were failing 5/6. It was NOT an acceptance test — it was a crash investigation tool.

### Diagnostic Design Intent

#### Console/PageError Capture Pattern (design intent)
```ts
const errors: string[] = []
page.on("console", msg => { if (msg.type() === "error") errors.push(msg.text()) })
page.on("pageerror", err => errors.push(err.message))
```
Intent: capture all JS runtime errors and console errors before any assertions.

#### Init Script — localStorage Auth Bypass
```ts
await page.addInitScript(() => {
  localStorage.setItem("token", "e2e-token")
  localStorage.setItem("person_id", "person-self")
  localStorage.setItem("onboarding_completed", "1")
})
```
Intent: simulate authenticated user without real login flow.

#### Wait Strategy
```ts
await page.goto("/platform/dashboard", { waitUntil: "domcontentloaded" })
await page.waitForTimeout(8000)
```
Intent: give Dashboard 8 seconds to fully render.

#### Body Text Dump
```ts
console.log("BODY TEXT:", text?.substring(0, 1000))
console.log("PAGE ERRORS:", JSON.stringify(errors))
```
Intent: record whether ErrorBoundary fallback or real content rendered.

#### Selectors / Assumptions
Worker assumed Dashboard would render within 8s with mocked routes.
Noted selectors: `body.textContent()` only — no component-level assertions.

#### Syntax Corruption (reason for TypeScript failure)
Lines 19–21 and 28 contain garbled/duplicated text (likely copy-paste corruption
during handoff). TypeScript rejected the file at collection → `tsc --noEmit` exit 1.
The file was untracked (??), so physical `rm` sufficed — no `git rm` needed.

---

## Step 2 — ErrorBoundary Root Cause

### Step 2A — Baseline Failure Reproduce

Ran: `npx playwright test tests/e2e/p64-daily-assistant-summary-quality.spec.ts --reporter=line`

Result: **5 failed, 1 passed**

| # | Test | Result |
|---|---|---|
| 1 | renders top risk / biggest change / next action | FAIL |
| 2 | missing data state renders safe fallback copy | **PASS** |
| 3 | outcome unknown copy visible when tracking items exist | FAIL |
| 4 | outcome unknown copy visible when insufficient_data items exist | FAIL |
| 5 | user-feedback disclaimer visible in outcome section | FAIL |
| 6 | unsafe medical effectiveness phrases do not appear | FAIL |

All 5 failures: `[data-testid="daily-assistant-entry"]` not visible with 12s timeout.

Error-context snapshot confirmed: page body shows `載入失敗，請重新整理` — the
`ErrorBoundary` fallback, meaning the entire Dashboard component tree crashed.

### Step 2B — PageError Stack (captured via page.on instrumentation)

```
[CONSOLE_ERROR] TypeError: Cannot read properties of undefined (reading 'length')
    at sC (http://127.0.0.1:3010/_next/static/chunks/app/platform/dashboard/page-9f34c3fea89de3b0.js:1:99153)
    at rE (http://127.0.0.1:3010/_next/static/chunks/fd9d1056-ef1dfcdb1be5147d.js:1:40344)
    at l$ (http://127.0.0.1:3010/_next/static/chunks/fd9d1056-ef1dfcdb1be5147d.js:1:59319)
    at iZ (http://127.0.0.1:3010/_next/static/chunks/fd9d1056-ef1dfcdb1be5147d.js:1:117926)
    at ia (http://127.0.0.1:3010/_next/static/chunks/fd9d1056-ef1dfcdb1be5147d.js:1:95165)
    at MessagePort.T (http://127.0.0.1:3010/_next/static/chunks/2117-6e62fb2b02925f4f.js:1:84275)
```

Source file: `app/platform/dashboard/page-*.js` — the dashboard page bundle.

### Step 2D — Root Cause Judgment

**[Decision]: `both` — production-side bug + mock-side gap**

#### Crash location (source-mapped from minified `sC`)

File: `frontend/app/components/platform/health-assistant-panel.tsx`
Lines 267–268:

```ts
const hasRecs = data && data.recommendations.length > 0;     // line 267
const hasMissing = data && data.missing_data.length > 0 && !hasRecs; // line 268 ← CRASH
```

When `data = { person_id: 'person-self', recommendations: [], total: 0 }` (no `missing_data`):
- `data.recommendations.length` → 0 (safe, field exists)
- `data.missing_data` → `undefined` → `.length` throws `TypeError`

#### Why test 2 (only) passed

Test 2 provides `recommendations: RECOMMENDATIONS_WITH_MISSING` which includes
`missing_data: ['症狀記錄', '健康指標...']` → `data.missing_data.length` → 2 → no crash.

Tests 1, 3, 4, 5, 6 used the default stub:
`{ person_id: 'person-self', recommendations: [], total: 0 }` — no `missing_data` → crash.

#### Production-side issue (real bug)
`health-assistant-panel.tsx:268` accesses `.length` on a field typed as required in
`HealthAssistantData` but absent from real API responses in low-data states.
Any runtime context where the API response omits `missing_data` causes the entire
Dashboard to fall back to ErrorBoundary.

#### Mock-side issue (test gap)
The default stub in `stubRoutes()` did not include `missing_data`, making 5/6 tests
exercise the crash path. Adding `missing_data: []` to the default stub makes the tests
realistic and serves as a regression guard.

---

## Step 3 — Minimum Fix Applied

### Fix 1 — Production (health-assistant-panel.tsx:267–268)

```ts
// Before (crashed when missing_data undefined):
const hasRecs = data && data.recommendations.length > 0;
const hasMissing = data && data.missing_data.length > 0 && !hasRecs;

// After (optional chaining + nullish coalescing):
const hasRecs = data && (data.recommendations?.length ?? 0) > 0;
const hasMissing = data && (data.missing_data?.length ?? 0) > 0 && !hasRecs;
```

Scope: 2-line change, no structural change, no new imports. Purely defensive null guard.

### Fix 2 — Mock (p64-daily-assistant-summary-quality.spec.ts stubRoutes default)

```ts
// Before:
const recommendations = opts.recommendations ?? { person_id: 'person-self', recommendations: [], total: 0 }

// After:
const recommendations = opts.recommendations ?? { person_id: 'person-self', recommendations: [], total: 0, missing_data: [] }
```

### Diagnostic Cleanup
Removed `page.on('pageerror', ...)` and `page.on('console', ...)` instrumentation
added in Step 2B from the spec file before committing.

---

## Validation Results (Step 3C)

| Check | Command | Result |
|---|---|---|
| TypeScript | `npx tsc --noEmit` | Exit 0, 0 errors ✅ |
| P64 targeted | `npx playwright test ...p64-daily-assistant-summary-quality.spec.ts` | **6/6 PASS** ✅ |
| P55 regression | `npx playwright test ...p55-action-feedback-loop.spec.ts` | 9/9 PASS ✅ |
| P56 regression | `npx playwright test ...p56-recommendation-feedback-persistence.spec.ts` | 4/4 PASS ✅ |
| P57 regression | `npx playwright test ...p57-snooze-persistence.spec.ts` | 4/4 PASS ✅ |
| Backend smoke | `make runtime-smoke` | 56 passed, 0 failed ✅ |
