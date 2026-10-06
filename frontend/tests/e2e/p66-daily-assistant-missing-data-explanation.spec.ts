/**
 * P66 — Daily Assistant Missing Data Explanation
 *
 * Validates that DailyAssistantEntry renders per-item gain text and a capability
 * explanation paragraph when the missing-data list is non-empty:
 *
 * 1. When missingData has items → [data-testid="daily-summary-missing-data-explanation"]
 *    is visible and contains the gain sentence.
 * 2. When missingData has items → gain text for a known item is rendered inline.
 * 3. When missingData is empty and no recommendations → the missing-data section
 *    (including explanation) does not appear.
 * 4. P65 regression: [data-testid="daily-summary-why-now"] remains visible when
 *    whyNow is populated.
 * 5. Dashboard does not render ErrorBoundary fallback.
 *
 * Strategy: fully mocked (no live backend, no auth required).
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
  explainability_summary: 'P66 mock summary',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P66 test',
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

/** Daily summary with whyNow and top risk populated */
const DAILY_SUMMARY_FULL = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.82,
}

/** Daily summary with no content */
const DAILY_SUMMARY_EMPTY = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '',
  biggestChange: '',
  todayAction: '',
  whyNow: '',
  confidence: 0.0,
}

/** Recommendations stub with known missing-data items */
const RECOMMENDATIONS_WITH_MISSING = {
  person_id: 'person-self',
  recommendations: [],
  total: 0,
  missing_data: ['症狀記錄', '健康指標（血壓、血糖、體重等）'],
}

/** Recommendations stub with NO missing data */
const RECOMMENDATIONS_NO_MISSING = {
  person_id: 'person-self',
  recommendations: [],
  total: 0,
  missing_data: [],
}

const EMPTY_OUTCOME = {
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
  } = {},
) {
  const dailySummary = opts.dailySummary ?? DAILY_SUMMARY_FULL
  const recommendations = opts.recommendations ?? RECOMMENDATIONS_WITH_MISSING

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
      return route.fulfill({ json: EMPTY_OUTCOME })
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

test.describe('P66 — Daily Assistant Missing Data Explanation', () => {

  test('explanation paragraph renders when missingData has items', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_EMPTY,
      recommendations: RECOMMENDATIONS_WITH_MISSING,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Explanation paragraph must be visible
    const explanation = page.locator('[data-testid="daily-summary-missing-data-explanation"]')
    await expect(explanation).toBeVisible()

    // Must contain the gain sentence
    await expect(explanation).toContainText('補齊後')
    await expect(explanation).toContainText('風險變化')
  })

  test('per-item gain text renders for known missing-data items', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_EMPTY,
      recommendations: RECOMMENDATIONS_WITH_MISSING,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Missing-data section must be visible
    const missingSection = page.locator('[data-testid="daily-summary-missing-data"]')
    await expect(missingSection).toBeVisible()

    // Gain text for '症狀記錄' should appear inside the section
    await expect(missingSection).toContainText('幫助偵測症狀模式')

    // Gain text for '健康指標（血壓、血糖、體重等）' should appear
    await expect(missingSection).toContainText('讓血壓、血糖趨勢更準確可信')
  })

  test('missing-data section absent when missingData is empty', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_EMPTY,
      recommendations: RECOMMENDATIONS_NO_MISSING,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Missing-data section must NOT appear
    await expect(page.locator('[data-testid="daily-summary-missing-data"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-missing-data-explanation"]')).not.toBeVisible()
  })

  test('P65 regression: whyNow still visible when populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_FULL,
      recommendations: RECOMMENDATIONS_WITH_MISSING,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // whyNow must still render (P65 regression)
    const whyNow = page.locator('[data-testid="daily-summary-why-now"]')
    await expect(whyNow).toBeVisible()
    await expect(whyNow).toContainText('近期記錄顯示血壓波動加劇')
  })

  test('dashboard renders without ErrorBoundary fallback', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_FULL,
      recommendations: RECOMMENDATIONS_WITH_MISSING,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // ErrorBoundary fallback must not appear
    const body = await page.locator('body').textContent() ?? ''
    expect(body).not.toContain('載入失敗，請重新整理')
    expect(body).not.toContain('Something went wrong')
  })

})
