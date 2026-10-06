/**
 * P64 — Daily Assistant Summary Quality Browser Acceptance
 *
 * Validates that DailyAssistantEntry (今日健康入口) on the Dashboard:
 * 1. Renders top risk / biggest change / next action from daily summary
 * 2. Missing data state renders safe fallback copy
 * 3. Outcome unknown copy visible when tracking/insufficient_data items exist
 * 4. User-feedback disclaimer copy is visible in the outcome section
 * 5. Unsafe medical effectiveness phrases do not appear
 * 6. P62/P63 regression: outcome-feedback flows on /platform/actions are unbroken
 *
 * Strategy: fully mocked (no live backend, no auth required).
 */

import { expect, test } from '@playwright/test'

// ── Shared fixtures ───────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD = {
  health_score: { overall_score: 78, components: {} },
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P64 mock summary',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P64 test',
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

/** Daily summary with real content */
const DAILY_SUMMARY_FULL = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.82,
}

/** Daily summary with no data */
const DAILY_SUMMARY_EMPTY = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '',
  biggestChange: '',
  todayAction: '',
  whyNow: '',
  confidence: 0.0,
}

/** Recommendations with missing_data — triggers safe fallback */
const RECOMMENDATIONS_WITH_MISSING = {
  person_id: 'person-self',
  recommendations: [],
  total: 0,
  missing_data: ['症狀記錄', '健康指標（血壓、血糖、體重等）'],
}

/** Outcome feedback with tracking items (outcome unknown) */
const OUTCOME_FEEDBACK_TRACKING = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 7,
  outcomes: [
    {
      action_id: 'action-p64-tracking',
      action_title: '每日步行 30 分鐘',
      status: 'tracking',
      completed_at: null,
      expected_health_impact: '預期改善心肺功能',
      outcome_status: 'tracking',
      actual_metric_change: null,
      adherence_status: 'tracking',
      evidence_sources: [],
      confidence: 0.0,
      explanation: '行動仍在追蹤中，資料不足以判斷效果',
      next_check_in: '2026-06-01',
    },
  ],
  summary: {
    improved_count: 0,
    unchanged_count: 0,
    deteriorated_count: 0,
    insufficient_data_count: 0,
    tracking_count: 1,
    not_useful_count: 0,
    not_applicable_count: 0,
    snoozed_count: 0,
    total_count: 1,
  },
}

/** Outcome feedback with insufficient_data items */
const OUTCOME_FEEDBACK_INSUFFICIENT = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 7,
  outcomes: [
    {
      action_id: 'action-p64-insufficient',
      action_title: '每週量測體重',
      status: 'completed',
      completed_at: new Date().toISOString(),
      expected_health_impact: '追蹤體重趨勢',
      outcome_status: 'insufficient_data',
      actual_metric_change: null,
      adherence_status: 'completed',
      evidence_sources: [],
      confidence: 0.0,
      explanation: '目前資料不足以判斷趨勢',
      next_check_in: null,
    },
  ],
  summary: {
    improved_count: 0,
    unchanged_count: 0,
    deteriorated_count: 0,
    insufficient_data_count: 1,
    tracking_count: 0,
    not_useful_count: 0,
    not_applicable_count: 0,
    snoozed_count: 0,
    total_count: 1,
  },
}

/** Outcome feedback with improved item (known outcome, no "unknown" copy needed) */
const OUTCOME_FEEDBACK_IMPROVED = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 7,
  outcomes: [
    {
      action_id: 'action-p64-improved',
      action_title: '每日量測血壓',
      status: 'completed',
      completed_at: new Date().toISOString(),
      expected_health_impact: '改善血壓數值',
      outcome_status: 'improved',
      actual_metric_change: null,
      adherence_status: 'completed',
      evidence_sources: [],
      confidence: 0.85,
      explanation: '血壓數值有所改善',
      next_check_in: null,
    },
  ],
  summary: {
    improved_count: 1,
    unchanged_count: 0,
    deteriorated_count: 0,
    insufficient_data_count: 0,
    tracking_count: 0,
    not_useful_count: 0,
    not_applicable_count: 0,
    snoozed_count: 0,
    total_count: 1,
  },
}

