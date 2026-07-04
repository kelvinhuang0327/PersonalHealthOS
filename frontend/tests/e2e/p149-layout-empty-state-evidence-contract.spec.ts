import { expect, test } from '@playwright/test'

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const DOC_CONFIRMED = {
  id: 'doc-confirmed-p149',
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
      id: 'doc-confirmed-p149',
      abnormal_items: 1,
      report_date: new Date().toISOString().split('T')[0],
    },
  ],
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P149 dashboard state',
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

const DAILY_SUMMARY = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '檢驗資料含 suppressed_unit_scale_mismatch，暫不判斷異常',
  biggestChange: '暫無顯著數據變化',
  todayAction: '先完成今日症狀與行動記錄',
  whyNow: '目前資料可協助整理健康趨勢',
  confidence: 0.7,
  topRiskRef: {
    source_type: 'lab_report_item',
    document_id: 'doc-confirmed-p149',
    summary: 'suppressed_unit_scale_mismatch（暫不判斷異常）',
  },
}

const RECOMMENDATIONS = {
  person_id: 'person-self',
  recommendations: [
    {
      action_id: 'rec-ast-p149',
      source_type: 'lab_report_item',
      source_id: 'rule-ast-high-p149',
      title: '建議進行肝臟健康管理',
      why_now: '您的健檢報告顯示 AST 偏高',
      priority: 'medium',
      evidence_summary: '檢驗資料含 suppressed_unit_scale_mismatch，暫不判斷異常',
      document_id: 'doc-confirmed-p149',
      expected_health_impact: '有助於掌握肝臟代謝功能',
      evidence_sources: [{ type: 'lab_report_item', id: 'rule-ast-high-p149', summary: 'AST 偏高' }],
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
    localStorage.setItem('token', 'p149-mock-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
}

type StubOptions = {
  documents?: any[]
  documentsStatus?: number
  freezeDocuments?: boolean
  dashboard?: any
  dashboardStatus?: number
  freezeDashboard?: boolean
  recommendations?: any
  recommendationsStatus?: number
  outcomeFeedback?: any
  outcomeFeedbackStatus?: number
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: StubOptions = {},
) {
  const {
    documents = [DOC_CONFIRMED],
    documentsStatus = 200,
    freezeDocuments = false,
    dashboard = BASE_DASHBOARD,
    dashboardStatus = 200,
    freezeDashboard = false,
    recommendations = RECOMMENDATIONS,
    recommendationsStatus = 200,
    outcomeFeedback = OUTCOME_EMPTY,
    outcomeFeedbackStatus = 200,
  } = opts

  let documentsResolve: (() => void) | null = null
  let dashboardResolve: (() => void) | null = null

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
      if (documentsStatus !== 200) {
        return route.fulfill({ status: documentsStatus, json: { detail: 'Simulated documents error' } })
      }
      if (freezeDocuments && documentsResolve === null) {
        await new Promise<void>((resolve) => { documentsResolve = resolve })
      }
      return route.fulfill({ json: documents })
    }

    if (path.includes('/documents/') && path.includes('/parsed-items')) {
      return route.fulfill({
        json: [
          {
            id: 'item-suppressed-p149',
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

    if (path.includes('/health-assistant/daily-summary')) return route.fulfill({ json: DAILY_SUMMARY })
    if (path.includes('/health-assistant/recommendations')) {
      if (recommendationsStatus !== 200) {
        return route.fulfill({ status: recommendationsStatus, json: { detail: 'Simulated recommendations error' } })
      }
      return route.fulfill({ json: recommendations })
    }
    if (path.includes('/health-assistant/outcome-feedback')) {
      if (outcomeFeedbackStatus !== 200) {
        return route.fulfill({ status: outcomeFeedbackStatus, json: { detail: 'Simulated outcome error' } })
      }
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
      if (dashboardStatus !== 200) {
        return route.fulfill({ status: dashboardStatus, json: { detail: 'Simulated dashboard error' } })
      }
      if (freezeDashboard && dashboardResolve === null) {
        await new Promise<void>((resolve) => { dashboardResolve = resolve })
      }
      return route.fulfill({ json: dashboard })
    }

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

  return {
    releaseDocuments: () => {
      if (documentsResolve) { documentsResolve(); documentsResolve = null }
    },
    releaseDashboard: () => {
      if (dashboardResolve) { dashboardResolve(); dashboardResolve = null }
    },
  }
}

test.describe('P149 — Layout Stability & Empty-State Evidence Contract', () => {
  
  test('1) Documents page loading state remains stable and safe', async ({ page }) => {
    await setAuthStorage(page)
    const { releaseDocuments } = await stubRoutes(page, { freezeDocuments: true })
    const nav = page.goto('/platform/documents')

    // Expect loading state to be visible
    await page.waitForSelector('[data-testid="documents-loading"]', { timeout: 10_000 })
    await expect(page.locator('[data-testid="documents-loading"]')).toBeVisible()

    // No ErrorBoundary must be visible
    const bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('Something went wrong')

    // Release the route and let it load
    releaseDocuments()
    await nav
    await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10_000 })
    await expect(page.locator('[data-testid="documents-loading"]')).not.toBeVisible()
  })

  test('2) Documents page empty state is explicit and does not imply medical normality', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { documents: [] })
    await page.goto('/platform/documents')

    await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10_000 })
    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()

    // Assert explicit empty state message is shown
    await expect(page.getByText('尚未上傳任何文件')).toBeVisible()

    // Safety checks: no copy implying medical normality, no overclaim
    const bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('正常代表沒問題')
    
    // Explicitly make sure we don't display "正常" when there is no data to back it up
    expect(bodyText).not.toContain('檢驗結果正常')
    expect(bodyText).not.toContain('指標正常')

    for (const phrase of PROHIBITED_PHRASES) {
      expect(bodyText.toLowerCase()).not.toContain(phrase.toLowerCase())
    }
  })

  test('3) Documents page API error state does not show ErrorBoundary and has no medical overclaim', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { documentsStatus: 500 })
    await page.goto('/platform/documents')

    await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10_000 })
    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()

    // Upload section must still be accessible for retry
    await expect(page.locator('[data-testid="documents-upload-section"]')).toBeVisible()

    // No ErrorBoundary
    const bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('Something went wrong')

    // No medical overclaim
    for (const phrase of PROHIBITED_PHRASES) {
      expect(bodyText.toLowerCase()).not.toContain(phrase.toLowerCase())
    }
  })

  test('4) Actions page loading / empty / API error state remains safe', async ({ page }) => {
    await setAuthStorage(page)
    
    // Loading State
    const { releaseDashboard } = await stubRoutes(page, { freezeDashboard: true })
    const nav = page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-loading"]', { timeout: 10_000 })
    await expect(page.locator('[data-testid="actions-loading"]')).toBeVisible()
    await expect(page.locator('[data-testid="actions-page"]')).not.toBeVisible()

    // Release loading
    releaseDashboard()
    await nav
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })
    await expect(page.locator('[data-testid="actions-loading"]')).not.toBeVisible()

    // Empty State
    await stubRoutes(page, {
      documents: [],
      dashboard: { ...BASE_DASHBOARD, recent_labs: [], alerts: [], insights: [], recommendations: [], decision_items: [], prioritized_actions: [] },
      recommendations: { recommendations: [], total: 0, missing_data: [] },
      outcomeFeedback: OUTCOME_EMPTY,
    })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()
    
    // Empty message/state should render
    await expect(page.getByText('目前還沒有任務')).toBeVisible()
    let bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('Something went wrong')
    for (const phrase of PROHIBITED_PHRASES) {
      expect(bodyText.toLowerCase()).not.toContain(phrase.toLowerCase())
    }

    // API Error State
    await stubRoutes(page, {
      dashboardStatus: 500,
      recommendationsStatus: 500,
      outcomeFeedbackStatus: 500,
    })
    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()
    bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('Something went wrong')
    for (const phrase of PROHIBITED_PHRASES) {
      expect(bodyText.toLowerCase()).not.toContain(phrase.toLowerCase())
    }
  })

  test('5) Dashboard evidence-related empty or partial data state does not erase confirmed report state incorrectly', async ({ page }) => {
    await setAuthStorage(page)
    // Stub dashboard as empty or partial (recent_labs: [])
    // but documents list has the confirmed report
    await stubRoutes(page, {
      documents: [DOC_CONFIRMED],
      dashboard: { ...BASE_DASHBOARD, recent_labs: [] },
    })

    // Navigate to Documents page and ensure the confirmed document is still present
    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10_000 })
    await expect(page.getByText('2026_synthetic_lab_report.pdf')).toBeVisible()
    await expect(page.getByText('已確認')).toBeVisible()

    // Navigate to Dashboard and verify narrative / dashboard functions correctly
    await page.goto('/platform/dashboard')
    await expect(page.locator('body')).toBeVisible()
    const bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('Something went wrong')
  })

  test('6) Partial data responses do not produce broken evidence links', async ({ page }) => {
    await setAuthStorage(page)
    
    // Recommendation links to a missing document_id
    const recsWithMissingDoc = {
      person_id: 'person-self',
      recommendations: [
        {
          action_id: 'rec-missing-doc-p149',
          source_type: 'lab_report_item',
          source_id: 'rule-missing-doc-p149',
          title: '建議進行肝臟健康管理',
          why_now: '測試遺失的報告ID連結',
          priority: 'medium',
          evidence_summary: '測試缺少 document_id 情況',
          document_id: 'non-existent-doc-id', // missing from documents list
          expected_health_impact: '有助於掌握肝臟代謝功能',
          evidence_sources: [],
          is_tracking: false,
          evidence_level: 'B',
          trust: null
        }
      ],
      total: 1,
      missing_data: []
    }

    await stubRoutes(page, {
      documents: [DOC_CONFIRMED], // doc-confirmed-p149 is here, non-existent-doc-id is not
      recommendations: recsWithMissingDoc,
    })

    await page.goto('/platform/actions')
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10_000 })
    
    // Link must be visible
    const sourceLink = page.locator('[data-testid="p89-source-page-link"]').first()
    await expect(sourceLink).toBeVisible()
    const href = await sourceLink.getAttribute('href')
    expect(href).toContain('/platform/documents?document_id=non-existent-doc-id')

    // Clicking the link should navigate to Documents page without a JS crash / error boundary
    await sourceLink.click()
    await page.waitForURL(/\/platform\/documents\?document_id=non-existent-doc-id/)
    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()
    const bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('Something went wrong')
  })

  test('7) Suppressed/not-judged/unknown copy is not described as normal', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    // Open drawer
    await page.goto('/platform/documents?document_id=doc-confirmed-p149')
    const drawer = page.locator('[role="dialog"]')
    await expect(drawer).toBeVisible()

    // Suppressed row: item_name ALT has mismatch reason, should not display "正常"
    const altRow = drawer.locator('tr').filter({ hasText: 'ALT' })
    await expect(altRow).toBeVisible()
    await expect(altRow.getByText('單位不同，暫不判斷異常')).toBeVisible()
    await expect(altRow.getByText('正常')).not.toBeVisible()

    // Safety checks
    const drawerText = await drawer.innerText()
    for (const phrase of PROHIBITED_PHRASES) {
      expect(drawerText.toLowerCase()).not.toContain(phrase.toLowerCase())
    }
  })
})
