import { expect, test, type BrowserContext, type Page } from '@playwright/test'

const EVENTS_KEY = 'health_platform_analytics_events_v1'
const SESSION_KEY = 'health_platform_session_id_v1'
const FIXED_NOW = new Date('2026-07-13T09:00:00.000Z')

type SyntheticEvent = {
  id: string
  event_name: string
  user_id: string
  session_id: string
  timestamp: string
  page: string
}

const event = (id: string, eventName: string, visitor: number, timestamp: string, page: string): SyntheticEvent => ({
  id,
  event_name: eventName,
  user_id: `synthetic-visitor-${visitor}`,
  session_id: `synthetic-session-${visitor}`,
  timestamp,
  page,
})

const SYNTHETIC_EVENTS: SyntheticEvent[] = [
  event('evt_fixture_v1_open', 'user_open_app', 1, '2026-06-01T06:00:00.000Z', '/platform/dashboard'),
  event('evt_fixture_v1_dashboard', 'view_dashboard', 1, '2026-06-02T06:00:00.000Z', '/platform/dashboard'),
  event('evt_fixture_v1_insight', 'view_insights', 1, '2026-06-08T06:00:00.000Z', '/platform/insights'),
  event('evt_fixture_v1_action', 'create_action', 1, '2026-07-01T06:00:00.000Z', '/platform/actions'),
  event('evt_fixture_v1_checkin', 'checkin_action', 1, '2026-07-13T06:00:00.000Z', '/platform/actions'),
  event('evt_fixture_v1_complete', 'complete_action', 1, '2026-07-13T06:05:00.000Z', '/platform/actions'),
  event('evt_fixture_v2_open', 'user_open_app', 2, '2026-07-10T07:00:00.000Z', '/platform/dashboard'),
  event('evt_fixture_v2_dashboard', 'view_dashboard', 2, '2026-07-11T07:00:00.000Z', '/platform/dashboard'),
  event('evt_fixture_v2_insight', 'view_insights', 2, '2026-07-13T07:00:00.000Z', '/platform/insights'),
  event('evt_fixture_v2_action', 'create_action', 2, '2026-07-13T07:05:00.000Z', '/platform/actions'),
  event('evt_fixture_v3_open', 'user_open_app', 3, '2026-07-01T08:00:00.000Z', '/platform/dashboard'),
  event('evt_fixture_v3_dashboard', 'view_dashboard', 3, '2026-07-02T08:00:00.000Z', '/platform/dashboard'),
  event('evt_fixture_v3_insight', 'view_insights', 3, '2026-07-08T08:00:00.000Z', '/platform/insights'),
  event('evt_fixture_v3_recent', 'view_weekly_report', 3, '2026-07-13T08:00:00.000Z', '/platform/weekly-report'),
  event('evt_fixture_v4_open', 'user_open_app', 4, '2026-07-05T04:00:00.000Z', '/platform/dashboard'),
  event('evt_fixture_v4_dashboard', 'view_dashboard', 4, '2026-07-06T04:00:00.000Z', '/platform/dashboard'),
  event('evt_fixture_v4_return', 'view_notifications', 4, '2026-07-12T04:00:00.000Z', '/platform/notifications'),
  event('evt_fixture_v5_open', 'user_open_app', 5, '2026-06-20T05:00:00.000Z', '/platform/dashboard'),
  event('evt_fixture_v5_return_d1', 'view_weekly_report', 5, '2026-06-21T05:00:00.000Z', '/platform/weekly-report'),
  event('evt_fixture_v5_return_d7', 'view_weekly_report', 5, '2026-06-28T05:00:00.000Z', '/platform/weekly-report'),
]

test.use({ locale: 'en-US', timezoneId: 'UTC' })

async function seedAnalytics(context: BrowserContext, events: SyntheticEvent[] | null) {
  await context.addInitScript(({ eventsKey, sessionKey, events }) => {
    localStorage.removeItem(eventsKey)
    localStorage.removeItem(sessionKey)
    if (events) localStorage.setItem(eventsKey, JSON.stringify(events))
    localStorage.setItem(sessionKey, 'p211-synthetic-session')
    localStorage.setItem('onboarding_completed', '1')
    sessionStorage.setItem('analytics_opened', '1')
  }, { eventsKey: EVENTS_KEY, sessionKey: SESSION_KEY, events })
}

async function isolateLocalAnalytics(page: Page) {
  await page.route(/^http:\/\/(?:localhost|127\.0\.0\.1):8000\/api\/v1\/.*/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })
}

function observeBrowser(page: Page) {
  const consoleErrors: string[] = []
  const pageErrors: string[] = []
  const externalRequests: string[] = []

  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('request', (request) => {
    const hostname = new URL(request.url()).hostname
    if (hostname !== '127.0.0.1' && hostname !== 'localhost') externalRequests.push(request.url())
  })

  return { consoleErrors, pageErrors, externalRequests }
}

function analyticsCard(page: Page, label: string) {
  return page.getByText(label, { exact: true }).locator('..')
}

