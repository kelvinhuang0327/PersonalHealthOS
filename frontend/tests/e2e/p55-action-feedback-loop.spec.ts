/**
 * P55 — Recommendation Action Feedback Loop Browser Acceptance
 *
 * Validates that:
 * - Tracked ActionCards expose "沒有用" and "不適合我" feedback buttons
 * - Recommendation layer exposes "沒有用", "不適合我", and "稍後提醒" buttons
 * - Clicking recommendation dismiss removes the item from the list (localStorage)
 * - Clicking "沒有用" on a tracked action calls PATCH with status=not_useful
 *
 * Strategy: fully mocked (no live backend, no auth required).
 */

import { expect, test } from '@playwright/test'

// ── Shared fixtures ────────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD = {
  health_score: { overall_score: 75, components: {} },
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P55 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P55 test summary',
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

/** A tracked action in todo status (will show "沒有用" / "不適合我" buttons) */
const TODO_ACTION = {
  id: 'action-p55-test',
  person_id: 'person-self',
  source_type: 'recommendation',
  source_id: 'rec_p55',
  title: '每日量測血壓',
  description: '這是 P55 測試用追蹤行動',
  action_type: 'lifestyle',
  priority: 'high',
  status: 'todo',
  frequency: 'daily',
  streak_count: 0,
  resurface_count: 0,
  confidence: 0.75,
  evidence_level: 'B',
  guideline_source: null,
  rule_id: null,
  category: 'blood_pressure',
  created_at: new Date(Date.now() - 60000).toISOString(),
  updated_at: new Date(Date.now() - 60000).toISOString(),
  outcomes: [],
}

/** A recommendation from health-assistant (not yet tracked) */
const UNTRACKED_REC = {
  action_id: null,
  rule_id: 'rec_p55_untracked',
  title: '每週量測體重',
  priority: 'medium',
  source_type: 'recommendation',
  why_now: '體重趨勢上升中',
  expected_health_impact: '控制體重',
  evidence_summary: '近 3 週體重上升',
  data_insufficiency_reason: null,
  next_action: '開始記錄',
  is_tracking: false,
  evidence_sources: [],
  evidence_level: 'B',
  trust: null,
  rank: 0,
}

const ASSISTANT_RESPONSE = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  recommendations: [UNTRACKED_REC],
}

