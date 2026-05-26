/**
 * P76 — Daily Assistant Signal Contract Test
 *
 * High-level contract smoke for DailyAssistantEntry signals after P64–P75.
 * This is NOT a detailed per-signal spec (those live in p64–p75 spec files).
 * Purpose: assert the overall contract: right signals visible in right states,
 * absent when source data is absent. Prevents silent contract breaks on refactor.
 *
 * Contract doc: docs/security/P76_DAILY_ASSISTANT_SIGNAL_CONTRACT.md
 *
 * Tests:
 *  1. Full signal happy path: all optional signals visible with fully-populated data
 *  2. Loading state contract: daily-assistant-loading visible while API pending
 *  3. Empty state contract: daily-summary-empty visible when no summary + no topRec
 *  4. Negative contract: optional signals absent when source fields absent/zero/none
 *  5. ErrorBoundary contract: dashboard renders without error fallback
 *
 * Strategy: fully mocked (no live backend). Uses same helper patterns as P73–P75.
 * No component changes. No new dependencies.
 */

import { expect, test } from '@playwright/test'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD = {
  health_score: { overall_score: 72, components: {} },
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P76 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P76',
    risks: [],
    trends: [],
    reasons: [],
    actions: [],
    delta_summary: '無變化',
    improvements: [],
    deteriorations: [],
    adherence: [],
    missed_risks: [],
  },
}

/** All optional fields populated — all optional signals should appear. */
const DAILY_SUMMARY_FULL = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.82,
  encouragement: '你本週記錄完整，繼續保持！',
  escalation: {
    escalationLevel: 'watch',
    reasons: ['血壓值超出正常範圍'],
    recommendedAction: '密切觀察並記錄血壓',
  },
}

/**
 * Only topRisk set; all optional fields absent/empty/zero.
 * Keeps hasDailySummary === true (grid shows) but all optional signals should be hidden.
 */
const DAILY_SUMMARY_MINIMAL = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '輕微血壓偏高',
  biggestChange: '',
  todayAction: '',
  whyNow: '',
  confidence: 0,
  // no encouragement → absent
  // no escalation → absent
}

/** All fields empty → hasDailySummary = false. */
const DAILY_SUMMARY_EMPTY = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '',
  biggestChange: '',
  todayAction: '',
  whyNow: '',
  confidence: 0,
}

/** Recommendations with all optional trust fields, non-trivial missing_data. */
const RECOMMENDATIONS_FULL = {
  person_id: 'person-self',
  recommendations: [
    {
      title: '量測早晨血壓',
      why_now: '血壓偏高',
      priority: 'high',
      source_type: 'lab_abnormality',
      expected_health_impact: '減少心血管風險',
      evidence_sources: [],
      next_action: '今早量測血壓',
      is_tracking: false,
      trust: {
        confidence: 0.85,
        level: 'high',
        reasons: ['有近期量測記錄'],
        limitations: [],
        verifiedByOutcome: false,
        nextCheckInSuggestion: '3 天後回來查看血壓變化。',
      },
    },
  ],
  total: 1,
  // Non-trivial missing data (triggers daily-summary-missing-data / explanation)
  missing_data: ['症狀記錄'],
}

/** No recommendations, no missing data. */
const RECOMMENDATIONS_NONE = {
  person_id: 'person-self',
  recommendations: [],
  total: 0,
  missing_data: [],
}

/** Outcome feedback with improved_count > 0 → daily-summary-outcome-improved-badge. */
const OUTCOME_WITH_IMPROVED = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 7,
  outcomes: [],
  summary: {
    improved_count: 2, unchanged_count: 1, deteriorated_count: 0,
    insufficient_data_count: 0, tracking_count: 1, not_useful_count: 0,
    not_applicable_count: 0, snoozed_count: 0, total_count: 4,
  },
}

/** Outcome feedback with improved_count === 0 → daily-summary-outcome-improved-badge absent. */
const OUTCOME_ZERO_IMPROVED = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 7,
  outcomes: [],
  summary: {
    improved_count: 0, unchanged_count: 3, deteriorated_count: 0,
    insufficient_data_count: 0, tracking_count: 0, not_useful_count: 0,
    not_applicable_count: 0, snoozed_count: 0, total_count: 3,
  },
}

/** Outcome feedback with total_count === 0 → hasFeedback = false. */
const OUTCOME_EMPTY = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 7,
  outcomes: [],
  summary: {
    improved_count: 0, unchanged_count: 0, deteriorated_count: 0,
    insufficient_data_count: 0, tracking_count: 0, not_useful_count: 0,
    not_applicable_count: 0, snoozed_count: 0, total_count: 0,
  },
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function setAuthStorage(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'e2e-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
}

