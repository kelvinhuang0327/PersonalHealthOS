/**
 * P69 — Daily Assistant Biggest Change Context Label
 *
 * Validates that DailyAssistantEntry renders a context label beneath the
 * 今日最大變化 (biggestChange) text when the field is populated:
 *
 * 1. [data-testid="daily-summary-biggest-change-context"] visible when biggestChange populated
 * 2. Context label absent when biggestChange is empty / absent
 * 3. P68 regression: outcome improved badge still visible when improved_count > 0
 * 4. P67 regression: action impact still visible when todayAction populated
 * 5. P66 regression: missing-data explanation still visible with missing data
 * 6. P65 regression: whyNow still visible when whyNow populated
 * 7. Dashboard renders without ErrorBoundary fallback
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
  explainability_summary: 'P69 mock summary',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P69 test',
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

/** Daily summary with all fields populated, including biggestChange */
const DAILY_SUMMARY_FULL = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.82,
}

/** Daily summary with biggestChange explicitly empty */
const DAILY_SUMMARY_NO_BIGGEST_CHANGE = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.75,
}

/** Daily summary entirely empty */
const DAILY_SUMMARY_EMPTY = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '',
  biggestChange: '',
  todayAction: '',
  whyNow: '',
  confidence: 0.0,
}

/** Recommendations with missing-data items (for P66 regression) */
const RECOMMENDATIONS_WITH_MISSING = {
  person_id: 'person-self',
  recommendations: [],
  total: 0,
  missing_data: ['症狀記錄', '健康指標（血壓、血糖、體重等）'],
}

const RECOMMENDATIONS_NO_MISSING = {
  person_id: 'person-self',
  recommendations: [],
  total: 0,
  missing_data: [],
}

/** Outcome feedback with improved_count > 0 (for P68 regression) */
const OUTCOME_WITH_IMPROVED = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 7,
  outcomes: [],
  summary: {
    improved_count: 2,
    unchanged_count: 1,
    deteriorated_count: 0,
    insufficient_data_count: 0,
    tracking_count: 0,
    not_useful_count: 0,
    not_applicable_count: 0,
    snoozed_count: 0,
    total_count: 3,
  },
}

/** Empty outcome — no data */
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

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: {
    dailySummary?: object
    recommendations?: object
    outcomeFeedback?: object
  } = {},
) {
  const dailySummary    = opts.dailySummary    ?? DAILY_SUMMARY_FULL
  const recommendations = opts.recommendations ?? RECOMMENDATIONS_NO_MISSING
  const outcomeFeedback = opts.outcomeFeedback ?? OUTCOME_WITH_IMPROVED

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
      return route.fulfill({ json: [] })
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

test.describe('P69 — Daily Assistant Biggest Change Context Label', () => {

  test('biggest-change context label visible when biggestChange populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_FULL,
      outcomeFeedback: OUTCOME_WITH_IMPROVED,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Biggest change card must be present
    await expect(page.locator('[data-testid="daily-summary-biggest-change"]')).toBeVisible()

    // Context label must appear
    const ctx = page.locator('[data-testid="daily-summary-biggest-change-context"]')
    await expect(ctx).toBeVisible()
    await expect(ctx).toContainText('近 7 天')
  })

  test('biggest-change context label absent when biggestChange is empty', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_NO_BIGGEST_CHANGE,
      outcomeFeedback: OUTCOME_WITH_IMPROVED,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Biggest change card still renders (shows fallback text)
    await expect(page.locator('[data-testid="daily-summary-biggest-change"]')).toBeVisible()

    // Context label must NOT appear when biggestChange is empty
    await expect(page.locator('[data-testid="daily-summary-biggest-change-context"]')).not.toBeVisible()
  })

  test('P68 regression: outcome improved badge still visible when improved_count > 0', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_FULL,
      outcomeFeedback: OUTCOME_WITH_IMPROVED,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const badge = page.locator('[data-testid="daily-summary-outcome-improved-badge"]')
    await expect(badge).toBeVisible()
    await expect(badge).toContainText('已改善')
    await expect(badge).toContainText('2')
  })

  test('P67 regression: action impact still visible when todayAction populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_FULL,
      outcomeFeedback: OUTCOME_WITH_IMPROVED,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const impact = page.locator('[data-testid="daily-summary-action-impact"]')
    await expect(impact).toBeVisible()
    await expect(impact).toContainText('完成後')
  })

  test('P66 regression: missing-data explanation still visible with missing data', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_EMPTY,
      recommendations: RECOMMENDATIONS_WITH_MISSING,
      outcomeFeedback: OUTCOME_EMPTY,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    await expect(page.locator('[data-testid="daily-summary-missing-data-explanation"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-missing-data-explanation"]')).toContainText('補齊後')
  })

  test('P65 regression: whyNow still visible when whyNow populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_FULL,
      outcomeFeedback: OUTCOME_WITH_IMPROVED,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const whyNow = page.locator('[data-testid="daily-summary-why-now"]')
    await expect(whyNow).toBeVisible()
    await expect(whyNow).toContainText('近期記錄顯示血壓波動加劇')
  })

  test('dashboard renders without ErrorBoundary fallback', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_FULL,
      outcomeFeedback: OUTCOME_WITH_IMPROVED,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const body = await page.locator('body').textContent() ?? ''
    expect(body).not.toContain('載入失敗，請重新整理')
    expect(body).not.toContain('Something went wrong')
  })

})
