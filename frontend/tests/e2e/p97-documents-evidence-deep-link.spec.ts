/**
 * P97 — Documents Evidence Deep Link Contract
 *
 * Verifies the source-specific deep-link path from evidence badges to the
 * documents page drawer:
 *
 *   1. /platform/documents?document_id=<id> auto-opens the matching drawer
 *   2. Unknown document_id -> page renders normally, no crash
 *   3. Actions page evidence link includes ?document_id= when ref has document_id
 *   4. Daily Assistant topRisk evidence link includes ?document_id= when ref has document_id
 *
 * Strategy: fully mocked (no live backend).
 */

import { expect, test } from '@playwright/test'

const PERSONS = [
  { id: 'person-p97', display_name: 'P97 User', relationship: 'self', is_default: true },
]

const DOC_TARGET_ID = 'doc-uuid-p97-target'

const DOC_WITH_ID = {
  id: DOC_TARGET_ID,
  original_filename: '2026_health_check.pdf',
  parse_status: 'confirmed',
  confirmed_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
  uploaded_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
  category: 'health_check',
  confirmed_data: { extracted_items: 12, abnormal_items: 2 },
}

const DOC_OTHER = {
  id: 'doc-uuid-p97-other',
  original_filename: '2025_health_check.pdf',
  parse_status: 'confirmed',
  confirmed_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
  uploaded_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
  category: 'health_check',
  confirmed_data: { extracted_items: 10, abnormal_items: 1 },
}

const DAILY_SUMMARY_WITH_DOC_REF = {
  person_id: 'person-p97',
  generated_at: new Date().toISOString(),
  topRisk: 'HbA1c elevated, needs follow-up',
  biggestChange: 'Blood sugar trend rising',
  todayAction: 'Discuss blood sugar anomaly with doctor',
  whyNow: 'Lab report shows blood sugar abnormality',
  confidence: 0.82,
  topRiskRef: {
    source_type: 'lab_report_item',
    source_id: 'lab-item-uuid-p97',
    document_id: DOC_TARGET_ID,
    summary: 'Lab report (2026-01-15): HbA1c 7.2% (H)',
  },
  todayActionRef: {
    source_type: 'lab_report_item',
    source_id: 'lab-item-uuid-p97',
    document_id: DOC_TARGET_ID,
    summary: 'Lab report (2026-01-15): HbA1c 7.2% (H)',
  },
}

const LAB_REC_WITH_DOC_ID = {
  title: 'Blood sugar abnormality needs follow-up',
  why_now: 'Lab report shows fasting glucose = 6.8 mmol/L (H)',
  priority: 'high',
  source_type: 'lab_report_item',
  source_id: 'lab-item-uuid-p97',
  document_id: DOC_TARGET_ID,
  evidence_summary: 'Lab report (2026-01-15): fasting glucose = 6.8 mmol/L, flag H',
  data_insufficiency_reason: null,
  next_action: 'Discuss blood sugar anomaly with doctor and schedule follow-up',
  expected_health_impact: 'Early follow-up helps track health trends',
  evidence_sources: [{ type: 'lab_report_item', id: 'lab-item-uuid-p97', summary: 'fasting glucose 6.8 mmol/L' }],
  is_tracking: false,
  evidence_level: 'A',
  trust: null,
}

const BASE_DASHBOARD = {
  health_score: { overall_score: 75, components: {} },
  alerts: [], insights: [], recommendations: [], trends: {},
  explainability_summary: 'P97 mock', medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [], prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P97 test', risks: [], trends: [], reasons: [], actions: [],
    delta_summary: 'no change', improvements: [], deteriorations: [],
    adherence: [], missed_risks: [],
  },
}

const OUTCOME_EMPTY = {
  person_id: 'person-p97',
  generated_at: new Date().toISOString(),
  window_days: 7,
  outcomes: [],
  summary: {
    improved_count: 0, unchanged_count: 0, deteriorated_count: 0,
    insufficient_data_count: 0, tracking_count: 0, not_useful_count: 0,
    not_applicable_count: 0, snoozed_count: 0, total_count: 0,
  },
}

