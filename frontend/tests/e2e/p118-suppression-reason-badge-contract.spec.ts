/**
 * P118 — Suppression Reason Badge Contract
 *
 * Verifies that the Documents parsed-items-drawer UI displays the correct badge/copy for abnormal_flag_reason = 'suppressed_unit_scale_mismatch'.
 *
 * - Lab item with abnormal_flag = null and abnormal_flag_reason = suppressed_unit_scale_mismatch displays the yellow badge/copy.
 * - Same-unit normal does not show the suppression badge.
 * - High/low abnormal flags remain visible as before.
 * - No misleading '正常' wording appears for suppressed_unit_scale_mismatch.
 *
 * Strategy: fully mocked. No live backend. No auth required.
 */

import { expect, test, Page, Route } from '@playwright/test'

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

const DOC_CONFIRMED = {
  id: 'doc-p118',
  original_filename: '2026_健檢_p118.pdf',
  parse_status: 'confirmed',
  confirmed_at: new Date().toISOString(),
  uploaded_at: new Date().toISOString(),
  category: 'health_check',
  confirmed_data: { extracted_items: 3, abnormal_items: 1 },
}

const PARSED_ITEMS = [
  {
    id: 'item-suppressed',
    item_name: '血糖',
    value_num: 5.5,
    value_text: null,
    unit: 'mg/dL',
    ref_range: '3.9–6.1',
    abnormal_flag: null,
    abnormal_flag_reason: 'suppressed_unit_scale_mismatch',
    parser_confidence: 0.95,
    is_abnormal: false,
  },
  {
    id: 'item-normal',
    item_name: '血紅素',
    value_num: 14.2,
    value_text: null,
    unit: 'g/dL',
    ref_range: '12–16',
    abnormal_flag: null,
    abnormal_flag_reason: null,
    parser_confidence: 0.98,
    is_abnormal: false,
  },
  {
    id: 'item-high',
    item_name: 'ALT',
    value_num: 55,
    value_text: null,
    unit: 'U/L',
    ref_range: '7-40',
    abnormal_flag: 'H',
    abnormal_flag_reason: null,
    parser_confidence: 0.99,
    is_abnormal: true,
  },
]

async function stubRoutes(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'p118-mock-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })

  await page.route('**/api/v1/**', async (route: Route) => {
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
    if ((path.endsWith('/documents') || path.includes('/documents?')) && method === 'GET') {
      return route.fulfill({ json: [DOC_CONFIRMED] })
    }
    if (path.endsWith(`/documents/${DOC_CONFIRMED.id}/parsed-items`)) {
      return route.fulfill({ json: PARSED_ITEMS })
    }
    return route.fulfill({ json: {} })
  })
}

test.describe('P118 — Suppression Reason Badge Contract', () => {
  test('suppression reason badge/copy logic', async ({ page }) => {
    await stubRoutes(page)
    await page.goto('/platform/documents')
    // Open the parsed items drawer for the confirmed doc
    // Find the row containing the target filename, then click its '審閱解析結果' button
    const docRow = page.locator('div.flex.items-center.gap-2.flex-wrap', { hasText: '2026_健檢_p118.pdf' }).first().locator('..').locator('..')
    await docRow.getByRole('button', { name: /審閱解析結果/ }).click()
    await page.getByRole('dialog').waitFor()

    // 1. Suppressed item: yellow badge, correct text
    const suppressedBadge = page.getByText('單位不同，暫不判斷異常')
    await expect(suppressedBadge).toBeVisible()
    await expect(suppressedBadge).toHaveClass(/bg-yellow-100/)
    // 2. No '正常' badge for suppressed item
    await expect(suppressedBadge).not.toHaveClass(/bg-emerald-100/)
    // 3. Normal item: green badge, correct text
    const normalBadges = page.locator('span', { hasText: '正常' })
    // Find the first visible normal badge (should correspond to the normal item)
    await expect(normalBadges.first()).toBeVisible()
    await expect(normalBadges.first()).toHaveClass(/bg-emerald-100/)
    // 4. High abnormal: red badge, correct text
    const highBadge = page.getByText('偏高')
    await expect(highBadge).toBeVisible()
    await expect(highBadge).toHaveClass(/bg-rose-100/)
    // 5. No misleading '正常' for suppressed
    const suppressedRows = await page.locator('tr', { hasText: '血糖' })
    const suppressedRowCount = await suppressedRows.count()
    for (let i = 0; i < suppressedRowCount; ++i) {
      const row = suppressedRows.nth(i)
      await expect(row.getByText('正常')).not.toBeVisible()
    }
  })
})