async function setAuthStorage(page: import('@playwright/test').Page, seedActions = false) {
  await page.addInitScript((actions) => {
    localStorage.setItem('token', 'e2e-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
    if (actions.length > 0) {
      localStorage.setItem('health_actions_cache_person-self', JSON.stringify(actions))
    }
  }, seedActions ? [TODO_ACTION] : [])
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: { actions?: object[]; noRecs?: boolean } = {}
) {
  const actions = opts.actions ?? [TODO_ACTION]
  const recsResponse = opts.noRecs
    ? { ...ASSISTANT_RESPONSE, recommendations: [] }
    : ASSISTANT_RESPONSE
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
      return route.fulfill({ json: recsResponse })
    }
    if (path.includes('/health-assistant/daily-summary')) {
      return route.fulfill({
        json: { topRisk: '', biggestChange: '', todayAction: '', generated_at: new Date().toISOString() },
      })
    }
    if (path.includes('/health-assistant/outcome-feedback')) {
      return route.fulfill({ json: { summary: { total_count: 0 } } })
    }
    if (path.includes('/health-assistant/notifications/intelligent')) {
      return route.fulfill({
        json: { person_id: 'person-self', generated_at: new Date().toISOString(), items: [], suppressed: [], total_candidates: 0 },
      })
    }
    if (path.includes('/orchestrator/dashboard-summary')) return route.fulfill({ json: null })
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
    if (path.endsWith('/dashboard')) return route.fulfill({ json: BASE_DASHBOARD })
    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') return route.fulfill({ json: actions })
    if (path.endsWith('/actions') && method === 'POST') {
      return route.fulfill({ status: 201, json: { id: `action-${Date.now()}`, status: 'todo' } })
    }
    if (path.includes('/actions/') && method === 'PATCH') {
      return route.fulfill({ json: { ...TODO_ACTION, status: 'not_useful' } })
    }
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if (path.endsWith('/weekly-report')) return route.fulfill({ json: { items: [] } })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

// ── Tests: ActionCard feedback buttons ────────────────────────────────────────

test.describe('P55 — ActionCard feedback buttons', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthStorage(page, true)
    await stubRoutes(page)
  })

  test('shows "沒有用" button on a todo action', async ({ page }) => {
    await page.goto('/platform/actions')
    await expect(page.getByRole('button', { name: '沒有用' }).first()).toBeVisible({ timeout: 10000 })
  })

  test('shows "不適合我" button on a todo action', async ({ page }) => {
    await page.goto('/platform/actions')
    await expect(page.getByRole('button', { name: '不適合我' }).first()).toBeVisible({ timeout: 10000 })
  })

  test('PATCH is called with status=not_useful when "沒有用" clicked', async ({ page }) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let patchBody: any = null
    await setAuthStorage(page, true)
    await stubRoutes(page, { noRecs: true })
    await page.route('**/api/v1/actions/action-p55-test**', async (route) => {
      if (route.request().method() === 'PATCH') {
        patchBody = JSON.parse(route.request().postData() ?? '{}')
        return route.fulfill({ json: { ...TODO_ACTION, status: 'not_useful' } })
      }
      return route.continue()
    })
    await page.goto('/platform/actions')
    await page.getByRole('button', { name: '沒有用' }).first().click()
    // Give the PATCH call time to fire
    await page.waitForTimeout(500)
    expect(patchBody).not.toBeNull()
    expect(patchBody?.status).toBe('not_useful')
  })

  test('PATCH is called with status=not_applicable when "不適合我" clicked', async ({ page }) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let patchBody: any = null
    await setAuthStorage(page, true)
    await stubRoutes(page, { noRecs: true })
    await page.route('**/api/v1/actions/action-p55-test**', async (route) => {
      if (route.request().method() === 'PATCH') {
        patchBody = JSON.parse(route.request().postData() ?? '{}')
        return route.fulfill({ json: { ...TODO_ACTION, status: 'not_applicable' } })
      }
      return route.continue()
    })
    await page.goto('/platform/actions')
    await page.getByRole('button', { name: '不適合我' }).first().click()
    await page.waitForTimeout(500)
    expect(patchBody).not.toBeNull()
    expect(patchBody?.status).toBe('not_applicable')
  })
})

// ── Tests: DecisionRecommendationLayer dismiss buttons ────────────────────────

test.describe('P55 — Recommendation dismiss buttons', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthStorage(page, false)
    // No tracked actions — so recommendation layer is visible with untracked rec
    await stubRoutes(page, { actions: [] })
  })

  test('shows "稍後提醒" button in recommendation layer', async ({ page }) => {
    await page.goto('/platform/actions')
    await expect(page.getByRole('button', { name: '稍後提醒' }).first()).toBeVisible({ timeout: 10000 })
  })

  test('shows "沒有用" button in recommendation layer', async ({ page }) => {
    await page.goto('/platform/actions')
    await expect(page.getByRole('button', { name: '沒有用' }).first()).toBeVisible({ timeout: 10000 })
  })

  test('shows "不適合我" button in recommendation layer', async ({ page }) => {
    await page.goto('/platform/actions')
    await expect(page.getByRole('button', { name: '不適合我' }).first()).toBeVisible({ timeout: 10000 })
  })

  test('clicking "稍後提醒" on recommendation removes it from list', async ({ page }) => {
    await page.goto('/platform/actions')
    // Verify the recommendation title is visible first
    await expect(page.getByText('每週量測體重').first()).toBeVisible({ timeout: 10000 })
    // Click snooze
    await page.getByRole('button', { name: '稍後提醒' }).first().click()
    // After dismiss, the recommendation card should disappear
    await expect(page.getByText('每週量測體重')).toHaveCount(0, { timeout: 5000 })
  })

  test('clicking "沒有用" on recommendation removes it from list', async ({ page }) => {
    await page.goto('/platform/actions')
    await expect(page.getByText('每週量測體重').first()).toBeVisible({ timeout: 10000 })
    // Click "沒有用" dismiss
    await page.getByRole('button', { name: '沒有用' }).first().click()
    await expect(page.getByText('每週量測體重')).toHaveCount(0, { timeout: 5000 })
  })
})
