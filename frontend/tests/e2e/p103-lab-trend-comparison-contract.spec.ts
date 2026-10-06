/**
 * P103 — Lab Trend Comparison Contract Smoke
 *
 * Contract guard for the /platform/documents "歷史比較" tab and LabComparisonTable.
 * Verifies:
 *   - comparison tab renders with mocked multi-document lab history
 *   - direction filter labels are neutral (數值下降 / 數值上升), not medically interpretive
 *   - empty state is safe
 *   - no prohibited overclaim phrases appear in the comparison surface
 *
 * Strategy: fully mocked (no live backend, no auth required).
 * Requires next build to be current before running.
 */

import { expect, test } from '@playwright/test'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const DOC_CONFIRMED = {
  id: 'doc-p103-confirmed',
  original_filename: '2026_健檢報告.pdf',
  parse_status: 'confirmed',
  confirmed_at: new Date().toISOString(),
  uploaded_at: new Date().toISOString(),
  category: 'health_check',
  confirmed_data: { extracted_items: 8, abnormal_items: 1 },
}

/** Two metrics, two data points each — sufficient for Δ% computation. */
const LAB_HISTORY_ROWS = [
  {
    metric: 'ALT',
    report_date: '2026-03-15',
    document_id: 'doc-p103-confirmed',
    document_name: '2026_健檢報告.pdf',
    value: 45.0,
    unit: 'U/L',
    is_abnormal: true,
    reference_range: '7-40 U/L',
  },
  {
    metric: 'ALT',
    report_date: '2025-03-10',
    document_id: 'doc-p103-prev',
    document_name: '2025_健檢報告.pdf',
    value: 38.0,
    unit: 'U/L',
    is_abnormal: false,
    reference_range: '7-40 U/L',
  },
  {
    metric: 'Glucose',
    report_date: '2026-03-15',
    document_id: 'doc-p103-confirmed',
    document_name: '2026_健檢報告.pdf',
    value: 95.0,
    unit: 'mg/dL',
    is_abnormal: false,
    reference_range: '70-100 mg/dL',
  },
  {
    metric: 'Glucose',
    report_date: '2025-03-10',
    document_id: 'doc-p103-prev',
    document_name: '2025_健檢報告.pdf',
    value: 100.0,
    unit: 'mg/dL',
    is_abnormal: false,
    reference_range: '70-100 mg/dL',
  },
]

