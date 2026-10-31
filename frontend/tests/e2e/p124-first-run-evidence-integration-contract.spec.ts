import { expect, test } from '@playwright/test'

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD = {
  health_score: { overall_score: 72, components: {} },
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P124 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P124',
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

const DAILY_SUMMARY_EMPTY = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '',
  biggestChange: '',
  todayAction: '',
  whyNow: '',
  confidence: 0,
}

const DAILY_SUMMARY_WITH_REFS = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '近期建議持續追蹤',
  biggestChange: '頭痛頻率略增加',
  todayAction: '先完成症狀與行動記錄',
  whyNow: '目前資料可協助整理趨勢',
  confidence: 0.72,
  topRiskRef: {
    source_type: 'lab_report_item',
    source_id: 'lab-1',
    document_id: 'doc-1',
    summary: '健檢報告顯示 LDL 偏高',
  },
  todayActionRef: {
    source_type: 'symptom',
    source_id: 'sym-1',
    summary: '近 7 天頭痛次數增加',
  },
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
}

async function setAuthStorage(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'p124-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
}

function makeRec(overrides: Record<string, unknown>) {
  return {
    title: '今日建議先記錄血壓',
    why_now: '資料已可提供初步追蹤建議',
    priority: 'medium',
    next_action: '前往行動頁開始追蹤',
    source_type: 'recommendation',
    source_id: 'rec-1',
    expected_health_impact: '建立可持續的追蹤節奏',
    evidence_sources: [],
    is_tracking: false,
    ...overrides,
  }
}

async function stubRoutes(page: import('@playwright/test').Page, opts: StubOptions = {}) {
  const documents = opts.documents ?? []
  const symptoms = opts.symptoms ?? []
  const dailySummary = opts.dailySummary ?? DAILY_SUMMARY_EMPTY
  const recommendations = opts.recommendations ?? { person_id: 'person-self', recommendations: [], total: 0, missing_data: [] }

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
    if ((path.endsWith('/metrics') || path.includes('/metrics?')) && method === 'GET') return route.fulfill({ json: [] })
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/risk-alerts')) return route.fulfill({ json: [] })
    if (path.includes('/risk-alerts/unread-count')) return route.fulfill({ json: { count: 0 } })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })

    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

