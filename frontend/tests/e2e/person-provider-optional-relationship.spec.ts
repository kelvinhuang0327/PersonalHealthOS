import { expect, test } from '@playwright/test'

type PersonFixture = Record<string, unknown>

test('PersonProvider selects valid records when relationship is optional', async ({ page }) => {
  let persons: PersonFixture[] = [
    { id: 'person-legacy', display_name: 'Fixture Legacy Person', relationship: 'self', is_default: true },
  ]

  await page.addInitScript(() => {
    localStorage.setItem('token', 'person-provider-e2e-token')
    localStorage.setItem('onboarding_completed', '1')
  })

  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname

    if (path.endsWith('/persons')) return route.fulfill({ json: persons })
    if (path.endsWith('/profile/me')) {
      return route.fulfill({ json: { id: 'person-self', display_name: 'Self', onboarding_completed: true } })
    }
    if (path.endsWith('/health-assistant/outcome-feedback')) return route.fulfill({ json: { outcomes: [] } })
    if (path.endsWith('/timeline') || path.endsWith('/weekly-report')) return route.fulfill({ json: { items: [] } })
    if (path.includes('/family-relationships')) return route.fulfill({ json: { relationships: [], total: 0 } })
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
    if (path.includes('/family-recommendations')) return route.fulfill({ json: { recommendations: [], total: 0 } })
    if (path.endsWith('/dashboard')) return route.fulfill({ json: { alerts: [], insights: [], recommendations: [], trends: {} } })
    if (route.request().method() === 'GET') return route.fulfill({ json: [] })
    return route.fulfill({ json: {} })
  })

  const waitForPersons = () =>
    page.waitForResponse((response) => new URL(response.url()).pathname.endsWith('/persons'))
  const assertSelected = async (displayName: string, id: string) => {
    const switcher = page.locator('header button').last()
    await expect(switcher).toContainText(displayName)
    await expect.poll(() => page.evaluate(() => localStorage.getItem('person_id'))).toBe(id)
    const observed = { display: await switcher.innerText(), personId: await page.evaluate(() => localStorage.getItem('person_id')) }
    console.log(`PERSON_PROVIDER_SELECTED=${JSON.stringify(observed)}`)
  }
  const reloadWith = async (nextPersons: PersonFixture[], clearStoredId = true) => {
    persons = nextPersons
    if (clearStoredId) await page.evaluate(() => localStorage.removeItem('person_id'))
    const personsResponse = waitForPersons()
    await page.reload()
    await personsResponse
  }

  const initialPersonsResponse = waitForPersons()
  await page.goto('/platform/insights')
  await initialPersonsResponse
  await assertSelected('Fixture Legacy Person', 'person-legacy')

  await reloadWith([{ id: 'person-no-relationship', display_name: 'Fixture No Relationship Person', is_default: true }])
  await assertSelected('Fixture No Relationship Person', 'person-no-relationship')

  await reloadWith([
    { id: 'person-relationship-type', display_name: 'Fixture Relationship Type Person', relationship_type: 'self', is_default: true },
  ])
  await assertSelected('Fixture Relationship Type Person', 'person-relationship-type')

  await reloadWith([
    { id: '', display_name: 'Fixture Empty ID', is_default: true },
    { id: 'person-empty-name', display_name: '   ', is_default: true },
    { id: 42, display_name: 'Fixture Invalid ID', is_default: true },
  ])
  await expect(page.locator('header button').last()).toContainText('Person')
  await expect.poll(() => page.evaluate(() => localStorage.getItem('person_id'))).toBeNull()
  console.log('PERSON_PROVIDER_INVALID_RECORDS_SELECTED=null')

  const multiplePeople = [
    { id: 'person-first', display_name: 'Fixture First Person', relationship: 'self', is_default: false },
    { id: 'person-default', display_name: 'Fixture Default Person', is_default: true },
    { id: 'person-child', display_name: 'Fixture Child Person', relationship: 'child', is_default: false },
  ]
  await reloadWith(multiplePeople)
  await assertSelected('Fixture Default Person', 'person-default')

  await page.evaluate(() => localStorage.setItem('person_id', 'person-first'))
  await reloadWith(multiplePeople, false)
  await assertSelected('Fixture First Person', 'person-first')

  await reloadWith([
    { id: 'person-first', display_name: 'Fixture First Person', relationship: 'self', is_default: false },
    { id: 'person-child', display_name: 'Fixture Child Person', relationship: 'child', is_default: false },
  ])
  await assertSelected('Fixture First Person', 'person-first')
})

test('PersonSwitcher safely displays optional relationship and preserves selected IDs', async ({ page }) => {
  const persons: PersonFixture[] = [
    { id: 'person-legacy', display_name: 'Fixture Legacy Person', relationship: 'child', relationship_type: 'self' },
    { id: 'person-relationship-type', display_name: 'Fixture Relationship Type Person', relationship_type: 'spouse', is_default: true },
    { id: 'person-no-relationship', display_name: 'Fixture No Relationship Person' },
  ]

  await page.addInitScript(() => {
    localStorage.setItem('token', 'person-switcher-e2e-token')
    localStorage.setItem('onboarding_completed', '1')
  })
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/persons')) return route.fulfill({ json: persons })
    if (route.request().method() === 'GET') return route.fulfill({ json: [] })
    return route.fulfill({ json: {} })
  })

  const personsResponse = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith('/persons'))
  await page.goto('/platform/insights')
  await personsResponse

  const currentPersonButton = page.locator('header button').last()
  await expect(currentPersonButton).toContainText('Fixture Relationship Type Person')
  await expect.poll(() => page.evaluate(() => localStorage.getItem('person_id'))).toBe('person-relationship-type')
  await currentPersonButton.click()

  const relationshipTypeOption = page.getByRole('button', { name: /Fixture Relationship Type Person/ }).last()
  const legacyOption = page.getByRole('button', { name: /Fixture Legacy Person/ }).last()
  const noRelationshipOption = page.getByRole('button', { name: /Fixture No Relationship Person/ }).last()
  await expect(relationshipTypeOption).toContainText('配偶')
  await expect(legacyOption).toContainText('子女')
  await expect(noRelationshipOption).toContainText('家人')

  await legacyOption.click()
  await expect.poll(() => page.evaluate(() => localStorage.getItem('person_id'))).toBe('person-legacy')
  const selectedLegacyPersonButton = page.getByRole('button', { name: /Fixture Legacy Person/ }).first()
  await expect(selectedLegacyPersonButton).toContainText('Fixture Legacy Person')
  console.log(`PERSON_SWITCHER_SELECTED=${JSON.stringify({ display: await selectedLegacyPersonButton.innerText(), personId: await page.evaluate(() => localStorage.getItem('person_id')) })}`)
})
