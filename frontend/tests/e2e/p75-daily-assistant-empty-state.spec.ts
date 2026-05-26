/**
 * P75 — Daily Assistant Empty State Testability / Copy Consistency
 *
 * Deepens coverage of the DailyAssistantEntry empty-state branch.
 * The empty state is triggered when:
 *   hasDailySummary === false   (summary?.topRisk || biggestChange || todayAction all falsy)
 *   AND topRec === null         (recommendations array is empty)
 *
 * Existing testid: data-testid="daily-summary-empty" (line 262, introduced pre-P65)
 * P74 already covers: "visible when no content" + "not visible in normal state".
 * P75 adds: copy verification, CTA link, null-summary path, topRec-fallback path,
 *           loading→empty transition, and loading-phase absence.
 *
 * Decision: Option A (tests-only). The existing testid is stable and functional.
 * No component change is needed or made.
 *
 * Tests:
 *  1. Empty state visible: all summary fields empty strings, no recommendations
 *  2. Empty state visible: summary returns null/empty object (API returns {})
 *  3. Empty state NOT visible: topRisk populated
 *  4. Empty state NOT visible: no summary but topRec present (grid fallback shown)
 *  5. Empty state copy "今日摘要尚未生成" is present and non-diagnostic
 *  6. Empty state supplementary copy mentions data entry (not diagnosis)
 *  7. CTA link points to /quick-check-in (safe action)
 *  8. Empty state absent while loading (loading shows, not empty)
 *  9. Loading → empty state transition: loading appears, then resolves to empty state
 * 10. P74 regression: daily-assistant-loading visible while pending
 * 11. P73 regression: next-checkin visible in normal loaded state
 * 12. Dashboard renders without ErrorBoundary fallback
 *
 * Strategy: fully mocked (no live backend). Uses next start (production build).
 * No component code changed. No new dependencies.
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
  explainability_summary: 'P75 mock summary',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P75 test',
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

/** Full populated summary → loaded state, grid shown */
const DAILY_SUMMARY_FULL = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.82,
  encouragement: '你本週記錄完整，繼續保持！',
}

/** All content fields are empty strings → hasDailySummary = false */
const DAILY_SUMMARY_ALL_EMPTY_STRINGS = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '',
  biggestChange: '',
  todayAction: '',
  whyNow: '',
  confidence: 0,
}

/** Empty object → all fields undefined → hasDailySummary = false */
const DAILY_SUMMARY_NULL_BODY = {} as Record<string, unknown>

const RECOMMENDATIONS_NONE = {
  person_id: 'person-self',
  recommendations: [],
  total: 0,
  missing_data: [],
}

