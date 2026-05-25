/**
 * P62 — Recommendation History Card Browser Acceptance
 *
 * Validates that:
 * - RecommendationHistoryCard renders not_useful / not_applicable / snoozed items
 * - Safe copy disclaimer is visible
 * - Summary counts (not_useful_count, not_applicable_count, snoozed_count) render
 * - Empty state renders when there are no outcomes
 * - Unsafe overclaiming phrases (建議有效 / 改善健康 / 治療有效 / 已證明有效) are NOT present
 *
 * Strategy: fully mocked (no live backend, no auth required).
 */

import { expect, test } from '@playwright/test'

// ── Shared fixtures ───────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD = {
  health_score: { overall_score: 75, components: {} },
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P62 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P62 test',
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

/** Full outcome-feedback response with multiple feedback statuses */
const OUTCOME_FEEDBACK_DATA = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 30,
  outcomes: [
    {
      action_id: 'action-p62-not-useful',
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
      action_id: 'action-p62-not-applicable',
      action_title: '增加每日步行量',
      status: 'not_applicable',
      completed_at: null,
      expected_health_impact: '預期改善心肺功能',
      outcome_status: 'not_applicable',
      actual_metric_change: null,
      adherence_status: 'dismissed',
      evidence_sources: [],
      confidence: 0.0,
      explanation: '使用者回饋：行動不適合目前狀況',
      next_check_in: null,
    },
    {
      action_id: 'action-p62-snoozed',
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
    {
      action_id: 'action-p62-completed',
      action_title: '每週量測體重',
      status: 'completed',
      completed_at: new Date().toISOString(),
      expected_health_impact: '追蹤體重趨勢',
      outcome_status: 'insufficient_data',
      actual_metric_change: null,
      adherence_status: 'completed',
      evidence_sources: [],
      confidence: 0.0,
      explanation: '目前尚在觀察期，資料仍不足以判斷趨勢',
      next_check_in: null,
    },
  ],
  summary: {
    improved_count: 0,
    unchanged_count: 0,
    deteriorated_count: 0,
    insufficient_data_count: 1,
    tracking_count: 0,
    not_useful_count: 1,
    not_applicable_count: 1,
    snoozed_count: 1,
    total_count: 4,
  },
}

/** Empty outcome-feedback response */
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

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: { outcomeFeedback?: object } = {},
) {
  const outcomeFeedback = opts.outcomeFeedback ?? OUTCOME_FEEDBACK_DATA

  await page.addInitScript(() => {
    // Minimal auth storage so platform pages render
    localStorage.setItem(
      'health_profile',
      JSON.stringify({
        id: 'person-self',
        display_name: 'Self',
        name: 'Self',
        age: 40,
        gender: 'male',
        onboarding_completed: true,
      }),
    )
    localStorage.setItem(
      'health_actions_cache_person-self',
      JSON.stringify([]),
    )
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
    if (path.endsWith('/dashboard')) return route.fulfill({ json: BASE_DASHBOARD })
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
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P62 — RecommendationHistoryCard', () => {
  test('renders not_useful item with correct label', async ({ page }) => {
    await stubRoutes(page)
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="recommendation-history-card"]', { timeout: 10_000 })

    const card = page.locator('[data-testid="recommendation-history-card"]')
    await expect(card).toBeVisible()
    await expect(card.getByText('每日量測血壓')).toBeVisible()
    await expect(card.getByText('沒有用').first()).toBeVisible()
  })

  test('renders not_applicable item with correct label', async ({ page }) => {
    await stubRoutes(page)
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="recommendation-history-card"]', { timeout: 10_000 })

    const card = page.locator('[data-testid="recommendation-history-card"]')
    await expect(card.getByText('增加每日步行量')).toBeVisible()
    await expect(card.getByText('不適合我').first()).toBeVisible()
  })

  test('renders snoozed item with correct label', async ({ page }) => {
    await stubRoutes(page)
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="recommendation-history-card"]', { timeout: 10_000 })

    const card = page.locator('[data-testid="recommendation-history-card"]')
    await expect(card.getByText('睡前冥想練習')).toBeVisible()
    await expect(card.getByText('已延後').first()).toBeVisible()
  })

  test('renders safe copy disclaimer', async ({ page }) => {
    await stubRoutes(page)
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="recommendation-history-card"]', { timeout: 10_000 })

    const card = page.locator('[data-testid="recommendation-history-card"]')
    await expect(card.getByText('回饋為使用者個人記錄，不代表醫療效果證明')).toBeVisible()
  })

  test('renders summary counts for dismissed/snoozed items', async ({ page }) => {
    await stubRoutes(page)
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="history-summary-bar"]', { timeout: 10_000 })

    const summaryBar = page.locator('[data-testid="history-summary-bar"]')
    await expect(summaryBar).toBeVisible()
    await expect(summaryBar.getByText(/沒有用\s*1/)).toBeVisible()
    await expect(summaryBar.getByText(/不適合\s*1/)).toBeVisible()
    await expect(summaryBar.getByText(/延後\s*1/)).toBeVisible()
  })

  test('shows insufficient_data safe copy for completed item without outcome', async ({ page }) => {
    await stubRoutes(page)
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="recommendation-history-card"]', { timeout: 10_000 })

    const card = page.locator('[data-testid="recommendation-history-card"]')
    await expect(card.getByText('目前尚無足夠後續資料判斷效果')).toBeVisible()
  })

  test('shows empty state when there are no outcomes', async ({ page }) => {
    await stubRoutes(page, { outcomeFeedback: OUTCOME_FEEDBACK_EMPTY })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="recommendation-history-card"]', { timeout: 10_000 })

    const card = page.locator('[data-testid="recommendation-history-card"]')
    await expect(card.getByText('目前還沒有足夠的建議回饋紀錄')).toBeVisible()
  })

  test('does NOT contain unsafe overclaiming phrases', async ({ page }) => {
    await stubRoutes(page)
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="recommendation-history-card"]', { timeout: 10_000 })

    const card = page.locator('[data-testid="recommendation-history-card"]')
    const text = await card.innerText()

    expect(text).not.toContain('建議有效')
    expect(text).not.toContain('改善健康')
    expect(text).not.toContain('治療有效')
    expect(text).not.toContain('已證明有效')
  })
})
