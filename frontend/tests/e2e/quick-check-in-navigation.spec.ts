import { expect, test } from '@playwright/test'

const QUICK_CHECK_IN_PATH = '/platform/quick-check-in'

test('quick check-in route renders from both existing dashboard entries', async ({ page }) => {
  const quickCheckInRscStatuses: number[] = []

  page.on('response', (response) => {
    const url = new URL(response.url())
    if (url.pathname === QUICK_CHECK_IN_PATH && url.searchParams.has('_rsc')) {
      quickCheckInRscStatuses.push(response.status())
    }
  })

  await page.addInitScript(() => {
    localStorage.setItem('token', 'e2e-token')
    localStorage.setItem('person_id', 'person-self')
    localStorage.setItem('onboarding_completed', '1')
  })

  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()

    if (path.endsWith('/persons')) {
      return route.fulfill({
        json: [{ id: 'person-self', display_name: 'Test Person', relationship: 'self', is_default: true }],
      })
    }
    if (path.endsWith('/profile/me')) {
      return route.fulfill({
        json: { id: 'person-self', display_name: 'Test Person', name: 'Test Person', onboarding_completed: true },
      })
    }
    if (path.includes('/actions/prioritized') || path.endsWith('/actions')) {
      return route.fulfill({ json: [] })
    }
    if (path.endsWith('/dashboard')) {
      return route.fulfill({
        json: {
          health_score: { overall_score: 82, components: {} },
          risk_level: 'stable',
          alerts: [],
          insights: [],
          recommendations: [],
          trends: {},
          explainability_summary: '隔離測試資料',
        },
      })
    }
    if (path.endsWith('/health-assistant/recommendations')) {
      return route.fulfill({
        json: { recommendations: [], missing_data: ['健康指標（血壓、血糖、體重等）'] },
      })
    }
    if (path.endsWith('/health-assistant/daily-summary')) {
      return route.fulfill({ json: null })
    }
    if (path.endsWith('/health-assistant/outcome-feedback')) {
      return route.fulfill({ json: { outcomes: [] } })
    }
    if (path.includes('/family-relationships')) {
      return route.fulfill({ json: { relationships: [], total: 0 } })
    }
    if (path.includes('/family-health-context')) {
      return route.fulfill({
        json: {
          context: {
            relatedProfiles: [],
            sharedRisks: [],
            caregiverAlerts: [],
            childAttentionItems: [],
            familyActionSuggestions: [],
            confidence: 0,
            limitations: [],
          },
        },
      })
    }
    if (path.includes('/family-recommendations')) {
      return route.fulfill({ json: { recommendations: [], total: 0 } })
    }
    if (path.endsWith('/metrics') || path.endsWith('/symptoms') || path.endsWith('/documents')) {
      return route.fulfill({ json: [] })
    }

    if (method === 'GET') return route.fulfill({ json: [] })
    return route.fulfill({ json: {} })
  })

  const directResponse = await page.goto(QUICK_CHECK_IN_PATH)
  expect(directResponse?.status()).toBe(200)
  await expect(page.getByRole('heading', { name: '快速健康打卡' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '今天狀況怎麼樣？' })).toBeVisible()
  await expect(page.getByText('Test Person', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: /今天 OK/ }).click()
  await expect(page.getByText('已完成今日打卡')).toBeVisible()
  await expect.poll(() =>
    page.evaluate(() => JSON.parse(localStorage.getItem('quick_checkins_person-self') || '[]').length),
  ).toBe(1)

  const dashboardResponse = await page.goto('/platform/dashboard')
  expect(dashboardResponse?.status()).toBe(200)
  await expect(page.getByRole('heading', { name: '儀表板' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '今天狀況怎麼樣？' })).toBeVisible()

  const dailyEntry = page.getByTestId('daily-assistant-entry')
  const dailyCheckInLink = dailyEntry.getByRole('link', { name: '填入指標' }).last()
  await dailyCheckInLink.scrollIntoViewIfNeeded()
  await expect(dailyCheckInLink).toBeVisible()
  await expect(dailyCheckInLink).toHaveAttribute('href', QUICK_CHECK_IN_PATH)
  await dailyCheckInLink.click()
  await expect(page).toHaveURL(new RegExp(`${QUICK_CHECK_IN_PATH.replaceAll('/', '\\/')}$`))
  await expect(page.getByRole('heading', { name: '快速健康打卡' })).toBeVisible()

  await page.goto('/platform/dashboard')
  const healthAssistantLink = page.getByRole('link', { name: '填入健康指標' }).last()
  await healthAssistantLink.scrollIntoViewIfNeeded()
  await expect(healthAssistantLink).toBeVisible()
  await expect(healthAssistantLink).toHaveAttribute('href', QUICK_CHECK_IN_PATH)
  await healthAssistantLink.click()
  await expect(page).toHaveURL(new RegExp(`${QUICK_CHECK_IN_PATH.replaceAll('/', '\\/')}$`))
  await expect(page.getByRole('heading', { name: '今天狀況怎麼樣？' })).toBeVisible()

  await expect.poll(() => quickCheckInRscStatuses.length).toBeGreaterThan(0)
  expect(quickCheckInRscStatuses).toContain(200)
  expect(quickCheckInRscStatuses).not.toContain(404)
  console.log(JSON.stringify({
    direct_route_http_status: directResponse?.status(),
    dashboard_http_status: dashboardResponse?.status(),
    quick_check_in_rsc_statuses: quickCheckInRscStatuses,
  }))
})
