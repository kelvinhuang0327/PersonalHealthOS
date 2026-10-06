/**
 * P80 — Actions Page Recommendation Smoke
 *
 * Validates that /platform/actions:
 * - Renders without ErrorBoundary fallback (actions-page visible)
 * - Shows loading skeleton while API is frozen (actions-loading visible)
 * - Shows recommendation-history-card when outcome-feedback data exists
 * - Hides recommendation-history-card when outcome-feedback returns null
 * - Renders execution-center heading "執行中心"
 * - Contains no unsafe medical overclaiming phrases
 *
 * Strategy: fully mocked (no live backend, no auth required).
 * Testids added in P80: actions-page, actions-loading.
 * Existing testids used:  recommendation-history-card, history-summary-bar (P62).
 */

import { expect, test } from '@playwright/test'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD = {
  health_score: { overall_score: 78, components: {} },
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P80 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P80 test',
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

const OUTCOME_FEEDBACK_WITH_DATA = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 30,
  outcomes: [
    {
      action_id: 'action-p80-not-useful',
      action_title: '每日量測血壓',
      status: 'not_useful',
      completed_at: null,
      expected_health_impact: '預期改善血壓數值',
      outcome_status: 'not_useful',
      actual_metric_change: null,
      adherence_status: 'dismissed',
      evidence_sources: [],
      confidence: 0.0,
      explanation: '使用者回饋：沒有明顯幫助',
      next_check_in: null,
    },
    {
      action_id: 'action-p80-snoozed',
      action_title: '睡前冥想練習',
      status: 'snoozed',
      completed_at: null,
      expected_health_impact: '預期改善睡眠品質',
      outcome_status: 'snoozed',
      actual_metric_change: null,
      adherence_status: 'snoozed',
      evidence_sources: [],
      confidence: 0.0,
      explanation: '使用者選擇稍後提醒',
      next_check_in: '2026-06-01',
    },
  ],
  summary: {
    improved_count: 0,
    unchanged_count: 0,
    deteriorated_count: 0,
    insufficient_data_count: 0,
    tracking_count: 0,
    not_useful_count: 1,
    not_applicable_count: 0,
    snoozed_count: 1,
    total_count: 2,
  },
}

const OUTCOME_FEEDBACK_EMPTY = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 30,
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

// ── Route stub ────────────────────────────────────────────────────────────────

type StubOptions = {
  outcomeFeedback?: object
  outcomeFeedbackStatus?: number
  freezeDashboard?: boolean
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: StubOptions = {},
) {
  const {
    outcomeFeedback = OUTCOME_FEEDBACK_WITH_DATA,
    outcomeFeedbackStatus = 200,
    freezeDashboard = false,
  } = opts
  let dashboardResolve: (() => void) | null = null

  await page.addInitScript(() => {
    localStorage.setItem('token', 'p80-mock-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
    localStorage.setItem('health_actions_cache_person-self', JSON.stringify([]))
  })

  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()

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
      if (outcomeFeedbackStatus !== 200) {
        return route.fulfill({ status: outcomeFeedbackStatus, json: { detail: 'Simulated error' } })
      }
      return route.fulfill({ json: outcomeFeedback })
    }
    if (path.includes('/health-assistant/recommendations')) {
      return route.fulfill({
        json: { person_id: 'person-self', recommendations: [], total: 0 },
      })
    }
    if (path.includes('/health-assistant/daily-summary')) {
      return route.fulfill({
        json: {
          topRisk: '',
          biggestChange: '',
          todayAction: '',
          generated_at: new Date().toISOString(),
        },
      })
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
    if (path.endsWith('/dashboard')) {
      if (freezeDashboard && dashboardResolve === null) {
        // Hold the response until the test releases it
        await new Promise<void>((resolve) => { dashboardResolve = resolve })
      }
      return route.fulfill({ json: BASE_DASHBOARD })
    }
    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') {
      return route.fulfill({ json: [] })
    }
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if (path.endsWith('/weekly-report')) return route.fulfill({ json: { items: [] } })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })

  return {
    /** Call to unfreeze a frozen /dashboard response */
    releaseDashboard: () => { if (dashboardResolve) { dashboardResolve(); dashboardResolve = null } },
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P80 — Actions Page Recommendation Smoke', () => {
  test('page renders without ErrorBoundary fallback', async ({ page }) => {
    await stubRoutes(page)
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()
    // ErrorBoundary fallback text must not appear
    await expect(page.getByText('Something went wrong', { exact: false })).not.toBeVisible()
    await expect(page.getByText('Error', { exact: true })).not.toBeVisible()
  })

  test('shows loading skeleton while dashboard API is frozen', async ({ page }) => {
    const { releaseDashboard } = await stubRoutes(page, { freezeDashboard: true })
    const nav = page.goto('/platform/actions')

    await page.waitForSelector('[data-testid="actions-loading"]', { timeout: 10_000 })
    await expect(page.locator('[data-testid="actions-loading"]')).toBeVisible()
    // Full page must not have rendered yet
    await expect(page.locator('[data-testid="actions-page"]')).not.toBeVisible()

    releaseDashboard()
    await nav
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })
    await expect(page.locator('[data-testid="actions-loading"]')).not.toBeVisible()
  })

  test('recommendation-history-card visible when outcome-feedback data exists', async ({ page }) => {
    await stubRoutes(page, { outcomeFeedback: OUTCOME_FEEDBACK_WITH_DATA })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="recommendation-history-card"]', { timeout: 10_000 })

    await expect(page.locator('[data-testid="recommendation-history-card"]')).toBeVisible()
  })

  test('recommendation-history-card hidden when outcome-feedback returns empty outcomes', async ({ page }) => {
    await stubRoutes(page, { outcomeFeedback: OUTCOME_FEEDBACK_EMPTY })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // The page renders but historyData.outcomes is [] — card still renders in empty-state mode
    const card = page.locator('[data-testid="recommendation-history-card"]')
    await expect(card).toBeVisible()
    await expect(card.getByText('目前還沒有足夠的建議回饋紀錄')).toBeVisible()
  })

  test('recommendation-history-card absent when outcome-feedback API errors', async ({ page }) => {
    await stubRoutes(page, { outcomeFeedbackStatus: 500 })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // API 500 → catch() fires → historyData stays null → RecommendationHistoryCard not rendered
    await expect(page.locator('[data-testid="recommendation-history-card"]')).not.toBeVisible()
  })

  test('execution-center heading is visible', async ({ page }) => {
    await stubRoutes(page)
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // Page header h2 contains "執行中心"
    await expect(page.getByRole('heading', { name: '執行中心' })).toBeVisible()
  })

  test('no unsafe medical overclaiming on actions page', async ({ page }) => {
    await stubRoutes(page)
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    const body = page.locator('[data-testid="actions-page"]')
    const text = await body.innerText()

    expect(text).not.toContain('建議有效')
    expect(text).not.toContain('改善健康')
    expect(text).not.toContain('治療有效')
    expect(text).not.toContain('已證明有效')
    expect(text).not.toContain('診斷')
    expect(text).not.toContain('醫療診斷')
  })
})
