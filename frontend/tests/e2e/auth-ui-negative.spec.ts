/**
 * P15 Full-UI Cross-User Auth Negative Smoke.
 *
 * Verifies that a user A browser session cannot expose user B's family health
 * data at the UI rendering layer.
 *
 * Isolation boundary under test:
 *   - User A is authenticated via the real /platform/login form
 *     (real JWT issued by backend, set in localStorage by the app itself)
 *   - localStorage['person_id'] is overwritten with user B's person_id
 *     to simulate a cross-user data access attempt
 *   - The dashboard reload triggers a real network call to
 *     GET /api/v1/health-assistant/family-health-context?person_id=<userB>
 *     authenticated with user A's JWT
 *   - Backend enforces owner check (get_target_person) → 404
 *   - FamilyHealthCard must render the error state '無法載入家庭健康資料'
 *     and must NOT render user B's person_id anywhere in the DOM
 *
 * Prerequisites (must be running before this test):
 *   - Backend: http://localhost:8000  (FastAPI + JWT HS256)
 *   - Frontend: started by Playwright webServer (http://127.0.0.1:3010)
 */

import { expect, test } from '@playwright/test'
import { setupTwoUsers } from './fixtures/auth'
import { bootstrapWithRealJWT } from './fixtures/auth-ui'

test.describe('P15 cross-user UI auth negative smoke', () => {
  // webServer cold-start + bootstrapWithRealJWT + dashboard load can total ~60s
  test.setTimeout(120_000)

  test(
    'user A real-JWT session → user B person_id → family-health-context 404 + error UI rendered',
    async ({ browser, request }) => {
      // ---- 1. Bootstrap test users (idempotent) ----------------------------
      // Re-uses P14 real-auth fixture to obtain valid tokens + person IDs.
      const { userA, userB } = await setupTwoUsers(request)

      // ---- 2. Authenticate user A via real-JWT localStorage injection ------
      const contextA = await browser.newContext()
      try {
        // Do NOT pass personId here — addInitScript would re-inject userA.personId
        // on every page load (including reload), which would overwrite the
        // cross-user injection below.  Let PersonProvider auto-select it.
        const page = await bootstrapWithRealJWT(contextA, userA.token)

        // Sanity: login page must have stored a real JWT
        const tokenA = await page.evaluate(
          () => localStorage.getItem('token') ?? '',
        )
        expect(tokenA.length).toBeGreaterThan(0)

        // ---- 3. Cross-user injection ----------------------------------------
        // Override person_id with user B's person_id.
        // PersonProvider preserves the localStorage value on the next load
        // (it trusts 'person_id' if already set), so all subsequent api.request()
        // calls will append ?person_id=<userB> to their URLs.
        await page.evaluate(
          (pid: string) => { localStorage.setItem('person_id', pid) },
          userB.personId,
        )

        // ---- 4. Reload and capture the network boundary --------------------
        // waitForResponse MUST be set up before the action that triggers the
        // request (page.reload()) to avoid a race condition.
        const responsePromise = page.waitForResponse(
          (res) =>
            res.url().includes('family-health-context') &&
            res.request().method() === 'GET',
          { timeout: 15_000 },
        )
        await page.reload()
        const familyCtxResponse = await responsePromise

        // ---- 5. Network-layer assertion -------------------------------------
        // Backend owner-check (get_target_person) must reject the cross-user
        // person_id with 404 "Person profile not found".
        expect(familyCtxResponse.status()).toBe(404)

        // ---- 6. UI-layer assertions -----------------------------------------
        // FamilyHealthCard catches the thrown error and sets:
        //   error = '無法載入家庭健康資料'
        // That text must be visible, confirming the error state is rendered.
        await expect(page.getByText('無法載入家庭健康資料')).toBeVisible({
          timeout: 10_000,
        })

        // User B's person_id must not appear as rendered page text.
        // This guards against any inadvertent data echo from the 404 response.
        const bodyText = (await page.textContent('body')) ?? ''
        expect(bodyText).not.toContain(userB.personId)
      } finally {
        await contextA.close()
      }
    },
  )
})
