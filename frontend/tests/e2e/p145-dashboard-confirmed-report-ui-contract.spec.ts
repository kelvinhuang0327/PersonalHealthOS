import { expect, test } from '@playwright/test'

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD_ALIGNED_WITH_P144 = {
  health_score: {
    overall_score: 72,
    components: {
      risk_alerts_penalty: 15,
    },
  },
  recent_labs: [
    {
      id: 'doc-confirmed-1',
      abnormal_items: 3, // AST, Glucose, Total Cholesterol
      report_date: new Date().toISOString().split('T')[0],
    },
  ],
  alerts: [
    { id: 'alert-1', rule_id: 'liver_ast_high', title: 'AST 偏高', severity: 'warning', priority: 'medium' },
    { id: 'alert-2', rule_id: 'lipid_cholesterol_high', title: '膽固醇偏高', severity: 'warning', priority: 'medium' },
  ],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P145 confirmed report dashboard state mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: '根據您已確認的報告，我們發現了 3 項異常。',
    risks: ['AST 及血糖偏高，建議關注肝臟與代謝指標。'],
    trends: [],
    reasons: [],
    actions: ['每天量測血壓與記錄飲食'],
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
  biggestChange: '本週睡眠時數略下降',
  todayAction: '先完成今日症狀與行動記錄',
  whyNow: '目前資料可協助整理健康趨勢',
  confidence: 0.68,
  topRiskRef: {
    source_type: 'lab_abnormality',
    summary: 'suppressed_unit_scale_mismatch（暫不判斷異常）',
  },
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
    insufficient_data_count: 1, // trigger daily-summary-outcome-unknown
    tracking_count: 1,         // trigger daily-summary-outcome-unknown
    not_useful_count: 0,
    not_applicable_count: 0,
    snoozed_count: 0,
    total_count: 2,
  },
}

const PROHIBITED_PHRASES = [
  '診斷',
  '治癒',
  '保證改善',
  '取代醫師',
  '正常代表沒問題',
  'guarantee',
  'cure',
]

type StubOptions = {
  documents?: object[]
  symptoms?: object[]
  dailySummary?: object
  recommendations?: object
  outcomeFeedback?: object
}

async function setAuthStorage(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'p145-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
}

async function stubRoutes(page: import('@playwright/test').Page, opts: StubOptions = {}) {
  const documents = opts.documents ?? []
  const symptoms = opts.symptoms ?? []
  const dailySummary = opts.dailySummary ?? DAILY_SUMMARY_WITH_CONFIRMED_REPORT
  const recommendations = opts.recommendations ?? { person_id: 'person-self', recommendations: [], total: 0, missing_data: [] }
  const outcomeFeedback = opts.outcomeFeedback ?? OUTCOME_WITH_UNKNOWN_DATA

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

    if ((path.endsWith('/documents') || path.includes('/documents?')) && method === 'GET') return route.fulfill({ json: documents })
    if ((path.endsWith('/symptoms') || path.includes('/symptoms?')) && method === 'GET') return route.fulfill({ json: symptoms })

    if (path.includes('/health-assistant/daily-summary')) return route.fulfill({ json: dailySummary })
    if (path.includes('/health-assistant/recommendations')) return route.fulfill({ json: recommendations })
    if (path.includes('/health-assistant/outcome-feedback')) return route.fulfill({ json: outcomeFeedback })
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
    if ((path.endsWith('/metrics') || path.includes('/metrics?')) && method === 'GET') return route.fulfill({ json: [] })
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/risk-alerts')) return route.fulfill({ json: [] })
    if (path.includes('/risk-alerts/unread-count')) return route.fulfill({ json: { count: 0 } })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })

    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

test.describe('P145 — Dashboard Confirmed Report UI Contract', () => {
  test('1) first-run card is not in empty state and shows confirmed report progress', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [],
    })
    await page.goto('/platform/dashboard')

    // 1. First-run journey card is visible and does not show empty state
    await expect(page.locator('[data-testid="first-run-journey-card"]')).toBeVisible()
    await expect(page.locator('[data-testid="first-run-journey-empty"]')).not.toBeVisible()
    await expect(page.locator('[data-testid="first-run-journey-in-progress"]')).toBeVisible()

    // 2. Report-related progress is visible and shows completed status
    const docStatus = page.locator('[data-testid="first-run-step-documents-status"]')
    await expect(docStatus).toBeVisible()
    await expect(docStatus).toContainText('已完成')

    // 3. No progress regression copy appears for documents
    await expect(docStatus).not.toContainText('尚未開始')
    await expect(docStatus).not.toContainText('待確認')
  })

  test('2) suppressed/not-judged state is not mislabeled as normal', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [],
    })
    await page.goto('/platform/dashboard')

    // 1. Suppression warning box is visible
    const note = page.locator('[data-testid="first-run-suppression-not-judged-note"]')
    await expect(note).toBeVisible()
    await expect(note).toContainText('暫不判斷異常')
    await expect(note).not.toContainText('正常')

    // 2. Outcome unknown state is visible and not mislabeled as normal
    const outcomeUnknown = page.locator('[data-testid="daily-summary-outcome-unknown"]')
    await expect(outcomeUnknown).toBeVisible()
    await expect(outcomeUnknown).toContainText('目前尚無足夠後續資料判斷效果')
  })

  test('3) safety audit: no medical overclaims or diagnostic language appears', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [],
    })
    await page.goto('/platform/dashboard')

    const bodyText = (await page.locator('body').innerText()).toLowerCase()
    for (const phrase of PROHIBITED_PHRASES) {
      expect(bodyText).not.toContain(phrase.toLowerCase())
    }
  })
})