function fulfillCommonRoute(
  route: import('@playwright/test').Route,
  path: string,
  method: string,
  recommendations: object,
  outcome: object,
) {
  if (path.endsWith('/persons')) return route.fulfill({ json: PERSONS })
  if (path.endsWith('/profile/me')) {
    return route.fulfill({
      json: {
        id: 'person-self', display_name: 'Self', name: 'Self',
        age: 40, gender: 'male', onboarding_completed: true,
      },
    })
  }
  if (path.includes('/health-assistant/outcome-feedback')) return route.fulfill({ json: outcome })
  if (path.includes('/health-assistant/recommendations')) return route.fulfill({ json: recommendations })
  if (path.includes('/health-assistant/notifications/intelligent')) {
    return route.fulfill({
      json: {
        person_id: 'person-self',
        generated_at: new Date().toISOString(),
        items: [], suppressed: [], total_candidates: 0,
      },
    })
  }
  if (path.includes('/orchestrator/dashboard-summary')) return route.fulfill({ json: null })
  if (path.includes('/health-assistant/family-relationships')) {
    return route.fulfill({ json: { person_id: 'person-self', relationships: [], total: 0 } })
  }
  if (path.includes('/health-assistant/family-health-context')) {
    return route.fulfill({ json: { person_id: 'person-self', context: null } })
  }
  if (path.includes('/health-assistant/family-recommendations')) {
    return route.fulfill({ json: { person_id: 'person-self', recommendations: [], total: 0 } })
  }
  if (path.includes('/health-assistant/narrative-memory/cross-period')) {
    return route.fulfill({ json: { person_id: 'person-self', reasoning: null } })
  }
  if (path.endsWith('/dashboard')) return route.fulfill({ json: BASE_DASHBOARD })
  if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
  if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') {
    return route.fulfill({ json: [] })
  }
  if (path.endsWith('/insights')) return route.fulfill({ json: [] })
  if (path.endsWith('/risk-alerts')) return route.fulfill({ json: [] })
  if (path.includes('/risk-alerts/unread-count')) return route.fulfill({ json: { count: 0 } })
  if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
  if (method === 'GET') return route.fulfill({ json: { items: [] } })
  return route.fulfill({ json: {} })
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: {
    dailySummary?: object
    recommendations?: object
    outcome?: object
  } = {},
) {
  const dailySummary    = opts.dailySummary    ?? DAILY_SUMMARY_FULL
  const recommendations = opts.recommendations ?? RECOMMENDATIONS_FULL
  const outcome         = opts.outcome         ?? OUTCOME_WITH_IMPROVED

  await page.route('**/api/v1/**', (route) => {
    const url    = new URL(route.request().url())
    const path   = url.pathname
    const method = route.request().method()

    if (path.includes('/health-assistant/daily-summary')) {
      return route.fulfill({ json: dailySummary })
    }
    return fulfillCommonRoute(route, path, method, recommendations, outcome)
  })
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P76 — Daily Assistant Signal Contract', () => {

  // ── Contract 1: Full signal happy path ──────────────────────────────────────

  test('contract: all optional signals visible with fully-populated data', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_FULL,
      recommendations: RECOMMENDATIONS_FULL,
      outcome: OUTCOME_WITH_IMPROVED,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Core state: loaded, not loading, not empty
    await expect(page.locator('[data-testid="daily-assistant-loading"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-empty"]')).not.toBeVisible()

    // Optional signals: present with full data
    await expect(page.locator('[data-testid="daily-summary-why-now"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-biggest-change-context"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-action-impact"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-confidence-signal"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-encouragement"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-escalation-notice"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-missing-data-explanation"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-outcome-improved-badge"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-next-checkin"]')).toBeVisible()
  })

  // ── Contract 2: Loading state ────────────────────────────────────────────────

  test('contract: loading state — daily-assistant-loading visible while summary API pending', async ({ page }) => {
    await setAuthStorage(page)

    let resolveSummary: (() => void) | null = null
    const holdSummary = new Promise<void>(r => { resolveSummary = r })

    await page.route('**/api/v1/**', async (route) => {
      const url    = new URL(route.request().url())
      const path   = url.pathname
      const method = route.request().method()

      if (path.includes('/health-assistant/daily-summary')) {
        await holdSummary
        return route.fulfill({ json: DAILY_SUMMARY_FULL })
      }
      return fulfillCommonRoute(route, path, method, RECOMMENDATIONS_FULL, OUTCOME_WITH_IMPROVED)
    })

    await page.goto('/platform/dashboard')

    // Loading skeleton visible — no other Daily Assistant states showing
    await expect(page.locator('[data-testid="daily-assistant-loading"]')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('[data-testid="daily-summary-empty"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-why-now"]')).not.toBeVisible()

    // Unblock → loading disappears
    resolveSummary!()
    await expect(page.locator('[data-testid="daily-assistant-loading"]')).not.toBeVisible({ timeout: 10_000 })
  })

  // ── Contract 3: Empty state ──────────────────────────────────────────────────

  test('contract: empty state — daily-summary-empty visible when no summary content and no topRec', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_EMPTY,
      recommendations: RECOMMENDATIONS_NONE,
      outcome: OUTCOME_EMPTY,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    await expect(page.locator('[data-testid="daily-summary-empty"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-assistant-loading"]')).not.toBeVisible()
    // Empty state CTA is safe: links to data-entry, not diagnosis
    await expect(page.locator('[data-testid="daily-summary-empty"] a[href*="quick-check-in"]')).toBeVisible()
  })

  // ── Contract 4: Negative — optional signals absent when source data absent ───

  test('contract: optional signals absent when source fields are absent/empty/zero/none', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_MINIMAL,     // topRisk only; all optional fields empty/zero/absent
      recommendations: RECOMMENDATIONS_NONE,   // no missing_data, no trust.nextCheckInSuggestion
      outcome: OUTCOME_ZERO_IMPROVED,          // improved_count = 0 → no badge
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Grid shows (topRisk is set), not loading, not empty
    await expect(page.locator('[data-testid="daily-assistant-loading"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-empty"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-top-risk"]')).toBeVisible()

    // All optional signals must be hidden
    await expect(page.locator('[data-testid="daily-summary-why-now"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-biggest-change-context"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-action-impact"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-confidence-signal"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-encouragement"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-escalation-notice"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-missing-data-explanation"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-outcome-improved-badge"]')).not.toBeVisible()
  })

  // ── Contract 5: ErrorBoundary / render health ────────────────────────────────

  test('contract: dashboard renders without ErrorBoundary fallback in any mocked state', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_FULL,
      recommendations: RECOMMENDATIONS_FULL,
      outcome: OUTCOME_WITH_IMPROVED,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('text=Something went wrong')).not.toBeVisible()
    await expect(page.locator('text=Application Error')).not.toBeVisible()
  })

})
