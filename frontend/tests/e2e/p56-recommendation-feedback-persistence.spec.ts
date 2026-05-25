/**
 * P56 — Recommendation Feedback Persistence Readiness
 *
 * Validates that:
 * - Clicking "沒有用" on a recommendation POSTs a new action (server persistence)
 * - POST body has correct status and source_id fields
 * - Dismissed recommendation stays hidden after page reload (localStorage)
 * - Dismissed recommendation stays hidden even when localStorage is cleared
 *   (server state synced via actions list with not_useful/not_applicable status)
 *
 * Strategy: fully mocked — no live backend required.
 */

import { expect, test } from '@playwright/test'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const BASE_DASHBOARD = {
  health_score: { overall_score: 75, components: {} },
  alerts: [],
  insights: [],
  recommendations: [],
  trends: {},
  explainability_summary: 'P56 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P56 test',
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

/** Untracked recommendation — appears in DecisionRecommendationLayer */
const UNTRACKED_REC = {
  action_id: null,
  rule_id: 'rec_p56_weight',
  title: '每週量測體重',
  priority: 'medium',
  source_type: 'recommendation',
  why_now: '體重趨勢上升中',
  expected_health_impact: '控制體重',
  evidence_summary: '近 3 週體重上升',
  data_insufficiency_reason: null,
  next_action: '開始記錄體重',
  is_tracking: false,
  evidence_sources: [],
  evidence_level: 'B',
  trust: null,
  rank: 0,
}

/**
 * source_id computed by actions/page.tsx from UNTRACKED_REC:
 *   r.action_id is null → `ha_rec_${r.rule_id}` = 'ha_rec_rec_p56_weight'
 */
const REC_SOURCE_ID = 'ha_rec_rec_p56_weight'

const ASSISTANT_RESPONSE = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  recommendations: [UNTRACKED_REC],
}

/** The action that the server returns after a dismiss POST */
const DISMISSED_ACTION_NOT_USEFUL = {
  id: 'action-p56-dismissed',
  person_id: 'person-self',
  source_type: 'recommendation',
  source_id: REC_SOURCE_ID,
  title: '每週量測體重',
  description: '體重趨勢上升中',
  action_type: 'lifestyle',
  priority: 'medium',
  status: 'not_useful',
  frequency: 'daily',
  streak_count: 0,
  resurface_count: 0,
  confidence: 0.7,
  evidence_level: 'B',
  guideline_source: null,
  rule_id: REC_SOURCE_ID,
  category: 'health',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  outcomes: [],
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function setAuthStorage(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'e2e-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
    // Ensure no stale rec_feedback from previous tests
    localStorage.removeItem('rec_feedback_person-self')
  })
}

/**
 * Set up a stateful route stub. Initially GET /actions returns [].
 * After POST /actions, subsequent GET /actions return [DISMISSED_ACTION_NOT_USEFUL].
 * Returns a getter for the captured POST body.
 */
