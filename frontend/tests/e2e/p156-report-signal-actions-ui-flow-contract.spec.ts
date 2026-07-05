import { expect, test } from '@playwright/test'

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const DOC_CONFIRMED = {
  id: 'doc-confirmed-1',
  original_filename: '2026_synthetic_lab_report.pdf',
  parse_status: 'confirmed',
  confirmed_at: new Date().toISOString(),
  uploaded_at: new Date().toISOString(),
  category: 'health_check',
  confirmed_data: { extracted_items: 4, abnormal_items: 2 },
}

const BASE_DASHBOARD = {
  health_score: {
    overall_score: 75,
    components: {
      risk_alerts_penalty: 10,
    },
  },
  recent_labs: [
    {
      id: 'doc-confirmed-1',
      abnormal_items: 2,
      report_date: new Date().toISOString().split('T')[0],
    },
  ],
  alerts: [
    { id: 'alert-ast-id', rule_id: 'liver_ast_high', title: 'AST 偏高', severity: 'warning', priority: 'medium', source_id: 'rule-ast-high' },
    { id: 'alert-chol-id', rule_id: 'lipid_cholesterol_high', title: '膽固醇偏高', severity: 'warning', priority: 'medium', source_id: 'rule-chol-high' }
  ],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P155 report-derived signal dashboard state',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: '根據您已確認的報告，我們發現了 2 項異常。',
    risks: ['AST 及膽固醇偏高，建議關注肝臟與代謝指標。'],
    trends: [],
    reasons: [],
    actions: ['建議進行肝臟健康管理', '控制飽和脂肪攝取'],
  },
}

const RECOMMENDATIONS = {
  person_id: 'person-self',
  recommendations: [
    {
      action_id: 'rec-liver-id',
      source_type: 'risk_alert',
      source_id: 'alert-ast-id',
      title: '建議進行肝臟健康管理',
      why_now: '您的健檢報告顯示 AST 偏高',
      priority: 'medium',
      evidence_summary: '檢驗資料含 suppressed_unit_scale_mismatch，暫不判斷異常',
      document_id: 'doc-confirmed-1',
      expected_health_impact: '有助於掌握肝臟代謝功能',
      evidence_sources: [{ type: 'risk_alert', id: 'alert-ast-id', summary: 'AST 偏高' }],
      is_tracking: false,
      evidence_level: 'B',
      trust: {
        confidence: 0.8,
        level: 'medium',
        reasons: ['已對比歷史健檢資料'],
        limitations: [],
        verifiedByOutcome: false,
        nextCheckInSuggestion: '30 天後重新追蹤'
      }
    },
    {
      action_id: 'rec-chol-id',
      source_type: 'lab_report_item',
      source_id: 'rule-chol-high',
      title: '控制飽和脂肪攝取',
      why_now: '您的健檢報告顯示膽固醇偏高',
      priority: 'medium',
      evidence_summary: '總膽固醇偏高（240 mg/dL）',
      document_id: 'doc-confirmed-1',
      expected_health_impact: '降低心血管風險',
      evidence_sources: [{ type: 'lab_report_item', id: 'rule-chol-high', summary: '膽固醇偏高' }],
      is_tracking: false,
      evidence_level: 'B',
    }
  ],
  total: 2,
  missing_data: []
}

const OUTCOME_EMPTY = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 30,
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

const PROHIBITED_PHRASES = [
  '診斷',
  '確診',
  '治療',
  '治癒',
  '一定',
  '絕對',
  '保證',
  '100%',
  '取代醫師',
  '正常代表沒問題',
  'diagnose',
  'guarantee',
  'cure',
]