async function stubDocsRoutes(page: import('@playwright/test').Page, documents: object[] = [DOC_WITH_ID, DOC_OTHER]) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'p97-mock-token')
    localStorage.setItem('person_id', 'person-p97')
    localStorage.setItem('onboarding_completed', '1')
  })
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    if (path.endsWith('/persons')) return route.fulfill({ json: PERSONS })
    if (path.endsWith('/profile/me')) return route.fulfill({ json: { id: 'person-p97', display_name: 'P97 User', name: 'P97 User', age: 42, gender: 'male', onboarding_completed: true } })
    if ((path.endsWith('/documents') || path.includes('/documents?')) && method === 'GET') return route.fulfill({ json: documents })
    if (path.includes('/documents/') && path.includes('/parsed-items')) return route.fulfill({ json: [] })
    if (path.includes('/health-assistant/daily-summary')) return route.fulfill({ json: { topRisk: '', biggestChange: '', todayAction: '', generated_at: new Date().toISOString() } })
    if (path.includes('/health-assistant/recommendations')) return route.fulfill({ json: { person_id: 'person-p97', recommendations: [], total: 0 } })
    if (path.includes('/health-assistant/notifications/intelligent')) return route.fulfill({ json: { person_id: 'person-p97', items: [], suppressed: [], total_candidates: 0 } })
    if (path.includes('/orchestrator/dashboard-summary')) return route.fulfill({ json: null })
    if (path.endsWith('/dashboard')) return route.fulfill({ json: BASE_DASHBOARD })
    if (path.includes('/health-assistant/family-relationships')) return route.fulfill({ json: { relationships: [] } })
    if (path.includes('/health-assistant/family-health-context')) return route.fulfill({ json: { context: null } })
    if (path.includes('/health-assistant/family-recommendations')) return route.fulfill({ json: { recommendations: [] } })
    if (path.includes('/health-assistant/narrative-memory/cross-period')) return route.fulfill({ json: { reasoning: null } })
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if (path.endsWith('/weekly-report')) return route.fulfill({ json: { items: [] } })
    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') return route.fulfill({ json: [] })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

async function stubActionsRoutes(page: import('@playwright/test').Page, recommendations: object[]) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'p97-mock-token')
    localStorage.setItem('person_id', 'person-p97')
    localStorage.setItem('onboarding_completed', '1')
  })
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    if (path.endsWith('/persons')) return route.fulfill({ json: PERSONS })
    if (path.endsWith('/profile/me')) return route.fulfill({ json: { id: 'person-p97', display_name: 'P97 User', name: 'P97 User', age: 42, gender: 'male', onboarding_completed: true } })
    if (path.includes('/health-assistant/recommendations')) return route.fulfill({ json: { person_id: 'person-p97', recommendations, total: recommendations.length } })
    if (path.includes('/health-assistant/daily-summary')) return route.fulfill({ json: { topRisk: '', biggestChange: '', todayAction: '', generated_at: new Date().toISOString() } })
    if (path.includes('/health-assistant/outcome-feedback')) return route.fulfill({ json: OUTCOME_EMPTY })
    if (path.includes('/health-assistant/notifications/intelligent')) return route.fulfill({ json: { person_id: 'person-p97', generated_at: new Date().toISOString(), items: [], suppressed: [], total_candidates: 0 } })
    if (path.includes('/orchestrator/dashboard-summary')) return route.fulfill({ json: null })
    if (path.includes('/health-assistant/family-relationships')) return route.fulfill({ json: { person_id: 'person-p97', relationships: [], total: 0 } })
    if (path.includes('/health-assistant/family-health-context')) return route.fulfill({ json: { person_id: 'person-p97', context: null } })
    if (path.includes('/health-assistant/family-recommendations')) return route.fulfill({ json: { person_id: 'person-p97', recommendations: [], total: 0 } })
    if (path.includes('/health-assistant/narrative-memory/cross-period')) return route.fulfill({ json: { person_id: 'person-p97', reasoning: null } })
    if (path.endsWith('/dashboard')) return route.fulfill({ json: BASE_DASHBOARD })
    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    if (path.includes('/actions/') && path.endsWith('/outcomes') && method === 'GET') return route.fulfill({ json: [] })
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') return route.fulfill({ json: [] })
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if (path.endsWith('/weekly-report')) return route.fulfill({ json: { items: [] } })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

