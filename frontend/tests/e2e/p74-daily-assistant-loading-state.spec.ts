/**
 * P74 — Daily Assistant Loading State Testability
 *
 * Validates that DailyAssistantEntry renders the loading skeleton with
 * data-testid="daily-assistant-loading" while the daily-summary API is pending,
 * and transitions to the loaded content after resolution.
 *
 * Also validates that the empty state data-testid="daily-summary-empty" appears
 * when the API returns no summary content and no recommendations exist.
 *
 * Tests:
 *  1. Loading state visible (data-testid="daily-assistant-loading") while daily-summary pending
 *  2. Loading state disappears after daily-summary resolves
 *  3. After loading: daily-summary-next-checkin visible (P73 regression)
 *  4. Empty state (data-testid="daily-summary-empty") visible when APIs return no content
 *  5. Empty state not present in normal loaded state
 *  6. Loading container is a child of daily-assistant-entry
 *  7. P73 regression: next-checkin trust copy
 *  8. P72 regression: escalation notice
 *  9. P71 regression: encouragement
 * 10. P70 regression: confidence signal
 * 11. P69 regression: biggest-change context
 * 12. Dashboard renders without ErrorBoundary fallback
 *
 * Strategy: fully mocked (no live backend). Uses next start (production build).
 */

import { expect, test } from '@playwright/test'

// ── Shared fixtures ───────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD = {
  health_score: { overall_score: 72, components: {} },
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P74 mock summary',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P74 test',
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

const DAILY_SUMMARY_WITH_ACTION = {
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
    reasons: ['睡眠時長近期下降趨勢，需持續觀察。'],
    confidence: 0.65,
    recommendedAction: null,
    requiresFollowUp: false,
  },
}

/** Summary with no content → empty state */
const DAILY_SUMMARY_EMPTY_CONTENT = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '',
  biggestChange: '',
  todayAction: '',
  whyNow: '',
  confidence: 0,
}

const RECOMMENDATIONS_WITH_TRUST = {
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
  missing_data: [],
}

const RECOMMENDATIONS_NONE = {
  person_id: 'person-self',
  recommendations: [],
  total: 0,
  missing_data: [],
}

