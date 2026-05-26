/**
 * P94 — Daily Summary 3-Grid Evidence Ref Badges Contract
 *
 * Validates that the three optional per-card evidence ref badges appear/absent
 * based on the presence of topRiskRef, biggestChangeRef, todayActionRef in the
 * DailyHealthSummary API response.
 *
 * Tests:
 *  T1: topRiskRef present (source_type=risk_alert) → badge visible, no link (no href for risk_alert)
 *  T2: todayActionRef present (source_type=lab_report_item) → badge + link to /platform/documents
 *  T3: biggestChangeRef present (source_type=health_metric) → badge visible, no link (no href)
 *  T4: no refs in response → no ref badges in any card
 *
 * Strategy: fully mocked. Extends P76 helper patterns — no live backend required.
 */

import { expect, test } from '@playwright/test'

// ── Shared fixtures (minimal — only what this spec needs) ─────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD = {
  health_score: { overall_score: 72, components: {} },
  alerts: [], insights: [], recommendations: [], trends: {},
  explainability_summary: 'P94 mock', medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [], prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P94', risks: [], trends: [], reasons: [], actions: [],
    delta_summary: '無變化', improvements: [], deteriorations: [],
    adherence: [], missed_risks: [],
  },
}

const RECOMMENDATIONS_NONE = {
  person_id: 'person-self',
  recommendations: [], total: 0, missing_data: [],
}

const OUTCOME_EMPTY = {
  person_id: 'person-self', generated_at: new Date().toISOString(),
  window_days: 7, outcomes: [],
  summary: {
    improved_count: 0, unchanged_count: 0, deteriorated_count: 0,
    insufficient_data_count: 0, tracking_count: 0, not_useful_count: 0,
    not_applicable_count: 0, snoozed_count: 0, total_count: 0,
  },
}

/** Base summary with all three narrative fields populated (no refs). */
const SUMMARY_NO_REFS = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '血壓偏高需密切關注',
  biggestChange: '收縮壓改善 12.0（improved，7天）',
  todayAction: '今日優先完成：量測早晨血壓',
  whyNow: '近期記錄顯示血壓波動加劇',
  confidence: 0.75,
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
    const url    = new URL(route.request().url())
    const path   = url.pathname
    const method = route.request().method()

    if (path.includes('/health-assistant/daily-summary')) return route.fulfill({ json: dailySummary })
    if (path.endsWith('/persons')) return route.fulfill({ json: PERSONS })
    if (path.endsWith('/profile/me')) {
      return route.fulfill({
        json: { id: 'person-self', display_name: 'Self', name: 'Self', age: 40, gender: 'male', onboarding_completed: true },
      })
    }
    if (path.includes('/health-assistant/outcome-feedback')) return route.fulfill({ json: OUTCOME_EMPTY })
    if (path.includes('/health-assistant/recommendations')) return route.fulfill({ json: RECOMMENDATIONS_NONE })
    if (path.includes('/health-assistant/notifications/intelligent')) {
      return route.fulfill({
        json: { person_id: 'person-self', generated_at: new Date().toISOString(), items: [], suppressed: [], total_candidates: 0 },
      })
    }
    if (path.includes('/orchestrator/dashboard-summary')) return route.fulfill({ json: null })
    if (path.includes('/health-assistant/family-relationships')) return route.fulfill({ json: { person_id: 'person-self', relationships: [], total: 0 } })
    if (path.includes('/health-assistant/family-health-context')) return route.fulfill({ json: { person_id: 'person-self', context: null } })
    if (path.includes('/health-assistant/family-recommendations')) return route.fulfill({ json: { person_id: 'person-self', recommendations: [], total: 0 } })
    if (path.includes('/health-assistant/narrative-memory/cross-period')) return route.fulfill({ json: { person_id: 'person-self', reasoning: null } })
    if (path.endsWith('/dashboard')) return route.fulfill({ json: BASE_DASHBOARD })
    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') return route.fulfill({ json: [] })
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/risk-alerts')) return route.fulfill({ json: [] })
    if (path.includes('/risk-alerts/unread-count')) return route.fulfill({ json: { count: 0 } })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

