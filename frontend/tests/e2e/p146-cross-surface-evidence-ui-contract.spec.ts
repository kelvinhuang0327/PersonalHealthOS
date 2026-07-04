import { expect, test } from '@playwright/test'

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const DOC_CONFIRMED = {
  id: 'doc-confirmed-p146',
  original_filename: '2026_synthetic_lab_report.pdf',
  parse_status: 'confirmed',
  confirmed_at: new Date().toISOString(),
  uploaded_at: new Date().toISOString(),
  category: 'health_check',
  confirmed_data: { extracted_items: 3, abnormal_items: 2 },
}

const BASE_DASHBOARD_ALIGNED_WITH_P144 = {
  health_score: {
    overall_score: 75,
    components: {
      risk_alerts_penalty: 10,
    },
  },
  recent_labs: [
    {
      id: 'doc-confirmed-p146',
      abnormal_items: 2,
      report_date: new Date().toISOString().split('T')[0],
    },
  ],
  alerts: [
    { id: 'alert-1', rule_id: 'liver_ast_high', title: 'AST 偏高', severity: 'warning', priority: 'medium' },
  ],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P146 synthetic lab report dashboard state',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: '根據您已確認的報告，我們發現了 2 項異常。',
    risks: ['AST 偏高，建議關注肝臟與代謝指標。'],
    trends: [],
    reasons: [],
    actions: ['建議進行肝臟健康管理'],
    delta_summary: '無變化',
    improvements: [],
    deteriorations: [],
    adherence: [],
    missed_risks: [],
  },
}

const DAILY_SUMMARY_WITH_CONFIRMED_REPORT = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '檢驗資料含 suppressed_unit_scale_mismatch，暫不判斷異常',
  biggestChange: '暫無顯著數據變化',
  todayAction: '先完成今日症狀與行動記錄',
  whyNow: '目前資料可協助整理健康趨勢',
  confidence: 0.7,
  topRiskRef: {
    source_type: 'lab_report_item',
    document_id: 'doc-confirmed-p146',
    summary: 'suppressed_unit_scale_mismatch（暫不判斷異常）',
  },
}

const RECOMMENDATIONS_WITH_CONFIRMED_REPORT = {
  person_id: 'person-self',
  recommendations: [
    {
      action_id: 'rec-ast-p146',
      source_type: 'lab_report_item',
      source_id: 'rule-ast-high',
      title: '建議進行肝臟健康管理',
      why_now: '您的健檢報告顯示 AST 偏高',
      priority: 'medium',
      evidence_summary: '檢驗資料含 suppressed_unit_scale_mismatch，暫不判斷異常',
      document_id: 'doc-confirmed-p146',
      expected_health_impact: '有助於掌握肝臟代謝功能',
      evidence_sources: [{ type: 'lab_report_item', id: 'rule-ast-high', summary: 'AST 偏高' }],
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
    }
  ],
  total: 1,
  missing_data: []
}

const OUTCOME_WITH_UNKNOWN_DATA = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 7,
  outcomes: [],
  summary: {
    improved_count: 0,
    unchanged_count: 0,
    deteriorated_count: 0,
    insufficient_data_count: 1,
    tracking_count: 1,
    not_useful_count: 0,
    not_applicable_count: 0,
    snoozed_count: 0,
    total_count: 2,
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
    localStorage.setItem('token', 'p146-mock-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
}

async function stubRoutes(page: import('@playwright/test').Page) {
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
        ],
      })
    }
    if (path.includes('/documents/lab-history')) return route.fulfill({ json: [] })

    if (path.includes('/health-assistant/daily-summary')) return route.fulfill({ json: DAILY_SUMMARY_WITH_CONFIRMED_REPORT })
    if (path.includes('/health-assistant/recommendations')) return route.fulfill({ json: RECOMMENDATIONS_WITH_CONFIRMED_REPORT })
    if (path.includes('/health-assistant/outcome-feedback')) return route.fulfill({ json: OUTCOME_WITH_UNKNOWN_DATA })
    if (path.includes('/health-assistant/notifications/intelligent')) {
      return route.fulfill({ json: { person_id: 'person-self', generated_at: new Date().toISOString(), items: [], suppressed: [], total_candidates: 0 } })
    }
    if (path.includes('/orchestrator/dashboard-summary')) return route.fulfill({ json: null })
    if (path.includes('/health-assistant/family-relationships')) return route.fulfill({ json: { person_id: 'person-self', relationships: [], total: 0 } })
    if (path.includes('/health-assistant/family-health-context')) return route.fulfill({ json: { person_id: 'person-self', context: null } })
    if (path.includes('/health-assistant/family-recommendations')) return route.fulfill({ json: { person_id: 'person-self', recommendations: [], total: 0 } })
    if (path.includes('/health-assistant/narrative-memory/cross-period')) return route.fulfill({ json: { person_id: 'person-self', reasoning: null } })

    if (path.endsWith('/dashboard')) return route.fulfill({ json: BASE_DASHBOARD_ALIGNED_WITH_P144 })
    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') return route.fulfill({ json: [] })
    if (path.includes('/actions/') && path.endsWith('/outcomes') && method === 'GET') return route.fulfill({ json: [] })
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/risk-alerts')) return route.fulfill({ json: [] })
    if (path.includes('/risk-alerts/unread-count')) return route.fulfill({ json: { count: 0 } })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if ((path.endsWith('/symptoms') || path.includes('/symptoms?')) && method === 'GET') return route.fulfill({ json: [] })

    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

