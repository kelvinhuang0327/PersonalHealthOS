/**
 * P73 — Daily Assistant Next Check-in Suggestion
 *
 * Validates that DailyAssistantEntry renders a next check-in suggestion with
 * data-testid="daily-summary-next-checkin" using the following priority:
 *
 *   1. trust.nextCheckInSuggestion  (Option B — dynamic API field from topRec.trust)
 *   2. fallback: summary.todayAction present  → '完成今日行動後，回來更新記錄。'
 *   3. fallback: summary.todayAction absent   → '今日資料已更新，明天繼續追蹤。'
 *
 * Guard: (trust?.nextCheckInSuggestion || summary) — always shown when daily
 * summary is loaded, regardless of whether topRec has a trust block.
 *
 * Tests:
 *  1. Next-checkin shows fallback with todayAction when trust is null
 *  2. Next-checkin shows fallback without todayAction when trust is null and todayAction absent
 *  3. Next-checkin shows trust.nextCheckInSuggestion when trust is populated
 *  4. P72 regression: escalation notice visible when escalationLevel !== 'none'
 *  5. P71 regression: encouragement visible when encouragement populated
 *  6. P70 regression: confidence signal visible when confidence > 0
 *  7. P69 regression: biggest-change context visible when biggestChange populated
 *  8. P68 regression: outcome improved badge visible when improved_count > 0
 *  9. P67 regression: action impact visible when todayAction exists
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
  explainability_summary: 'P73 mock summary',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P73 test',
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

/** Base daily summary — all fields populated */
const DAILY_SUMMARY_WITH_ACTION = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.82,
  encouragement: '你本週記錄完整，繼續保持！',
  escalation: {
    escalationLevel: 'watch',
    reasons: ['睡眠時長近期下降趨勢，需持續觀察。'],
    confidence: 0.65,
    recommendedAction: null,
    requiresFollowUp: false,
  },
}

/** Daily summary without todayAction — fallback should show 明天繼續追蹤 */
const DAILY_SUMMARY_NO_ACTION = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高',
  biggestChange: '本週睡眠品質下降',
  todayAction: '',      // empty string — should be treated as absent
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.7,
  encouragement: '繼續記錄！',
}

/** Recommendations with a trust block (nextCheckInSuggestion present) */
const RECOMMENDATIONS_WITH_TRUST = {
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

const RECOMMENDATIONS_NO_TRUST = {
  person_id: 'person-self',
  recommendations: [],
  total: 0,
  missing_data: [],
}

const RECOMMENDATIONS_WITH_MISSING = {
  person_id: 'person-self',
  recommendations: [],
  total: 0,
  missing_data: ['症狀記錄', '健康指標（血壓、血糖、體重等）'],
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
  const dailySummary    = opts.dailySummary    ?? DAILY_SUMMARY_WITH_ACTION
  const recommendations = opts.recommendations ?? RECOMMENDATIONS_NO_TRUST
  const outcomeFeedback = opts.outcomeFeedback ?? OUTCOME_EMPTY

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

test.describe('P73 — Daily Assistant Next Check-in Suggestion', () => {

  test('next-checkin shows completion-follow-up copy when todayAction present (trust null)', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WITH_ACTION,
      recommendations: RECOMMENDATIONS_NO_TRUST,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-next-checkin"]')
    await expect(el).toBeVisible()
    await expect(el).toContainText('完成今日行動後，回來更新記錄。')
  })

  test('next-checkin shows tomorrow-tracking copy when todayAction absent (trust null)', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_NO_ACTION,
      recommendations: RECOMMENDATIONS_NO_TRUST,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-next-checkin"]')
    await expect(el).toBeVisible()
    await expect(el).toContainText('今日資料已更新，明天繼續追蹤。')
  })

  test('next-checkin shows trust.nextCheckInSuggestion when trust is populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WITH_ACTION,
      recommendations: RECOMMENDATIONS_WITH_TRUST,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-next-checkin"]')
    await expect(el).toBeVisible()
    await expect(el).toContainText('3 天後回來查看血壓變化。')
  })

  test('P72 regression: escalation notice visible when escalationLevel !== none', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_WITH_ACTION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-escalation-notice"]')
    await expect(el).toBeVisible()
    await expect(el).toContainText('觀察')
  })

  test('P71 regression: encouragement visible when encouragement populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_WITH_ACTION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const enc = page.locator('[data-testid="daily-summary-encouragement"]')
    await expect(enc).toBeVisible()
    await expect(enc).toContainText('你本週記錄完整，繼續保持！')
  })

  test('P70 regression: confidence signal visible when confidence > 0', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_WITH_ACTION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const sig = page.locator('[data-testid="daily-summary-confidence-signal"]')
    await expect(sig).toBeVisible()
    await expect(sig).toContainText('可信度 82%')
  })

  test('P69 regression: biggest-change context visible when biggestChange populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_WITH_ACTION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const ctx = page.locator('[data-testid="daily-summary-biggest-change-context"]')
    await expect(ctx).toBeVisible()
    await expect(ctx).toContainText('此為近 7 天最顯著的健康趨勢變化')
  })

  test('P68 regression: outcome improved badge visible when improved_count > 0', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WITH_ACTION,
      outcomeFeedback: OUTCOME_WITH_IMPROVED,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const badge = page.locator('[data-testid="daily-summary-outcome-improved-badge"]')
    await expect(badge).toBeVisible()
    await expect(badge).toContainText('已改善 2 項')
  })

  test('P67 regression: action impact visible when todayAction exists', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_WITH_ACTION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const impact = page.locator('[data-testid="daily-summary-action-impact"]')
    await expect(impact).toBeVisible()
    await expect(impact).toContainText('完成後，小助手可以把今日行動與後續結果連起來追蹤')
  })

  test('P66 regression: missing-data explanation visible with missing data', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_WITH_ACTION,
      recommendations: RECOMMENDATIONS_WITH_MISSING,
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const expl = page.locator('[data-testid="daily-summary-missing-data-explanation"]')
    await expect(expl).toBeVisible()
    await expect(expl).toContainText('補齊後，小助手可以更準確判斷風險變化與下一步建議')
  })

  test('P65 regression: whyNow visible when whyNow populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_WITH_ACTION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const whyNow = page.locator('[data-testid="daily-summary-why-now"]')
    await expect(whyNow).toBeVisible()
    await expect(whyNow).toContainText('近期記錄顯示血壓波動加劇')
  })

  test('dashboard renders without ErrorBoundary fallback', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_WITH_ACTION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    await expect(page.locator('text=Something went wrong')).not.toBeVisible()
    await expect(page.locator('text=出現錯誤')).not.toBeVisible()
  })
})
