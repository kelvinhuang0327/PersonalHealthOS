/**
 * P91 — Daily Assistant Top Recommendation Evidence Badge
 *
 * Verifies that the `topRec` block in DailyAssistantEntry correctly renders:
 *   1. An evidence badge when `topRec.evidence_summary` is present.
 *   2. A source-page link for lab_report_item / symptom sources.
 *   3. No source-page link for generic `recommendation` source.
 *   4. No badge when `topRec.evidence_summary` is absent.
 *
 * Strategy: fully mocked routes, no live backend.
 */

import { expect, test } from '@playwright/test'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-p91', display_name: 'P91 User', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD = {
  health_score: { overall_score: 75, components: {} },
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P91 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P91',
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

const BASE_DAILY_SUMMARY = {
  person_id: 'person-p91',
  generated_at: new Date().toISOString(),
  topRisk: '血糖偏高需關注',
  biggestChange: '近期血糖持續偏高',
  todayAction: '追蹤血糖變化',
  whyNow: '健檢報告顯示血糖異常',
  confidence: 0.75,
}

const BASE_OUTCOME = {
  person_id: 'person-p91',
  generated_at: new Date().toISOString(),
  window_days: 7,
  outcomes: [],
  summary: {
    improved_count: 0, unchanged_count: 0, deteriorated_count: 0,
    insufficient_data_count: 0, tracking_count: 0, not_useful_count: 0,
    not_applicable_count: 0, snoozed_count: 0, total_count: 0,
  },
}

const makeRec = (overrides: Record<string, unknown>) => ({
  title: '追蹤血糖異常',
  why_now: '健檢報告顯示空腹血糖 6.8 mmol/L（H）',
  priority: 'high' as const,
  source_type: 'recommendation',
  source_id: 'rec-001',
  expected_health_impact: '早期追蹤可降低長期風險',
  evidence_sources: [],
  next_action: '與醫師討論並安排複查',
  is_tracking: false,
  trust: {
    confidence: 0.8,
    level: 'high' as const,
    reasons: ['有近期檢查資料'],
    limitations: [],
    verifiedByOutcome: false,
    nextCheckInSuggestion: '3 天後回來查看。',
  },
  ...overrides,
})

const makeRecsResponse = (rec: ReturnType<typeof makeRec>) => ({
  person_id: 'person-p91',
  recommendations: [rec],
  total: 1,
  missing_data: [],
})

// ── Route stub ────────────────────────────────────────────────────────────────

async function stubRoutes(
  page: import('@playwright/test').Page,
  recommendations: object,
) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'p91-mock-token')
    localStorage.setItem('person_id', 'person-p91')
    localStorage.setItem('onboarding_completed', '1')
  })

  await page.route('**/api/v1/**', async (route) => {
    const url  = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()

    if (path.endsWith('/persons')) return route.fulfill({ json: PERSONS })
    if (path.endsWith('/profile/me')) {
      return route.fulfill({
        json: {
          id: 'person-p91', display_name: 'P91 User', name: 'P91 User',
          age: 38, gender: 'female', onboarding_completed: true,
        },
      })
    }
    if (path.includes('/health-assistant/daily-summary')) {
      return route.fulfill({ json: BASE_DAILY_SUMMARY })
    }
    if (path.includes('/health-assistant/recommendations')) {
      return route.fulfill({ json: recommendations })
    }
    if (path.includes('/health-assistant/outcome-feedback')) {
      return route.fulfill({ json: BASE_OUTCOME })
    }
    if (path.includes('/health-assistant/notifications/intelligent')) {
      return route.fulfill({
        json: { person_id: 'person-p91', generated_at: new Date().toISOString(), items: [], suppressed: [], total_candidates: 0 },
      })
    }
    if (path.includes('/orchestrator/dashboard-summary')) return route.fulfill({ json: null })
    if (path.includes('/health-assistant/family-relationships')) {
      return route.fulfill({ json: { person_id: 'person-p91', relationships: [], total: 0 } })
    }
    if (path.includes('/health-assistant/family-health-context')) {
      return route.fulfill({ json: { person_id: 'person-p91', context: null } })
    }
    if (path.includes('/health-assistant/family-recommendations')) {
      return route.fulfill({ json: { person_id: 'person-p91', recommendations: [], total: 0 } })
    }
    if (path.includes('/health-assistant/narrative-memory/cross-period')) {
      return route.fulfill({ json: { person_id: 'person-p91', reasoning: null } })
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

test.describe('P91 Daily Assistant Top-Rec Evidence Badge', () => {

  test('T1: lab_report_item source — badge visible, link to /platform/documents', async ({ page }) => {
    const rec = makeRec({
      source_type: 'lab_report_item',
      source_id: 'lab-uuid-001',
      evidence_summary: '健檢報告（2026-01-15）：血糖 6.8，旗標 H',
    })
    await stubRoutes(page, makeRecsResponse(rec))
    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Badge visible with correct text
    const badge = page.getByTestId('daily-toprec-evidence-badge')
    await expect(badge).toBeVisible()
    await expect(badge).toContainText('健檢報告（2026-01-15）：血糖 6.8，旗標 H')

    // Source link visible and points to documents
    const link = page.getByTestId('p91-daily-source-page-link')
    await expect(link).toBeVisible()
    await expect(link).toContainText('查看健檢報告')
    const href = await link.getAttribute('href')
    expect(href).toContain('/platform/documents')
  })

  test('T2: symptom source — badge visible, link to /platform/symptoms', async ({ page }) => {
    const rec = makeRec({
      source_type: 'symptom',
      source_id: 'symptom-uuid-002',
      evidence_summary: '近 14 天頭痛紀錄增加',
    })
    await stubRoutes(page, makeRecsResponse(rec))
    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Badge visible
    const badge = page.getByTestId('daily-toprec-evidence-badge')
    await expect(badge).toBeVisible()
    await expect(badge).toContainText('近 14 天頭痛紀錄增加')

    // Source link visible and points to symptoms
    const link = page.getByTestId('p91-daily-source-page-link')
    await expect(link).toBeVisible()
    await expect(link).toContainText('查看症狀紀錄')
    const href = await link.getAttribute('href')
    expect(href).toContain('/platform/symptoms')
  })

  test('T3: generic recommendation source — badge visible, no source-page link', async ({ page }) => {
    const rec = makeRec({
      source_type: 'recommendation',
      evidence_summary: '系統建議：記錄今日健康指標以提升可信度',
    })
    await stubRoutes(page, makeRecsResponse(rec))
    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Badge visible (evidence_summary present)
    await expect(page.getByTestId('daily-toprec-evidence-badge')).toBeVisible()

    // No source-page link for generic recommendation
    await expect(page.getByTestId('p91-daily-source-page-link')).toHaveCount(0)
  })

  test('T4: evidence_summary absent — no badge, no source-page link', async ({ page }) => {
    const rec = makeRec({
      source_type: 'lab_report_item',
      // evidence_summary deliberately omitted
    })
    // Remove evidence_summary if makeRec somehow includes a default
    delete (rec as Record<string, unknown>)['evidence_summary']

    await stubRoutes(page, makeRecsResponse(rec))
    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-assistant-entry"]')).toBeVisible({ timeout: 12_000 })

    // Neither badge nor link should appear
    await expect(page.getByTestId('daily-toprec-evidence-badge')).toHaveCount(0)
    await expect(page.getByTestId('p91-daily-source-page-link')).toHaveCount(0)
  })

})