test.describe('P146 — Cross-Surface Evidence UI Contract', () => {
  test('1) Documents page correctly displays confirmed synthetic report state and details', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)
    await page.goto('/platform/documents')

    // Verify root container and elements
    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()
    await expect(page.locator('[data-testid="documents-list-section"]')).toBeVisible()

    // Confirmed report details must show
    await expect(page.getByText('2026_synthetic_lab_report.pdf')).toBeVisible()
    await expect(page.getByText('已確認')).toBeVisible()
    await expect(page.locator('[data-testid="documents-confirmed-summary"]')).toContainText('3 項指標')
    await expect(page.locator('[data-testid="documents-confirmed-summary"]')).toContainText('2 項異常')
  })

  test('2) Actions page displays report-linked action/recommendation and evidence badge', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)
    await page.goto('/platform/actions')

    // Verify actions page root
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()

    // Verify top recommendation is rendered
    await expect(page.getByText('建議進行肝臟健康管理')).toBeVisible()
    await expect(page.getByText('您的健檢報告顯示 AST 偏高')).toBeVisible()

    // Verify evidence summary and deep link source page link
    const sourceLink = page.locator('[data-testid="p89-source-page-link"]').first()
    await expect(sourceLink).toBeVisible()
    await expect(sourceLink).toContainText('查看健檢報告')
    const href = await sourceLink.getAttribute('href')
    expect(href).toContain('/platform/documents')
    expect(href).toContain('document_id=doc-confirmed-p146')
  })

  test('3) Cross-surface navigation and deep-link integration does not regress to empty state', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    // Go to dashboard first
    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="first-run-journey-card"]')).toBeVisible()
    await expect(page.locator('[data-testid="first-run-journey-empty"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="first-run-journey-in-progress"]')).toBeVisible()

    // Click the topRiskRef link
    const refLink = page.locator('[data-testid="p94-top-risk-ref-link"]').first()
    await expect(refLink).toBeVisible()
    const href = await refLink.getAttribute('href')
    expect(href).toContain('/platform/documents')
    expect(href).toContain('document_id=doc-confirmed-p146')

    // Perform click and verify it opens Documents page with ParsedItemsDrawer open
    await refLink.click()
    await page.waitForURL(/\/platform\/documents\?document_id=doc-confirmed-p146/)
    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()
    
    const drawer = page.locator('[role="dialog"]')
    await expect(drawer).toBeVisible()
    await expect(drawer.getByText('AST')).toBeVisible()
    await expect(drawer.getByText('45')).toBeVisible()

    // Close the drawer
    await drawer.locator('button').first().click()
    await expect(drawer).not.toBeVisible()

    // Navigate to actions
    await page.goto('/platform/actions')
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()
    await expect(page.locator('[data-testid="recommendation-history-card"]')).toBeVisible()

    // Click source page link on recommendation to deep link back to documents page
    const sourceLink = page.locator('[data-testid="p89-source-page-link"]').first()
    await sourceLink.click()
    await page.waitForURL(/\/platform\/documents\?document_id=doc-confirmed-p146/)
    await expect(page.locator('[role="dialog"]')).toBeVisible()
  })

  test('4) Safety audit: no medical overclaims, and suppressed state is not described as normal', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    // Check Dashboard Page safety
    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="first-run-suppression-not-judged-note"]')).toBeVisible()
    const dashboardBody = (await page.locator('body').innerText()).toLowerCase()
    expect(dashboardBody).toContain('暫不判斷異常')
    expect(dashboardBody).not.toContain('正常代表沒問題')
    for (const phrase of PROHIBITED_PHRASES) {
      expect(dashboardBody).not.toContain(phrase.toLowerCase())
    }

    // Check Documents Page safety
    await page.goto('/platform/documents')
    const docBody = (await page.locator('body').innerText()).toLowerCase()
    for (const phrase of PROHIBITED_PHRASES) {
      expect(docBody).not.toContain(phrase.toLowerCase())
    }

    // Check Actions Page safety
    await page.goto('/platform/actions')
    const actionBody = (await page.locator('body').innerText()).toLowerCase()
    for (const phrase of PROHIBITED_PHRASES) {
      expect(actionBody).not.toContain(phrase.toLowerCase())
    }
  })
})