async function stubRoutesWithPostCapture(
  page: import('@playwright/test').Page,
  opts: { capturePost?: boolean } = {}
) {
  let returnDismissedAction = false
  let capturedPostBody: Record<string, unknown> | null = null

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
      return route.fulfill({
        json: { topRisk: '', biggestChange: '', todayAction: '', generated_at: new Date().toISOString() },
      })
    }
    if (path.includes('/health-assistant/outcome-feedback')) {
      return route.fulfill({ json: { summary: { total_count: 0 } } })
    }
    if (path.includes('/health-assistant/notifications/intelligent')) {
      return route.fulfill({
        json: {
          person_id: 'person-self',
          generated_at: new Date().toISOString(),
          items: [],
          suppressed: [],
          total_candidates: 0,
        },
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

    // GET /actions — returns dismissed action after POST has been called
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') {
      return route.fulfill({ json: returnDismissedAction ? [DISMISSED_ACTION_NOT_USEFUL] : [] })
    }

    // POST /actions — capture body and flip state
    if (path.endsWith('/actions') && method === 'POST') {
      try {
        capturedPostBody = JSON.parse(route.request().postData() ?? '{}')
      } catch {
        capturedPostBody = {}
      }
      returnDismissedAction = true
      return route.fulfill({ status: 201, json: { ...DISMISSED_ACTION_NOT_USEFUL, id: 'action-server-dismissed' } })
    }

    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if (path.endsWith('/weekly-report')) return route.fulfill({ json: { items: [] } })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })

  return {
    getPostBody: () => capturedPostBody,
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P56 — Recommendation Feedback Persistence', () => {
  test('POSTs a new action with status=not_useful when "沒有用" clicked on recommendation', async ({ page }) => {
    await setAuthStorage(page)
    const { getPostBody } = await stubRoutesWithPostCapture(page)

    await page.goto('/platform/actions')
    await expect(page.getByText('每週量測體重').first()).toBeVisible({ timeout: 10000 })

    // Wait for POST request to be made when dismiss is clicked
    const responsePromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/actions') && resp.request().method() === 'POST',
      { timeout: 5000 }
    )
    await page.getByRole('button', { name: '沒有用' }).first().click()
    await responsePromise

    const body = getPostBody()
    expect(body).not.toBeNull()
    expect(body?.status).toBe('not_useful')
  })

  test('POST body for recommendation dismiss includes source_id', async ({ page }) => {
    await setAuthStorage(page)
    const { getPostBody } = await stubRoutesWithPostCapture(page)

    await page.goto('/platform/actions')
    await expect(page.getByText('每週量測體重').first()).toBeVisible({ timeout: 10000 })

    const responsePromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/actions') && resp.request().method() === 'POST',
      { timeout: 5000 }
    )
    await page.getByRole('button', { name: '沒有用' }).first().click()
    await responsePromise

    const body = getPostBody()
    expect(body?.source_id).toBe(REC_SOURCE_ID)
  })

  test('dismissed recommendation stays hidden after page reload (localStorage)', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesWithPostCapture(page)

    await page.goto('/platform/actions')
    await expect(page.getByText('每週量測體重').first()).toBeVisible({ timeout: 10000 })

    // Dismiss and wait for POST
    const responsePromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/actions') && resp.request().method() === 'POST',
      { timeout: 5000 }
    )
    await page.getByRole('button', { name: '沒有用' }).first().click()
    await responsePromise

    // Reload — localStorage rec_feedback survives
    await page.reload()
    await page.waitForLoadState('networkidle', { timeout: 10000 })

    // Recommendation must still be filtered: the layer-specific snooze button should not appear.
    // ("稍後提醒" only appears for untracked recommendations in the decision layer.)
    // The dismissed action still shows in grouped.dismissed — so the title text may still be
    // visible there — but without the recommendation-layer buttons.
    await expect(page.getByRole('button', { name: '稍後提醒' })).toHaveCount(0, { timeout: 8000 })
    await expect(page.getByRole('button', { name: '加入追蹤' })).toHaveCount(0, { timeout: 5000 })
  })

  test('dismissed recommendation stays hidden after localStorage cleared (server sync)', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesWithPostCapture(page)

    await page.goto('/platform/actions')
    await expect(page.getByText('每週量測體重').first()).toBeVisible({ timeout: 10000 })

    // Dismiss and wait for server persistence
    const responsePromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/actions') && resp.request().method() === 'POST',
      { timeout: 5000 }
    )
    await page.getByRole('button', { name: '沒有用' }).first().click()
    await responsePromise

    // Simulate localStorage cleared (e.g. browser data wipe / incognito re-open)
    await page.evaluate(() => {
      localStorage.removeItem('rec_feedback_person-self')
      localStorage.removeItem('health_actions_cache_person-self')
    })

    // Reload — server returns the not_useful action; sync effect hides the recommendation
    await page.reload()
    await page.waitForLoadState('networkidle', { timeout: 10000 })

    // Server sync: dismissed action (status=not_useful) populates recFeedback from server,
    // which filters the recommendation out of the decision layer.
    // "稍後提醒" is exclusive to the recommendation layer — its absence proves the rec is filtered.
    // Use a generous timeout to allow server state → React state → DOM re-render to complete.
    await expect(page.getByRole('button', { name: '稍後提醒' })).toHaveCount(0, { timeout: 10000 })
    await expect(page.getByRole('button', { name: '加入追蹤' })).toHaveCount(0, { timeout: 5000 })
  })
})
