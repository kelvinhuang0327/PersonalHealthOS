/**
 * P101 — Report + Symptom → Recommendation Integration Contract
 *
 * Proves the PersonalHealthOS core product loop (P1 gap closure):
 *   1. Lab report evidence surfaces in Daily Assistant 3-grid topRiskRef with
 *      correct ?document_id= deep link.
 *   2. Symptom evidence surfaces in Daily Assistant 3-grid todayActionRef with
 *      /platform/symptoms link — no fake deep link created.
 *   3. Actions page lab recommendation evidence link includes ?document_id= when
 *      source has document_id.
 *   4. Documents page auto-opens matching drawer when navigated via ?document_id= deep link.
 *   5. Unknown document_id does not crash the documents page.
 *
 * Strategy: fully mocked (no live backend). Based on P97 mock infrastructure.
 *
 * Key testids exercised:
 *   p94-top-risk-ref-link      — topRiskRef evidence nav link (lab → ?document_id=)
 *   p94-today-action-ref-link  — todayActionRef evidence nav link (symptom → /platform/symptoms)
 *   p89-source-page-link       — Actions page recommendation source link
 *   documents-page             — documents page root
 *   documents-loading          — documents loading sentinel
 *   [role="dialog"]            — ParsedItemsDrawer
 */

import { expect, test } from '@playwright/test'

// ── Constants ─────────────────────────────────────────────────────────────────

const DOC_ID       = 'doc-uuid-p101-lab'
const LAB_ITEM_ID  = 'lab-item-uuid-p101'
const SYMPTOM_ID   = 'symptom-uuid-p101'

// ── Mock data ─────────────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-p101', display_name: 'P101 User', relationship: 'self', is_default: true },
]

/** Lab document that matches DOC_ID — used by documents page tests. */
const DOC_WITH_ID = {
  id: DOC_ID,
  original_filename: '2026_lab_report.pdf',
  parse_status: 'confirmed',
  confirmed_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  uploaded_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  category: 'health_check',
  confirmed_data: { extracted_items: 8, abnormal_items: 2 },
}

/**
 * Daily summary with BOTH source types:
 *   topRiskRef    → lab_report_item + document_id  (should produce ?document_id= href)
 *   todayActionRef → symptom, no document_id       (should produce /platform/symptoms href)
 *
 * This is the integration mock that proves both source types coexist correctly.
 */
const DAILY_SUMMARY_LAB_AND_SYMPTOM = {
  person_id: 'person-p101',
  generated_at: new Date().toISOString(),
  topRisk: '血糖偏高，建議追蹤',
  biggestChange: '空腹血糖近 3 個月上升趨勢',
  todayAction: '記錄頭痛症狀——近 14 天趨勢增加',
  whyNow: '健檢報告顯示空腹血糖 6.8 mmol/L（旗標 H）',
  confidence: 0.78,
  topRiskRef: {
    source_type: 'lab_report_item',
    source_id: LAB_ITEM_ID,
    document_id: DOC_ID,
    summary: '健檢報告（2026-01-15）：血糖 6.8，旗標 H',
  },
  todayActionRef: {
    source_type: 'symptom',
    source_id: SYMPTOM_ID,
    summary: '近 14 天頭痛紀錄增加',
  },
}

/** Lab recommendation for the Actions page (T3 + T5). */
const LAB_REC_WITH_DOC_ID = {
  title: '血糖異常需追蹤',
  why_now: '健檢報告顯示空腹血糖 6.8 mmol/L（旗標 H）',
  priority: 'high',
  source_type: 'lab_report_item',
  source_id: LAB_ITEM_ID,
  document_id: DOC_ID,
  evidence_summary: '健檢報告（2026-01-15）：空腹血糖 6.8 mmol/L，旗標 H',
  data_insufficiency_reason: null,
  next_action: '與醫師討論血糖異常並安排追蹤',
  expected_health_impact: '及早追蹤有助掌握健康趨勢',
  evidence_sources: [{ type: 'lab_report_item', id: LAB_ITEM_ID, summary: '空腹血糖 6.8 mmol/L' }],
  is_tracking: false,
  evidence_level: 'A',
  trust: null,
}