// ── Route stub ────────────────────────────────────────────────────────────────

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: { labHistory?: object[]; labHistoryStatus?: number } = {},
) {
  const { labHistory = [], labHistoryStatus = 200 } = opts

  await page.addInitScript(() => {
    localStorage.setItem('token', 'p103-mock-token')
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

    if (path.includes('/documents/lab-history')) {
      if (labHistoryStatus !== 200) {
        return route.fulfill({ status: labHistoryStatus, json: { detail: 'Simulated error' } })
      }
      return route.fulfill({ json: labHistory })
    }

    if ((path.endsWith('/documents') || path.includes('/documents?')) && method === 'GET') {
      return route.fulfill({ json: [DOC_CONFIRMED] })
    }

    if (path.includes('/health-assistant/daily-summary')) {
      return route.fulfill({
        json: { topRisk: '', biggestChange: '', todayAction: '', generated_at: new Date().toISOString() },
      })
    }
    if (path.includes('/health-assistant/recommendations')) {
      return route.fulfill({ json: { person_id: 'person-self', recommendations: [], total: 0 } })
    }
    if (path.includes('/health-assistant/notifications/intelligent')) {
      return route.fulfill({
        json: { person_id: 'person-self', items: [], suppressed: [], total_candidates: 0 },
      })
    }
    if (path.includes('/orchestrator/dashboard-summary')) return route.fulfill({ json: null })
    if (path.endsWith('/dashboard')) {
      return route.fulfill({
        json: { health_score: {}, alerts: [], insights: [], recommendations: [], trends: {}, medical_disclaimer: 'Not a medical diagnosis.', decision_items: [], prioritized_actions: [] },
      })
    }
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

// ── Overclaim guard ───────────────────────────────────────────────────────────

const PROHIBITED_PHRASES = [
  '已治癒',
  '保證改善',
  '取代醫師',
  '診斷為',
  '治療成功',
  '惡化',
]

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P103 — Lab Trend Comparison Contract', () => {
  /**
   * T1 — "歷史比較" tab renders LabComparisonTable with mocked multi-document lab history.
   * Verifies the tab is discoverable and the comparison table renders with data.
   */
  test('T1: "歷史比較" tab renders LabComparisonTable with mocked multi-document lab history', async ({ page }) => {
    await stubRoutes(page, { labHistory: LAB_HISTORY_ROWS })
    await page.goto('/platform/documents')
    await expect(page.getByTestId('documents-page')).toBeVisible()

    await page.getByRole('button', { name: '歷史比較' }).click()

    await expect(page.getByTestId('lab-comparison-table')).toBeVisible()
    await expect(page.getByText('ALT')).toBeVisible()
  })

  /**
   * T2 — Direction filter labels are neutral.
   * "數值下降" and "數值上升" must be visible as filter buttons.
   * "已改善" and "未改善" must NOT appear — they imply medical outcome judgement.
   */
  test('T2: filter labels use neutral direction wording — 數值下降/數值上升 visible, 已改善/未改善 absent', async ({ page }) => {
    await stubRoutes(page, { labHistory: LAB_HISTORY_ROWS })
    await page.goto('/platform/documents')
    await page.getByRole('button', { name: '歷史比較' }).click()
    await expect(page.getByTestId('lab-comparison-table')).toBeVisible()

    await expect(page.getByRole('button', { name: '數值下降' })).toBeVisible()
    await expect(page.getByRole('button', { name: '數值上升' })).toBeVisible()

    await expect(page.getByRole('button', { name: '已改善' })).not.toBeVisible()
    await expect(page.getByRole('button', { name: '未改善' })).not.toBeVisible()
  })

  /**
   * T3 — Empty state is safe.
   * When lab history is empty the table renders with a safe empty message, no crash.
   */
  test('T3: empty lab history renders safe empty state — no crash, no fake data', async ({ page }) => {
    await stubRoutes(page, { labHistory: [] })
    await page.goto('/platform/documents')
    await page.getByRole('button', { name: '歷史比較' }).click()

    await expect(page.getByTestId('lab-comparison-table')).toBeVisible()
    await expect(page.getByText('尚無歷史資料')).toBeVisible()
  })

  /**
   * T4 — Overclaim guard.
   * No medically interpretive or promise-like phrases appear in the comparison surface.
   */
  test('T4: no prohibited overclaim phrases visible in comparison tab', async ({ page }) => {
    await stubRoutes(page, { labHistory: LAB_HISTORY_ROWS })
    await page.goto('/platform/documents')
    await page.getByRole('button', { name: '歷史比較' }).click()
    await expect(page.getByTestId('lab-comparison-table')).toBeVisible()

    const body = page.locator('body')
    for (const phrase of PROHIBITED_PHRASES) {
      await expect(body).not.toContainText(phrase)
    }
  })

  /**
   * T5 — Mixed-unit delta suppression.
   * When the same metric has different units across reports:
   * - delta cell shows "單位不同，暫不比較" (unit-mismatch-label)
   * - delta cell does NOT show ↑ or ↓ directional arrows
   * Raw values are still visible in latest/prev columns.
   */
  test('T5: mixed-unit rows suppress delta% and show 單位不同，暫不比較', async ({ page }) => {
    const MIXED_UNIT_ROWS = [
      {
        metric: 'Glucose',
        report_date: '2026-03-15',
        document_id: 'doc-p106-new',
        document_name: '2026_外國健檢.pdf',
        value: 100.0,
        unit: 'mg/dL',
        is_abnormal: false,
        reference_range: '70-100 mg/dL',
      },
      {
        metric: 'Glucose',
        report_date: '2025-03-10',
        document_id: 'doc-p106-prev',
        document_name: '2025_健檢報告.pdf',
        value: 5.5,
        unit: 'mmol/L',
        is_abnormal: false,
        reference_range: '3.9-5.5 mmol/L',
      },
    ]

    await stubRoutes(page, { labHistory: MIXED_UNIT_ROWS })
    await page.goto('/platform/documents')
    await page.getByRole('button', { name: '歷史比較' }).click()
    await expect(page.getByTestId('lab-comparison-table')).toBeVisible()

    // Mismatch label must be present
    await expect(page.getByTestId('unit-mismatch-label')).toBeVisible()
    await expect(page.getByTestId('unit-mismatch-label')).toContainText('單位不同')

    // Directional arrows must NOT appear anywhere in the table
    const table = page.getByTestId('lab-comparison-table')
    await expect(table).not.toContainText('↑')
    await expect(table).not.toContainText('↓')

    // Raw values must still be visible
    await expect(table).toContainText('100')
    await expect(table).toContainText('5.5')
  })

  /**
   * T6 — IU/L and U/L compare as alias (P108 unit alias normalization).
   * When latest unit is U/L and previous unit is IU/L (or vice versa):
   * - delta% is calculated and shown
   * - "單位不同，暫不比較" must NOT appear for that row
   */
  test('T6: IU/L and U/L compare as alias — delta calculated, no unit-mismatch label', async ({ page }) => {
    const IU_ALIAS_ROWS = [
      {
        metric: 'ALT',
        report_date: '2026-03-15',
        document_id: 'doc-p108-new',
        document_name: '2026_健檢報告.pdf',
        value: 30.0,
        unit: 'U/L',
        is_abnormal: false,
        reference_range: '7-40 U/L',
      },
      {
        metric: 'ALT',
        report_date: '2025-03-10',
        document_id: 'doc-p108-prev',
        document_name: '2025_健檢報告.pdf',
        value: 25.0,
        unit: 'IU/L',
        is_abnormal: false,
        reference_range: '7-40 IU/L',
      },
    ]

    await stubRoutes(page, { labHistory: IU_ALIAS_ROWS })
    await page.goto('/platform/documents')
    await page.getByRole('button', { name: '歷史比較' }).click()
    await expect(page.getByTestId('lab-comparison-table')).toBeVisible()

    // Unit-mismatch label must NOT appear (IU/L ≡ U/L after normalization)
    await expect(page.getByTestId('unit-mismatch-label')).not.toBeVisible()

    // Delta must be visible (30 vs 25 → +20%)
    const table = page.getByTestId('lab-comparison-table')
    await expect(table).toContainText('20.0%')
  })

  /**
   * T7 — Unicode μ and ASCII u compare as alias (P108 unit alias normalization).
   * When latest unit is umol/L and previous unit is μmol/L (or µmol/L):
   * - delta% is calculated and shown
   * - "單位不同，暫不比較" must NOT appear for that row
   */
  test('T7: Unicode mu and ASCII u compare as alias — delta calculated, no unit-mismatch label', async ({ page }) => {
    const MU_ALIAS_ROWS = [
      {
        metric: 'Bilirubin',
        report_date: '2026-03-15',
        document_id: 'doc-p108-mu-new',
        document_name: '2026_健檢報告.pdf',
        value: 18.0,
        unit: 'umol/L',
        is_abnormal: false,
        reference_range: '3-21 umol/L',
      },
      {
        metric: 'Bilirubin',
        report_date: '2025-03-10',
        document_id: 'doc-p108-mu-prev',
        document_name: '2025_健檢報告.pdf',
        value: 15.0,
        unit: 'μmol/L',
        is_abnormal: false,
        reference_range: '3-21 μmol/L',
      },
    ]

    await stubRoutes(page, { labHistory: MU_ALIAS_ROWS })
    await page.goto('/platform/documents')
    await page.getByRole('button', { name: '歷史比較' }).click()
    await expect(page.getByTestId('lab-comparison-table')).toBeVisible()

    // Unit-mismatch label must NOT appear (μmol/L ≡ umol/L after normalization)
    await expect(page.getByTestId('unit-mismatch-label')).not.toBeVisible()

    // Delta must be visible (18 vs 15 → +20%)
    const table = page.getByTestId('lab-comparison-table')
    await expect(table).toContainText('20.0%')
  })
})
