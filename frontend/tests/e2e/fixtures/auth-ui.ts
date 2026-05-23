/**
 * P15 Real-JWT storageState Bootstrap Fixture.
 *
 * Classification: real-JWT storageState bootstrap (not login-form smoke).
 *
 * The Next.js login page uses React controlled inputs (value= binding) which
 * are unreliable targets for Playwright fill() in a production (next start)
 * build.  This fixture uses the safer approach of injecting a real HS256 JWT —
 * obtained from the live backend via setupTwoUsers() — directly into
 * localStorage via page.addInitScript() before first navigation.
 *
 * CORS note: The Playwright webServer runs at http://127.0.0.1:3010 but the
 * backend's CORS whitelist only covers :3000 and :3100.  A context-level route
 * handler intercepts all requests to localhost:8000 and injects the required
 * CORS response headers so the browser can read the API responses.  The
 * upstream request is forwarded unchanged; only CORS headers are added to the
 * response.
 *
 * Usage:
 *   import { bootstrapWithRealJWT } from './fixtures/auth-ui'
 *   const page = await bootstrapWithRealJWT(context, token, personId)
 *   const state = await context.storageState()  // real-JWT storageState
 *
 * Requirements:
 *   - Next.js frontend server running at baseURL (http://127.0.0.1:3010)
 *   - A real JWT string obtained from the live backend
 */

import { BrowserContext, Page } from '@playwright/test'

const FRONTEND_ORIGIN = 'http://127.0.0.1:3010'
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': FRONTEND_ORIGIN,
  'Access-Control-Allow-Credentials': 'true',
  'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
  'Access-Control-Allow-Headers': 'Authorization,Content-Type,Accept',
}

/**
 * Bootstraps a browser context with a real JWT obtained from the live backend.
 *
 * Installs a context-level CORS route handler, injects the JWT into
 * localStorage via addInitScript, navigates to /platform/dashboard, and
 * waits for PersonProvider to populate localStorage['person_id'].
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
  // Install CORS bridge before any page is created.
  // The backend allows :3000 and :3100 but not :3010 (the Playwright port).
  // We intercept every backend request, forward it unchanged, and add the
  // missing CORS headers to the response so the browser accepts it.
  await context.route('http://localhost:8000/**', async (route, request) => {
    if (request.method() === 'OPTIONS') {
      // Respond to CORS preflight immediately — no need to hit the backend
      await route.fulfill({ status: 200, headers: CORS_HEADERS })
      return
    }
    // For all other methods: forward to backend, patch CORS headers on the way back
    const response = await route.fetch()
    await route.fulfill({
      response,
      headers: { ...response.headers(), ...CORS_HEADERS },
    })
  })

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
  // Passing { timeout } as 2nd arg silently becomes the function argument and
  // the actual Playwright timeout remains 0 (infinite), causing the test to
  // hang until the overall test.setTimeout fires.
  await page.waitForFunction(
    () => Boolean(localStorage.getItem('person_id')),
    undefined, // no arg to pass into the page function
    { timeout: 10_000 }, // options (3rd param)
  )

  return page
}
