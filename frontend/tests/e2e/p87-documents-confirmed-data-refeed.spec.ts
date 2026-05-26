/**
 * P87 — Documents Confirmed-Data Re-feed Contract Smoke
 *
 * Verifies that after the drawer confirm action, confirmed_data (item counts)
 * is stored via PUT /confirm and surfaced inline in the document list row.
 *
 * Gap closed: P84 Gap G1 — confirmed_data from confirm was not re-fed into
 * LabReportItem display rows in /platform/documents.
 *
 * Fix summary:
 *  - ParsedItemsDrawer now calls PUT /confirm with confirmed_data payload
 *  - Doc interface extended with confirmed_data
 *  - List row renders `documents-confirmed-summary` when extracted_items present
 *
 * Strategy: fully mocked. No live backend. No auth required.
 */

import { expect, test } from '@playwright/test'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const DOC_ID = 'doc-p87-lab'

/** Document in 'parsed' state — awaiting confirm. */
const DOC_PARSED = {
  id: DOC_ID,
  original_filename: '2026_健檢_p87.pdf',
  parse_status: 'parsed',
  confirmed_at: null,
  uploaded_at: new Date().toISOString(),
  category: 'health_check',
  confirmed_data: null,
}

/** Same document after PUT /confirm — now carries extracted_items + abnormal_items. */
const DOC_CONFIRMED = {
  ...DOC_PARSED,
  parse_status: 'confirmed',
  confirmed_at: new Date().toISOString(),
  confirmed_data: {
    extracted_items: 5,
    abnormal_items: 2,
    reviewed_at: new Date().toISOString(),
    items: [],
  },
}

/** Document already confirmed with confirmed_data (pre-existing). */
const DOC_CONFIRMED_PREEXISTING = {
  id: 'doc-p87-preexist',
  original_filename: '2025_健檢_p87.pdf',
  parse_status: 'confirmed',
  confirmed_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
  uploaded_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
  category: 'health_check',
  confirmed_data: {
    extracted_items: 8,
    abnormal_items: 3,
    reviewed_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
    items: [],
  },
}

/** Two parsed items returned by GET /documents/{id}/parsed-items. */
const PARSED_ITEMS = [
  {
    id: 'item-p87-1',
    item_name: '血糖',
    value_num: 6.8,
    value_text: null,
    unit: 'mmol/L',
    ref_range: '3.9–6.1',
    abnormal_flag: 'H',
    parser_confidence: 0.95,
    is_abnormal: true,
  },
  {
    id: 'item-p87-2',
    item_name: '血紅素',
    value_num: 14.2,
    value_text: null,
    unit: 'g/dL',
    ref_range: '12–16',
    abnormal_flag: null,
    parser_confidence: 0.98,
    is_abnormal: false,
  },
]

// ── Route stub ────────────────────────────────────────────────────────────────

const LAYOUT_STUBS: Record<string, unknown> = {
  '/health-assistant/daily-summary': { topRisk: '', biggestChange: '', todayAction: '', generated_at: new Date().toISOString() },
  '/health-assistant/recommendations': { person_id: 'person-self', recommendations: [], total: 0 },
  '/health-assistant/notifications/intelligent': { person_id: 'person-self', items: [], suppressed: [], total_candidates: 0 },
  '/orchestrator/dashboard-summary': null,
  '/dashboard': { health_score: {}, alerts: [], insights: [], recommendations: [], trends: {}, medical_disclaimer: 'Not a medical diagnosis.', decision_items: [], prioritized_actions: [] },
  '/health-assistant/family-relationships': { relationships: [] },
  '/health-assistant/family-health-context': { context: null },
  '/health-assistant/family-recommendations': { recommendations: [] },
  '/health-assistant/narrative-memory/cross-period': { reasoning: null },
  '/insights': [],
  '/timeline': { items: [] },
  '/weekly-report': { items: [] },
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: {
    documents: object[]
    /** If provided, second GET /documents call returns this list (simulates post-confirm refresh). */
    documentsAfterConfirm?: object[]
  },
) {
  let confirmCalled = false

  await page.addInitScript(() => {
    localStorage.setItem('token', 'p87-mock-token')
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
        json: { id: 'person-self', display_name: 'Self', name: 'Self', age: 40, gender: 'male', onboarding_completed: true },
      })
    }

    // Documents list — stateful: second call after confirm returns updated list
    if ((path.endsWith('/documents') || path.includes('/documents?')) && method === 'GET') {
      if (confirmCalled && opts.documentsAfterConfirm) {
        return route.fulfill({ json: opts.documentsAfterConfirm })
      }
      return route.fulfill({ json: opts.documents })
    }

    // Parsed items for DOC_ID
    if (path.includes(`/documents/${DOC_ID}/parsed-items`) && method === 'GET') {
      return route.fulfill({ json: PARSED_ITEMS })
    }

    // PUT /documents/{id}/confirm — store items, return confirmed doc
    if (path.includes('/documents/') && path.endsWith('/confirm') && method === 'PUT') {
      confirmCalled = true
      return route.fulfill({ json: DOC_CONFIRMED })
    }

    // POST /documents/{id}/confirm — fallback (should not be called after P87 fix)
    if (path.includes('/documents/') && path.endsWith('/confirm') && method === 'POST') {
      confirmCalled = true
      return route.fulfill({ json: { ...DOC_CONFIRMED, confirmed_data: { reviewed: true } } })
    }

    // Lab history for the compare preview in drawer
    if (path.includes('/documents/lab-history')) return route.fulfill({ json: [] })

    // Layout stubs
    for (const [key, val] of Object.entries(LAYOUT_STUBS)) {
      if (path.includes(key)) return route.fulfill({ json: val })
    }
    if (path.includes('/actions/prioritized')) return route.fulfill({ json: [] })
    if ((path.endsWith('/actions') || path.includes('/actions?')) && method === 'GET') return route.fulfill({ json: [] })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
}

