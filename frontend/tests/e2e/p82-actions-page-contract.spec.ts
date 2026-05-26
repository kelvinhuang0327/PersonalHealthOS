/**
 * P82 — Actions Page Contract Smoke
 *
 * High-level contract for /platform/actions recommendation history,
 * feedback loop, and snooze surfaces (established across P80–P81).
 *
 * This is not a detailed behavior spec — it is a regression gate that
 * verifies the stable test-id surface remains intact after any PR
 * touching the Actions page or its child components.
 *
 * Contract doc: docs/security/P82_ACTIONS_PAGE_CONTRACT.md
 *
 * Strategy: fully mocked (no live backend, no auth required).
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
  explainability_summary: 'P82 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P82 test',
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

const OUTCOME_FEEDBACK_DATA = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 30,
  outcomes: [
    {
      action_id: 'action-p82-not-useful',
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
  ],
  summary: {
    improved_count: 0,
    unchanged_count: 0,
    deteriorated_count: 0,
    insufficient_data_count: 0,
    tracking_count: 0,
    not_useful_count: 1,
    not_applicable_count: 0,
    snoozed_count: 0,
    total_count: 1,
  },
}

/** Triggers grouped.completed → actions-feedback-loop */
const DONE_ACTION = {
  id: 'action-p82-done',
  person_id: 'person-self',
  source_type: 'user_created',
  source_id: 'user-p82-done',
  title: '每週量測體重',
  description: '追蹤體重趨勢',
  action_type: 'lifestyle',
  priority: 'medium',
  status: 'done',
  frequency: 'weekly',
  streak_count: 2,
  resurface_count: 0,
  confidence: 0.8,
  evidence_level: 'B',
  guideline_source: null,
  rule_id: null,
  category: 'health',
  impact_status: 'no_change',
  reminder_status: null,
  snoozed_until: null,
  completed_at: new Date().toISOString(),
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  outcomes: [],
}

/** Triggers grouped.snoozed → actions-snoozed-section */
const SNOOZED_ACTION = {
  id: 'action-p82-snoozed',
  person_id: 'person-self',
  source_type: 'recommendation',
  source_id: 'ha_rec_p82_activity',
  title: '每日步行目標',
  description: '活動量不足',
  action_type: 'lifestyle',
  priority: 'medium',
  status: 'snoozed',
  snoozed_until: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
  frequency: 'daily',
  streak_count: 0,
  resurface_count: 0,
  confidence: 0.7,
  evidence_level: 'B',
  guideline_source: null,
  rule_id: 'ha_rec_p82_activity',
  category: 'health',
  impact_status: null,
  reminder_status: null,
  completed_at: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  outcomes: [],
}

// ── Route stub ────────────────────────────────────────────────────────────────

type StubOptions = {
  actions?: object[]
  outcomeFeedback?: object
  outcomeFeedbackStatus?: number
  freezeDashboard?: boolean
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: StubOptions = {},
) {
  const {
    actions = [],
    outcomeFeedback = OUTCOME_FEEDBACK_DATA,
    outcomeFeedbackStatus = 200,
    freezeDashboard = false,
  } = opts

  let dashboardResolve: (() => void) | null = null

  await page.addInitScript(() => {
    localStorage.setItem('token', 'p82-mock-token')
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
        json: { topRisk: '', biggestChange: '', todayAction: '', generated_at: new Date().toISOString() },
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
        await new Promise<void>((resolve) => { dashboardResolve = resolve })
      }
      return route.fulfill({ json: BASE_DASHBOARD })
    }
    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    // Intercept getActionOutcomes for any done action (called by ActionFeedbackCard)
    if (path.includes('/actions/') && path.endsWith('/outcomes') && method === 'GET') {
      return route.fulfill({ json: [] })
    }
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') {
      return route.fulfill({ json: actions })
    }
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if (path.endsWith('/weekly-report')) return route.fulfill({ json: { items: [] } })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })

  return {
    releaseDashboard: () => {
      if (dashboardResolve) { dashboardResolve(); dashboardResolve = null }
    },
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P82 — Actions Page Contract', () => {
  /**
   * Contract test 1 — full loaded state
   * All stable test-id surfaces must be visible simultaneously
   * when the page loads with completed actions + snoozed actions + outcome history.
   */
  test('contract: loaded state — actions-page, recommendation-history-card, feedback-loop, snoozed-section all visible', async ({ page }) => {
    await stubRoutes(page, { actions: [DONE_ACTION, SNOOZED_ACTION] })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // Required surfaces
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()
    await expect(page.locator('[data-testid="recommendation-history-card"]')).toBeVisible()
    await expect(page.locator('[data-testid="actions-feedback-loop"]')).toBeVisible()
    await expect(page.locator('[data-testid="actions-snoozed-section"]')).toBeVisible()

    // Loading skeleton must be gone
    await expect(page.locator('[data-testid="actions-loading"]')).not.toBeVisible()
  })

  /**
   * Contract test 2 — loading state
   * actions-loading visible while getDashboard is pending.
   * actions-page must not be visible until dashboard resolves.
   */
  test('contract: loading state — actions-loading visible while dashboard pending', async ({ page }) => {
    const { releaseDashboard } = await stubRoutes(page, { freezeDashboard: true })
    const nav = page.goto('/platform/actions')

    await page.waitForSelector('[data-testid="actions-loading"]', { timeout: 10_000 })
    await expect(page.locator('[data-testid="actions-loading"]')).toBeVisible()
    await expect(page.locator('[data-testid="actions-page"]')).not.toBeVisible()

    releaseDashboard()
    await nav
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })
    await expect(page.locator('[data-testid="actions-loading"]')).not.toBeVisible()
  })

  /**
   * Contract test 3 — API failure safe
   * When outcome-feedback API returns 500:
   * - actions-page must remain visible (no crash)
   * - recommendation-history-card must not render
   */
  test('contract: api failure safe — page survives outcome-feedback 500, history card absent', async ({ page }) => {
    await stubRoutes(page, { outcomeFeedbackStatus: 500 })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // Page must not crash
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()
    await expect(page.getByText('Something went wrong', { exact: false })).not.toBeVisible()

    // History card must be absent (historyData stays null when API fails)
    await expect(page.locator('[data-testid="recommendation-history-card"]')).not.toBeVisible()
  })

  /**
   * Contract test 4 — medical overclaim guard
   * The Actions page must not contain unsafe medical certainty phrases
   * even when all sections are visible.
   * See: docs/security/P82_ACTIONS_PAGE_CONTRACT.md §4.5
   */
  test('contract: medical overclaim guard — no prohibited phrases visible', async ({ page }) => {
    await stubRoutes(page, { actions: [DONE_ACTION, SNOOZED_ACTION] })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    const text = await page.locator('[data-testid="actions-page"]').innerText()

    expect(text).not.toContain('建議有效')
    expect(text).not.toContain('改善健康')
    expect(text).not.toContain('治療有效')
    expect(text).not.toContain('已證明有效')
    expect(text).not.toContain('醫療診斷')
  })
})
