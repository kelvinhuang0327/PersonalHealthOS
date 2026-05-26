/**
 * P81 — Actions Page Feedback / Snooze Detail Smoke
 *
 * Validates that /platform/actions:
 * - Shows the feedback loop section (actions-feedback-loop) when a completed
 *   action is present in the mocked actions list
 * - Hides the feedback loop section when no completed actions exist
 * - Shows the snoozed section (actions-snoozed-section) when a snoozed action
 *   is present in the mocked actions list
 * - Hides the snoozed section when no snoozed actions exist
 * - Keeps recommendation-history-card visible alongside feedback/snooze sections
 * - Contains no unsafe medical overclaiming phrases
 *
 * Strategy: fully mocked (no live backend, no auth required).
 * Testids added in P81: actions-feedback-loop, actions-snoozed-section.
 * Testids from P80 reused: actions-page.
 * Testids from P62 reused: recommendation-history-card.
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
  explainability_summary: 'P81 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P81 test',
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
      action_id: 'action-p81-history',
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

/** A completed action that triggers Section 4 (行動效果回饵) */
const DONE_ACTION = {
  id: 'action-p81-done',
  person_id: 'person-self',
  source_type: 'user_created',
  source_id: 'user-p81-done',
  title: '每週量測體重',
  description: '追蹤體重趨勢',
  action_type: 'lifestyle',
  priority: 'medium',
  status: 'done',
  frequency: 'weekly',
  streak_count: 3,
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

/** A snoozed action that triggers the 稍後提醒 section */
const SNOOZED_ACTION = {
  id: 'action-p81-snoozed',
  person_id: 'person-self',
  source_type: 'recommendation',
  source_id: 'ha_rec_p81_activity',
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
  rule_id: 'ha_rec_p81_activity',
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
  outcomeFeedbackStatus?: number
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: StubOptions = {},
) {
  const { actions = [], outcomeFeedbackStatus = 200 } = opts

  await page.addInitScript(() => {
    localStorage.setItem('token', 'p81-mock-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
    localStorage.setItem('health_actions_cache_person-self', JSON.stringify([]))
  })

  await page.route('**/api/v1/**', (route) => {
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
      return route.fulfill({ json: OUTCOME_FEEDBACK_DATA })
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
    if (path.endsWith('/dashboard')) return route.fulfill({ json: BASE_DASHBOARD })
    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    // Intercept getActionOutcomes for DONE_ACTION (called by ActionFeedbackCard)
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
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P81 — Actions Page Feedback / Snooze Detail Smoke', () => {
  test('feedback-loop section visible when completed action exists', async ({ page }) => {
    await stubRoutes(page, { actions: [DONE_ACTION] })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    const feedbackLoop = page.locator('[data-testid="actions-feedback-loop"]')
    await expect(feedbackLoop).toBeVisible()
    await expect(feedbackLoop.getByRole('heading', { name: '行動效果回饵' })).toBeVisible()
    await expect(feedbackLoop.getByText('每週量測體重')).toBeVisible()
  })

  test('feedback-loop section absent when no completed actions', async ({ page }) => {
    await stubRoutes(page, { actions: [] })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // No done actions → Section 4 not rendered
    await expect(page.locator('[data-testid="actions-feedback-loop"]')).not.toBeVisible()
  })

  test('snoozed section visible when snoozed action exists', async ({ page }) => {
    await stubRoutes(page, { actions: [SNOOZED_ACTION] })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    const snoozedSection = page.locator('[data-testid="actions-snoozed-section"]')
    await expect(snoozedSection).toBeVisible()
    await expect(snoozedSection.getByRole('heading', { name: '稍後提醒' })).toBeVisible()
    await expect(snoozedSection.getByText('每日步行目標')).toBeVisible()
  })

  test('snoozed section absent when no snoozed actions', async ({ page }) => {
    await stubRoutes(page, { actions: [] })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // No snoozed actions → snoozed section not rendered
    await expect(page.locator('[data-testid="actions-snoozed-section"]')).not.toBeVisible()
  })

  test('both feedback-loop and snoozed section visible simultaneously', async ({ page }) => {
    await stubRoutes(page, { actions: [DONE_ACTION, SNOOZED_ACTION] })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    await expect(page.locator('[data-testid="actions-feedback-loop"]')).toBeVisible()
    await expect(page.locator('[data-testid="actions-snoozed-section"]')).toBeVisible()
  })

  test('recommendation-history-card still visible alongside feedback and snooze sections', async ({ page }) => {
    await stubRoutes(page, { actions: [DONE_ACTION, SNOOZED_ACTION] })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="recommendation-history-card"]', { timeout: 10_000 })

    // All three sections co-exist on the page
    await expect(page.locator('[data-testid="actions-feedback-loop"]')).toBeVisible()
    await expect(page.locator('[data-testid="actions-snoozed-section"]')).toBeVisible()
    await expect(page.locator('[data-testid="recommendation-history-card"]')).toBeVisible()
  })

  test('no unsafe medical overclaiming phrases on actions page with feedback and snooze', async ({ page }) => {
    await stubRoutes(page, { actions: [DONE_ACTION, SNOOZED_ACTION] })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    const body = page.locator('[data-testid="actions-page"]')
    const text = await body.innerText()

    expect(text).not.toContain('建議有效')
    expect(text).not.toContain('改善健康')
    expect(text).not.toContain('治療有效')
    expect(text).not.toContain('已證明有效')
    expect(text).not.toContain('醫療診斷')
  })
})
