/**
 * P85 — Documents Page Contract Smoke
 *
 * High-level contract for /platform/documents (health report upload/parse path).
 * This is not a detailed behaviour spec — it is a regression gate that verifies:
 *   - the stable testid surface introduced in P85 remains intact
 *   - the page survives API failure without crash or medical overclaiming
 *   - core upload and list sections are always discoverable
 *
 * Contract gap closed: P84 Gap G4 — /platform/documents had zero testids.
 *
 * Strategy: fully mocked (no live backend, no auth required).
 * No next build required for this spec change (testid-only, no logic change).
 */

import { expect, test } from '@playwright/test'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

/** A single pending document (just uploaded, not yet parsed). */
const DOC_PENDING = {
  id: 'doc-p85-pending',
  original_filename: '2026_健檢報告.pdf',
  parse_status: 'pending',
  confirmed_at: null,
  uploaded_at: new Date().toISOString(),
  category: 'health_check',
}

/** A document that has been parsed and confirmed. */
const DOC_CONFIRMED = {
  id: 'doc-p85-confirmed',
  original_filename: '2025_健檢報告.pdf',
  parse_status: 'confirmed',
  confirmed_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
  uploaded_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
  category: 'health_check',
}

// ── Route stub ────────────────────────────────────────────────────────────────

type StubOptions = {
  documents?: object[]
  documentsStatus?: number
  freezeDocuments?: boolean
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: StubOptions = {},
) {
  const {
    documents = [],
    documentsStatus = 200,
    freezeDocuments = false,
  } = opts

  let documentsResolve: (() => void) | null = null

  await page.addInitScript(() => {
    localStorage.setItem('token', 'p85-mock-token')
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

    // Documents list — primary surface under test
    if ((path.endsWith('/documents') || path.includes('/documents?')) && method === 'GET') {
      if (documentsStatus !== 200) {
        return route.fulfill({ status: documentsStatus, json: { detail: 'Simulated error' } })
      }
      if (freezeDocuments && documentsResolve === null) {
        await new Promise<void>((resolve) => { documentsResolve = resolve })
      }
      return route.fulfill({ json: documents })
    }

    // Stub other health-assistant paths that might be triggered by layout
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
    if (path.endsWith('/dashboard')) return route.fulfill({ json: { health_score: {}, alerts: [], insights: [], recommendations: [], trends: {}, medical_disclaimer: 'Not a medical diagnosis.', decision_items: [], prioritized_actions: [] } })
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

  return {
    releaseDocuments: () => {
      if (documentsResolve) { documentsResolve(); documentsResolve = null }
    },
  }
}

// ── Overclaim guard ───────────────────────────────────────────────────────────

const PROHIBITED_PHRASES = [
  '診斷',
  '確診',
  '治療',
  '一定',
  '絕對',
  '保證',
  '100%',
  'diagnose',
  'guarantee',
  'cure',
]

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe('P85 — Documents Page Contract', () => {
  /**
   * Contract test 1 — page renders safely with no documents
   * documents-page testid must be visible, no ErrorBoundary fallback,
   * list section present.
   */
  test('contract: page renders — documents-page visible, no ErrorBoundary fallback', async ({ page }) => {
    await stubRoutes(page, { documents: [] })
    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10_000 })

    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()
    await expect(page.getByText('Something went wrong')).not.toBeVisible()

    // Loading skeleton must not persist after data resolves
    await expect(page.locator('[data-testid="documents-loading"]')).not.toBeVisible()
  })

  /**
   * Contract test 2 — upload section is always discoverable
   * documents-upload-section must be present and visible regardless of
   * document count. The upload form is the primary call-to-action.
   */
  test('contract: upload section discoverable — documents-upload-section visible with upload copy', async ({ page }) => {
    await stubRoutes(page, { documents: [] })
    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10_000 })

    await expect(page.locator('[data-testid="documents-upload-section"]')).toBeVisible()

    // Upload section must contain safe copy (role-scoped to avoid strict-mode multi-match)
    const uploadSection = page.locator('[data-testid="documents-upload-section"]')
    await expect(uploadSection.getByRole('heading', { name: '健檢報告' })).toBeVisible()
    await expect(uploadSection.getByText('上傳', { exact: false })).toBeVisible()
  })

  /**
   * Contract test 3 — list section shows existing documents
   * When GET /documents returns documents, documents-list-section must be
   * visible and render document filenames.
   */
  test('contract: list section shows uploaded documents — documents-list-section visible', async ({ page }) => {
    await stubRoutes(page, { documents: [DOC_PENDING, DOC_CONFIRMED] })
    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-list-section"]', { timeout: 10_000 })

    await expect(page.locator('[data-testid="documents-list-section"]')).toBeVisible()

    // Both document filenames must appear
    await expect(page.getByText('2026_健檢報告.pdf', { exact: false })).toBeVisible()
    await expect(page.getByText('2025_健檢報告.pdf', { exact: false })).toBeVisible()

    // Confirmed document should show 已確認 badge
    await expect(page.getByText('已確認', { exact: false })).toBeVisible()
  })

  /**
   * Contract test 4 — API failure safe + medical overclaim guard
   * When GET /documents returns 500, the page must survive without crash.
   * No prohibited medical overclaiming phrases must appear.
   */
  test('contract: api failure safe — page survives documents 500, no medical overclaim', async ({ page }) => {
    await stubRoutes(page, { documentsStatus: 500 })
    await page.goto('/platform/documents')
    await page.waitForSelector('[data-testid="documents-page"]', { timeout: 10_000 })

    // Page root must still be visible
    await expect(page.locator('[data-testid="documents-page"]')).toBeVisible()

    // Upload section must still be accessible (user can retry upload)
    await expect(page.locator('[data-testid="documents-upload-section"]')).toBeVisible()

    // No ErrorBoundary fallback
    await expect(page.getByText('Something went wrong')).not.toBeVisible()

    // Overclaim guard
    const bodyText = await page.locator('body').innerText()
    for (const phrase of PROHIBITED_PHRASES) {
      expect(bodyText.toLowerCase()).not.toContain(phrase.toLowerCase())
    }
  })
})