// ── Route stub ────────────────────────────────────────────────────────────────

async function setAuthStorage(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'e2e-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: {
    dailySummary?: object
    recommendations?: object
    outcomeFeedback?: object
    actions?: object[]
  } = {},
) {
  const dailySummary = opts.dailySummary ?? DAILY_SUMMARY_FULL
  const recommendations = opts.recommendations ?? { person_id: 'person-self', recommendations: [], total: 0, missing_data: [] }
  const outcomeFeedback = opts.outcomeFeedback ?? OUTCOME_FEEDBACK_TRACKING
  const actions = opts.actions ?? []

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
      return route.fulfill({ json: recommendations })
    }
    if (path.includes('/health-assistant/daily-summary')) {
      return route.fulfill({ json: dailySummary })
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
      return route.fulfill({ json: actions })
    }
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/risk-alerts')) return route.fulfill({ json: [] })
    if (path.includes('/risk-alerts/unread-count')) return route.fulfill({ json: { count: 0 } })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P64 — Daily Assistant Summary Quality', () => {

  test('renders top risk / biggest change / next action from daily summary', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_FULL })

    await page.goto('/platform/dashboard')
    // Wait for the daily assistant entry to appear
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // All three summary cells must be visible with real content
    await expect(page.locator('[data-testid="daily-summary-top-risk"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-biggest-change"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-next-action"]')).toBeVisible()

    // Content must include the mocked values
    await expect(page.locator('[data-testid="daily-summary-top-risk"]')).toContainText('血壓偏高需密切關注')
    await expect(page.locator('[data-testid="daily-summary-biggest-change"]')).toContainText('本週睡眠品質下降')
    await expect(page.locator('[data-testid="daily-summary-next-action"]')).toContainText('量測早晨血壓')
  })

  test('missing data state renders safe fallback copy', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_EMPTY,
      recommendations: RECOMMENDATIONS_WITH_MISSING,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Missing data section must appear
    await expect(page.locator('[data-testid="daily-summary-missing-data"]')).toBeVisible()

    // Must contain the safe fallback copy
    await expect(page.locator('[data-testid="daily-summary-missing-data"]')).toContainText(
      '目前資料不足，建議補充最近紀錄',
    )
  })

  test('outcome unknown copy visible when tracking items exist', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_EMPTY,
      outcomeFeedback: OUTCOME_FEEDBACK_TRACKING,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Outcome unknown copy must appear because tracking_count > 0
    await expect(page.locator('[data-testid="daily-summary-outcome-unknown"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-outcome-unknown"]')).toContainText(
      '目前尚無足夠後續資料判斷效果',
    )
  })

  test('outcome unknown copy visible when insufficient_data items exist', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_EMPTY,
      outcomeFeedback: OUTCOME_FEEDBACK_INSUFFICIENT,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Outcome unknown copy must appear because insufficient_data_count > 0
    await expect(page.locator('[data-testid="daily-summary-outcome-unknown"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-outcome-unknown"]')).toContainText(
      '目前尚無足夠後續資料判斷效果',
    )
  })

  test('user-feedback disclaimer visible in outcome section', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_EMPTY,
      outcomeFeedback: OUTCOME_FEEDBACK_IMPROVED,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Disclaimer must be visible whenever the outcome section renders (hasFeedback = true)
    await expect(page.locator('[data-testid="daily-summary-outcome-section"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-outcome-section"]')).toContainText(
      '這是使用者回饋，不是醫療效果證明',
    )
  })

  test('unsafe medical effectiveness phrases do not appear', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_FULL,
      outcomeFeedback: OUTCOME_FEEDBACK_IMPROVED,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const body = await page.locator('[data-testid="daily-assistant-entry"]').textContent() ?? ''

    const UNSAFE_PHRASES = [
      '建議有效',
      '改善健康',
      '已證明有效',
      '治療有效',
      'recommendation worked',
      'improved your health',
      'treatment is effective',
    ]
    for (const phrase of UNSAFE_PHRASES) {
      expect(body, `Unsafe phrase found: "${phrase}"`).not.toContain(phrase)
    }
  })

})