// ── Overclaim guard ───────────────────────────────────────────────────────────

const PROHIBITED_PHRASES = ['診斷', '確診', '治療', '一定', '絕對', '保證', '100%', 'diagnose', 'guarantee', 'cure']

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P87 — Documents Confirmed-Data Re-feed Contract', () => {
  /**
   * Contract test 1 — pre-existing confirmed_data summary renders in list row
   * When GET /documents returns a confirmed doc with extracted_items,
   * documents-confirmed-summary must be visible showing the item count.
   */
  test('contract: pre-confirmed doc with extracted_items shows summary in list row', async ({ page }) => {
    await stubRoutes(page, { documents: [DOC_CONFIRMED_PREEXISTING] })
    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-list-section"]', { timeout: 10_000 })

    // Confirmed badge present (scope to emerald badge span to avoid strict-mode collision)
    await expect(page.locator('.bg-emerald-100').filter({ hasText: '已確認' })).toBeVisible()

    // Summary row must show extracted_items count
    const summary = page.locator('[data-testid="documents-confirmed-summary"]')
    await expect(summary).toBeVisible()
    await expect(summary).toContainText('8 項指標')
    await expect(summary).toContainText('3 項異常')
  })

  /**
   * Contract test 2 — confirm action via drawer stores confirmed_data via PUT
   * and summary appears in the list row after drawer closes.
   *
   * Flow: open drawer → items load → click 確認並分析 → PUT /confirm called →
   *       onConfirmed triggers refresh → GET /documents returns confirmed_data →
   *       list row shows documents-confirmed-summary.
   */
  test('contract: confirm action stores confirmed_data; summary visible after drawer closes', async ({ page }) => {
    await stubRoutes(page, {
      documents: [DOC_PARSED],
      documentsAfterConfirm: [DOC_CONFIRMED],
    })
    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-list-section"]', { timeout: 10_000 })

    // Click 審閱解析結果 to open drawer
    await page.getByRole('button', { name: '審閱解析結果' }).click()

    // Drawer: wait for items to load (item names appear)
    await expect(page.getByText('血糖', { exact: false })).toBeVisible({ timeout: 8_000 })
    await expect(page.getByText('血紅素', { exact: false })).toBeVisible()

    // Click confirm button in drawer footer
    await page.getByRole('button', { name: '確認並分析' }).click()

    // Drawer must close (dialog role gone)
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 8_000 })

    // After drawer closes, list must show summary from confirmed_data
    const summary = page.locator('[data-testid="documents-confirmed-summary"]')
    await expect(summary).toBeVisible({ timeout: 8_000 })
    await expect(summary).toContainText('5 項指標')
    await expect(summary).toContainText('2 項異常')
  })

  /**
   * Contract test 3 — confirmed doc without extracted_items shows no summary
   * A doc with parse_status=confirmed but confirmed_data={reviewed:true} (old POST path)
   * must NOT render documents-confirmed-summary (avoid empty/broken display).
   */
  test('contract: confirmed doc without extracted_items shows no summary element', async ({ page }) => {
    const OLD_CONFIRMED = {
      id: 'doc-p87-old',
      original_filename: '2024_健檢_p87.pdf',
      parse_status: 'confirmed',
      confirmed_at: new Date().toISOString(),
      uploaded_at: new Date().toISOString(),
      category: 'health_check',
      confirmed_data: { reviewed: true },
    }
    await stubRoutes(page, { documents: [OLD_CONFIRMED] })
    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-list-section"]', { timeout: 10_000 })

    // Already-confirmed badge is visible
    await expect(page.getByText('已確認', { exact: false })).toBeVisible()

    // Summary element must NOT appear when no extracted_items
    await expect(page.locator('[data-testid="documents-confirmed-summary"]')).not.toBeVisible()
  })

  /**
   * Contract test 4 — medical overclaim guard
   * Confirmed doc with summary must not contain prohibited clinical phrases.
   */
  test('contract: no medical overclaim phrases in confirmed doc summary view', async ({ page }) => {
    await stubRoutes(page, { documents: [DOC_CONFIRMED_PREEXISTING] })
    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-list-section"]', { timeout: 10_000 })

    const bodyText = await page.locator('body').innerText()
    for (const phrase of PROHIBITED_PHRASES) {
      expect(bodyText, `Prohibited phrase found: "${phrase}"`).not.toContain(phrase)
    }
  })
})
