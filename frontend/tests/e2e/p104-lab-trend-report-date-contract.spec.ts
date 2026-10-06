/**
 * P104 — Lab Trend Report Date Contract Smoke
 *
 * Contract guard for the optional report_date input in ParsedItemsDrawer
 * confirm footer and its write-through to the PUT /documents/{id}/confirm
 * endpoint.
 *
 * Verifies:
 *   T1 — ParsedItemsDrawer confirm footer shows the report-date-input
 *   T2 — Date input value is sent in PUT confirm request body as report_date
 *   T3 — Empty date confirm still succeeds without crashing
 *   T4 — Lab trend table can display a user-set report date from lab-history
 *
 * Strategy: fully mocked (no live backend, no auth required).
 * Requires next build to be current before running.
 */

import { expect, test } from '@playwright/test'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const DOC_ID = 'doc-p104-parsed'

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const DOC_PARSED = {
  id: DOC_ID,
  original_filename: '2025_健檢_p104.pdf',
  parse_status: 'parsed',
  confirmed_at: null,
  uploaded_at: new Date().toISOString(),
  category: 'health_check',
  confirmed_data: null,
}

const DOC_CONFIRMED = {
  ...DOC_PARSED,
  parse_status: 'confirmed',
  confirmed_at: new Date().toISOString(),
  confirmed_data: {
    extracted_items: 2,
    abnormal_items: 0,
    reviewed_at: new Date().toISOString(),
    items: [],
  },
}

const PARSED_ITEMS = [
  {
    id: 'item-p104-1',
    item_name: 'ALT',
    value_num: 32.0,
    value_text: null,
    unit: 'U/L',
    ref_range: '7-40 U/L',
    abnormal_flag: null,
    parser_confidence: 0.97,
    is_abnormal: false,
  },
  {
    id: 'item-p104-2',
    item_name: 'Glucose',
    value_num: 88.0,
    value_text: null,
    unit: 'mg/dL',
    ref_range: '70-100 mg/dL',
    abnormal_flag: null,
    parser_confidence: 0.95,
    is_abnormal: false,
  },
]

const LAB_HISTORY_WITH_USER_DATE = [
  {
    metric: 'ALT',
    report_date: '2025-03-12',
    document_id: DOC_ID,
    document_name: '2025_健檢_p104.pdf',
    value: 32.0,
    unit: 'U/L',
    is_abnormal: false,
    reference_range: '7-40 U/L',
  },
]

// ── Layout stubs ──────────────────────────────────────────────────────────────

const LAYOUT_STUBS: Record<string, unknown> = {
  '/health-assistant/daily-summary': {
    topRisk: '',
    biggestChange: '',
    todayAction: '',
    generated_at: new Date().toISOString(),
  },
  '/health-assistant/recommendations': { person_id: 'person-self', recommendations: [], total: 0 },
  '/health-assistant/notifications/intelligent': {
    person_id: 'person-self',
    items: [],
    suppressed: [],
    total_candidates: 0,
  },
  '/orchestrator/dashboard-summary': null,
  '/dashboard': {
    health_score: {},
    alerts: [],
    insights: [],
    recommendations: [],
    trends: {},
    medical_disclaimer: 'Not a medical diagnosis.',
    decision_items: [],
    prioritized_actions: [],
  },
  '/health-assistant/family-relationships': { relationships: [] },
  '/health-assistant/family-health-context': { context: null },
  '/health-assistant/family-recommendations': { recommendations: [] },
  '/health-assistant/narrative-memory/cross-period': { reasoning: null },
  '/insights': [],
  '/timeline': { items: [] },
  '/weekly-report': { items: [] },
}

