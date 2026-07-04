import { expect, test } from '@playwright/test'

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const DOC_CONFIRMED = {
  id: 'doc-confirmed-p147',
  original_filename: '2026_synthetic_lab_report.pdf',
  parse_status: 'confirmed',
  confirmed_at: new Date().toISOString(),
  uploaded_at: new Date().toISOString(),
  category: 'health_check',
  confirmed_data: { extracted_items: 3, abnormal_items: 1 },
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
      id: 'doc-confirmed-p147',
      abnormal_items: 1,
      report_date: new Date().toISOString().split('T')[0],
    },
  ],
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P147 synthetic lab report dashboard state',
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
    document_id: 'doc-confirmed-p147',
    summary: 'suppressed_unit_scale_mismatch（暫不判斷異常）',
  },
}

// Edge case recommendations
const EDGE_CASE_RECOMMENDATIONS = {
  person_id: 'person-self',
  recommendations: [
    {
      action_id: 'rec-missing-doc-id',
      source_type: 'lab_report_item',
      source_id: 'rule-ast-high-missing',
      title: '建議進行肝臟健康管理',
      why_now: '您的健檢報告顯示 AST 偏高',
      priority: 'medium',
      evidence_summary: '檢驗資料顯示異常但無報告ID',
      document_id: null, // missing document_id fallback
      expected_health_impact: '有助於掌握肝臟代謝功能',
      evidence_sources: [],
      is_tracking: false,
      evidence_level: 'B',
      trust: null
    },
    {
      action_id: 'rec-unknown-source-type',
      source_type: 'unknown_source_type', // unknown source_type
      source_id: 'rule-unknown',
      title: '未知來源建議',
      why_now: '測試未知來源類型',
      priority: 'low',
      evidence_summary: '未知來源的證據摘要',
      document_id: 'doc-confirmed-p147',
      expected_health_impact: '無特定影響',
      evidence_sources: [],
      is_tracking: false,
      evidence_level: 'C',
      trust: null
    },
    {
      action_id: 'rec-risk-alert',
      source_type: 'risk_alert', // source type with no href mapping
      source_id: 'rule-risk-alert',
      title: '風險警示建議',
      why_now: '測試風險警示無連結',
      priority: 'high',
      evidence_summary: '風險警示的證據摘要',
      document_id: 'doc-confirmed-p147',
      expected_health_impact: '降低風險',
      evidence_sources: [],
      is_tracking: false,
      evidence_level: 'A',
      trust: null
    }
  ],
  total: 3,
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
    localStorage.setItem('token', 'p147-mock-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  customDocs: any[] = [DOC_CONFIRMED],
  customRecs: any = EDGE_CASE_RECOMMENDATIONS,
) {
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
      return route.fulfill({ json: customDocs })
    }
    if (path.includes('/documents/') && path.includes('/parsed-items')) {
      return route.fulfill({
        json: [
          {
            id: 'item-suppressed',
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
    if (path.includes('/health-assistant/recommendations')) return route.fulfill({ json: customRecs })
    if (path.includes('/health-assistant/outcome-feedback')) return route.fulfill({ json: OUTCOME_EMPTY })
    if (path.includes('/health-assistant/notifications/intelligent')) {
      return route.fulfill({ json: { person_id: 'person-self', generated_at: new Date().toISOString(), items: [], suppressed: [], total_candidates: 0 } })
    }
    if (path.includes('/orchestrator/dashboard-summary')) return route.fulfill({ json: null })
    if (path.includes('/health-assistant/family-relationships')) return route.fulfill({ json: { person_id: 'person-self', relationships: [], total: 0 } })
    if (path.includes('/health-assistant/family-health-context')) return route.fulfill({ json: { person_id: 'person-self', context: null } })
    if (path.includes('/health-assistant/family-recommendations')) return route.fulfill({ json: { person_id: 'person-self', recommendations: [], total: 0 } })
    if (path.includes('/health-assistant/narrative-memory/cross-period')) return route.fulfill({ json: { person_id: 'person-self', reasoning: null } })

    if (path.endsWith('/dashboard')) return route.fulfill({ json: BASE_DASHBOARD })
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

test.describe('P147 — Evidence Edge-Case UI Contract', () => {
  test('1) Documents deep link with unknown document_id does not crash & does not open wrong drawer', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)
    
    // Go to Documents page with unknown document_id
    await page.goto('/platform/documents?document_id=unknown-doc-id')
    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()
    await expect(page.locator('[data-testid="documents-list-section"]')).toBeVisible()

    // Wrong drawer should not be open
    await expect(page.locator('[role="dialog"]')).not.toBeVisible()
  })

  test('2) Actions recommendation metadata edge cases degrade safely without crashes', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    // Go to Actions page
    await page.goto('/platform/actions')
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()

    // 1. Check recommendation with missing document_id (falls back to meta.href)
    const recMissingDocId = page.locator('div.rounded-2xl').filter({ hasText: '建議進行肝臟健康管理' })
    await expect(recMissingDocId).toBeVisible()
    const linkMissingDocId = recMissingDocId.locator('[data-testid="p89-source-page-link"]')
    await expect(linkMissingDocId).toBeVisible()
    const href1 = await linkMissingDocId.getAttribute('href')
    expect(href1).toBe('/platform/documents') // no document_id query param

    // 2. Check recommendation with unknown source_type (no link rendered)
    const recUnknownType = page.locator('div.rounded-2xl').filter({ hasText: '未知來源建議' })
    await expect(recUnknownType).toBeVisible()
    const linkUnknownType = recUnknownType.locator('[data-testid="p89-source-page-link"]')
    await expect(linkUnknownType).not.toBeVisible()

    // 3. Check recommendation with risk_alert source_type (no href mapping → no link rendered)
    const recRiskAlert = page.locator('div.rounded-2xl').filter({ hasText: '風險警示建議' })
    await expect(recRiskAlert).toBeVisible()
    const linkRiskAlert = recRiskAlert.locator('[data-testid="p89-source-page-link"]')
    await expect(linkRiskAlert).not.toBeVisible()
  })

  test('3) Safe fallback copy and suppressed/not-judged handling inside drawer', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    // Go to Documents page with correct document_id to trigger drawer
    await page.goto('/platform/documents?document_id=doc-confirmed-p147')
    await expect(page.locator('[role="dialog"]')).toBeVisible()

    // Verify suppressed state display
    await expect(page.getByText('單位不同，暫不判斷異常')).toBeVisible()

    // Safety audit: check that no medical overclaims or diagnostic language appears
    const drawerText = await page.locator('[role="dialog"]').innerText()
    for (const phrase of PROHIBITED_PHRASES) {
      expect(drawerText.toLowerCase()).not.toContain(phrase.toLowerCase())
    }
  })

  test('4) Cross-surface navigation does not regress to empty state or ErrorBoundary', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    // Go to Dashboard
    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="first-run-journey-card"]')).toBeVisible()

    // Click navigation to Documents
    await page.click('a[href="/platform/documents"]')
    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()

    // Click navigation to Actions
    await page.click('a[href="/platform/actions"]')
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()

    // Navigate back to Dashboard
    await page.click('a[href="/platform/dashboard"]')
    await expect(page.locator('[data-testid="first-run-journey-card"]')).toBeVisible()

    // Verify no error boundary text is shown anywhere
    const bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('Something went wrong')
  })
})