const BASE_DASHBOARD = {
  health_score: { overall_score: 72, components: {} },
  alerts: [], insights: [], recommendations: [], trends: {},
  explainability_summary: 'P101 mock', medical_disclaimer: 'Not a medical diagnosis.',
  decision_items: [], prioritized_actions: [],
  health_narrative_v2: {
    summary: 'P101 test', risks: [], trends: [], reasons: [], actions: [],
    delta_summary: 'no change', improvements: [], deteriorations: [],
    adherence: [], missed_risks: [],
  },
}

const OUTCOME_EMPTY = {
  person_id: 'person-p101',
  generated_at: new Date().toISOString(),
  window_days: 7,
  outcomes: [],
  summary: {
    improved_count: 0, unchanged_count: 0, deteriorated_count: 0,
    insufficient_data_count: 0, tracking_count: 0, not_useful_count: 0,
    not_applicable_count: 0, snoozed_count: 0, total_count: 0,
  },
}

// ── Route stubs ───────────────────────────────────────────────────────────────

/** Stub for /platform/dashboard — injects dailySummary into the daily-summary endpoint. */
async function stubDashboardRoutes(
  page: import('@playwright/test').Page,
  dailySummary: object,
) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'p101-mock-token')
    localStorage.setItem('person_id', 'person-p101')
    localStorage.setItem('onboarding_completed', '1')
  })
  await page.route('**/api/v1/**', (route) => {
    const url    = new URL(route.request().url())
    const path   = url.pathname
    const method = route.request().method()
    if (path.includes('/health-assistant/daily-summary'))             return route.fulfill({ json: dailySummary })
    if (path.endsWith('/persons'))                                    return route.fulfill({ json: PERSONS })
    if (path.endsWith('/profile/me'))                                 return route.fulfill({ json: { id: 'person-p101', display_name: 'P101 User', name: 'P101 User', age: 40, gender: 'male', onboarding_completed: true } })
    if (path.includes('/health-assistant/outcome-feedback'))          return route.fulfill({ json: OUTCOME_EMPTY })
    if (path.includes('/health-assistant/recommendations'))           return route.fulfill({ json: { person_id: 'person-p101', recommendations: [], total: 0, missing_data: [] } })
    if (path.includes('/health-assistant/notifications/intelligent')) return route.fulfill({ json: { person_id: 'person-p101', generated_at: new Date().toISOString(), items: [], suppressed: [], total_candidates: 0 } })
    if (path.includes('/orchestrator/dashboard-summary'))             return route.fulfill({ json: null })
    if (path.includes('/health-assistant/family-relationships'))      return route.fulfill({ json: { person_id: 'person-p101', relationships: [], total: 0 } })
    if (path.includes('/health-assistant/family-health-context'))     return route.fulfill({ json: { person_id: 'person-p101', context: null } })
    if (path.includes('/health-assistant/family-recommendations'))    return route.fulfill({ json: { person_id: 'person-p101', recommendations: [], total: 0 } })
    if (path.includes('/health-assistant/narrative-memory/cross-period')) return route.fulfill({ json: { person_id: 'person-p101', reasoning: null } })
    if (path.endsWith('/dashboard'))                                  return route.fulfill({ json: BASE_DASHBOARD })
    if (path.includes('/actions/prioritized'))                        return route.fulfill({ json: [] })
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') return route.fulfill({ json: [] })
    if (path.endsWith('/insights'))                                   return route.fulfill({ json: [] })
    if (path.endsWith('/risk-alerts'))                                return route.fulfill({ json: [] })
    if (path.includes('/risk-alerts/unread-count'))                   return route.fulfill({ json: { count: 0 } })
    if (path.endsWith('/timeline'))                                   return route.fulfill({ json: { items: [] } })
    if (method === 'GET')                                             return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

/** Stub for /platform/actions — injects recommendations list. */
async function stubActionsRoutes(
  page: import('@playwright/test').Page,
  recommendations: object[],
) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'p101-mock-token')
    localStorage.setItem('person_id', 'person-p101')
    localStorage.setItem('onboarding_completed', '1')
  })
  await page.route('**/api/v1/**', (route) => {
    const url    = new URL(route.request().url())
    const path   = url.pathname
    const method = route.request().method()
    if (path.endsWith('/persons'))                                    return route.fulfill({ json: PERSONS })
    if (path.endsWith('/profile/me'))                                 return route.fulfill({ json: { id: 'person-p101', display_name: 'P101 User', name: 'P101 User', age: 40, gender: 'male', onboarding_completed: true } })
    if (path.includes('/health-assistant/recommendations'))           return route.fulfill({ json: { person_id: 'person-p101', recommendations, total: recommendations.length } })
    if (path.includes('/health-assistant/daily-summary'))             return route.fulfill({ json: { topRisk: '', biggestChange: '', todayAction: '', generated_at: new Date().toISOString() } })
    if (path.includes('/health-assistant/outcome-feedback'))          return route.fulfill({ json: OUTCOME_EMPTY })
    if (path.includes('/health-assistant/notifications/intelligent')) return route.fulfill({ json: { person_id: 'person-p101', generated_at: new Date().toISOString(), items: [], suppressed: [], total_candidates: 0 } })
    if (path.includes('/orchestrator/dashboard-summary'))             return route.fulfill({ json: null })
    if (path.includes('/health-assistant/family-relationships'))      return route.fulfill({ json: { person_id: 'person-p101', relationships: [], total: 0 } })
    if (path.includes('/health-assistant/family-health-context'))     return route.fulfill({ json: { person_id: 'person-p101', context: null } })
    if (path.includes('/health-assistant/family-recommendations'))    return route.fulfill({ json: { person_id: 'person-p101', recommendations: [], total: 0 } })
    if (path.includes('/health-assistant/narrative-memory/cross-period')) return route.fulfill({ json: { person_id: 'person-p101', reasoning: null } })
    if (path.endsWith('/dashboard'))                                  return route.fulfill({ json: BASE_DASHBOARD })
    if (path.includes('/actions/prioritized'))                        return route.fulfill({ json: [] })
    if (path.includes('/actions/') && path.endsWith('/outcomes') && method === 'GET') return route.fulfill({ json: [] })
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') return route.fulfill({ json: [] })
    if (path.endsWith('/insights'))                                   return route.fulfill({ json: [] })
    if (path.endsWith('/timeline'))                                   return route.fulfill({ json: { items: [] } })
    if (method === 'GET')                                             return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

/** Stub for /platform/documents — injects documents list. */
async function stubDocsRoutes(
  page: import('@playwright/test').Page,
  documents: object[] = [DOC_WITH_ID],
) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'p101-mock-token')
    localStorage.setItem('person_id', 'person-p101')
    localStorage.setItem('onboarding_completed', '1')
  })
  await page.route('**/api/v1/**', async (route) => {
    const url    = new URL(route.request().url())
    const path   = url.pathname
    const method = route.request().method()
    if (path.endsWith('/persons'))                                    return route.fulfill({ json: PERSONS })
    if (path.endsWith('/profile/me'))                                 return route.fulfill({ json: { id: 'person-p101', display_name: 'P101 User', name: 'P101 User', age: 40, gender: 'male', onboarding_completed: true } })
    if ((path.endsWith('/documents') || path.includes('/documents?')) && method === 'GET') return route.fulfill({ json: documents })
    if (path.includes('/documents/') && path.includes('/parsed-items')) return route.fulfill({ json: [] })
    if (path.includes('/health-assistant/daily-summary'))             return route.fulfill({ json: { topRisk: '', biggestChange: '', todayAction: '', generated_at: new Date().toISOString() } })
    if (path.includes('/health-assistant/recommendations'))           return route.fulfill({ json: { person_id: 'person-p101', recommendations: [], total: 0 } })
    if (path.includes('/health-assistant/notifications/intelligent')) return route.fulfill({ json: { person_id: 'person-p101', items: [], suppressed: [], total_candidates: 0 } })
    if (path.includes('/orchestrator/dashboard-summary'))             return route.fulfill({ json: null })
    if (path.endsWith('/dashboard'))                                  return route.fulfill({ json: BASE_DASHBOARD })
    if (path.includes('/health-assistant/family-relationships'))      return route.fulfill({ json: { relationships: [] } })
    if (path.includes('/health-assistant/family-health-context'))     return route.fulfill({ json: { context: null } })
    if (path.includes('/health-assistant/family-recommendations'))    return route.fulfill({ json: { recommendations: [] } })
    if (path.includes('/health-assistant/narrative-memory/cross-period')) return route.fulfill({ json: { reasoning: null } })
    if (path.endsWith('/insights'))                                   return route.fulfill({ json: [] })
    if (path.endsWith('/timeline'))                                   return route.fulfill({ json: { items: [] } })
    if (path.endsWith('/weekly-report'))                              return route.fulfill({ json: { items: [] } })
    if (path.includes('/actions/prioritized'))                        return route.fulfill({ json: [] })
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') return route.fulfill({ json: [] })
    if (method === 'GET')                                             return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test('T1: Daily Assistant topRiskRef lab evidence link includes ?document_id= (not page-level only)', async ({ page }) => {
  await stubDashboardRoutes(page, DAILY_SUMMARY_LAB_AND_SYMPTOM)
  await page.goto('/platform/dashboard')
  await expect(page.locator('[data-testid="daily-assistant-entry"]').first()).toBeVisible({ timeout: 12000 })
  await expect(page.locator('[data-testid="daily-assistant-loading"]').first()).not.toBeVisible()

  const refLink = page.locator('[data-testid="p94-top-risk-ref-link"]').first()
  await expect(refLink).toBeVisible({ timeout: 8000 })

  const href = await refLink.getAttribute('href')
  expect(href).toContain('/platform/documents')
  expect(href).toContain(`document_id=${DOC_ID}`)
})

test('T2: Daily Assistant todayActionRef symptom evidence link is /platform/symptoms — no fake document_id deep link', async ({ page }) => {
  await stubDashboardRoutes(page, DAILY_SUMMARY_LAB_AND_SYMPTOM)
  await page.goto('/platform/dashboard')
  await expect(page.locator('[data-testid="daily-assistant-entry"]').first()).toBeVisible({ timeout: 12000 })
  await expect(page.locator('[data-testid="daily-assistant-loading"]').first()).not.toBeVisible()

  const refLink = page.locator('[data-testid="p94-today-action-ref-link"]').first()
  await expect(refLink).toBeVisible({ timeout: 8000 })

  const href = await refLink.getAttribute('href')
  expect(href).toBe('/platform/symptoms')
  expect(href).not.toContain('document_id')
})

test('T3: Actions page p89-source-page-link for lab recommendation includes ?document_id=', async ({ page }) => {
  await stubActionsRoutes(page, [LAB_REC_WITH_DOC_ID])
  await page.goto('/platform/actions')
  await page.waitForSelector('[data-testid="actions-page"]', { timeout: 10000 })

  const sourceLink = page.getByTestId('p89-source-page-link').first()
  await expect(sourceLink).toBeVisible({ timeout: 8000 })

  const href = await sourceLink.getAttribute('href')
  expect(href).toContain('/platform/documents')
  expect(href).toContain(`document_id=${DOC_ID}`)
})

test('T4: Documents page auto-opens drawer when ?document_id= matches a lab document', async ({ page }) => {
  await stubDocsRoutes(page, [DOC_WITH_ID])
  await page.goto(`/platform/documents?document_id=${DOC_ID}`)
  await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10000 })
  await page.waitForSelector('[data-testid="documents-loading"]', { state: 'detached', timeout: 8000 })

  const drawer = page.locator('[role="dialog"]')
  await expect(drawer).toBeVisible({ timeout: 5000 })
})

test('T5: Documents page does not crash when ?document_id= does not match any document', async ({ page }) => {
  await stubDocsRoutes(page, [DOC_WITH_ID])
  await page.goto('/platform/documents?document_id=unknown-p101-missing')
  await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10000 })
  await page.waitForSelector('[data-testid="documents-loading"]', { state: 'detached', timeout: 8000 })

  await expect(page.locator('[data-testid="documents-list-section"]').first()).toBeVisible()
  await expect(page.locator('[role="dialog"]')).not.toBeVisible()
})
