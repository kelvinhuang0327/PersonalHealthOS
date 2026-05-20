/**
 * Minimal smoke tests — FamilyHealthCard evidence transparency (P10)
 *
 * NOTE: These tests require a running dev server (`npx next dev`).
 * Status in current sprint: NOT RUN (no live server in CI pipeline).
 * Written for future E2E validation when server is available.
 */
import { expect, test } from '@playwright/test'

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

test.describe('FamilyHealthCard — evidence transparency smoke', () => {
  test.beforeEach(async ({ page }) => {
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
      if (route.request().method() === 'GET') return route.fulfill({ json: { items: [] } })
      return route.fulfill({ json: {} })
    })
  })

  test('family health card section is visible on dashboard', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText('家庭健康脈絡')).toBeVisible()
  })

  test('no-diagnosis disclaimer is visible', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText('非醫療診斷')).toBeVisible()
  })

  test('source badge labels visible (child_health → 兒童健康)', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText('兒童健康').first()).toBeVisible()
  })

  test('source badge labels visible (action → 行動建議)', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText('行動建議').first()).toBeVisible()
  })

  test('audience badge visible (caregiver → 照護者)', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText('照護者').first()).toBeVisible()
  })

  test('source origin label visible on sections', async ({ page }) => {
    await page.goto('/platform/dashboard')
    await expect(page.getByText('健康觀察資料').first()).toBeVisible()
  })
})