/** Has one rec → topRec is present; summary empty → grid shows fallback, no empty state */
const RECOMMENDATIONS_WITH_ONE = {
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
  if (path.includes('/health-assistant/outcome-feedback')) return route.fulfill({ json: OUTCOME_EMPTY })
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

async function stubRoutesNormal(
  page: import('@playwright/test').Page,
  opts: { dailySummary?: object; recommendations?: object } = {},
) {
  const dailySummary    = opts.dailySummary    ?? DAILY_SUMMARY_FULL
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

test.describe('P75 — Daily Assistant Empty State Testability', () => {

  // ── Scenario 1: empty strings ────────────────────────────────────────────────

  test('empty state visible when all summary fields are empty strings and no recommendations', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, {
      dailySummary: DAILY_SUMMARY_ALL_EMPTY_STRINGS,
      recommendations: RECOMMENDATIONS_NONE,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('[data-testid="daily-summary-empty"]')).toBeVisible()
  })

  // ── Scenario 2: null-body summary ────────────────────────────────────────────

  test('empty state visible when daily-summary route returns empty body and no recommendations', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, {
      dailySummary: DAILY_SUMMARY_NULL_BODY,
      recommendations: RECOMMENDATIONS_NONE,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('[data-testid="daily-summary-empty"]')).toBeVisible()
  })

  // ── Scenario 3: topRisk populated → no empty state ──────────────────────────

  test('empty state NOT visible when summary.topRisk is populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, {
      dailySummary: DAILY_SUMMARY_FULL,
      recommendations: RECOMMENDATIONS_NONE,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('[data-testid="daily-summary-empty"]')).not.toBeVisible()
  })

  // ── Scenario 4: topRec present + no summary → grid fallback, no empty state ──

  test('empty state NOT visible when recommendations exist even if summary fields are empty', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, {
      dailySummary: DAILY_SUMMARY_ALL_EMPTY_STRINGS,
      recommendations: RECOMMENDATIONS_WITH_ONE,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    // topRec fills the grid → empty state branch is not entered
    await expect(page.locator('[data-testid="daily-summary-empty"]')).not.toBeVisible()
    // 3-card grid is visible instead
    await expect(page.locator('[data-testid="daily-summary-top-risk"]')).toBeVisible()
  })

  // ── Copy and link verification ───────────────────────────────────────────────

  test('empty state heading copy is non-diagnostic and does not imply medical findings', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, {
      dailySummary: DAILY_SUMMARY_ALL_EMPTY_STRINGS,
      recommendations: RECOMMENDATIONS_NONE,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const emptyEl = page.locator('[data-testid="daily-summary-empty"]')
    await expect(emptyEl).toBeVisible()
    // Heading
    await expect(emptyEl).toContainText('今日摘要尚未生成')
    // Supplementary copy mentions data entry, not diagnosis
    await expect(emptyEl).toContainText('補充健康資料後')
    await expect(emptyEl).toContainText('個人化建議')
  })

  test('empty state CTA link points to /quick-check-in', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, {
      dailySummary: DAILY_SUMMARY_ALL_EMPTY_STRINGS,
      recommendations: RECOMMENDATIONS_NONE,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const ctaLink = page.locator('[data-testid="daily-summary-empty"] a')
    await expect(ctaLink).toBeVisible()
    await expect(ctaLink).toContainText('填入今日健康指標')
    const href = await ctaLink.getAttribute('href')
    expect(href).toContain('quick-check-in')
  })

  // ── Loading-phase absence ────────────────────────────────────────────────────

  test('empty state NOT visible while daily-summary is still loading', async ({ page }) => {
    await setAuthStorage(page)

    let resolveSummary: (() => void) | null = null
    const holdSummary = new Promise<void>(r => { resolveSummary = r })

    await page.route('**/api/v1/**', async (route) => {
      const url    = new URL(route.request().url())
      const path   = url.pathname
      const method = route.request().method()

      if (path.includes('/health-assistant/daily-summary')) {
        await holdSummary
        return route.fulfill({ json: DAILY_SUMMARY_ALL_EMPTY_STRINGS })
      }
      return fulfillCommonRoute(route, path, method, RECOMMENDATIONS_NONE)
    })

    await page.goto('/platform/dashboard')

    // Loading is visible, so empty state must not be shown yet
    await expect(page.locator('[data-testid="daily-assistant-loading"]')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('[data-testid="daily-summary-empty"]')).not.toBeVisible()

    // Unblock
    resolveSummary!()
  })

  // ── Loading → empty state transition ────────────────────────────────────────

  test('loading transitions to empty state after daily-summary resolves with no content', async ({ page }) => {
    await setAuthStorage(page)

    let resolveSummary: (() => void) | null = null
    const holdSummary = new Promise<void>(r => { resolveSummary = r })

    await page.route('**/api/v1/**', async (route) => {
      const url    = new URL(route.request().url())
      const path   = url.pathname
      const method = route.request().method()

      if (path.includes('/health-assistant/daily-summary')) {
        await holdSummary
        return route.fulfill({ json: DAILY_SUMMARY_ALL_EMPTY_STRINGS })
      }
      return fulfillCommonRoute(route, path, method, RECOMMENDATIONS_NONE)
    })

    await page.goto('/platform/dashboard')

    // Phase 1: loading is visible
    await expect(page.locator('[data-testid="daily-assistant-loading"]')).toBeVisible({ timeout: 10_000 })

    // Unblock with empty content
    resolveSummary!()

    // Phase 2: loading disappears, empty state appears
    await expect(page.locator('[data-testid="daily-assistant-loading"]')).not.toBeVisible({ timeout: 10_000 })
    await expect(page.locator('[data-testid="daily-summary-empty"]')).toBeVisible({ timeout: 5_000 })
  })

  // ── Regression ──────────────────────────────────────────────────────────────

  test('P74 regression: daily-assistant-loading visible while API is pending', async ({ page }) => {
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
      return fulfillCommonRoute(route, path, method, RECOMMENDATIONS_NONE)
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-loading"]')).toBeVisible({ timeout: 10_000 })

    resolveSummary!()
    await expect(page.locator('[data-testid="daily-assistant-loading"]')).not.toBeVisible({ timeout: 10_000 })
  })

  test('P73 regression: next-checkin visible in normal loaded state', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, { dailySummary: DAILY_SUMMARY_FULL })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('[data-testid="daily-summary-next-checkin"]')).toBeVisible()
  })

  test('dashboard renders without ErrorBoundary fallback', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesNormal(page, {
      dailySummary: DAILY_SUMMARY_ALL_EMPTY_STRINGS,
      recommendations: RECOMMENDATIONS_NONE,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
    await expect(page.locator('text=Something went wrong')).not.toBeVisible()
    await expect(page.locator('text=Application Error')).not.toBeVisible()
  })

})