test.describe('P124 — First-Run and Actions Evidence Integration Contract', () => {
  test('first-run completion links to the evidence-backed recommendation surface', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [{ id: 's1', symptom: '疲勞', occurred_at: new Date().toISOString() }],
      dailySummary: DAILY_SUMMARY_WITH_REFS,
      recommendations: {
        person_id: 'person-self',
        recommendations: [
          makeRec({ source_type: 'lab_report_item', source_id: 'lab-1', document_id: 'doc-1', evidence_summary: '健檢報告：LDL 偏高' }),
        ],
        total: 1,
        missing_data: [],
      },
    })

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="first-run-journey-completed"]')).toBeVisible()
    for (const [testId, href] of [
      ['first-run-link-documents', '/platform/documents'],
      ['first-run-link-symptoms', '/platform/symptoms'],
      ['first-run-link-dashboard', '/platform/dashboard'],
      ['first-run-link-actions', '/platform/actions'],
    ]) {
      const link = page.locator(`[data-testid="${testId}"]`)
      await expect(link).toBeVisible()
      await expect(link).toHaveAttribute('href', href)
    }
    await expect(page.locator('[data-testid="daily-toprec-evidence-badge"]')).toBeVisible()
    await expect(page.locator('[data-testid="p91-daily-source-page-link"]')).toBeVisible()

    await page.locator('[data-testid="first-run-link-documents"]').click()
    await expect(page).toHaveURL(/\/platform\/documents/)
    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()
    await expect(page.getByText('載入失敗，請重新整理')).not.toBeVisible()

    await page.goto('/platform/dashboard')
    await page.locator('[data-testid="first-run-link-symptoms"]').click()
    await expect(page).toHaveURL(/\/platform\/symptoms/)
    await expect(page.getByText('載入失敗，請重新整理')).not.toBeVisible()

    await page.goto('/platform/dashboard')
    await page.locator('[data-testid="first-run-link-actions"]').click()
    await expect(page).toHaveURL(/\/platform\/actions/)
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()
    await expect(page.getByText('載入失敗，請重新整理')).not.toBeVisible()
  })

  test('suppressed first-run evidence remains cautious and outcome stays unknown', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [{ id: 's1', symptom: '疲勞', occurred_at: new Date().toISOString() }],
      dailySummary: {
        ...DAILY_SUMMARY_WITH_REFS,
        topRisk: '檢驗資料含 suppressed_unit_scale_mismatch，暫不判斷異常',
      },
      recommendations: {
        person_id: 'person-self',
        recommendations: [
          makeRec({
            source_type: 'lab_report_item',
            source_id: 'lab-suppressed',
            evidence_summary: 'suppressed_unit_scale_mismatch（暫不判斷異常）',
            why_now: '資料仍需追蹤，可作為就醫討論參考',
          }),
        ],
        total: 1,
        missing_data: [],
      },
    })

    await page.goto('/platform/dashboard')
    const note = page.locator('[data-testid="first-run-suppression-not-judged-note"]')
    await expect(note).toBeVisible()
    await expect(note).toContainText('暫不判斷異常')
    await expect(note).not.toContainText('正常')
  })

  test('1) lab_report_item recommendation shows evidence_summary with documents source link', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [{ id: 's1', symptom: '疲勞', occurred_at: new Date().toISOString() }],
      dailySummary: DAILY_SUMMARY_WITH_REFS,
      recommendations: {
        person_id: 'person-self',
        recommendations: [
          makeRec({ source_type: 'lab_report_item', source_id: 'lab-1', document_id: 'doc-1', evidence_summary: '健檢報告：LDL 偏高' }),
        ],
        total: 1,
        missing_data: [],
      },
    })

    await page.goto('/platform/actions')
    const evidenceBadge = page.locator('text=健檢報告：LDL 偏高').first()
    await expect(evidenceBadge).toBeVisible()
    const sourceLink = page.locator('[data-testid="p89-source-page-link"]').first()
    await expect(sourceLink).toBeVisible()
    await expect(sourceLink).toHaveAttribute('href', /\/platform\/documents\?document_id=doc-1/)
  })

  test('2) symptom recommendation shows evidence_summary with symptoms source link', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [{ id: 's1', symptom: '頭痛', occurred_at: new Date().toISOString() }],
      dailySummary: DAILY_SUMMARY_WITH_REFS,
      recommendations: {
        person_id: 'person-self',
        recommendations: [
          makeRec({ source_type: 'symptom', source_id: 'sym-1', evidence_summary: '症狀記錄：近 7 天頭痛增加' }),
        ],
        total: 1,
        missing_data: [],
      },
    })

    await page.goto('/platform/actions')
    await expect(page.getByText('症狀記錄：近 7 天頭痛增加')).toBeVisible()
    const sourceLink = page.locator('[data-testid="p89-source-page-link"]').first()
    await expect(sourceLink).toBeVisible()
    await expect(sourceLink).toHaveAttribute('href', '/platform/symptoms')
  })

  test('3) recommendation without evidence does not render an Actions evidence link', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [{ id: 's1', symptom: '頭痛', occurred_at: new Date().toISOString() }],
      dailySummary: DAILY_SUMMARY_WITH_REFS,
      recommendations: {
        person_id: 'person-self',
        recommendations: [
          makeRec({ source_type: 'recommendation', source_id: 'rec-no-evidence', evidence_summary: undefined }),
        ],
        total: 1,
        missing_data: [],
      },
    })

    await page.goto('/platform/actions')
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()
    await expect(page.locator('[data-testid="p89-source-page-link"]')).toHaveCount(0)
    await expect(page.getByText('載入失敗，請重新整理')).not.toBeVisible()

    await page.goto('/platform/dashboard')
    await expect(page.locator('[data-testid="daily-toprec-evidence-badge"]')).toHaveCount(0)
    await expect(page.getByText('載入失敗，請重新整理')).not.toBeVisible()
  })

  test('4) overclaim guard: prohibited medical claim phrases are absent', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [{ id: 's1', symptom: '疲勞', occurred_at: new Date().toISOString() }],
      dailySummary: DAILY_SUMMARY_WITH_REFS,
      recommendations: {
        person_id: 'person-self',
        recommendations: [
          makeRec({ source_type: 'symptom', source_id: 'sym-1', evidence_summary: '症狀記錄：近 7 天頭痛增加' }),
        ],
        total: 1,
        missing_data: [],
      },
    })

    await page.goto('/platform/actions')
    const bodyText = (await page.locator('[data-testid="actions-page"]').innerText()).toLowerCase()
    for (const phrase of PROHIBITED_PHRASES) {
      expect(bodyText).not.toContain(phrase.toLowerCase())
    }
  })

  test('5) retained navigation keeps documents, symptoms, and actions healthy', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [{ id: 's1', symptom: '疲勞', occurred_at: new Date().toISOString() }],
      dailySummary: DAILY_SUMMARY_WITH_REFS,
      recommendations: {
        person_id: 'person-self',
        recommendations: [
          makeRec({ source_type: 'lab_report_item', source_id: 'lab-1', document_id: 'doc-1', evidence_summary: '健檢報告：LDL 偏高' }),
        ],
        total: 1,
        missing_data: [],
      },
    })

    await page.goto('/platform/insights')
    await expect(page.getByRole('heading', { name: '深度分析' })).toBeVisible()

    await page.locator('a[href="/platform/documents"]').click()
    await expect(page).toHaveURL(/\/platform\/documents/)
    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()
    await expect(page.getByText('載入失敗，請重新整理')).not.toBeVisible()

    await page.getByRole('button', { name: '更多' }).click()
    await page.locator('a[href="/platform/symptoms"]').click()
    await expect(page).toHaveURL(/\/platform\/symptoms/)
    await expect(page.getByText('載入失敗，請重新整理')).not.toBeVisible()

    await page.locator('header').getByRole('link', { name: '行動', exact: true }).click()
    await expect(page).toHaveURL(/\/platform\/actions/)
    await expect(page.locator('[data-testid="actions-page"]')).toBeVisible()
    await expect(page.getByText('載入失敗，請重新整理')).not.toBeVisible()

    await page.locator('a[href="/platform/insights"]').click()
    await expect(page).toHaveURL(/\/platform\/insights/)
    await expect(page.getByRole('heading', { name: '深度分析' })).toBeVisible()
  })
})
