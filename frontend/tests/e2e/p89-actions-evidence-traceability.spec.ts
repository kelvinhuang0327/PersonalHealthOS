/**
 * P89 — Actions Page Evidence Source Traceability
 *
 * Verifies that the DecisionRecommendationLayer correctly:
 *   1. Renders evidence_summary + a source-page link for lab_report_item recs.
 *   2. Renders evidence_summary + a source-page link for symptom recs.
 *   3. Renders evidence_summary but NO source-page link for generic recommendation.
 *   4. Does not display medically overclaiming language.
 *
 * Strategy: fully mocked (no live backend).
 */

import { expect, test } from '@playwright/test'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-p89', display_name: 'P89 User', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD = {
  health_score: { overall_score: 72, components: {} },
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P89 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P89 test',
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

const LAB_REC = {
  title: '血糖異常需追蹤',
  why_now:
    '健檢報告顯示空腹血糖 = 6.8 mmol/L（H），報告日期 2026-01-15',
  priority: 'high',
  source_type: 'lab_report_item',
  source_id: 'lab-item-uuid-001',
  evidence_summary: '健檢報告（2026-01-15）：空腹血糖 = 6.8 mmol/L，旗標 H',
  data_insufficiency_reason: null,
  next_action: '與醫師討論血糖異常並安排複查',
  expected_health_impact: '及早追蹤有助掌握健康趨勢',
  evidence_sources: [{ type: 'lab_report_item', id: 'lab-item-uuid-001', summary: '空腹血糖 6.8 mmol/L' }],
  is_tracking: false,
  evidence_level: 'A',
  trust: null,
}

const SYMPTOM_REC = {
  title: '持續頭痛需關注',
  why_now: '症狀頭痛已持續估計 5 天，嚴重度 7/10',
  priority: 'medium',
  source_type: 'symptom',
  source_id: 'symptom-uuid-002',
  evidence_summary: '自述症狀（C 級）：頭痛，嚴重度 7/10，估計已持續 5 天',
  data_insufficiency_reason: '此建議基於自述症狀（C 級），補充健檢報告可提高可信度。',
  next_action: '就醫評估持續症狀的原因',
  expected_health_impact: '長期症狀若不處理可能發展為慢性問題',
  evidence_sources: [{ type: 'symptom', id: 'symptom-uuid-002', summary: '頭痛 7/10' }],
  is_tracking: false,
  evidence_level: 'C',
  trust: null,
}

const GENERIC_REC = {
  title: '記錄今日健康指標',
  why_now: '目前沒有近期健康指標記錄，無法進行精準評估',
  priority: 'medium',
  source_type: 'recommendation',
  source_id: 'ha_rec_fallback_0',
  evidence_summary: '系統建議：補充近期健康指標',
  data_insufficiency_reason: null,
  next_action: '前往健康指標頁面新增記錄',
  expected_health_impact: '補充資料後評估更精準',
  evidence_sources: [],
  is_tracking: false,
  evidence_level: 'C',
  trust: null,
}

// ── Route stub ────────────────────────────────────────────────────────────────