async function setAuthStorage(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'p156-mock-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: {
    actions?: any[]
    dashboard?: any
    recommendations?: any
    outcomeFeedback?: any
  } = {}
) {
  const {
    actions = [],
    dashboard = BASE_DASHBOARD,
    recommendations = RECOMMENDATIONS,
    outcomeFeedback = OUTCOME_EMPTY,
  } = opts

  await page.route('**/api/v1/**', async (route) => {
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

    if ((path.endsWith('/documents') || path.includes('/documents?')) && method === 'GET') {
      return route.fulfill({ json: [DOC_CONFIRMED] })
    }

    if (path.includes('/documents/') && path.includes('/parsed-items')) {
      return route.fulfill({
        json: [
          {
            id: 'item-ast',
            item_name: 'AST',
            value_num: 45,
            value_text: null,
            unit: 'U/L',
            ref_range: '0-40',
            abnormal_flag: 'H',
            parser_confidence: 0.95,
            is_abnormal: true,
          },
          {
            id: 'item-cholesterol',
            item_name: 'Total Cholesterol',
            value_num: 240,
            value_text: null,
            unit: 'mg/dL',
            ref_range: '0-200',
            abnormal_flag: 'H',
            parser_confidence: 0.95,
            is_abnormal: true,
          },
        ],
      })
    }
    if (path.includes('/documents/lab-history')) return route.fulfill({ json: [] })

    if (path.includes('/health-assistant/daily-summary')) {
      return route.fulfill({
        json: {
          person_id: 'person-self',
          generated_at: new Date().toISOString(),
          topRisk: '',
          biggestChange: '',
          todayAction: '',
          whyNow: '',
          confidence: 0.7,
        }
      })
    }
    if (path.includes('/health-assistant/recommendations')) {
      return route.fulfill({ json: recommendations })
    }
    if (path.includes('/health-assistant/outcome-feedback')) {
      return route.fulfill({ json: outcomeFeedback })
    }
    if (path.includes('/health-assistant/notifications/intelligent')) {
      return route.fulfill({ json: { person_id: 'person-self', generated_at: new Date().toISOString(), items: [], suppressed: [], total_candidates: 0 } })
    }
    if (path.includes('/orchestrator/dashboard-summary')) return route.fulfill({ json: null })
    if (path.includes('/health-assistant/family-relationships')) return route.fulfill({ json: { person_id: 'person-self', relationships: [], total: 0 } })
    if (path.includes('/health-assistant/family-health-context')) return route.fulfill({ json: { person_id: 'person-self', context: null } })
    if (path.includes('/health-assistant/family-recommendations')) return route.fulfill({ json: { person_id: 'person-self', recommendations: [], total: 0 } })
    if (path.includes('/health-assistant/narrative-memory/cross-period')) return route.fulfill({ json: { person_id: 'person-self', reasoning: null } })

    if (path.endsWith('/dashboard')) {
      return route.fulfill({ json: dashboard })
    }

    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    if (path.includes('/actions/') && path.endsWith('/outcomes') && method === 'GET') {
      return route.fulfill({ json: [] })
    }
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') {
      return route.fulfill({ json: actions })
    }
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'POST') {
      return route.fulfill({
        json: {
          id: `act_created_${Date.now()}`,
          ...JSON.parse(route.request().postData() || '{}'),
        }
      })
    }
    if (path.includes('/actions/') && method === 'PATCH') {
      const parts = path.split('/')
      const patchId = parts[parts.length - 1]
      return route.fulfill({
        json: {
          id: patchId,
          ...JSON.parse(route.request().postData() || '{}'),
        }
      })
    }
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/risk-alerts')) return route.fulfill({ json: [] })
    if (path.includes('/risk-alerts/unread-count')) return route.fulfill({ json: { count: 0 } })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if ((path.endsWith('/symptoms') || path.includes('/symptoms?')) && method === 'GET') return route.fulfill({ json: [] })

    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

test.describe('P156 — Report Signal and Actions UI Flow Contract', () => {

  test('1) Dashboard shows report-derived risk alerts and narrative correctly', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    await page.goto('/platform/dashboard')
    await page.waitForSelector('[data-testid="first-run-journey-card"]', { timeout: 10_000 })

    // Verify report-derived signals/alerts on dashboard (use exact check to avoid strict mode violation)
    await expect(page.getByText('AST 偏高', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('膽固醇偏高', { exact: true }).first()).toBeVisible()

    // Verify non-empty risk state / narrative elements
    await expect(page.getByText('根據您已確認的報告，我們發現了 2 項異常。').first()).toBeVisible()
    await expect(page.getByText('AST 及膽固醇偏高，建議關注肝臟與代謝指標。').first()).toBeVisible()

    // Safety audit
    const bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('Something went wrong')
  })

  test('2) Actions page displays linked recommendations and supports feedback snooze flow', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // Use specific card wrapper container to check recommendations visibility
    const recSection = page.locator('div.rounded-3xl', { has: page.locator('h3:has-text("系統現在建議你先做")') }).first()

    // Verify linked recommendations are displayed in the recommendation section
    await expect(recSection.getByText('建議進行肝臟健康管理')).toBeVisible()
    await expect(recSection.getByText('控制飽和脂肪攝取')).toBeVisible()

    // Verify evidence/source link is visible and deep-linked for lab-sourced evidence
    const sourceLink = recSection.locator('[data-testid="p89-source-page-link"]').first()
    await expect(sourceLink).toBeVisible()
    await expect(sourceLink).toContainText('查看健檢報告')
    const href = await sourceLink.getAttribute('href')
    expect(href).toContain('/platform/documents?document_id=doc-confirmed-1')

    // Click source page link to verify deep link works
    await sourceLink.click()
    await page.waitForURL(/\/platform\/documents\?document_id=doc-confirmed-1/)
    await expect(page.locator('[role="dialog"]')).toBeVisible()
    
    // Close the drawer
    await page.locator('[role="dialog"]').locator('button').first().click()
    await expect(page.locator('[role="dialog"]')).not.toBeVisible()

    // Navigate back to actions to test feedback & snooze
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // Dismiss first recommendation with "沒有用" feedback
    const liverCard = recSection.locator('div.rounded-2xl.border.p-4').filter({ hasText: '建議進行肝臟健康管理' })
    const dismissBtn = liverCard.getByRole('button', { name: '沒有用' })
    await expect(dismissBtn).toBeVisible()

    const dismissRequestPromise = page.waitForRequest(
      (req) => req.url().includes('/actions') && req.method() === 'POST'
    )
    await dismissBtn.click()

    const dismissRequest = await dismissRequestPromise
    const dismissPayload = JSON.parse(dismissRequest.postData() || '{}')
    expect(dismissPayload.status).toBe('not_useful')
    expect(dismissPayload.source_id).toBe('alert-ast-id')

    // Verify dismissed card is removed from the recommendation section
    await expect(recSection.getByText('建議進行肝臟健康管理')).not.toBeVisible()

    // Snooze second recommendation
    const cholCard = recSection.locator('div.rounded-2xl.border.p-4').filter({ hasText: '控制飽和脂肪攝取' })
    const snoozeBtn = cholCard.getByRole('button', { name: '稍後提醒' })
    await expect(snoozeBtn).toBeVisible()

    const snoozeRequestPromise = page.waitForRequest(
      (req) => req.url().includes('/actions') && req.method() === 'POST'
    )
    await snoozeBtn.click()

    const snoozeRequest = await snoozeRequestPromise
    const snoozePayload = JSON.parse(snoozeRequest.postData() || '{}')
    expect(snoozePayload.status).toBe('snoozed')
    expect(snoozePayload.snoozed_until).toBeDefined()

    // Verify snoozed card is removed from the recommendation section
    await expect(recSection.getByText('控制飽和脂肪攝取')).not.toBeVisible()
  })

  test('3) Prohibited medical claims and normal-state suppression audit', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    // Audit Dashboard page
    await page.goto('/platform/dashboard')
    await page.waitForSelector('[data-testid="first-run-journey-card"]', { timeout: 10_000 })
    const dashboardText = await page.locator('body').innerText()

    for (const phrase of PROHIBITED_PHRASES) {
      expect(dashboardText.toLowerCase()).not.toContain(phrase.toLowerCase())
    }

    // Audit Actions page
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })
    const actionsText = await page.locator('body').innerText()

    for (const phrase of PROHIBITED_PHRASES) {
      expect(actionsText.toLowerCase()).not.toContain(phrase.toLowerCase())
    }

    // Check that missing/unknown evidence is not described as normal/healthy
    expect(actionsText).not.toContain('資料缺少正常')
    expect(actionsText).not.toContain('數值正常')
    expect(dashboardText).not.toContain('資料缺少正常')
    expect(dashboardText).not.toContain('數值正常')
  })
})
