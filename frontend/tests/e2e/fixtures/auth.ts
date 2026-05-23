/**
 * P14 Real-Auth Playwright Fixture — browser-context token bootstrap.
 *
 * Obtains real JWTs from the live backend (POST /api/v1/auth/login) and
 * ensures each test user has at least one PersonProfile owned by them.
 * No API responses are intercepted — all requests hit the real backend.
 *
 * Usage:
 *   import { setupTwoUsers } from './fixtures/auth'
 *   const { userA, userB } = await setupTwoUsers(request)
 *
 * Bootstrap contract:
 *   - e2e-user-a@example.com / E2eTestA1!  (seeded on first run via /register)
 *   - e2e-user-b@example.com / E2eTestB1!  (seeded on first run via /register)
 *   - Both registrations are idempotent: 400 = already exists → ignored.
 *
 * The fixture intentionally avoids storageState / globalSetup so it remains
 * self-contained and runnable with a single-file `npx playwright test` call.
 */

import { APIRequestContext } from '@playwright/test'

/** Resolve backend origin from the env var the Next.js app uses, stripping /api/v1 suffix. */
const BACKEND_URL =
  (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1')
    .replace(/\/api\/v1\/?$/, '')

export interface E2EUser {
  token: string
  personId: string
}

/**
 * Attempts to register a user; silently accepts 400 (already registered).
 * Then logs in and returns the access_token.
 */
async function registerOrLogin(
  request: APIRequestContext,
  email: string,
  password: string,
): Promise<string> {
  // Idempotent registration: 400 = already exists → ok
  await request.post(`${BACKEND_URL}/api/v1/auth/register`, {
    data: { email, password },
  })

  const loginRes = await request.post(`${BACKEND_URL}/api/v1/auth/login`, {
    data: { email, password },
  })
  if (!loginRes.ok()) {
    throw new Error(
      `[auth fixture] Login failed for ${email}: ${await loginRes.text()}`,
    )
  }
  const body = (await loginRes.json()) as { access_token: string }
  return body.access_token
}

/**
 * Returns the first existing PersonProfile id for the user, or creates one
 * if none exists.  Idempotent across test runs.
 */
async function ensurePersonProfile(
  request: APIRequestContext,
  token: string,
  displayName: string,
): Promise<string> {
  const listRes = await request.get(`${BACKEND_URL}/api/v1/persons`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  const persons = (await listRes.json()) as Array<{ id: string }>
  if (persons.length > 0) return persons[0].id

  const createRes = await request.post(`${BACKEND_URL}/api/v1/persons`, {
    data: { display_name: displayName, relationship: 'self', is_default: true },
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!createRes.ok()) {
    throw new Error(
      `[auth fixture] PersonProfile creation failed for ${displayName}: ${await createRes.text()}`,
    )
  }
  const person = (await createRes.json()) as { id: string }
  return person.id
}

/**
 * Sets up two isolated test users against the live backend.
 * Returns tokens and person IDs for both users.
 * Fully idempotent — safe to call in every test.
 */
export async function setupTwoUsers(request: APIRequestContext): Promise<{
  userA: E2EUser
  userB: E2EUser
}> {
  const tokenA = await registerOrLogin(
    request,
    'e2e-user-a@example.com',
    'E2eTestA1!',
  )
  const tokenB = await registerOrLogin(
    request,
    'e2e-user-b@example.com',
    'E2eTestB1!',
  )

  const [personIdA, personIdB] = await Promise.all([
    ensurePersonProfile(request, tokenA, 'E2E User A'),
    ensurePersonProfile(request, tokenB, 'E2E User B'),
  ])

  return {
    userA: { token: tokenA, personId: personIdA },
    userB: { token: tokenB, personId: personIdB },
  }
}
