/**
 * Minimal smoke tests — FamilyHealthCard evidence transparency (P10)
 *
 * NOTE: These tests require a running dev server (`npx next dev`).
 * Status in current sprint: NOT RUN (no live server in CI pipeline).
 * Written for future E2E validation when server is available.
 */
import { writeFileSync } from 'node:fs'
import { expect, test, type Page } from '@playwright/test'

const MOCK_RELATIONSHIPS = {
  relationships: [
    {
      id: 'rel-1',
      owner_user_id: 'user-1',
      subject_profile_id: 'pid-self',
      related_profile_id: 'pid-child',
      relationship_type: 'child',
      permission_level: 'manage',
      related_display_name: '小明',
    },
  ],
}

const MOCK_CONTEXT = {
  context: {
    relatedProfiles: [
      {
        profile_id: 'pid-child',
        display_name: '小明',
        relationship_type: 'child',
        permission_level: 'manage',
      },
    ],
    sharedRisks: ['血糖偏高'],
    caregiverAlerts: ['小明：血壓偏高'],
    childAttentionItems: ['小明：發燒'],
    familyActionSuggestions: ['每天散步30分鐘'],
    confidence: 0.65,
    limitations: ['相關成員健康資料仍在收集中。'],
  },
}

const MOCK_RECOMMENDATIONS = {
  recommendations: [
    {
      text: '小明：發燒',
      target_profile_id: null,
      audience: 'caregiver',
      urgency: 'high',
      evidence_source: 'child_attention_item',
      source_type: 'child_health',
    },
    {
      text: '家庭共同關注：血糖偏高',
      target_profile_id: null,
      audience: 'family',
      urgency: 'medium',
      evidence_source: 'shared_risk',
      source_type: 'shared_risk',
    },
    {
      text: '每天散步30分鐘',
      target_profile_id: null,
      audience: 'family',
      urgency: 'low',
      evidence_source: 'family_suggestion',
      source_type: 'action',
    },
  ],
}

const MOCK_EMPTY_FAMILY = {
  relationships: [],
}

const MOCK_EMPTY_CONTEXT = {
  context: {
    relatedProfiles: [],
    sharedRisks: [],
    caregiverAlerts: [],
    childAttentionItems: [],
    familyActionSuggestions: [],
    confidence: 0.65,
    limitations: [],
  },
}

const MOCK_EMPTY_RECOMMENDATIONS = {
  recommendations: [],
}

const MOCK_REFRESH_RELATIONSHIPS = {
  relationships: [
    {
      id: 'rel-2',
      owner_user_id: 'user-1',
      subject_profile_id: 'pid-self',
      related_profile_id: 'pid-new-child',
      relationship_type: 'child',
      permission_level: 'manage',
      related_display_name: '小華',
    },
  ],
}

const MOCK_REFRESH_CONTEXT = {
  context: {
    relatedProfiles: [
      {
        profile_id: 'pid-new-child',
        display_name: '小華',
        relationship_type: 'child',
        permission_level: 'manage',
      },
    ],
    sharedRisks: ['小華：共同關注資料'],
    caregiverAlerts: ['小華：照護資料已更新'],
    childAttentionItems: ['小華：注意事項已更新'],
    familyActionSuggestions: ['小華：每日散步'],
    confidence: 0.72,
    limitations: ['小華資料正持續收集中。'],
  },
}

const MOCK_REFRESH_RECOMMENDATIONS = {
  recommendations: [
    {
      text: '小華：檢視健康紀錄',
      target_profile_id: 'pid-new-child',
      audience: 'caregiver',
      urgency: 'low',
      evidence_source: 'child_attention_item',
      source_type: 'child_health',
    },
  ],
}

type BrowserDiagnostics = {
  pageErrors: string[]
  consoleErrors: string[]
  httpErrors: Array<{ status: number; url: string }>
}

const browserDiagnosticsByPage = new WeakMap<Page, BrowserDiagnostics>()

