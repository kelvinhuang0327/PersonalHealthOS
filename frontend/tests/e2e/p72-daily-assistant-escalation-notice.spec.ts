/**
 * P72 — Daily Assistant Escalation Notice
 *
 * Validates that DailyAssistantEntry renders an escalation notice from
 * DailyHealthSummary.escalation when escalationLevel is not 'none'.
 *
 * EscalationDecision shape (from lib/api.ts):
 *   escalationLevel: 'none' | 'watch' | 'warning' | 'urgent'
 *   reasons: string[]
 *   confidence: number
 *   recommendedAction: string | null
 *   requiresFollowUp: boolean
 *
 * Guard: summary?.escalation != null && summary.escalation.escalationLevel !== 'none'
 *
 *  1. Escalation notice appears when escalationLevel === 'urgent'
 *  2. Escalation notice displays provided reason text
 *  3. Escalation notice displays urgency label for 'urgent' level
 *  4. Escalation notice displays urgency label for 'warning' level
 *  5. Escalation notice displays urgency label for 'watch' level
 *  6. Escalation notice displays recommendedAction when present
 *  7. Escalation notice does not appear when escalation is absent
 *  8. Escalation notice does not appear when escalationLevel === 'none'
 *  9. P71 regression: encouragement visible when encouragement populated
 * 10. P70 regression: confidence signal visible when confidence > 0
 * 11. P69 regression: biggest-change context label visible when biggestChange populated
 * 12. P68 regression: outcome improved badge visible when improved_count > 0
 * 13. P67 regression: action impact visible when todayAction populated
 * 14. P66 regression: missing-data explanation visible with missing data
 * 15. P65 regression: whyNow visible when whyNow populated
 * 16. Dashboard renders without ErrorBoundary fallback
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
  explainability_summary: 'P72 mock summary',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P72 test',
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

/** Base daily summary — all fields populated, no escalation */
const DAILY_SUMMARY_BASE = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '本週睡眠品質下降 15%',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.82,
  encouragement: '你本週記錄完整，繼續保持！',
}

/** Daily summary with urgent escalation */
const DAILY_SUMMARY_ESCALATION_URGENT = {
  ...DAILY_SUMMARY_BASE,
  escalation: {
    escalationLevel: 'urgent',
    reasons: ['收縮壓連續 3 天超過 160mmHg，建議盡快就醫。'],
    confidence: 0.91,
    recommendedAction: '建議今日聯繫醫師或前往診所量測血壓。',
    requiresFollowUp: true,
  },
}

/** Daily summary with warning escalation */
const DAILY_SUMMARY_ESCALATION_WARNING = {
  ...DAILY_SUMMARY_BASE,
  escalation: {
    escalationLevel: 'warning',
    reasons: ['心率偏快，近 5 天平均 98bpm。'],
    confidence: 0.78,
    recommendedAction: null,
    requiresFollowUp: false,
  },
}

/** Daily summary with watch escalation */
const DAILY_SUMMARY_ESCALATION_WATCH = {
  ...DAILY_SUMMARY_BASE,
  escalation: {
    escalationLevel: 'watch',
    reasons: ['睡眠時長近期下降趨勢，需持續觀察。'],
    confidence: 0.65,
    recommendedAction: null,
    requiresFollowUp: false,
  },
}

/** Daily summary with escalation = none — notice must NOT appear */
const DAILY_SUMMARY_ESCALATION_NONE = {
  ...DAILY_SUMMARY_BASE,
  escalation: {
    escalationLevel: 'none',
    reasons: [],
    confidence: 0.5,
    recommendedAction: null,
    requiresFollowUp: false,
  },
}

/** Daily summary without escalation field — notice must NOT appear */
const DAILY_SUMMARY_NO_ESCALATION = {
  ...DAILY_SUMMARY_BASE,
  // escalation intentionally omitted
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
  const dailySummary    = opts.dailySummary    ?? DAILY_SUMMARY_ESCALATION_URGENT
  const recommendations = opts.recommendations ?? RECOMMENDATIONS_NO_MISSING
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

test.describe('P72 — Daily Assistant Escalation Notice', () => {

  test('escalation notice appears when escalationLevel === urgent', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_URGENT })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-escalation-notice"]')
    await expect(el).toBeVisible()
  })

  test('escalation notice displays provided reason text', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_URGENT })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-escalation-notice"]')
    await expect(el).toContainText('收縮壓連續 3 天超過 160mmHg')
  })

  test('escalation notice displays urgency label for urgent level', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_URGENT })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-escalation-notice"]')
    await expect(el).toContainText('需要留意')
    await expect(el).toContainText('緊急')
  })

  test('escalation notice displays urgency label for warning level', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_WARNING })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-escalation-notice"]')
    await expect(el).toBeVisible()
    await expect(el).toContainText('警告')
    await expect(el).toContainText('心率偏快')
  })

  test('escalation notice displays urgency label for watch level', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_WATCH })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-escalation-notice"]')
    await expect(el).toBeVisible()
    await expect(el).toContainText('觀察')
    await expect(el).toContainText('睡眠時長近期下降趨勢')
  })

  test('escalation notice displays recommendedAction when present', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_URGENT })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-escalation-notice"]')
    await expect(el).toContainText('建議：')
    await expect(el).toContainText('建議今日聯繫醫師或前往診所量測血壓')
  })

  test('escalation notice does not appear when escalation is absent', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_NO_ESCALATION })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-escalation-notice"]')
    await expect(el).not.toBeVisible()
  })

  test('escalation notice does not appear when escalationLevel === none', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_NONE })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const el = page.locator('[data-testid="daily-summary-escalation-notice"]')
    await expect(el).not.toBeVisible()
  })

  test('P71 regression: encouragement visible when encouragement populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_URGENT })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const enc = page.locator('[data-testid="daily-summary-encouragement"]')
    await expect(enc).toBeVisible()
    await expect(enc).toContainText('你本週記錄完整，繼續保持！')
  })

  test('P70 regression: confidence signal visible when confidence > 0', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_URGENT })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const sig = page.locator('[data-testid="daily-summary-confidence-signal"]')
    await expect(sig).toBeVisible()
    await expect(sig).toContainText('可信度 82%')
  })

  test('P69 regression: biggest-change context label visible when biggestChange populated', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_URGENT })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const ctx = page.locator('[data-testid="daily-summary-biggest-change-context"]')
    await expect(ctx).toBeVisible()
    await expect(ctx).toContainText('此為近 7 天最顯著的健康趨勢變化')
  })

  test('P68 regression: outcome improved badge visible when improved_count > 0', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_ESCALATION_URGENT,
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
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_URGENT })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const impact = page.locator('[data-testid="daily-summary-action-impact"]')
    await expect(impact).toBeVisible()
    await expect(impact).toContainText('完成後，小助手可以把今日行動與後續結果連起來追蹤')
  })

  test('P66 regression: missing-data explanation visible with missing data', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      dailySummary: DAILY_SUMMARY_ESCALATION_URGENT,
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
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_URGENT })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    const whyNow = page.locator('[data-testid="daily-summary-why-now"]')
    await expect(whyNow).toBeVisible()
    await expect(whyNow).toContainText('近期記錄顯示血壓波動加劇')
  })

  test('dashboard renders without ErrorBoundary fallback', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { dailySummary: DAILY_SUMMARY_ESCALATION_URGENT })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    await expect(page.locator('text=Something went wrong')).not.toBeVisible()
    await expect(page.locator('text=出現錯誤')).not.toBeVisible()
  })
})