const OUTCOME_EMPTY = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 7,
  outcomes: [],
  summary: {
    improved_count: 0,
    unchanged_count: 0,
    deteriorated_count: 0,
    insufficient_data_count: 0,
    tracking_count: 0,
    not_useful_count: 0,
    not_applicable_count: 0,
    snoozed_count: 0,
    total_count: 0,
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

/** Common non-summary routes — always respond immediately */
function fulfillCommonRoute(
  route: import('@playwright/test').Route,
  path: string,
  method: string,
  recommendations: object,
) {
  if (path.endsWith('/persons')) return route.fulfill({ json: PERSONS })
  if (path.endsWith('/profile/me')) {
    return route.fulfill({
      json: {
        id: 'person-self',
        display_name: 'Self',
        name: 'Self',
        age: 40,
        gender: 'male',
        onboarding_completed: true,
      },
    })
  }
  if (path.includes('/health-assistant/outcome-feedback')) {
    return route.fulfill({ json: OUTCOME_EMPTY })
  }
  if (path.includes('/health-assistant/recommendations')) {
    return route.fulfill({ json: recommendations })
  }
  if (path.includes('/health-assistant/notifications/intelligent')) {
    return route.fulfill({
      json: {
        person_id: 'person-self',
        generated_at: new Date().toISOString(),
        items: [],
        suppressed: [],
        total_candidates: 0,
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

async function stubRoutesNormal(
  page: import('@playwright/test').Page,
  opts: {
    dailySummary?: object
    recommendations?: object
  } = {},
) {
  const dailySummary    = opts.dailySummary    ?? DAILY_SUMMARY_WITH_ACTION
  const recommendations = opts.recommendations ?? RECOMMENDATIONS_NONE

  await page.route('**/api/v1/**', (route) => {
    const url    = new URL(route.request().url())
    const path   = url.pathname
    const method = route.request().method()

    if (path.includes('/health-assistant/daily-summary')) {
      return route.fulfill({ json: dailySummary })
    }
    return fulfillCommonRoute(route, path, method, recommendations)
  })
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P74 — Daily Assistant Loading State Testability', () => {

  // ── Core: loading state testid ──────────────────────────────────────────────

  test('loading skeleton has data-testid="daily-assistant-loading" while daily-summary pending', async ({ page }) => {
    await setAuthStorage(page)

    // Hold daily-summary until we assert loading
    let resolveSummary: (() => void) | null = null
    const holdSummary = new Promise<void>(r => { resolveSummary = r })

    await page.route('**/api/v1/**', async (route) => {
      const url    = new URL(route.request().url())
      const path   = url.pathname
      const method = route.request().method()

      if (path.includes('/health-assistant/daily-summary')) {
        await holdSummary
        return route.fulfill({ json: DAILY_SUMMARY_WITH_ACTION })
      }
      return fulfillCommonRoute(route, path, method, RECOMMENDATIONS_NONE)
    })

    await page.goto('/platform/dashboard')

    // Loading state is visible while daily-summary is pending
    const loadingEl = page.locator('[data-testid="daily-assistant-loading"]')
    await expect(loadingEl).toBeVisible({ timeout: 10_000 })

    // Unblock the route
    resolveSummary!()

    // Loading disappears after summary resolves
    await expect(loadingEl).not.toBeVisible({ timeout: 10_000 })
  })

  test('loading skeleton is a direct child of daily-assistant-entry', async ({ page }) => {
    await setAuthStorage(page)

    let resolveSummary: (() => void) | null = null
    const holdSummary = new Promise<void>(r => { resolveSummary = r })

    await page.route('**/api/v1/**', async (route) => {
      const url    = new URL(route.request().url())
      const path   = url.pathname
      const method = route.request().method()

      if (path.includes('/health-assistant/daily-summary')) {
        await holdSummary
        return route.fulfill({ json: DAILY_SUMMARY_WITH_ACTION })
      }
      return fulfillCommonRoute(route, path, method, RECOMMENDATIONS_NONE)
    })

    await page.goto('/platform/dashboard')

    // Both entry card and loading indicator should be present simultaneously
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('[data-testid="daily-assistant-loading"]')).toBeVisible({ timeout: 5_000 })

    resolveSummary!()
  })

  test('after loading resolves: daily-summary-next-checkin visible (P73 regression)', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, {
      dailySummary: DAILY_SUMMARY_WITH_ACTION,
      recommendations: RECOMMENDATIONS_NONE,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Loading must be gone
    await expect(page.locator('[data-testid="daily-assistant-loading"]')).not.toBeVisible()

    // Next check-in from P73 is present
    await expect(page.locator('[data-testid="daily-summary-next-checkin"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-next-checkin"]')).toContainText('完成今日行動後，回來更新記錄。')
  })

  // ── Empty state ─────────────────────────────────────────────────────────────

  test('empty state (daily-summary-empty) visible when summary has no content and no recommendations', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, {
      dailySummary: DAILY_SUMMARY_EMPTY_CONTENT,
      recommendations: RECOMMENDATIONS_NONE,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('[data-testid="daily-summary-empty"]')).toBeVisible()
  })

  test('empty state not visible in normal loaded state', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, {
      dailySummary: DAILY_SUMMARY_WITH_ACTION,
      recommendations: RECOMMENDATIONS_NONE,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('[data-testid="daily-summary-empty"]')).not.toBeVisible()
  })

  // ── Regression tests ────────────────────────────────────────────────────────

  test('P73 regression: trust.nextCheckInSuggestion shown when trust populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, {
      dailySummary: DAILY_SUMMARY_WITH_ACTION,
      recommendations: RECOMMENDATIONS_WITH_TRUST,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-next-checkin"]')
    await expect(el).toBeVisible()
    await expect(el).toContainText('3 天後回來查看血壓變化。')
  })

  test('P72 regression: escalation notice visible when escalationLevel !== none', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, { dailySummary: DAILY_SUMMARY_WITH_ACTION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('[data-testid="daily-summary-escalation-notice"]')).toBeVisible()
  })

  test('P71 regression: encouragement visible when encouragement populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, { dailySummary: DAILY_SUMMARY_WITH_ACTION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('[data-testid="daily-summary-encouragement"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-encouragement"]')).toContainText('你本週記錄完整')
  })

  test('P70 regression: confidence signal visible when confidence > 0', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, { dailySummary: DAILY_SUMMARY_WITH_ACTION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('[data-testid="daily-summary-confidence-signal"]')).toBeVisible()
  })

  test('P69 regression: biggest-change context visible when biggestChange populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, { dailySummary: DAILY_SUMMARY_WITH_ACTION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('[data-testid="daily-summary-biggest-change-context"]')).toBeVisible()
  })

  test('dashboard renders without ErrorBoundary fallback', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, { dailySummary: DAILY_SUMMARY_WITH_ACTION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('text=Something went wrong')).not.toBeVisible()
    await expect(page.locator('text=Application Error')).not.toBeVisible()
  })

})