async function stubDashboardRoutes(page: import('@playwright/test').Page, dailySummary: object) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'p97-mock-token')
    localStorage.setItem('person_id', 'person-p97')
    localStorage.setItem('onboarding_completed', '1')
  })
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    if (path.includes('/health-assistant/daily-summary')) return route.fulfill({ json: dailySummary })
    if (path.endsWith('/persons')) return route.fulfill({ json: PERSONS })
    if (path.endsWith('/profile/me')) return route.fulfill({ json: { id: 'person-p97', display_name: 'P97 User', name: 'P97 User', age: 42, gender: 'male', onboarding_completed: true } })
    if (path.includes('/health-assistant/outcome-feedback')) return route.fulfill({ json: OUTCOME_EMPTY })
    if (path.includes('/health-assistant/recommendations')) return route.fulfill({ json: { person_id: 'person-p97', recommendations: [], total: 0, missing_data: [] } })
    if (path.includes('/health-assistant/notifications/intelligent')) return route.fulfill({ json: { person_id: 'person-p97', generated_at: new Date().toISOString(), items: [], suppressed: [], total_candidates: 0 } })
    if (path.includes('/orchestrator/dashboard-summary')) return route.fulfill({ json: null })
    if (path.includes('/health-assistant/family-relationships')) return route.fulfill({ json: { person_id: 'person-p97', relationships: [], total: 0 } })
    if (path.includes('/health-assistant/family-health-context')) return route.fulfill({ json: { person_id: 'person-p97', context: null } })
    if (path.includes('/health-assistant/family-recommendations')) return route.fulfill({ json: { person_id: 'person-p97', recommendations: [], total: 0 } })
    if (path.includes('/health-assistant/narrative-memory/cross-period')) return route.fulfill({ json: { person_id: 'person-p97', reasoning: null } })
    if (path.endsWith('/dashboard')) return route.fulfill({ json: BASE_DASHBOARD })
    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') return route.fulfill({ json: [] })
    if (path.endsWith('/insights')) return route.fulfill({ json: [] })
    if (path.endsWith('/risk-alerts')) return route.fulfill({ json: [] })
    if (path.includes('/risk-alerts/unread-count')) return route.fulfill({ json: { count: 0 } })
    if (path.endsWith('/timeline')) return route.fulfill({ json: { items: [] } })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

test('documents page auto-opens drawer when document_id param matches a document', async ({ page }) => {
  await stubDocsRoutes(page)
  await page.goto(`/platform/documents?document_id=${DOC_TARGET_ID}`)
  await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10000 })
  await page.waitForSelector('[data-testid="documents-loading"]', { state: 'detached', timeout: 8000 })
  const drawer = page.locator('[role="dialog"]')
  await expect(drawer).toBeVisible({ timeout: 5000 })
})

test('documents page does not crash when document_id param does not match any document', async ({ page }) => {
  await stubDocsRoutes(page)
  await page.goto('/platform/documents?document_id=unknown-uuid-does-not-exist')
  await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10000 })
  await page.waitForSelector('[data-testid="documents-loading"]', { state: 'detached', timeout: 8000 })
  await expect(page.locator('[data-testid="documents-list-section"]').first()).toBeVisible()
  const drawer = page.locator('[role="dialog"]')
  await expect(drawer).not.toBeVisible()
})

test('Actions page lab evidence link includes ?document_id= when source has document_id', async ({ page }) => {
  await stubActionsRoutes(page, [LAB_REC_WITH_DOC_ID])
  await page.goto('/platform/actions')
  await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10000 })
  const sourceLink = page.getByTestId('p89-source-page-link').first()
  await expect(sourceLink).toBeVisible({ timeout: 8000 })
  const href = await sourceLink.getAttribute('href')
  expect(href).toContain('/platform/documents')
  expect(href).toContain(`document_id=${DOC_TARGET_ID}`)
})

test('Daily Assistant topRisk lab evidence link includes ?document_id= when ref has document_id', async ({ page }) => {
  await stubDashboardRoutes(page, DAILY_SUMMARY_WITH_DOC_REF)
  await page.goto('/platform/dashboard')
  await expect(page.locator('[data-testid="daily-assistant-entry"]').first()).toBeVisible({ timeout: 12000 })
  await expect(page.locator('[data-testid="daily-assistant-loading"]').first()).not.toBeVisible()
  const refLink = page.locator('[data-testid="p94-top-risk-ref-link"]').first()
  await expect(refLink).toBeVisible({ timeout: 8000 })
  const href = await refLink.getAttribute('href')
  expect(href).toContain('/platform/documents')
  expect(href).toContain(`document_id=${DOC_TARGET_ID}`)
})
