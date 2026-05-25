/**
 * P52 — Daily Recommendation Browser Acceptance
 *
 * Validates that evidence_summary, why_now, next_action, and
 * data_insufficiency_reason are all visible on Dashboard and Actions surfaces
 * after the P51 backend enrichment.
 *
 * Strategy: fully mocked (no live backend, no auth required).
 * All API routes are intercepted by page.route() before navigation.
 */

import { expect, test } from '@playwright/test'

// ── Shared fixtures ───────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD = {
  health_score: { overall_score: 78, components: {} },
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P52 mocked summary',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P52 test summary',
    risks: [],
    trends: [],
    reasons: [],
    actions: [],
    delta_summary: '目前無明顯變化',
    improvements: [],
    deteriorations: [],
    adherence: [],
    missed_risks: [],
  },
}

/** One rich recommendation returned by /health-assistant/recommendations */
const RICH_REC = {
  action_id: null,
  rule_id: 'rec_p52_risk',
  title: '每日監測血壓',
  priority: 'high',
  source_type: 'risk_alert',
  why_now: '目前有 主動風險警示：血壓偏高，嚴重度 high',
  expected_health_impact: '穩定控制血壓，降低心血管風險',
  evidence_summary: '風險警示：血壓偏高（this_week觸發）',
  data_insufficiency_reason: null,
  next_action: '請查看完整風險說明',
  is_tracking: false,
  evidence_sources: [],
  evidence_level: 'A',
  trust: null,
  rank: 0,
}

/** A fallback recommendation with data_insufficiency_reason set */
const FALLBACK_REC = {
  action_id: null,
  rule_id: 'missing_data_metrics',
  title: '記錄健康指標',
  priority: 'medium',
  source_type: 'missing_data',
  why_now: '目前沒有近期健康指標記錄，無法進行精準健康評估',
  expected_health_impact: '補充資料後提升評估精準度',
  evidence_summary: '目前無健康指標資料（血壓、血糖、體重等）',
  data_insufficiency_reason:
    '缺少近期健康指標，建議可信度有限。補充資料後系統可提供個人化建議。',
  next_action: '前往記錄血壓、血糖或體重',
  is_tracking: false,
  evidence_sources: [],
  evidence_level: 'C',
  trust: null,
  rank: 1,
}

const ASSISTANT_RESPONSE = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  recommendations: [RICH_REC, FALLBACK_REC],
  missing_data: ['健康指標（血壓、血糖、體重等）'],
}

/** Install shared localStorage state before page is loaded */
async function setAuthStorage(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'e2e-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
}

/** Install API route stubs */
async function stubRoutes(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/**', (route) => {
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
    if (path.includes('/health-assistant/recommendations')) {
      return route.fulfill({ json: ASSISTANT_RESPONSE })
    }
    if (path.includes('/health-assistant/daily-summary')) {
      return route.fulfill({ json: { topRisk: '', biggestChange: '', todayAction: '', generated_at: new Date().toISOString() } })
    }
    if (path.includes('/health-assistant/outcome-feedback')) {
      return route.fulfill({ json: { summary: { total_count: 0 } } })
    }
    if (path.includes('/health-assistant/notifications/intelligent')) {
      return route.fulfill({ json: { person_id: 'person-self', generated_at: new Date().toISOString(), items: [], suppressed: [], total_candidates: 0 } })
    }
    if (path.includes('/orchestrator/dashboard-summary')) {
      return route.fulfill({ json: null })
    }
    if (path.includes('/health-assistant/family-relationships')) {
      return route.fulfill({ json: { person_id: 'person-self', relationships: [], total: 0 } })
    }
    if (path.includes('/health-assistant/family-health-context')) {
      return route.fulfill({ json: { person_id: 'person-self', context: null } })
    }
    if (path.includes('/health-assistant/family-recommendations')) {
      return route.fulfill({ json: { person_id: 'person-self', recommendations: [], total: 0 } })
    }
    if (path.includes('/health-assistant/narrative-memory/cross-period')) {
      return route.fulfill({ json: { person_id: 'person-self', reasoning: null } })
    }
    if (path.endsWith('/dashboard')) {
      return route.fulfill({ json: BASE_DASHBOARD })
    }
    if (path.includes('/actions/prioritized') || path.endsWith('/actions')) {
      return route.fulfill({ json: [] })
    }
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if (path.endsWith('/weekly-report')) return route.fulfill({ json: { items: [] } })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

// ── Test group: Actions page ──────────────────────────────────────────────────

test.describe('P52 — Actions page recommendation fields', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)
  })

  test('renders evidence_summary for a rich recommendation', async ({ page }) => {
    await page.goto('/platform/actions')
    await expect(page.getByText('風險警示：血壓偏高（this_week觸發）')).toBeVisible()
  })

  test('renders why_now bullet for a rich recommendation', async ({ page }) => {
    await page.goto('/platform/actions')
    await expect(
      page.getByText('目前有 主動風險警示：血壓偏高，嚴重度 high')
    ).toBeVisible()
  })

  test('renders next_action for a rich recommendation', async ({ page }) => {
    await page.goto('/platform/actions')
    await expect(page.getByText(/請查看完整風險說明/)).toBeVisible()
  })

  test('renders data_insufficiency_reason for a fallback recommendation', async ({ page }) => {
    await page.goto('/platform/actions')
    await expect(
      page.getByText('缺少近期健康指標，建議可信度有限。補充資料後系統可提供個人化建議。')
    ).toBeVisible()
  })

  test('fallback recommendation title is visible', async ({ page }) => {
    await page.goto('/platform/actions')
    await expect(page.getByText('記錄健康指標')).toBeVisible()
  })

  test('rich recommendation does not show data_insufficiency_reason block', async ({ page }) => {
    await page.goto('/platform/actions')
    // The rich rec has null data_insufficiency_reason — amber warning should appear only once (from fallback)
    const warnings = page.getByText(/缺少近期健康指標/)
    await expect(warnings).toHaveCount(1)
  })
})

// ── Test group: Dashboard ─────────────────────────────────────────────────────

test.describe('P52 — Dashboard health-assistant panel recommendation fields', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page)
  })

  test('dashboard loads without error', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByRole('heading', { name: '儀表板' })).toBeVisible()
  })

  test('renders why_now in health-assistant panel', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(
      page.getByText('目前有 主動風險警示：血壓偏高，嚴重度 high').first()
    ).toBeVisible()
  })

  test('renders next_action in health-assistant panel', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText(/請查看完整風險說明/).first()).toBeVisible()
  })

  test('renders evidence_summary in health-assistant panel', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText('風險警示：血壓偏高（this_week觸發）').first()).toBeVisible()
  })

  test('renders data_insufficiency_reason for fallback rec in health-assistant panel', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(
      page.getByText('缺少近期健康指標，建議可信度有限。補充資料後系統可提供個人化建議。').first()
    ).toBeVisible()
  })
})
