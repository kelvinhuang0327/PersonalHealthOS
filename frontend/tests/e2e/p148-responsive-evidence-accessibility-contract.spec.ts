import { expect, test } from '@playwright/test'

// Set viewport to mobile
test.use({ viewport: { width: 390, height: 844 } })

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const DOC_CONFIRMED = {
  id: 'doc-confirmed-p148',
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
      id: 'doc-confirmed-p148',
      abnormal_items: 1,
      report_date: new Date().toISOString().split('T')[0],
    },
  ],
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P148 mobile lab report dashboard state',
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
    document_id: 'doc-confirmed-p148',
    summary: 'suppressed_unit_scale_mismatch（暫不判斷異常）',
  },
}

const RECOMMENDATIONS = {
  person_id: 'person-self',
  recommendations: [
    {
      action_id: 'rec-ast-p148',
      source_type: 'lab_report_item',
      source_id: 'rule-ast-high-p148',
      title: '建議進行肝臟健康管理',
      why_now: '您的健檢報告顯示 AST 偏高',
      priority: 'medium',
      evidence_summary: '檢驗資料含 suppressed_unit_scale_mismatch，暫不判斷異常',
      document_id: 'doc-confirmed-p148',
      expected_health_impact: '有助於掌握肝臟代謝功能',
      evidence_sources: [{ type: 'lab_report_item', id: 'rule-ast-high-p148', summary: 'AST 偏高' }],
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
    localStorage.setItem('token', 'p148-mock-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  customDocs: any[] = [DOC_CONFIRMED],
  customRecs: any = RECOMMENDATIONS,
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
            id: 'item-suppressed-p148',
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

test.describe('P148 — Responsive Evidence Accessibility Contract (Mobile Viewport)', () => {
  test('1) Documents page renders and remains usable on mobile viewport with basic accessibility roles', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)
    await page.goto('/platform/documents')

    // 1. Documents page remains usable on mobile viewport
    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()
    await expect(page.locator('[data-testid="documents-list-section"]')).toBeVisible()
    await expect(page.locator('[data-testid="documents-upload-section"]')).toBeVisible()

    // 2. No ErrorBoundary appears
    const bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('Something went wrong')

    // 3. No diagnosis/cure/guarantee/doctor-replacement language appears
    for (const phrase of PROHIBITED_PHRASES) {
      expect(bodyText.toLowerCase()).not.toContain(phrase.toLowerCase())
    }

    // 4. Basic accessible names/roles
    const uploadButton = page.getByRole('button', { name: '上傳' })
    await expect(uploadButton).toBeVisible()
    await expect(uploadButton).toBeDisabled()

    const reviewButton = page.getByRole('button', { name: '審閱解析結果' })
    await expect(reviewButton).toBeVisible()
    await expect(reviewButton).toBeEnabled()
  })

  test('2) Actions page renders and remains usable on mobile viewport with evidence/source link', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)
    await page.goto('/platform/actions')

    // 1. Actions page remains usable on mobile viewport
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()

    // 2. Recommendation is visible
    await expect(page.getByText('建議進行肝臟健康管理')).toBeVisible()

    // 3. Evidence/source link remains reachable and readable
    const sourceLink = page.locator('[data-testid="p89-source-page-link"]').first()
    await expect(sourceLink).toBeVisible()
    await expect(sourceLink).toContainText('查看健檢報告')
    const href = await sourceLink.getAttribute('href')
    expect(href).toContain('/platform/documents?document_id=doc-confirmed-p148')

    // 4. No ErrorBoundary appears
    const bodyText = await page.locator('body').innerText()
    expect(bodyText).not.toContain('Something went wrong')

    // 5. Basic accessible roles on Actions page
    const snoozeButton = page.getByRole('button', { name: '稍後提醒' })
    await expect(snoozeButton).toBeVisible()
  })

  test('3) Parsed items drawer can open, close, shows suppressed copy properly, and has accessible elements on mobile viewport', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)

    // 1. Navigate directly using deep link to open the drawer
    await page.goto('/platform/documents?document_id=doc-confirmed-p148')

    // Verify drawer (role="dialog") opens
    const drawer = page.locator('[role="dialog"]')
    await expect(drawer).toBeVisible()

    // 2. Suppressed/not-judged copy remains visible and is not described as normal
    const suppressedBadge = drawer.getByText('單位不同，暫不判斷異常')
    await expect(suppressedBadge).toBeVisible()
    
    // The status cell for ALT (suppressed mismatch) must NOT show "正常"
    const row = drawer.locator('tr').filter({ hasText: 'ALT' })
    await expect(row).toBeVisible()
    await expect(row.getByText('正常')).not.toBeVisible()

    // 3. Basic accessible names/roles in drawer
    // Input for date has matching label (accessible name via label)
    const dateInput = page.getByLabel('健檢日期（選填）')
    await expect(dateInput).toBeVisible()

    const confirmButton = page.getByRole('button', { name: '確認並分析' })
    await expect(confirmButton).toBeVisible()

    const laterButton = page.getByRole('button', { name: '稍後確認' })
    await expect(laterButton).toBeVisible()

    // 4. No diagnosis/cure/guarantee/doctor-replacement language inside drawer
    const drawerText = await drawer.innerText()
    for (const phrase of PROHIBITED_PHRASES) {
      expect(drawerText.toLowerCase()).not.toContain(phrase.toLowerCase())
    }

    // 5. Drawer can close on mobile viewport
    const closeBtn = drawer.locator('button').first()
    await expect(closeBtn).toBeVisible()
    await closeBtn.click()

    // Verify it closed
    await expect(drawer).not.toBeVisible()
  })
})
