/**
 * P16 Multi-Browser Full UI Auth Negative Smoke.
 *
 * Extends P15 to prove isolation across TWO simultaneously-active browser
 * contexts (userA + userB), and to verify storageState round-trip: auth state
 * saved to a JSON file and reloaded in a fresh context without addInitScript.
 *
 * Two tests:
 *
 *   Test 1 — simultaneous sessions
 *     • userA context and userB context are bootstrapped concurrently via
 *       Promise.all (true multi-browser, not sequential)
 *     • Positive control (userB): GET /api/v1/persons with userB's JWT returns
 *       200 and includes userB's personId — proves JWT is correctly scoped
 *     • Negative (userA cross-user): person_id overwritten with userB's UUID →
 *       family-health-context → 404 + error UI + no data leakage in DOM
 *
 *   Test 2 — storageState round-trip
 *     • Bootstrap userA → save context.storageState() to a temp file
 *     • Create a FRESH context from that file (no addInitScript)
 *     • Navigate to /platform/dashboard — localStorage already carries JWT
 *     • Assert person_id survived the round-trip (PersonProvider preserves it)
 *     • Assert GET /api/v1/persons returns 200 with userA's personId (JWT still
 *       valid, CORS bridge works on storageState-restored context)
 *
 * Architecture notes:
 *   - CORS bridge is installed via installCORSBridge() on every context
 *     (route handlers are NOT stored in storageState files)
 *   - storageState files written to /tmp — no secrets committed to the repo
 *
 * Prerequisites:
 *   - Backend: http://localhost:8000
 *   - Frontend: http://127.0.0.1:3010 (started by Playwright webServer)
 */

import { expect, test } from '@playwright/test'
import { setupTwoUsers } from './fixtures/auth'
import {
  bootstrapWithRealJWT,
  contextFromStorageState,
} from './fixtures/auth-ui'
import * as path from 'path'
import * as os from 'os'

test.describe('P16 multi-browser storageState auth isolation smoke', () => {
  // Two bootstraps (parallel) + two reloads + storageState IO
  test.setTimeout(180_000)

  // ── Test 1 ────────────────────────────────────────────────────────────────
  test(
    'simultaneous sessions — userB positive control + userA cross-user 404 + error UI',
    async ({ browser, request }) => {
      const { userA, userB } = await setupTwoUsers(request)

      const contextA = await browser.newContext()
      const contextB = await browser.newContext()

      try {
        // Bootstrap both users concurrently (true multi-browser, saves ~8 s)
        const [pageA, pageB] = await Promise.all([
          bootstrapWithRealJWT(contextA, userA.token),
          bootstrapWithRealJWT(contextB, userB.token),
        ])

        // ── Positive control: userB's own session ──────────────────────────
        // GET /api/v1/persons is called by PersonProvider on every page load.
        // With userB's JWT it must return 200 and include userB's personId.
        // This proves JWT-to-person scoping is correct (not cross-contaminated).
        // api.request() appends ?person_id=<id> once localStorage has it,
        // so the URL is /api/v1/persons?person_id=... — match by pathname only.
        const bPersonsPromise = pageB.waitForResponse(
          (res) =>
            /\/api\/v1\/persons(\?|$)/.test(res.url()) &&
            res.request().method() === 'GET',
          { timeout: 15_000 },
        )
        await pageB.reload()
        const bPersonsResponse = await bPersonsPromise
        expect(bPersonsResponse.status()).toBe(200)
        const bPersonsList = (await bPersonsResponse.json()) as Array<{
          id: string
        }>
        const bIds = bPersonsList.map((p) => p.id)
        expect(bIds).toContain(userB.personId)
        // UserA's personId must NOT appear in userB's persons list
        expect(bIds).not.toContain(userA.personId)

        // ── Cross-user negative: userA context with userB's person_id ──────
        // Overwrite person_id — addInitScript will NOT re-inject it on reload
        // because we did NOT pass personId to bootstrapWithRealJWT.
        await pageA.evaluate(
          (pid: string) => {
            localStorage.setItem('person_id', pid)
          },
          userB.personId,
        )

        const aCrossResponsePromise = pageA.waitForResponse(
          (res) =>
            res.url().includes('family-health-context') &&
            res.request().method() === 'GET',
          { timeout: 15_000 },
        )
        await pageA.reload()
        const aCrossResponse = await aCrossResponsePromise

        // Backend get_target_person enforces owner_user_id == current_user.id
        expect(aCrossResponse.status()).toBe(404)

        // FamilyHealthCard must render its error state
        await expect(pageA.getByText('無法載入家庭健康資料')).toBeVisible({
          timeout: 10_000,
        })

        // UserB's personId must not appear anywhere in the rendered DOM
        const bodyTextA = (await pageA.textContent('body')) ?? ''
        expect(bodyTextA).not.toContain(userB.personId)
      } finally {
        await contextA.close().catch(() => {})
        await contextB.close().catch(() => {})
      }
    },
  )

  // ── Test 2 ────────────────────────────────────────────────────────────────
  test(
    'storageState round-trip — auth persists in fresh context without addInitScript',
    async ({ browser, request }) => {
      const { userA } = await setupTwoUsers(request)

      const stateFile = path.join(os.tmpdir(), 'p16-userA-state.json')
      const contextA = await browser.newContext()

      try {
        // Bootstrap userA and persist the storageState
        await bootstrapWithRealJWT(contextA, userA.token)
        await contextA.storageState({ path: stateFile })
      } finally {
        await contextA.close().catch(() => {})
      }

      // Create a completely fresh context from the saved state.
      // No addInitScript — localStorage carries the JWT and person_id.
      const contextA2 = await contextFromStorageState(browser, stateFile)
      try {
        const pageA2 = await contextA2.newPage()

        // Listen for PersonProvider's listPersons call before navigating
        const personsPromise = pageA2.waitForResponse(
          (res) =>
            /\/api\/v1\/persons(\?|$)/.test(res.url()) &&
            res.request().method() === 'GET',
          { timeout: 15_000 },
        )
        await pageA2.goto('/platform/dashboard')
        const personsResponse = await personsPromise

        // JWT still valid → PersonProvider's listPersons returns 200
        expect(personsResponse.status()).toBe(200)

        // person_id from storageState must survive — PersonProvider preserves
        // a truthy localStorage['person_id'] value without overwriting it
        const personIdAfterRoundTrip = await pageA2.evaluate(
          () => localStorage.getItem('person_id') ?? '',
        )
        expect(personIdAfterRoundTrip).toBe(userA.personId)

        // The persons list must still contain userA's profile
        const personsList = (await personsResponse.json()) as Array<{
          id: string
        }>
        expect(personsList.map((p) => p.id)).toContain(userA.personId)
      } finally {
        await contextA2.close().catch(() => {})
      }
    },
  )
})