test.describe('P211 Analytics hydration stability', () => {
  test('populated local Analytics hydrates cleanly and renders the expected summary', async ({ context, page }) => {
    await seedAnalytics(context, SYNTHETIC_EVENTS)
    await page.clock.setFixedTime(FIXED_NOW)
    await isolateLocalAnalytics(page)
    const observed = observeBrowser(page)

    await page.goto('/platform/analytics')
    await expect(page.getByTestId('analytics-loading')).toHaveCount(0)

    await expect(analyticsCard(page, 'DAU')).toContainText('3')
    await expect(analyticsCard(page, 'WAU')).toContainText('4')
    await expect(analyticsCard(page, 'MAU')).toContainText('5')
    await expect(analyticsCard(page, '黏著度')).toContainText('60.0%')

    const retention = page.getByRole('heading', { name: 'Retention' }).locator('..')
    await expect(retention).toContainText('D1 100.0%')
    await expect(retention).toContainText('D7 100.0%')
    await expect(retention).toContainText('D30 100.0%')

    const topEvents = page.getByRole('heading', { name: 'Top Events' }).locator('..')
    await expect(topEvents.getByText('user_open_app').locator('..')).toContainText('5')
    await expect(topEvents.getByText('view_dashboard').locator('..')).toContainText('4')
    await expect(topEvents.getByText('view_insights').locator('..')).toContainText('3')

    const funnel = page.getByRole('heading', { name: 'Funnel' }).locator('..')
    for (const label of ['App Open', 'View Dashboard', 'View Insight', 'Create Action', 'Check-in Action', 'Complete Action']) {
      await expect(funnel.getByText(label, { exact: true })).toBeVisible()
    }
    await expect(funnel.locator('.recharts-bar-rectangle')).toHaveCount(6)

    const recentEvents = page.getByRole('heading', { name: 'Recent Events' }).locator('..')
    await expect(recentEvents).toContainText('view_weekly_report')
    await expect(recentEvents).toContainText('7/13/2026, 8:00:00 AM')
    await expect(recentEvents).toContainText('person: - · page: /platform/weekly-report')

    expect(observed.pageErrors).toEqual([])
    expect(observed.consoleErrors).toEqual([])
    expect(observed.externalRequests).toEqual([])
  })

  test('empty local Analytics has deterministic loading markup and a usable final empty state', async ({ context, page }) => {
    await seedAnalytics(context, null)
    await page.clock.setFixedTime(FIXED_NOW)
    await isolateLocalAnalytics(page)
    const observed = observeBrowser(page)

    const response = await page.goto('/platform/analytics')
    const serverHtml = await response!.text()
    expect(serverHtml).toContain('data-testid="analytics-loading"')
    expect(serverHtml).toContain('正在載入本地分析資料...')
    await expect(page.getByTestId('analytics-loading')).toHaveCount(0)

    await expect(analyticsCard(page, 'DAU')).toContainText('0')
    await expect(analyticsCard(page, 'WAU')).toContainText('0')
    await expect(analyticsCard(page, 'MAU')).toContainText('0')
    await expect(analyticsCard(page, '黏著度')).toContainText('0.0%')
    await expect(page.getByText('資料不足')).toHaveCount(3)
    await expect(page.getByText('No events yet.')).toHaveCount(2)

    const viewAnalyticsCount = await page.evaluate((key) => {
      const stored = JSON.parse(localStorage.getItem(key) || '[]') as Array<{ event_name: string }>
      return stored.filter((item) => item.event_name === 'view_analytics').length
    }, EVENTS_KEY)
    expect(viewAnalyticsCount).toBe(1)
    expect(observed.pageErrors).toEqual([])
    expect(observed.consoleErrors).toEqual([])
    expect(observed.externalRequests).toEqual([])
  })

  test('timezone rendering waits for hydration and records view_analytics exactly once', async ({ browser }) => {
    const context = await browser.newContext({ locale: 'zh-TW', timezoneId: 'Asia/Taipei' })
    await seedAnalytics(context, SYNTHETIC_EVENTS)
    const page = await context.newPage()

    try {
      await page.clock.setFixedTime(FIXED_NOW)
      await isolateLocalAnalytics(page)
      const observed = observeBrowser(page)

      const response = await page.goto('/platform/analytics')
      const serverHtml = await response!.text()
      expect(serverHtml.match(/data-testid="analytics-loading"/g)).toHaveLength(1)
      expect(serverHtml).not.toContain('2026/7/13 下午4:00:00')

      const recentEvents = page.getByRole('heading', { name: 'Recent Events' }).locator('..')
      await expect(recentEvents).toContainText('2026/7/13 下午4:00:00')
      await expect(page.getByText('DAU', { exact: true })).toHaveCount(1)

      await expect.poll(async () => page.evaluate((key) => {
        const stored = JSON.parse(localStorage.getItem(key) || '[]') as Array<{ event_name: string }>
        return stored.filter((item) => item.event_name === 'view_analytics').length
      }, EVENTS_KEY)).toBe(1)

      const topEvents = page.getByRole('heading', { name: 'Top Events' }).locator('..')
      await expect(topEvents.getByText('view_analytics', { exact: true })).toHaveCount(0)
      expect(observed.pageErrors).toEqual([])
      expect(observed.consoleErrors).toEqual([])
      expect(observed.externalRequests).toEqual([])
    } finally {
      await context.close()
    }
  })
})
