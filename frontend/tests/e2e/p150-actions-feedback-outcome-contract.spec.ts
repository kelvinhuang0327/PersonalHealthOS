import { expect, test } from '@playwright/test'

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const DOC_CONFIRMED = {
  id: 'doc-confirmed-p150',
  original_filename: '2026_synthetic_lab_report.pdf',
  parse_status: 'confirmed',
  confirmed_at: new Date().toISOString(),
  uploaded_at: new Date().toISOString(),
  category: 'health_check',
  confirmed_data: { extracted_items: 2, abnormal_items: 1 },
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
      id: 'doc-confirmed-p150',
      abnormal_items: 1,
      report_date: new Date().toISOString().split('T')[0],
    },
  ],
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P150 dashboard state',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: '根據您已確認的報告，我們發現了 1 項異常。',
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

const RECOMMENDATIONS = {
  person_id: 'person-self',
  recommendations: [
    {
      action_id: 'rec-ast-p150',
      source_type: 'lab_report_item',
      source_id: 'rule-ast-high-p150',
      title: '建議進行肝臟健康管理',
      why_now: '您的健檢報告顯示 AST 偏高',
      priority: 'medium',
      evidence_summary: '檢驗資料含 suppressed_unit_scale_mismatch，暫不判斷異常',
      document_id: 'doc-confirmed-p150',
      expected_health_impact: '有助於掌握肝臟代謝功能',
      evidence_sources: [{ type: 'lab_report_item', id: 'rule-ast-high-p150', summary: 'AST 偏高' }],
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
      action_id: 'rec-glucose-p150',
      source_type: 'lab_report_item',
      source_id: 'rule-glucose-insufficient-p150',
      title: '建議追蹤血糖趨勢',
      why_now: '缺少空腹血糖歷史資料，暫時無法分析長期糖化血色素趨勢',
      priority: 'low',
      data_insufficiency_reason: '由於缺少空腹血糖歷史資料，暫時無法分析長期糖化血色素趨勢',
      is_tracking: false,
      evidence_level: 'C',
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
    localStorage.setItem('token', 'p150-mock-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
}

type StubOptions = {
  actions?: any[]
  dashboard?: any
  recommendations?: any
  outcomeFeedback?: any
  outcomesResponse?: any
  outcomesStatus?: number
  actionPostStatus?: number
  actionPatchStatus?: number
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: StubOptions = {},
) {
  const {
    actions = [],
    dashboard = BASE_DASHBOARD,
    recommendations = RECOMMENDATIONS,
    outcomeFeedback = OUTCOME_EMPTY,
    outcomesResponse = [],
    outcomesStatus = 200,
    actionPostStatus = 200,
    actionPatchStatus = 200,
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
            id: 'item-suppressed-p150',
            item_name: 'ALT',
            value_num: 35,
            value_text: null,
            unit: 'U/L',
            ref_range: '0-40',
            abnormal_flag: null,
            abnormal_flag_reason: 'suppressed_unit_scale_mismatch',
            parser_confidence: 0.9,
            is_abnormal: false,
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
      if (outcomesStatus !== 200) {
        return route.fulfill({ status: outcomesStatus, json: { detail: 'Simulated outcomes error' } })
      }
      return route.fulfill({ json: outcomesResponse })
    }
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') {
      return route.fulfill({ json: actions })
    }
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'POST') {
      if (actionPostStatus !== 200) {
        return route.fulfill({ status: actionPostStatus, json: { detail: 'Simulated create error' } })
      }
      return route.fulfill({
        json: {
          id: `act_created_${Date.now()}`,
          ...JSON.parse(route.request().postData() || '{}'),
        }
      })
    }
    if (path.includes('/actions/') && method === 'PATCH') {
      if (actionPatchStatus !== 200) {
        return route.fulfill({ status: actionPatchStatus, json: { detail: 'Simulated patch error' } })
      }
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

test.describe('P150 — Actions Page Feedback, Outcome, and Snooze Contract', () => {

  test('1) Feedback button click triggers correct API payload and removes recommendation', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // Verify recommendations are visible
    await expect(page.getByText('建議進行肝臟健康管理')).toBeVisible()

    // Click "沒有用" button on the first recommendation card
    const firstCard = page.locator('div.rounded-2xl.border.p-4').first()
    const dismissButton = firstCard.getByRole('button', { name: '沒有用' })
    await expect(dismissButton).toBeVisible()

    // Wait for the request to be triggered
    const requestPromise = page.waitForRequest(
      (req) => req.url().includes('/actions') && req.method() === 'POST'
    )
    await dismissButton.click()

    const request = await requestPromise
    const postPayload = JSON.parse(request.postData() || '{}')
    expect(postPayload).toBeDefined()
    expect(postPayload.status).toBe('not_useful')
    expect(postPayload.source_id).toBe('rule-ast-high-p150')

    // Verify recommendation card is removed from the recommendation section
    const recSection = page.locator('div.rounded-3xl', { has: page.locator('h3:has-text("系統現在建議你先做")') }).first()
    await expect(recSection.getByText('建議進行肝臟健康管理')).not.toBeVisible()
  })

  test('2) Feedback POST failure recovers gracefully and retains page navigation', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { actionPostStatus: 500 })

    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // Click "沒有用" button
    const firstCard = page.locator('div.rounded-2xl.border.p-4').first()
    const dismissButton = firstCard.getByRole('button', { name: '沒有用' })
    await expect(dismissButton).toBeVisible()
    await dismissButton.click()

    // Page must not crash or show ErrorBoundary
    const bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('Something went wrong')

    // Navigation must remain functional
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()
  })

  test('3) Outcome completion shows feedback card and displays detailed metrics successfully', async ({ page }) => {
    const DONE_ACTION = {
      id: 'action-done-p150',
      person_id: 'person-self',
      source_type: 'recommendation',
      source_id: 'rec-ast-p150',
      title: '每日步行三十分鐘',
      description: '有助於掌握肝臟代謝功能',
      action_type: 'lifestyle',
      priority: 'medium',
      status: 'done',
      streak_count: 5,
      impact_status: 'improved',
      completed_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
    }

    const MOCK_OUTCOMES = [
      {
        metric_type: 'steps',
        before_value: 4000,
        after_value: 8000,
        delta: 4000,
        delta_pct: 100,
        time_window_days: 14,
        outcome_label: 'improved'
      }
    ]

    await setAuthStorage(page)
    await stubRoutes(page, {
      actions: [DONE_ACTION],
      outcomesResponse: MOCK_OUTCOMES
    })

    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // Verify feedback loop container and feedback card
    await expect(page.locator('[data-testid="actions-feedback-loop"]')).toBeVisible()
    
    // Target feedback card specifically to avoid strict mode violations
    const feedbackCard = page.locator('[data-testid="actions-feedback-loop"]').locator('div.rounded-2xl.border').first()
    await expect(feedbackCard.getByText('每日步行三十分鐘')).toBeVisible()
    await expect(feedbackCard.getByText('有改善 ✓')).toBeVisible()
    await expect(feedbackCard.getByText('連續 5 天 🔥')).toBeVisible()

    // Verify outcome details rendered from outcomes response
    await expect(feedbackCard.getByText('步數')).toBeVisible()
    await expect(feedbackCard.getByText('改善', { exact: true })).toBeVisible()
    await expect(feedbackCard.getByText('變化 ↓ 4000.0 (100.0%)｜14 天觀察')).toBeVisible()
  })

  test('4) Outcome feedback API failure does not crash the page', async ({ page }) => {
    const DONE_ACTION = {
      id: 'action-done-p150',
      person_id: 'person-self',
      source_type: 'recommendation',
      source_id: 'rec-ast-p150',
      title: '每日步行三十分鐘',
      description: '有助於掌握肝臟代謝功能',
      action_type: 'lifestyle',
      priority: 'medium',
      status: 'done',
      streak_count: 5,
      impact_status: 'improved',
      completed_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
    }

    await setAuthStorage(page)
    await stubRoutes(page, {
      actions: [DONE_ACTION],
      outcomesStatus: 500
    })

    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // The card itself should render, but no outcome data
    await expect(page.locator('[data-testid="actions-feedback-loop"]')).toBeVisible()
    
    const feedbackCard = page.locator('[data-testid="actions-feedback-loop"]').locator('div.rounded-2xl.border').first()
    await expect(feedbackCard.getByText('每日步行三十分鐘')).toBeVisible()

    // Verify page survives without ErrorBoundary
    const bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('Something went wrong')
  })

  test('5) Snooze interaction hides recommendation and triggers correct API status', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // Click "稍後提醒"
    const firstCard = page.locator('div.rounded-2xl.border.p-4').first()
    const snoozeButton = firstCard.getByRole('button', { name: '稍後提醒' })
    await expect(snoozeButton).toBeVisible()

    // Wait for the request
    const requestPromise = page.waitForRequest(
      (req) => req.url().includes('/actions') && req.method() === 'POST'
    )
    await snoozeButton.click()

    const request = await requestPromise
    const postPayload = JSON.parse(request.postData() || '{}')
    expect(postPayload).toBeDefined()
    expect(postPayload.status).toBe('snoozed')
    expect(postPayload.snoozed_until).toBeDefined()

    // Recommendation card is hidden from recommendation section
    const recSection = page.locator('div.rounded-3xl', { has: page.locator('h3:has-text("系統現在建議你先做")') }).first()
    await expect(recSection.getByText('建議進行肝臟健康管理')).not.toBeVisible()
  })

  test('6) Report-linked recommendation remains traceable to evidence', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    // Verify source link is present and points to documents
    const sourceLink = page.locator('[data-testid="p89-source-page-link"]').first()
    await expect(sourceLink).toBeVisible()
    await expect(sourceLink).toContainText('查看健檢報告')
    const href = await sourceLink.getAttribute('href')
    expect(href).toContain('/platform/documents?document_id=doc-confirmed-p150')

    // Click source page link and verify navigation to documents
    await sourceLink.click()
    await page.waitForURL(/\/platform\/documents\?document_id=doc-confirmed-p150/)
    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()
  })

  test('7) Prohibited medical claims and normal-state suppression audit', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })

    const text = await page.locator('body').innerText()

    // Audit prohibited phrases
    for (const phrase of PROHIBITED_PHRASES) {
      expect(text.toLowerCase()).not.toContain(phrase.toLowerCase())
    }

    // Verify data insufficiency warning is displayed
    await expect(page.getByText('由於缺少空腹血糖歷史資料，暫時無法分析長期糖化血色素趨勢')).toBeVisible()

    // Check that missing/unknown evidence is not described as normal/healthy
    expect(text).not.toContain('資料缺少正常')
    expect(text).not.toContain('數值正常')
  })
})