// ── Route stub ────────────────────────────────────────────────────────────────

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: {
    documents?: object[]
    documentsAfterConfirm?: object[]
    labHistory?: object[]
    captureConfirmBody?: (body: unknown) => void
  } = {},
) {
  const {
    documents = [DOC_PARSED],
    documentsAfterConfirm,
    labHistory = [],
    captureConfirmBody,
  } = opts

  let confirmCalled = false

  await page.addInitScript(() => {
    localStorage.setItem('token', 'p104-mock-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })

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

    // Documents list — stateful after confirm
    if ((path.endsWith('/documents') || path.includes('/documents?')) && method === 'GET') {
      if (confirmCalled && documentsAfterConfirm) {
        return route.fulfill({ json: documentsAfterConfirm })
      }
      return route.fulfill({ json: documents })
    }

    // Parsed items
    if (path.includes(`/documents/${DOC_ID}/parsed-items`) && method === 'GET') {
      return route.fulfill({ json: PARSED_ITEMS })
    }

    // PUT confirm — capture body if requested
    if (path.includes('/documents/') && path.endsWith('/confirm') && method === 'PUT') {
      confirmCalled = true
      if (captureConfirmBody) {
        try {
          captureConfirmBody(route.request().postDataJSON())
        } catch {
          captureConfirmBody(null)
        }
      }
      return route.fulfill({ json: DOC_CONFIRMED })
    }

    // Lab history
    if (path.includes('/documents/lab-history')) {
      return route.fulfill({ json: labHistory })
    }

    // Layout stubs
    for (const [key, val] of Object.entries(LAYOUT_STUBS)) {
      if (path.includes(key)) return route.fulfill({ json: val })
    }
    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET')
      return route.fulfill({ json: [] })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P104 — Lab Trend Report Date Contract', () => {
  /**
   * T1 — Drawer confirm footer shows report-date-input.
   * Open documents page with a parsed doc, open the drawer, assert the date
   * input is visible.
   */
  test('T1: ParsedItemsDrawer confirm footer shows report-date-input', async ({ page }) => {
    await stubRoutes(page, { documents: [DOC_PARSED] })
    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-list-section"]', { timeout: 10_000 })

    await page.getByRole('button', { name: '審閱解析結果' }).click()

    // Drawer open — wait for item row (cell match is exact, avoids 'health_check' false-positive)
    await expect(page.getByRole('cell', { name: 'ALT' })).toBeVisible({ timeout: 8_000 })

    // Date input must be present in the confirm footer
    const dateInput = page.getByTestId('report-date-input')
    await expect(dateInput).toBeVisible()
    await expect(dateInput).toHaveAttribute('type', 'date')
  })

  /**
   * T2 — Date input value is forwarded in PUT confirm body as report_date.
   * Set date to 2025-03-12, click confirm, intercept the PUT body and assert
   * report_date is "2025-03-12".
   */
  test('T2: date input value is sent in PUT confirm body as report_date', async ({ page }) => {
    let capturedBody: unknown = undefined

    await stubRoutes(page, {
      documents: [DOC_PARSED],
      documentsAfterConfirm: [DOC_CONFIRMED],
      captureConfirmBody: (body) => {
        capturedBody = body
      },
    })

    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-list-section"]', { timeout: 10_000 })

    await page.getByRole('button', { name: '審閱解析結果' }).click()
    await expect(page.getByRole('cell', { name: 'ALT' })).toBeVisible({ timeout: 8_000 })

    // Set the date
    await page.getByTestId('report-date-input').fill('2025-03-12')

    // Confirm
    await page.getByRole('button', { name: '確認並分析' }).click()
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 8_000 })

    // Verify captured body
    expect(capturedBody).toBeTruthy()
    const body = capturedBody as Record<string, unknown>
    expect(body['report_date']).toBe('2025-03-12')
  })

  /**
   * T3 — Empty date confirm still succeeds, page does not crash.
   * Leave the date input blank, click confirm, assert drawer closes normally
   * and report_date in body is null or absent.
   */
  test('T3: empty date confirm still succeeds — page does not crash', async ({ page }) => {
    let capturedBody: unknown = undefined

    await stubRoutes(page, {
      documents: [DOC_PARSED],
      documentsAfterConfirm: [DOC_CONFIRMED],
      captureConfirmBody: (body) => {
        capturedBody = body
      },
    })

    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-list-section"]', { timeout: 10_000 })

    await page.getByRole('button', { name: '審閱解析結果' }).click()
    await expect(page.getByRole('cell', { name: 'ALT' })).toBeVisible({ timeout: 8_000 })

    // Leave date blank, click confirm
    await page.getByRole('button', { name: '確認並分析' }).click()
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 8_000 })

    // report_date should be null or absent — must not be a non-empty string
    const body = capturedBody as Record<string, unknown>
    const reportDateValue = body?.['report_date']
    expect(
      reportDateValue === null || reportDateValue === undefined || reportDateValue === '',
      `Expected report_date to be null/undefined/'', got: ${JSON.stringify(reportDateValue)}`,
    ).toBe(true)
  })

  /**
   * T4 — Lab trend table can display a user-set report date from lab-history.
   * Mock /documents/lab-history with report_date "2025-03-12".
   * Navigate to the 歷史比較 tab and assert the date "2025-03-12" appears in the table.
   */
  test('T4: lab trend table can display user-set report date from lab-history', async ({ page }) => {
    await stubRoutes(page, {
      documents: [{ ...DOC_PARSED, parse_status: 'confirmed', confirmed_at: new Date().toISOString() }],
      labHistory: LAB_HISTORY_WITH_USER_DATE,
    })

    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10_000 })

    await page.getByRole('button', { name: '歷史比較' }).click()

    await expect(page.getByTestId('lab-comparison-table')).toBeVisible({ timeout: 8_000 })
    // Expand the ALT row to reveal per-entry detail (date is in the collapsed detail view)
    await page.getByRole('row', { name: /ALT/ }).getByRole('button').click()
    await expect(page.getByText('2025-03-12', { exact: false })).toBeVisible({ timeout: 5_000 })
  })
})
