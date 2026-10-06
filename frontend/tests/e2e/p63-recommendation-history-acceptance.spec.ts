/**
 * P63 — Recommendation History Card Product Acceptance
 *
 * Validates product acceptance gaps not covered by P62:
 * 1. Placement: RecommendationHistoryCard renders BELOW the "行動效果回饵"
 *    Section 4 when both sections are present.
 * 2. Error state: card is absent (not rendered) when getOutcomeFeedback API
 *    returns a server error — no crash, no phantom card rendered.
 *
 * Strategy: fully mocked (no live backend, no auth required).
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
  explainability_summary: 'P63 mock',
  medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [],
  prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P63 test',
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

/** A completed action so Section 4 ("行動效果回饵") renders */
const DONE_ACTION = {
  id: 'action-p63-done',
  person_id: 'person-self',
  source_type: 'recommendation',
  source_id: 'rec_p63_done',
  title: 'P63 完成行動',
  description: 'P63 測試用已完成行動',
  action_type: 'lifestyle',
  priority: 'medium',
  status: 'done',
  frequency: 'daily',
  streak_count: 3,
  resurface_count: 0,
  confidence: 0.7,
  evidence_level: 'B',
  guideline_source: null,
  rule_id: null,
  category: 'health',
  created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
  completed_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  outcomes: [],
}

/** Minimal outcome feedback with one not_useful item */
const OUTCOME_FEEDBACK_ONE = {
  person_id: 'person-self',
  generated_at: new Date().toISOString(),
  window_days: 30,
  outcomes: [
    {
      action_id: 'action-p63-history',
      action_title: 'P63 歷史建議',
      status: 'not_useful',
      completed_at: null,
      expected_health_impact: null,
      outcome_status: 'not_useful',
      actual_metric_change: null,
      adherence_status: 'dismissed',
      evidence_sources: [],
      confidence: 0.0,
      explanation: 'P63 test explanation',
      next_check_in: null,
    },
  ],
  summary: {
    improved_count: 0,
    unchanged_count: 0,
    deteriorated_count: 0,
    insufficient_data_count: 0,
    tracking_count: 0,
    not_useful_count: 1,
    not_applicable_count: 0,
    snoozed_count: 0,
    total_count: 1,
  },
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function setAuthStorage(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'e2e-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: {
    outcomeFeedbackStatus?: number
    actions?: object[]
  } = {},
) {
  const actions = opts.actions ?? []
  const outcomeFeedbackStatus = opts.outcomeFeedbackStatus ?? 200

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
    if (path.includes('/health-assistant/outcome-feedback')) {
      if (outcomeFeedbackStatus !== 200) {
        return route.fulfill({
          status: outcomeFeedbackStatus,
          json: { detail: 'Simulated server error' },
        })
      }
      return route.fulfill({ json: OUTCOME_FEEDBACK_ONE })
    }
    if (path.includes('/health-assistant/recommendations')) {
      return route.fulfill({
        json: { person_id: 'person-self', recommendations: [], total: 0 },
      })
    }
    if (path.includes('/health-assistant/daily-summary')) {
      return route.fulfill({
        json: {
          topRisk: '',
          biggestChange: '',
          todayAction: '',
          generated_at: new Date().toISOString(),
        },
      })
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
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') {
      return route.fulfill({ json: actions })
    }
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if (path.endsWith('/weekly-report')) return route.fulfill({ json: { items: [] } })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P63 — RecommendationHistoryCard Product Acceptance', () => {
  test('placement: history card renders below feedback loop section', async ({ page }) => {
    await setAuthStorage(page)
    // Provide a completed action so Section 4 ("行動效果回饵") renders alongside Section 5
    await stubRoutes(page, { actions: [DONE_ACTION] })

    await page.goto('/platform/actions')

    // Both section headings must be visible
    await expect(page.getByText('行動效果回饵')).toBeVisible({ timeout: 12_000 })
    await expect(page.getByText('建議回饋紀錄')).toBeVisible({ timeout: 5_000 })

    // Verify DOM order: Section 5 (history) must come AFTER Section 4 (feedback loop)
    const order = await page.evaluate(() => {
      const headings = Array.from(document.querySelectorAll('h3'))
      const feedbackLoopIdx = headings.findIndex((h) =>
        (h.textContent ?? '').includes('行動效果回'),
      )
      const historyIdx = headings.findIndex((h) =>
        (h.textContent ?? '').includes('建議回饋紀錄'),
      )
      return { feedbackLoopIdx, historyIdx }
    })

    expect(order.feedbackLoopIdx).toBeGreaterThanOrEqual(0)
    expect(order.historyIdx).toBeGreaterThanOrEqual(0)
    expect(order.historyIdx).toBeGreaterThan(order.feedbackLoopIdx)
  })

  test('error state: card absent when outcome-feedback API returns 500', async ({ page }) => {
    await setAuthStorage(page)
    await stubRoutes(page, { outcomeFeedbackStatus: 500 })

    await page.goto('/platform/actions')
    // Wait for the page main content to render (loading state cleared) before asserting absence.
    // '執行中心' is the Actions page header — rendered as soon as getDashboard() resolves.
    await expect(page.getByText('執行中心')).toBeVisible({ timeout: 12_000 })

    // History card must NOT be present — getOutcomeFeedback error → historyData null → no render
    await expect(
      page.locator('[data-testid="recommendation-history-card"]'),
    ).not.toBeVisible({ timeout: 3_000 })
  })
})
