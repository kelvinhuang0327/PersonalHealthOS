/**
 * P14 Cross-user browser-context auth negative smoke.
 *
 * Verification scope: browser-context / API smoke (APIRequestContext).
 * This is NOT a full UI smoke — the frontend login UI flow is not exercised
 * because no multi-user storageState fixture exists yet (documented gap from
 * P13 report).  All HTTP calls go directly to the backend with real JWTs.
 *
 * Isolation boundary under test:
 *   backend/app/core/deps.py :: get_target_person()
 *   Filters: PersonProfile.owner_user_id == current_user.id
 *   Expected: 404 when user A supplies user B's person_id.
 *
 * Test users (idempotent, seeded by fixture):
 *   e2e-user-a@example.com / E2eTestA1!
 *   e2e-user-b@example.com / E2eTestB1!
 *
 * Requires: backend running at http://localhost:8000 (or NEXT_PUBLIC_API_BASE_URL)
 */

import { expect, test } from '@playwright/test'
import { setupTwoUsers } from './fixtures/auth'

const BACKEND =
  (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1')
    .replace(/\/api\/v1\/?$/, '')

test.describe('cross-user auth isolation — real JWT, no API interception', () => {
  test(
    'user A JWT cannot access user B family-health-context → 404',
    async ({ request }) => {
      const { userA, userB } = await setupTwoUsers(request)

      const res = await request.get(
        `${BACKEND}/api/v1/health-assistant/family-health-context?person_id=${userB.personId}`,
        { headers: { Authorization: `Bearer ${userA.token}` } },
      )

      expect(res.status()).toBe(404)
      const body = (await res.json()) as { detail: string }
      expect(body.detail.toLowerCase()).toContain('not found')
    },
  )

  test(
    'request without Authorization header → 401 (no credential path)',
    async ({ request }) => {
      const { userB } = await setupTwoUsers(request)

      const res = await request.get(
        `${BACKEND}/api/v1/health-assistant/family-health-context?person_id=${userB.personId}`,
      )

      expect(res.status()).toBe(401)
    },
  )

  test(
    'user A JWT cannot access user B family-recommendations → 404',
    async ({ request }) => {
      const { userA, userB } = await setupTwoUsers(request)

      const res = await request.get(
        `${BACKEND}/api/v1/health-assistant/family-recommendations?person_id=${userB.personId}`,
        { headers: { Authorization: `Bearer ${userA.token}` } },
      )

      expect(res.status()).toBe(404)
      const body = (await res.json()) as { detail: string }
      expect(body.detail.toLowerCase()).toContain('not found')
    },
  )
})