async function waitForEntry(page: import('@playwright/test').Page) {
  await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })
  await expect(page.locator('[data-testid="daily-assistant-loading"]')).not.toBeVisible()
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P94 — Daily Summary 3-Grid Evidence Ref Badges', () => {

  /**
   * T1: topRiskRef present with source_type=risk_alert
   *     → badge visible in top-risk card
   *     → no navigation link (risk_alert has no href in EVIDENCE_SOURCE_META)
   */
  test('T1: topRiskRef risk_alert → badge visible, no source-page link', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      ...SUMMARY_NO_REFS,
      topRiskRef: {
        source_type: 'risk_alert',
        source_id: 'alert-uuid-001',
        summary: '血壓偏高',
      },
    })

    await page.goto('/platform/dashboard')
    await waitForEntry(page)

    // Badge is visible in top-risk card
    const badge = page.locator('[data-testid="p94-top-risk-ref-badge"]')
    await expect(badge).toBeVisible()

    // risk_alert has no href → no navigation link
    await expect(page.locator('[data-testid="p94-top-risk-ref-link"]')).not.toBeVisible()

    // biggestChange and todayAction cards should NOT have ref badges (no refs in mock)
    await expect(page.locator('[data-testid="p94-biggest-change-ref-badge"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="p94-today-action-ref-badge"]')).not.toBeVisible()
  })

  /**
   * T2: todayActionRef present with source_type=lab_report_item
   *     → badge visible in next-action card
   *     → navigation link to /platform/documents (lab_report_item has href)
   */
  test('T2: todayActionRef lab_report_item → badge + link to /platform/documents', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      ...SUMMARY_NO_REFS,
      todayActionRef: {
        source_type: 'lab_report_item',
        source_id: 'item-uuid-001',
        summary: '查看健檢報告異常項目',
      },
    })

    await page.goto('/platform/dashboard')
    await waitForEntry(page)

    // Badge is visible
    const badge = page.locator('[data-testid="p94-today-action-ref-badge"]')
    await expect(badge).toBeVisible()

    // lab_report_item has href=/platform/documents → link visible
    const link = page.locator('[data-testid="p94-today-action-ref-link"]')
    await expect(link).toBeVisible()
    await expect(link).toHaveAttribute('href', '/platform/documents')

    // topRisk and biggestChange cards should NOT have ref badges
    await expect(page.locator('[data-testid="p94-top-risk-ref-badge"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="p94-biggest-change-ref-badge"]')).not.toBeVisible()
  })

  /**
   * T3: biggestChangeRef present with source_type=health_metric
   *     → badge visible in biggest-change card
   *     → no navigation link (health_metric has no href in EVIDENCE_SOURCE_META)
   */
  test('T3: biggestChangeRef health_metric → badge visible, no source-page link', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      ...SUMMARY_NO_REFS,
      biggestChangeRef: {
        source_type: 'health_metric',
        source_id: null,
        summary: '收縮壓 近期趨勢',
      },
    })

    await page.goto('/platform/dashboard')
    await waitForEntry(page)

    // Badge is visible
    const badge = page.locator('[data-testid="p94-biggest-change-ref-badge"]')
    await expect(badge).toBeVisible()

    // health_metric has no href → no navigation link
    await expect(page.locator('[data-testid="p94-biggest-change-ref-link"]')).not.toBeVisible()

    // topRisk and todayAction cards should NOT have ref badges
    await expect(page.locator('[data-testid="p94-top-risk-ref-badge"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="p94-today-action-ref-badge"]')).not.toBeVisible()
  })

  /**
   * T4: no ref fields in response → no ref badges anywhere in the 3-grid
   */
  test('T4: no evidence refs in response → no ref badges in any card', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, SUMMARY_NO_REFS)

    await page.goto('/platform/dashboard')
    await waitForEntry(page)

    // All three 3-grid cards load normally
    await expect(page.locator('[data-testid="daily-summary-top-risk"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-biggest-change"]')).toBeVisible()
    await expect(page.locator('[data-testid="daily-summary-next-action"]')).toBeVisible()

    // No ref badges at all
    await expect(page.locator('[data-testid="p94-top-risk-ref-badge"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="p94-biggest-change-ref-badge"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="p94-today-action-ref-badge"]')).not.toBeVisible()
  })
})