function createDeferred() {
  let release = () => {}
  const promise = new Promise<void>((resolve) => {
    release = resolve
  })
  return { promise, release }
}

async function reloadFamilyCard(page: Page) {
  const cardHeader = page.getByRole('heading', { name: '家庭健康總覽' }).locator('xpath=../..')
  await cardHeader.getByTitle('重新載入').click()
}

async function openFamilyRecommendations(page: import('@playwright/test').Page) {
  const toggle = page.getByRole('button', { name: /家庭健康建議/ })
  await expect(toggle).toBeVisible()
  await toggle.click()
}

test.describe('FamilyHealthCard — evidence transparency smoke', () => {
  test.beforeEach(async ({ page }) => {
    const diagnostics: BrowserDiagnostics = { pageErrors: [], consoleErrors: [], httpErrors: [] }
    browserDiagnosticsByPage.set(page, diagnostics)
    page.on('pageerror', error => diagnostics.pageErrors.push(error.message))
    page.on('console', message => {
      if (message.type() === 'error') diagnostics.consoleErrors.push(message.text())
    })
    page.on('response', response => {
      if (response.status() >= 400) diagnostics.httpErrors.push({ status: response.status(), url: response.url() })
    })

    await page.addInitScript(() => {
      localStorage.setItem('token', 'e2e-token')
      localStorage.setItem('person_id', 'pid-self')
      localStorage.setItem('onboarding_completed', '1')
    })

    await page.route('**/api/v1/**', async (route) => {
      const url = new URL(route.request().url())
      const path = url.pathname

      if (path.includes('/family-relationships')) {
        return route.fulfill({ json: MOCK_RELATIONSHIPS })
      }
      if (path.includes('/family-health-context')) {
        return route.fulfill({ json: MOCK_CONTEXT })
      }
      if (path.includes('/family-recommendations')) {
        return route.fulfill({ json: MOCK_RECOMMENDATIONS })
      }
      if (path.endsWith('/persons')) {
        return route.fulfill({
          json: [{ id: 'pid-self', display_name: '本人', relationship: 'self', is_default: true }],
        })
      }
      if (path.endsWith('/profile/me')) {
        return route.fulfill({
          json: { id: 'pid-self', display_name: '本人', onboarding_completed: true },
        })
      }
      if (path.endsWith('/metrics')) {
        return route.fulfill({ json: [] })
      }
      if (route.request().method() === 'GET') return route.fulfill({ json: { items: [] } })
      return route.fulfill({ json: {} })
    })
  })

  test.afterEach(async ({ page }, testInfo) => {
    const diagnostics = browserDiagnosticsByPage.get(page)
    if (!diagnostics) return
    const diagnosticsPath = testInfo.outputPath('browser-diagnostics.json')
    writeFileSync(diagnosticsPath, JSON.stringify(diagnostics, null, 2))
    await testInfo.attach('browser-diagnostics.json', {
      path: diagnosticsPath,
      contentType: 'application/json',
    })
  })

  test('family health card section is visible on dashboard', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText('家庭健康總覽')).toBeVisible()
  })

  test('no-diagnosis disclaimer is visible', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText('非醫療診斷')).toBeVisible()
  })

  test('source badge labels visible (child_health → 兒童健康)', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await openFamilyRecommendations(page)
    await expect(page.getByText('兒童健康').first()).toBeVisible()
  })

  test('source badge labels visible (action → 行動建議)', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await openFamilyRecommendations(page)
    await expect(page.getByText('行動建議').first()).toBeVisible()
  })

  test('audience badge visible (caregiver → 照護者)', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await openFamilyRecommendations(page)
    await expect(page.getByText('照護者').first()).toBeVisible()
  })

  test('source origin label visible on sections', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText('健康觀察資料').first()).toBeVisible()
  })

  test('family API 503 shows the safe fallback without stale family data', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText('小明').first()).toBeVisible()

    await page.route('**/family-health-context**', route => route.fulfill({
      status: 503,
      json: { detail: 'fixture unavailable' },
    }))
    await reloadFamilyCard(page)

    await expect(page.getByText('無法載入家庭健康資料')).toBeVisible()
    await expect(page.getByText('小明')).toHaveCount(0)
    await expect(page.getByText('血糖偏高')).toHaveCount(0)
    await expect(page.getByText('可信度 65%')).toHaveCount(0)
    expect(browserDiagnosticsByPage.get(page)?.pageErrors).toEqual([])
  })

  test('empty family responses render the empty state without health conclusions', async ({ page }) => {
    await page.route('**/family-relationships**', route => route.fulfill({ json: MOCK_EMPTY_FAMILY }))
    await page.route('**/family-health-context**', route => route.fulfill({ json: MOCK_EMPTY_CONTEXT }))
    await page.route('**/family-recommendations**', route => route.fulfill({ json: MOCK_EMPTY_RECOMMENDATIONS }))
    await page.goto('/platform/dashboard')

    await expect(page.getByText('尚未設定家庭成員')).toBeVisible()
    await expect(page.getByText('新增家庭成員後即可查看家庭健康概覽')).toBeVisible()
    await expect(page.getByText('小明')).toHaveCount(0)
    await expect(page.getByText('血糖偏高')).toHaveCount(0)
    await expect(page.getByText('可信度 65%')).toHaveCount(0)
    await expect(page.getByText('非醫療診斷')).toHaveCount(0)
    expect(browserDiagnosticsByPage.get(page)?.pageErrors).toEqual([])
  })

  test('delayed family response keeps prior family content hidden while loading', async ({ page }) => {
    const gate = createDeferred()
    let contextRequestIntercepted = false
    await page.route('**/family-health-context**', async route => {
      contextRequestIntercepted = true
      await gate.promise
      await route.fulfill({ json: MOCK_CONTEXT })
    })

    await page.goto('/platform/dashboard')
    try {
      await expect.poll(() => contextRequestIntercepted).toBe(true)
      await expect(page.getByText('載入中…')).toBeVisible()
      await expect(page.getByText('小明')).toHaveCount(0)
      await expect(page.getByText('血糖偏高')).toHaveCount(0)
    } finally {
      gate.release()
    }

    await expect(page.getByText('小明').first()).toBeVisible()
    expect(browserDiagnosticsByPage.get(page)?.pageErrors).toEqual([])
  })

  test('delayed refresh transitions from the prior family result to the new result', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText('小明').first()).toBeVisible()

    const gate = createDeferred()
    let interceptedResponses = 0
    const delayWith = (response: Record<string, unknown>) => async (route: import('@playwright/test').Route) => {
      interceptedResponses += 1
      await gate.promise
      await route.fulfill({ json: response })
    }

    await page.route('**/family-relationships**', delayWith(MOCK_REFRESH_RELATIONSHIPS))
    await page.route('**/family-health-context**', delayWith(MOCK_REFRESH_CONTEXT))
    await page.route('**/family-recommendations**', delayWith(MOCK_REFRESH_RECOMMENDATIONS))
    await reloadFamilyCard(page)

    try {
      await expect.poll(() => interceptedResponses).toBe(3)
      await expect(page.getByText('載入中…')).toBeVisible()
      await expect(page.getByText('小明')).toHaveCount(0)
      await expect(page.getByText('小華')).toHaveCount(0)
      await expect(page.getByText('可信度 65%')).toHaveCount(0)
    } finally {
      gate.release()
    }

    await expect(page.getByText('小華：注意事項已更新')).toBeVisible()
    await expect(page.getByText('可信度 72%')).toBeVisible()
    await openFamilyRecommendations(page)
    await expect(page.getByText('小華：檢視健康紀錄')).toBeVisible()
    await expect(page.getByText('小明')).toHaveCount(0)
    expect(browserDiagnosticsByPage.get(page)?.pageErrors).toEqual([])
  })
})
