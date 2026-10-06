/**
 * P57 — Snooze Server Persistence Readiness
 *
 * Validates that:
 * - Clicking "稍後提醒" on a recommendation POSTs a new action with status=snoozed
 * - POST body includes a snoozed_until field (3 days from now)
 * - Snoozed recommendation stays hidden after page reload (localStorage)
 * - Snoozed recommendation stays hidden even when localStorage is cleared
 *   (server state synced via actions list with snoozed status + future snoozed_until)
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
  explainability_summary: 'P57 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P57 test',
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

const UNTRACKED_REC = {
  action_id: null,
  rule_id: 'rec_p57_activity',
  title: '每日步行目標',
  priority: 'medium',
  source_type: 'recommendation',
  why_now: '活動量不足',
  expected_health_impact: '改善心肺功能',
  evidence_summary: '近兩週步數下降',
  data_insufficiency_reason: null,
  next_action: '開始記錄步數',
  is_tracking: false,
  evidence_sources: [],
  evidence_level: 'B',
  trust: null,
  rank: 0,
}

/**
 * source_id computed by actions/page.tsx:
 *   r.action_id is null → `ha_rec_${r.rule_id}` = 'ha_rec_rec_p57_activity'
 */
const REC_SOURCE_ID = 'ha_rec_rec_p57_activity'

const ASSISTANT_RESPONSE = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  recommendations: [UNTRACKED_REC],
}

/** Future snoozed_until for the action the server returns after POST */
const SNOOZED_UNTIL_FUTURE = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString()

const SNOOZED_ACTION = {
  id: 'action-p57-snoozed',
  person_id: 'person-self',
  source_type: 'recommendation',
  source_id: REC_SOURCE_ID,
  title: '每日步行目標',
  description: '活動量不足',
  action_type: 'lifestyle',
  priority: 'medium',
  status: 'snoozed',
  snoozed_until: SNOOZED_UNTIL_FUTURE,
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
    localStorage.removeItem('rec_feedback_person-self')
  })
}

/**
 * Set up stateful route stubs. Initially GET /actions returns [].
 * After POST /actions (snooze), subsequent GET /actions return [SNOOZED_ACTION].
 */
async function stubRoutesWithPostCapture(page: import('@playwright/test').Page) {
  let returnSnoozedAction = false
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

    // GET /actions — returns snoozed action after POST
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') {
      return route.fulfill({ json: returnSnoozedAction ? [SNOOZED_ACTION] : [] })
    }

    // POST /actions — capture body and flip state
    if (path.endsWith('/actions') && method === 'POST') {
      try {
        capturedPostBody = JSON.parse(route.request().postData() ?? '{}')
      } catch {
        capturedPostBody = {}
      }
      returnSnoozedAction = true
      return route.fulfill({ status: 201, json: { ...SNOOZED_ACTION, id: 'action-server-snoozed' } })
    }

    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if (path.endsWith('/weekly-report')) return route.fulfill({ json: { items: [] } })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })

  return { getPostBody: () => capturedPostBody }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P57 — Snooze Server Persistence', () => {
  test('POSTs a new action with status=snoozed when "稍後提醒" clicked on recommendation', async ({ page }) => {
    await setAuthStorage(page)
    const { getPostBody } = await stubRoutesWithPostCapture(page)

    await page.goto('/platform/actions')
    await expect(page.getByText('每日步行目標').first()).toBeVisible({ timeout: 10000 })

    const responsePromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/actions') && resp.request().method() === 'POST',
      { timeout: 5000 }
    )
    await page.getByRole('button', { name: '稍後提醒' }).first().click()
    await responsePromise

    const body = getPostBody()
    expect(body).not.toBeNull()
    expect(body?.status).toBe('snoozed')
  })

  test('POST body for snooze includes snoozed_until', async ({ page }) => {
    await setAuthStorage(page)
    const { getPostBody } = await stubRoutesWithPostCapture(page)

    await page.goto('/platform/actions')
    await expect(page.getByText('每日步行目標').first()).toBeVisible({ timeout: 10000 })

    const responsePromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/actions') && resp.request().method() === 'POST',
      { timeout: 5000 }
    )
    await page.getByRole('button', { name: '稍後提醒' }).first().click()
    await responsePromise

    const body = getPostBody()
    expect(body?.snoozed_until).toBeTruthy()
    // snoozed_until must be a future ISO date
    const snoozedUntil = new Date(body?.snoozed_until as string).getTime()
    expect(snoozedUntil).toBeGreaterThan(Date.now())
  })

  test('snoozed recommendation stays hidden after page reload (localStorage)', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesWithPostCapture(page)

    await page.goto('/platform/actions')
    await expect(page.getByText('每日步行目標').first()).toBeVisible({ timeout: 10000 })

    const responsePromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/actions') && resp.request().method() === 'POST',
      { timeout: 5000 }
    )
    await page.getByRole('button', { name: '稍後提醒' }).first().click()
    await responsePromise

    // After snooze, rec card's snooze button should be gone (rec removed from recommendation layer)
    await expect(page.getByRole('button', { name: '稍後提醒' })).not.toBeVisible({ timeout: 3000 })

    // Reload and check rec is still hidden (localStorage persisted the snooze)
    await page.reload()
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: '稍後提醒' })).not.toBeVisible({ timeout: 5000 })
  })

  test('snoozed recommendation stays hidden after localStorage cleared (server sync)', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutesWithPostCapture(page)

    await page.goto('/platform/actions')
    await expect(page.getByText('每日步行目標').first()).toBeVisible({ timeout: 10000 })

    const responsePromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/actions') && resp.request().method() === 'POST',
      { timeout: 5000 }
    )
    await page.getByRole('button', { name: '稍後提醒' }).first().click()
    await responsePromise

    // Clear localStorage to simulate a fresh session (server state must take over)
    await page.evaluate(() => localStorage.removeItem('rec_feedback_person-self'))

    // Reload — the snoozed action from GET /actions syncs into recFeedback via useEffect
    await page.reload()
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: '稍後提醒' })).not.toBeVisible({ timeout: 5000 })
  })
})
