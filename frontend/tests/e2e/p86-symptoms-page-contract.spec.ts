/**
 * P86 — Symptoms Page Contract Smoke
 *
 * High-level contract for /platform/symptoms (symptom input → timeline → recommendations path).
 * This is not a detailed behaviour spec — it is a regression gate that verifies:
 *   - the stable testid surface introduced in P86 remains intact
 *   - the page survives API failure without crash or medical overclaiming
 *   - core input, heatmap/insight, and list sections are always discoverable
 *
 * Contract gap closed: P84 Gap G5 — /platform/symptoms had zero testids.
 *
 * Strategy: fully mocked (no live backend, no auth required).
 */

import { expect, test } from '@playwright/test'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PERSONS = [
  { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
]

/** A recent symptom log entry. */
const SYMPTOM_RECENT = {
  id: 'sym-p86-recent',
  symptom: '頭痛',
  severity: 2,
  duration_category: 'today',
  notes: null,
  note: null,
  occurred_at: new Date().toISOString(),
}

/** An older chronic symptom log entry. */
const SYMPTOM_CHRONIC = {
  id: 'sym-p86-chronic',
  symptom: '疲勞',
  severity: 1,
  duration_category: 'chronic',
  notes: null,
  note: null,
  occurred_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
}

// ── Route stub ────────────────────────────────────────────────────────────────

type StubOptions = {
  symptoms?: object[]
  symptomsStatus?: number
  metricsStatus?: number
}

async function stubRoutes(
  page: import('@playwright/test').Page,
  opts: StubOptions = {},
) {
  const {
    symptoms = [],
    symptomsStatus = 200,
    metricsStatus = 200,
  } = opts

  await page.addInitScript(() => {
    localStorage.setItem('token', 'p86-mock-token')
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

    // Symptoms list — primary surface under test
    if ((path.endsWith('/symptoms') || path.includes('/symptoms?')) && method === 'GET') {
      if (symptomsStatus !== 200) {
        return route.fulfill({ status: symptomsStatus, json: { detail: 'Simulated error' } })
      }
      return route.fulfill({ json: symptoms })
    }

    // Metrics — secondary surface (drives heatmap abnormal indicators)
    if ((path.endsWith('/metrics') || path.includes('/metrics?')) && method === 'GET') {
      if (metricsStatus !== 200) {
        return route.fulfill({ status: metricsStatus, json: { detail: 'Simulated error' } })
      }
      return route.fulfill({ json: [] })
    }

    // Stub layout/shell paths
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
        json: {
          health_score: {},
          alerts: [],
          insights: [],
          recommendations: [],
          trends: {},
          medical_disclaimer: 'Not a medical diagnosis.',
          decision_items: [],
          prioritized_actions: [],
        },
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
    if ((path.endsWith('/documents') || path.includes('/documents?')) && method === 'GET') return route.fulfill({ json: [] })
    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })
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

test.describe('P86 — Symptoms Page Contract', () => {
  /**
   * Contract test 1 — page renders safely with no symptoms
   * symptoms-page testid must be visible, no ErrorBoundary fallback.
   */
  test('contract: page renders — symptoms-page visible, no ErrorBoundary fallback', async ({ page }) => {
    await stubRoutes(page, { symptoms: [] })
    await page.goto('/platform/symptoms')
    await page.waitForSelector('[data-testid="symptoms-page"]', { timeout: 10_000 })

    await expect(page.locator('[data-testid="symptoms-page"]')).toBeVisible()
    await expect(page.getByText('Something went wrong')).not.toBeVisible()
  })

  /**
   * Contract test 2 — input section is always discoverable
   * symptoms-input-section must be present and contain quick-entry copy and
   * the save button regardless of symptom history.
   */
  test('contract: input section discoverable — symptoms-input-section visible with entry copy', async ({ page }) => {
    await stubRoutes(page, { symptoms: [] })
    await page.goto('/platform/symptoms')
    await page.waitForSelector('[data-testid="symptoms-page"]', { timeout: 10_000 })

    const inputSection = page.locator('[data-testid="symptoms-input-section"]')
    await expect(inputSection).toBeVisible()

    // Heading and save button
    await expect(inputSection.getByRole('heading', { name: '快速症狀記錄' })).toBeVisible()
    await expect(inputSection.getByRole('button', { name: '儲存症狀' })).toBeVisible()

    // At least one quick-symptom chip
    await expect(inputSection.getByRole('button', { name: '頭痛' })).toBeVisible()
  })

  /**
   * Contract test 3 — insight/heatmap section discoverable, list shows symptoms
   * symptoms-insight-section (heatmap) and symptoms-list-section (recent logs)
   * must both be visible. When symptoms are present, they appear in the list.
   */
  test('contract: heatmap and list sections visible — symptom entries appear in list', async ({ page }) => {
    await stubRoutes(page, { symptoms: [SYMPTOM_RECENT, SYMPTOM_CHRONIC] })
    await page.goto('/platform/symptoms')
    await page.waitForSelector('[data-testid="symptoms-page"]', { timeout: 10_000 })

    // Heatmap/insight section
    await expect(page.locator('[data-testid="symptoms-insight-section"]')).toBeVisible()
    await expect(
      page.locator('[data-testid="symptoms-insight-section"]').getByText('症狀熱度日曆', { exact: false }),
    ).toBeVisible()

    // List section
    await expect(page.locator('[data-testid="symptoms-list-section"]')).toBeVisible()

    // Symptom names must appear in the list
    await expect(page.locator('[data-testid="symptoms-list-section"]').getByText('頭痛', { exact: false })).toBeVisible()
    await expect(page.locator('[data-testid="symptoms-list-section"]').getByText('疲勞', { exact: false })).toBeVisible()
  })

  /**
   * Contract test 4 — API failure safe + medical overclaim guard
   * When GET /symptoms returns 500, page must survive without crash.
   * Input section must remain accessible. No prohibited phrases.
   */
  test('contract: api failure safe — page survives symptoms 500, no medical overclaim', async ({ page }) => {
    await stubRoutes(page, { symptomsStatus: 500 })
    await page.goto('/platform/symptoms')
    await page.waitForSelector('[data-testid="symptoms-page"]', { timeout: 10_000 })

    await expect(page.locator('[data-testid="symptoms-page"]')).toBeVisible()

    // Input section must still be accessible even when history load fails
    await expect(page.locator('[data-testid="symptoms-input-section"]')).toBeVisible()

    // No ErrorBoundary fallback
    await expect(page.getByText('Something went wrong')).not.toBeVisible()

    // Overclaim guard
    const bodyText = await page.locator('body').innerText()
    for (const phrase of PROHIBITED_PHRASES) {
      expect(bodyText.toLowerCase()).not.toContain(phrase.toLowerCase())
    }
  })

  /**
   * Contract test 5 — datetime-local control and submission
   */
  test('contract: datetime-local control default value and submission', async ({ page }) => {
    let lastRequestBody: any = null
    await stubRoutes(page, { symptoms: [] })

    // Override the POST symptom endpoint to intercept data
    await page.route('**/api/v1/symptoms*', async (route) => {
      const method = route.request().method()
      if (method === 'POST') {
        lastRequestBody = route.request().postDataJSON()
        return route.fulfill({
          status: 200,
          json: {
            id: 'new-sym',
            symptom: '頭痛',
            severity: 2,
            duration_category: 'today',
            notes: null,
            note: null,
            occurred_at: lastRequestBody?.occurred_at || new Date().toISOString()
          }
        })
      }
      if (method === 'GET') {
        return route.fulfill({ status: 200, json: [] })
      }
      return route.fallback()
    })

    await page.goto('/platform/symptoms')
    await page.waitForSelector('[data-testid="symptoms-page"]', { timeout: 10_000 })

    // 1. Labeled control is rendered
    const dateInput = page.getByLabel('症狀發生日期與時間')
    await expect(dateInput).toBeVisible()

    // 2. Default value is present and matches format (YYYY-MM-DDTHH:mm)
    const defaultValue = await dateInput.inputValue()
    expect(defaultValue).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/)

    // Check that it's close to current time (within 5 minutes to avoid clock drifts in CI)
    const [datePart, timePart] = defaultValue.split('T')
    const [year, month, day] = datePart.split('-').map(Number)
    const [hour, minute] = timePart.split(':').map(Number)
    const defaultDate = new Date(year, month - 1, day, hour, minute)
    expect(Math.abs(Date.now() - defaultDate.getTime())).toBeLessThan(5 * 60 * 1000)

    // 3. Select a past date/time (e.g. 2 hours ago)
    const pastDate = new Date(Date.now() - 2 * 60 * 60 * 1000)
    const pad = (n: number) => String(n).padStart(2, '0')
    const pastStr = `${pastDate.getFullYear()}-${pad(pastDate.getMonth() + 1)}-${pad(pastDate.getDate())}T${pad(pastDate.getHours())}:${pad(pastDate.getMinutes())}`
    await dateInput.fill(pastStr)

    // Select symptom '頭痛' and click save
    await page.getByRole('button', { name: '頭痛' }).click()
    const responsePromise = page.waitForResponse(response =>
      response.url().includes('/api/v1/symptoms') && response.request().method() === 'POST'
    )
    await page.getByRole('button', { name: '儲存症狀' }).click()
    await responsePromise

    // Verify submission contains occurred_at matching the local pastDate in ISO format
    expect(lastRequestBody).not.toBeNull()
    expect(lastRequestBody.symptom_names).toContain('頭痛')

    // Parse the submitted UTC timestamp and check it matches the selected local time
    const submittedDate = new Date(lastRequestBody.occurred_at)
    const selectMinutes = Math.floor(pastDate.getTime() / 60000)
    const submittedMinutes = Math.floor(submittedDate.getTime() / 60000)
    expect(submittedMinutes).toBe(selectMinutes)
  })

  /**
   * Contract test 6 — Future date validation
   */
  test('contract: future date is rejected with validation message', async ({ page }) => {
    await stubRoutes(page, { symptoms: [] })
    await page.goto('/platform/symptoms')
    await page.waitForSelector('[data-testid="symptoms-page"]', { timeout: 10_000 })

    const dateInput = page.getByLabel('症狀發生日期與時間')
    await expect(dateInput).toBeVisible()

    // Fill with a future date (1 day in the future)
    const futureDate = new Date(Date.now() + 24 * 60 * 60 * 1000)
    const pad = (n: number) => String(n).padStart(2, '0')
    const futureStr = `${futureDate.getFullYear()}-${pad(futureDate.getMonth() + 1)}-${pad(futureDate.getDate())}T${pad(futureDate.getHours())}:${pad(futureDate.getMinutes())}`
    await dateInput.fill(futureStr)

    // Attempt to submit
    await page.getByRole('button', { name: '頭痛' }).click()
    await page.getByRole('button', { name: '儲存症狀' }).click()

    // Assert that the error message is shown and has "不能選擇未來的時間"
    const errorMessage = page.locator('[data-testid="symptoms-error-message"]')
    await expect(errorMessage).toBeVisible()
    await expect(errorMessage).toContainText('不能選擇未來的時間')
  })
})
