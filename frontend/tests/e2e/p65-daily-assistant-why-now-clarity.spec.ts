/**
 * P65 — Daily Assistant Why-Now Clarity
 *
 * Validates that DailyAssistantEntry renders the `whyNow` explanation from the
 * daily summary data:
 * 1. When whyNow is populated → [data-testid="daily-summary-why-now"] is visible
 *    and contains the expected contextual explanation text.
 * 2. When whyNow is empty string → [data-testid="daily-summary-why-now"] is absent.
 * 3. P64 regression: top-risk card still renders with risk text in both states.
 * 4. P64 regression: overall daily-assistant-entry is visible and not broken.
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
  explainability_summary: 'P65 mock summary',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P65 test',
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

/** Daily summary with whyNow populated */
const DAILY_SUMMARY_WITH_WHY_NOW = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.82,
}

/** Daily summary with whyNow empty — should NOT render why-now element */
const DAILY_SUMMARY_WITHOUT_WHY_NOW = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '',
  confidence: 0.75,
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
  dailySummary: object,
) {
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
      return route.fulfill({
        json: { person_id: 'person-self', recommendations: [], total: 0, missing_data: [] },
      })
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

test.describe('P65 — Daily Assistant Why-Now Clarity', () => {

  test('why-now explanation renders when whyNow is populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, DAILY_SUMMARY_WITH_WHY_NOW)

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // why-now element must be visible
    const whyNow = page.locator('[data-testid="daily-summary-why-now"]')
    await expect(whyNow).toBeVisible()

    // must contain the mocked whyNow text
    await expect(whyNow).toContainText('近期記錄顯示血壓波動加劇')

    // must include the label prefix
    await expect(whyNow).toContainText('為什麼重要')
  })

  test('why-now element is absent when whyNow is empty string', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, DAILY_SUMMARY_WITHOUT_WHY_NOW)

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // why-now element must NOT be rendered when whyNow is ''
    await expect(page.locator('[data-testid="daily-summary-why-now"]')).not.toBeVisible()
  })

  test('P64 regression: top-risk card renders risk text with whyNow present', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, DAILY_SUMMARY_WITH_WHY_NOW)

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Top-risk card must still show the primary risk text
    const topRisk = page.locator('[data-testid="daily-summary-top-risk"]')
    await expect(topRisk).toBeVisible()
    await expect(topRisk).toContainText('血壓偏高需密切關注')
  })

  test('P64 regression: top-risk card renders risk text without whyNow', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, DAILY_SUMMARY_WITHOUT_WHY_NOW)

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Top-risk card must still show the primary risk text even when whyNow is absent
    const topRisk = page.locator('[data-testid="daily-summary-top-risk"]')
    await expect(topRisk).toBeVisible()
    await expect(topRisk).toContainText('血壓偏高需密切關注')
  })

})
