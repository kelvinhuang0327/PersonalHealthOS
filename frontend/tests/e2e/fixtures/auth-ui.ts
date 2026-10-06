/**
 * P15/P16 Real-JWT storageState Bootstrap Fixture.
 *
 * P15 introduced:
 *   - Real JWT via addInitScript (login form fill unreliable in production build)
 *   - CORS bridge: backend whitelist is :3000/:3100 but webServer runs on :3010
 *   - waitForFunction arg/options fix (3rd param, not 2nd)
 *
 * P16 adds:
 *   - installCORSBridge() exported for reuse on storageState-restored contexts
 *   - contextFromStorageState() creates a fresh context from a saved state file
 *     without needing addInitScript (localStorage already carries the JWT)
 *
 * Usage:
 *   // JWT bootstrap (first login)
 *   const page = await bootstrapWithRealJWT(context, token)
 *   await context.storageState({ path: '/tmp/userA-state.json' })
 *
 *   // StorageState roundtrip (subsequent contexts)
 *   const ctx2 = await contextFromStorageState(browser, '/tmp/userA-state.json')
 *   const page2 = await ctx2.newPage()
 *   await page2.goto('/platform/dashboard')  // JWT already in localStorage
 *
 * Requirements:
 *   - Next.js frontend server running at baseURL (http://127.0.0.1:3010)
 *   - A real JWT string obtained from the live backend
 */

import { Browser, BrowserContext, Page } from '@playwright/test'

const FRONTEND_ORIGIN = 'http://127.0.0.1:3010'
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': FRONTEND_ORIGIN,
  'Access-Control-Allow-Credentials': 'true',
  'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
  'Access-Control-Allow-Headers': 'Authorization,Content-Type,Accept',
}

/**
 * Installs the CORS bridge route handler on a BrowserContext.
 *
 * Must be called on EVERY context (including ones created from storageState)
 * because route handlers are not persisted in storageState files.
 *
 * The bridge forwards all requests to localhost:8000 unchanged and patches
 * Access-Control-Allow-Origin onto responses so Chromium accepts them.
 */
export async function installCORSBridge(context: BrowserContext): Promise<void> {
  await context.route('http://localhost:8000/**', async (route, request) => {
    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 200, headers: CORS_HEADERS }).catch(() => {})
      return
    }
    try {
      const response = await route.fetch()
      await route.fulfill({
        response,
        headers: { ...response.headers(), ...CORS_HEADERS },
      })
    } catch {
      // Context closed while request was in flight — abort silently so the
      // error does not propagate to the test runner and end the test early.
      await route.abort().catch(() => {})
    }
  })
}

/**
 * Creates a new BrowserContext pre-seeded from a saved storageState file.
 *
 * The storageState file must have been written by a previously bootstrapped
 * context (via context.storageState({ path })).  It carries localStorage
 * entries (token, person_id) so addInitScript is NOT needed for subsequent
 * navigations in this context.
 *
 * The CORS bridge is re-installed because route handlers are not stored in
 * storageState.
 *
 * @param browser   - Playwright Browser fixture
 * @param statePath - Absolute path to the stored storageState JSON file
 * @returns BrowserContext with storageState restored and CORS bridge active
 */
export async function contextFromStorageState(
  browser: Browser,
  statePath: string,
): Promise<BrowserContext> {
  const context = await browser.newContext({ storageState: statePath })
  await installCORSBridge(context)
  return context
}

/**
 * Bootstraps a browser context with a real JWT obtained from the live backend.
 *
 * Installs the CORS bridge, injects the JWT into localStorage via addInitScript,
 * navigates to /platform/dashboard, and waits for PersonProvider to populate
 * localStorage['person_id'].
 *
 * @param context  - a fresh BrowserContext (no prior storageState)
 * @param token    - real JWT access_token from POST /api/v1/auth/login
 * @param personId - optional person_id; if omitted PersonProvider auto-selects
 * @returns the Page instance on /platform/dashboard with localStorage populated
 */
export async function bootstrapWithRealJWT(
  context: BrowserContext,
  token: string,
  personId?: string,
): Promise<Page> {
  await installCORSBridge(context)

  const page = await context.newPage()

  // Inject real JWT before any page script runs so the app hydrates authenticated
  await page.addInitScript(
    ({ t, pid }: { t: string; pid?: string }) => {
      localStorage.setItem('token', t)
      if (pid) localStorage.setItem('person_id', pid)
    },
    { t: token, pid: personId },
  )

  // Navigate to dashboard — PersonProvider will call listPersons() on mount
  // and set person_id if we did not pre-set it
  await page.goto('/platform/dashboard')

  // Wait for PersonProvider to write person_id (it resolves async listPersons).
  // IMPORTANT: pass options as the 3rd argument, not the 2nd (which is `arg`).
  await page.waitForFunction(
    () => Boolean(localStorage.getItem('person_id')),
    undefined, // no arg to pass into the page function
    { timeout: 10_000 }, // options (3rd param)
  )

  return page
}
