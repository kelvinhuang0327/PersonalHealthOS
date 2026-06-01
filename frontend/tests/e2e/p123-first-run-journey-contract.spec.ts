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
  explainability_summary: 'P123 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P123',
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

const DAILY_SUMMARY_BASIC = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  topRisk: '近期建議持續追蹤',
  biggestChange: '本週睡眠時數略下降',
  todayAction: '先完成今日症狀與行動記錄',
  whyNow: '目前資料可協助整理健康趨勢',
  confidence: 0.68,
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
    localStorage.setItem('token', 'p123-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
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

test.describe('P123 — Minimal First-Run Journey Contract', () => {
  test('1) empty state shows first-run checklist', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { documents: [], symptoms: [], dailySummary: DAILY_SUMMARY_EMPTY })
    await page.goto('/platform/dashboard')

    await expect(page.locator('[data-testid="first-run-journey-card"]')).toBeVisible()
    await expect(page.locator('[data-testid="first-run-journey-empty"]')).toBeVisible()
  })

  test('2) checklist has clickable entries for documents/symptoms/dashboard/actions routes', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { documents: [], symptoms: [] })
    await page.goto('/platform/dashboard')

    await expect(page.locator('[data-testid="first-run-link-documents"]')).toHaveAttribute('href', '/platform/documents')
    await expect(page.locator('[data-testid="first-run-link-symptoms"]')).toHaveAttribute('href', '/platform/symptoms')
    await expect(page.locator('[data-testid="first-run-link-dashboard"]')).toHaveAttribute('href', '/platform/dashboard')
    await expect(page.locator('[data-testid="first-run-link-actions"]')).toHaveAttribute('href', '/platform/actions')
  })

  test('3) documents present but symptoms missing -> prompt next step symptoms', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [],
      dailySummary: DAILY_SUMMARY_EMPTY,
    })
    await page.goto('/platform/dashboard')

    await expect(page.locator('[data-testid="first-run-journey-in-progress"]')).toBeVisible()
    await expect(page.locator('[data-testid="first-run-next-step-symptoms"]')).toBeVisible()
  })

  test('4) symptoms present but documents missing -> prompt next step documents', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [],
      symptoms: [{ id: 's1', symptom: '頭痛', occurred_at: new Date().toISOString() }],
      dailySummary: DAILY_SUMMARY_EMPTY,
    })
    await page.goto('/platform/dashboard')

    await expect(page.locator('[data-testid="first-run-journey-in-progress"]')).toBeVisible()
    await expect(page.locator('[data-testid="first-run-next-step-documents"]')).toBeVisible()
  })

  test('5) basic data ready -> completed state and dashboard/actions routes remain healthy', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [{ id: 's1', symptom: '疲勞', occurred_at: new Date().toISOString() }],
      dailySummary: DAILY_SUMMARY_BASIC,
      recommendations: {
        person_id: 'person-self',
        recommendations: [
          {
            title: '今日建議先記錄血壓',
            why_now: '資料已可提供初步追蹤建議',
            priority: 'medium',
            next_action: '前往行動頁開始追蹤',
            source_type: 'recommendation',
            expected_health_impact: '建立可持續的每日追蹤節奏',
            evidence_sources: [],
            is_tracking: false,
          },
        ],
        total: 1,
        missing_data: [],
      },
    })
    await page.goto('/platform/dashboard')

    await expect(page.locator('[data-testid="first-run-journey-completed"]')).toBeVisible()
    await expect(page.getByText('Something went wrong')).not.toBeVisible()

    await page.click('[data-testid="first-run-link-actions"]')
    await expect(page).toHaveURL(/\/platform\/actions/)
    await expect(page.getByText('Something went wrong')).not.toBeVisible()
  })

  test('6) overclaim guard: prohibited medical claim phrases are absent', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { documents: [], symptoms: [], dailySummary: DAILY_SUMMARY_EMPTY })
    await page.goto('/platform/dashboard')

    const bodyText = (await page.locator('body').innerText()).toLowerCase()
    for (const phrase of PROHIBITED_PHRASES) {
      expect(bodyText).not.toContain(phrase.toLowerCase())
    }
  })

  test('7) suppression/not-judged evidence note does not claim normal', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, {
      documents: [{ id: 'd1', parse_status: 'confirmed' }],
      symptoms: [{ id: 's1', symptom: '疲勞', occurred_at: new Date().toISOString() }],
      dailySummary: {
        ...DAILY_SUMMARY_BASIC,
        topRisk: '檢驗資料含 suppressed_unit_scale_mismatch，暫不判斷異常',
      },
      recommendations: {
        person_id: 'person-self',
        recommendations: [
          {
            title: '先追蹤資料一致性',
            why_now: '避免對單一抑制資料做過度推論',
            next_action: '持續記錄並安排後續檢查',
            source_type: 'lab_abnormality',
            evidence_summary: 'suppressed_unit_scale_mismatch（暫不判斷異常）',
          },
        ],
        total: 1,
        missing_data: [],
      },
    })
    await page.goto('/platform/dashboard')

    const note = page.locator('[data-testid="first-run-suppression-not-judged-note"]')
    await expect(note).toBeVisible()
    await expect(note).not.toContainText('正常')
    await expect(note).toContainText('暫不判斷異常')
  })
})