async function stubRoutes(
  page: import('@playwright/test').Page,
  recommendations: object[],
) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'p89-mock-token')
    localStorage.setItem('person_id', 'person-p89')
    localStorage.setItem('onboarding_completed', '1')
    localStorage.setItem('health_actions_cache_person-p89', JSON.stringify([]))
  })

  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()

    if (path.endsWith('/persons')) return route.fulfill({ json: PERSONS })
    if (path.endsWith('/profile/me')) {
      return route.fulfill({
        json: {
          id: 'person-p89',
          display_name: 'P89 User',
          name: 'P89 User',
          age: 40,
          gender: 'male',
          onboarding_completed: true,
        },
      })
    }
    if (path.includes('/health-assistant/recommendations')) {
      return route.fulfill({
        json: { person_id: 'person-p89', recommendations, total: recommendations.length },
      })
    }
    if (path.includes('/health-assistant/daily-summary')) {
      return route.fulfill({
        json: { topRisk: '', biggestChange: '', todayAction: '', generated_at: new Date().toISOString() },
      })
    }
    if (path.includes('/health-assistant/outcome-feedback')) {
      return route.fulfill({
        json: {
          person_id: 'person-p89',
          generated_at: new Date().toISOString(),
          window_days: 30,
          outcomes: [],
          summary: {
            improved_count: 0, unchanged_count: 0, deteriorated_count: 0,
            insufficient_data_count: 0, tracking_count: 0, not_useful_count: 0,
            not_applicable_count: 0, snoozed_count: 0, total_count: 0,
          },
        },
      })
    }
    if (path.includes('/health-assistant/notifications/intelligent')) {
      return route.fulfill({
        json: { person_id: 'person-p89', generated_at: new Date().toISOString(), items: [], suppressed: [], total_candidates: 0 },
      })
    }
    if (path.includes('/orchestrator/dashboard-summary')) return route.fulfill({ json: null })
    if (path.includes('/health-assistant/family-relationships')) {
      return route.fulfill({ json: { person_id: 'person-p89', relationships: [], total: 0 } })
    }
    if (path.includes('/health-assistant/family-health-context')) {
      return route.fulfill({ json: { person_id: 'person-p89', context: null } })
    }
    if (path.includes('/health-assistant/family-recommendations')) {
      return route.fulfill({ json: { person_id: 'person-p89', recommendations: [], total: 0 } })
    }
    if (path.includes('/health-assistant/narrative-memory/cross-period')) {
      return route.fulfill({ json: { person_id: 'person-p89', reasoning: null } })
    }
    if (path.endsWith('/dashboard')) return route.fulfill({ json: BASE_DASHBOARD })
    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    if (path.includes('/actions/') && path.endsWith('/outcomes') && method === 'GET') {
      return route.fulfill({ json: [] })
    }
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

test.describe('P89 Actions Evidence Source Traceability', () => {

  test('T1: lab_report_item source renders evidence_summary and documents link', async ({ page }) => {
    await stubRoutes(page, [LAB_REC])
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10000 })

    // evidence_summary text visible
    await expect(page.getByText('健檢報告（2026-01-15）：空腹血糖 = 6.8 mmol/L，旗標 H')).toBeVisible()

    // source-page link present and points to documents
    const sourceLink = page.getByTestId('p89-source-page-link').first()
    await expect(sourceLink).toBeVisible()
    await expect(sourceLink).toContainText('查看健檢報告')
    const href = await sourceLink.getAttribute('href')
    expect(href).toContain('/platform/documents')
  })

  test('T2: symptom source renders evidence_summary and symptoms link', async ({ page }) => {
    await stubRoutes(page, [SYMPTOM_REC])
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10000 })

    // evidence_summary text visible
    await expect(page.getByText('自述症狀（C 級）：頭痛，嚴重度 7/10，估計已持續 5 天')).toBeVisible()

    // source-page link present and points to symptoms
    const sourceLink = page.getByTestId('p89-source-page-link').first()
    await expect(sourceLink).toBeVisible()
    await expect(sourceLink).toContainText('查看症狀紀錄')
    const href = await sourceLink.getAttribute('href')
    expect(href).toContain('/platform/symptoms')
  })

  test('T3: generic recommendation renders evidence_summary but no source-page link', async ({ page }) => {
    await stubRoutes(page, [GENERIC_REC])
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10000 })

    // evidence_summary text visible
    await expect(page.getByText('系統建議：補充近期健康指標')).toBeVisible()

    // source-page link NOT present for generic recommendations
    await expect(page.getByTestId('p89-source-page-link')).toHaveCount(0)
  })

  test('T4: overclaim guard — no diagnostic/treatment claims on actions page', async ({ page }) => {
    await stubRoutes(page, [LAB_REC, SYMPTOM_REC])
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10000 })

    const body = await page.locator('body').innerText()
    expect(body).not.toMatch(/確診|診斷為|治療方案|保證改善/)
  })

})
