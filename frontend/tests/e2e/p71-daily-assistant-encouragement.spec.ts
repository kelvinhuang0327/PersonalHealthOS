/**
 * P71 — Daily Assistant Encouragement Message
 *
 * Validates that DailyAssistantEntry renders the encouragement message from
 * DailyHealthSummary.encouragement when present, non-empty, and not whitespace-only.
 *
 *  1. Encouragement block appears when summary.encouragement is populated
 *  2. Encouragement block displays the provided encouragement text
 *  3. Encouragement block does not appear when encouragement is absent
 *  4. Encouragement block does not appear when encouragement is empty string
 *  5. Encouragement block does not appear when encouragement is whitespace-only
 *  6. P70 regression: confidence signal visible when confidence > 0
 *  7. P69 regression: biggest-change context label visible when biggestChange populated
 *  8. P68 regression: outcome improved badge visible when improved_count > 0
 *  9. P67 regression: action impact visible when todayAction populated
 * 10. P66 regression: missing-data explanation visible with missing data
 * 11. P65 regression: whyNow visible when whyNow populated
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
  explainability_summary: 'P71 mock summary',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P71 test',
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

/** Daily summary with encouragement populated */
const DAILY_SUMMARY_WITH_ENCOURAGEMENT = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.82,
  encouragement: '你本週的血壓記錄完整，繼續保持這個好習慣！',
}

/** Daily summary with encouragement absent (field not present) */
const DAILY_SUMMARY_NO_ENCOURAGEMENT = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.82,
  // encouragement intentionally omitted
}

/** Daily summary with encouragement as empty string */
const DAILY_SUMMARY_EMPTY_ENCOURAGEMENT = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.82,
  encouragement: '',
}

/** Daily summary with encouragement as whitespace-only */
const DAILY_SUMMARY_WHITESPACE_ENCOURAGEMENT = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.82,
  encouragement: '   ',
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
  const dailySummary    = opts.dailySummary    ?? DAILY_SUMMARY_WITH_ENCOURAGEMENT
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

test.describe('P71 — Daily Assistant Encouragement Message', () => {

  test('encouragement block appears when summary.encouragement is populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WITH_ENCOURAGEMENT,
      outcomeFeedback: OUTCOME_EMPTY,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-encouragement"]')
    await expect(el).toBeVisible()
  })

  test('encouragement block displays the provided encouragement text', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WITH_ENCOURAGEMENT,
      outcomeFeedback: OUTCOME_EMPTY,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-encouragement"]')
    await expect(el).toContainText('你本週的血壓記錄完整，繼續保持這個好習慣！')
    await expect(el).toContainText('小助手鼓勵')
  })

  test('encouragement block does not appear when encouragement is absent', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_NO_ENCOURAGEMENT,
      outcomeFeedback: OUTCOME_EMPTY,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-encouragement"]')
    await expect(el).not.toBeVisible()
  })

  test('encouragement block does not appear when encouragement is empty string', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_EMPTY_ENCOURAGEMENT,
      outcomeFeedback: OUTCOME_EMPTY,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-encouragement"]')
    await expect(el).not.toBeVisible()
  })

  test('encouragement block does not appear when encouragement is whitespace-only', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WHITESPACE_ENCOURAGEMENT,
      outcomeFeedback: OUTCOME_EMPTY,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-encouragement"]')
    await expect(el).not.toBeVisible()
  })

  test('P70 regression: confidence signal visible when confidence > 0', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WITH_ENCOURAGEMENT, // confidence: 0.82
      outcomeFeedback: OUTCOME_EMPTY,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const sig = page.locator('[data-testid="daily-summary-confidence-signal"]')
    await expect(sig).toBeVisible()
    await expect(sig).toContainText('可信度 82%')
  })

  test('P69 regression: biggest-change context label visible when biggestChange populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WITH_ENCOURAGEMENT,
      outcomeFeedback: OUTCOME_EMPTY,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const ctx = page.locator('[data-testid="daily-summary-biggest-change-context"]')
    await expect(ctx).toBeVisible()
    await expect(ctx).toContainText('此為近 7 天最顯著的健康趨勢變化')
  })

  test('P68 regression: outcome improved badge visible when improved_count > 0', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WITH_ENCOURAGEMENT,
      outcomeFeedback: OUTCOME_WITH_IMPROVED,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const badge = page.locator('[data-testid="daily-summary-outcome-improved-badge"]')
    await expect(badge).toBeVisible()
    await expect(badge).toContainText('已改善 2 項')
  })

  test('P67 regression: action impact visible when todayAction populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WITH_ENCOURAGEMENT,
      outcomeFeedback: OUTCOME_EMPTY,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const impact = page.locator('[data-testid="daily-summary-action-impact"]')
    await expect(impact).toBeVisible()
    await expect(impact).toContainText('完成後，小助手可以把今日行動與後續結果連起來追蹤')
  })

  test('P66 regression: missing-data explanation visible with missing data', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WITH_ENCOURAGEMENT,
      recommendations: RECOMMENDATIONS_WITH_MISSING,
      outcomeFeedback: OUTCOME_EMPTY,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const expl = page.locator('[data-testid="daily-summary-missing-data-explanation"]')
    await expect(expl).toBeVisible()
    await expect(expl).toContainText('補齊後，小助手可以更準確判斷風險變化與下一步建議')
  })

  test('P65 regression: whyNow visible when whyNow populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WITH_ENCOURAGEMENT,
      outcomeFeedback: OUTCOME_EMPTY,
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
      dailySummary: DAILY_SUMMARY_WITH_ENCOURAGEMENT,
      outcomeFeedback: OUTCOME_EMPTY,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // ErrorBoundary fallback text — must NOT appear
    await expect(page.locator('text=Something went wrong')).not.toBeVisible()
    await expect(page.locator('text=出現錯誤')).not.toBeVisible()
  })
})
