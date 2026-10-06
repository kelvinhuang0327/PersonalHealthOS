import { expect, test } from '@playwright/test'

test('platform dashboard loads with explainability', async ({ page }) => {
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
        json: [
          { id: 'person-self', display_name: 'Self', relationship: 'self', is_default: true },
          { id: 'person-child', display_name: 'Child', relationship: 'child', is_default: false },
        ],
      })
    }
    if (path.endsWith('/profile/me')) {
      return route.fulfill({
        json: { id: 'person-self', display_name: 'Self', name: 'Self', age: 30, gender: 'male', onboarding_completed: true },
      })
    }
    if (path.includes('/actions/prioritized') || path.endsWith('/actions')) {
      return route.fulfill({ json: [] })
    }
    if (path.endsWith('/health-assistant/outcome-feedback')) {
      return route.fulfill({ json: { outcomes: [] } })
    }
    if (path.endsWith('/dashboard')) {
      return route.fulfill({
        json: {
          health_score: { overall_score: 82, components: { blood_pressure: 80 } },
          alerts: [
            {
              id: 'a1',
              title: 'High blood pressure',
              description: 'Recent readings are elevated',
              rule_id: 'bp_rule',
              category: 'cardio',
              priority: 10,
              confidence: 0.8,
              evidence_level: 'A',
              guideline_source: 'ACC/AHA',
            },
          ],
          insights: [
            {
              id: 'i1',
              title: 'Blood pressure trend',
              summary: 'Systolic trend is increasing',
              recommendation: 'Track 3 times weekly',
              rule_id: 'trend_bp',
              category: 'cardio',
              priority: 8,
              confidence: 0.79,
              evidence_level: 'B',
              guideline_source: 'ACC/AHA',
            },
          ],
          recommendations: [
            {
              recommendation: 'Reduce sodium intake',
              rule_id: 'rec_lifestyle',
              category: 'recommendation',
              priority: 9,
              confidence: 0.83,
              evidence_level: 'A',
              guideline_source: 'ACC/AHA',
            },
          ],
          trends: { systolic_bp: [{ recorded_at: new Date().toISOString(), value: 130 }] },
          explainability_summary: 'Based on ACC/AHA guideline with confidence 0.82',
          medical_disclaimer: 'This system is a health guidance tool, not a medical diagnosis.',
        },
      })
    }
    if (path.endsWith('/insights')) {
      return route.fulfill({
        json: [
          {
            id: 'i1',
            title: 'Blood pressure trend',
            summary: 'Systolic trend is increasing',
            recommendation: 'Track 3 times weekly',
            rule_id: 'trend_bp',
            category: 'cardio',
            priority: 8,
            confidence: 0.79,
            evidence_level: 'B',
            guideline_source: 'ACC/AHA',
          },
        ],
      })
    }
    if (path.endsWith('/timeline')) {
      return route.fulfill({
        json: {
          items: [
            {
              type: 'narrative_summary',
              title: '健康敘事更新',
              label: '敘事',
              description: '與上週相比，血壓仍偏高，但行動已開始執行。',
              start_date: new Date().toISOString().slice(0, 10),
              end_date: new Date().toISOString().slice(0, 10),
            },
            {
              type: 'insight',
              title: '血壓趨勢洞察',
              label: '洞察',
              description: '最近三次的血壓趨勢需要留意。',
              start_date: new Date().toISOString().slice(0, 10),
              end_date: new Date().toISOString().slice(0, 10),
              data: {
                rule_id: 'trend_bp',
                category: 'cardio',
                priority: 8,
                confidence: 0.79,
                evidence_level: 'B',
                guideline_source: 'ACC/AHA',
              },
            },
          ],
        },
      })
    }
    if (path.endsWith('/weekly-report')) {
      return route.fulfill({ json: { items: [] } })
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
            confidence: 0.0,
            limitations: [],
          },
        },
      })
    }
    if (path.includes('/family-recommendations')) {
      return route.fulfill({ json: { recommendations: [], total: 0 } })
    }
    if (path.endsWith('/metrics')) {
      return route.fulfill({ json: [] })
    }

    if (method === 'GET') return route.fulfill({ json: { items: [] } })
    return route.fulfill({ json: {} })
  })

  await page.goto('/platform/dashboard')
  await expect(page.getByRole('heading', { name: '儀表板' })).toBeVisible()
  await expect(page.getByText('Based on ACC/AHA guideline with confidence 0.82')).toBeVisible()

  await page.getByRole('button', { name: '加入追蹤' }).first().click()

  await page.goto('/platform/actions')
  await expect(page.getByRole('heading', { name: /執行中心|行動中心/ }).first()).toBeVisible()

  await page.goto('/platform/timeline')
  await expect(page.getByRole('heading', { name: '健康時間軸' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '健康敘事更新' }).first()).toBeVisible()

  await page.goto('/platform/weekly-report')
  await expect(page.getByRole('heading', { name: '每週健康報告' }).first()).toBeVisible()

  await page.goto('/platform/dashboard')
  await page.goto('/platform/notifications')
  await expect(page).toHaveURL(/\/platform\/notifications$/)
  await expect(page.getByText('健康待處理中心', { exact: true }).first()).toBeVisible()
  await expect(page.getByText(/你目前有 .* 件需要處理的健康事項/)).toBeVisible()
  await expect(page.getByRole('button', { name: '開始改善' }).first()).toBeVisible()
  const lowPriorityToggle = page.getByRole('button', { name: '展開' })
  if (await lowPriorityToggle.count()) {
    await lowPriorityToggle.first().click()
  }
  const activeCards = page.locator('[data-testid^="notification-card-"]')
  await expect(activeCards.first()).toBeVisible()
  await activeCards.first().getByRole('button', { name: '稍後提醒' }).click()
  const snoozedCards = page.locator('[data-testid="notifications-section-snoozed"] [data-testid^="notification-card-"]')
  await expect(snoozedCards).toHaveCount(1)

  await page.evaluate(() => {
    const key = 'notifications_center_lifecycle_person-self'
    const rows = JSON.parse(localStorage.getItem(key) || '[]')
    if (rows[0]) {
      rows[0].snoozed_until = new Date(Date.now() - 60_000).toISOString()
    }
    localStorage.setItem(key, JSON.stringify(rows))
  })

  await page.reload()
  const lowPriorityToggleAfterReload = page.getByRole('button', { name: '展開' })
  if (await lowPriorityToggleAfterReload.count()) {
    await lowPriorityToggleAfterReload.first().click()
  }
  await expect(page.locator('[data-testid="notifications-section-snoozed"] [data-testid^="notification-card-"]')).toHaveCount(0)
  await expect(page.locator('[data-testid^="notification-card-"]').first()).toBeVisible()
  await expect(page.getByText('已重新提醒').first()).toBeVisible()

  // Person switcher is now a button-dropdown (not a <select>)
  // Use localStorage to switch person directly instead of UI interaction
  await page.evaluate(() => {
    localStorage.setItem('person_id', 'person-child')
  })
  await page.reload()
  const lowPriorityToggleAfterSwitch = page.getByRole('button', { name: '展開' })
  if (await lowPriorityToggleAfterSwitch.count()) {
    await lowPriorityToggleAfterSwitch.first().click()
  }
  await expect(page.locator('[data-testid^="notification-card-"]').first()).toBeVisible()
  await expect(page.locator('[data-testid="notifications-section-snoozed"] [data-testid^="notification-card-"]')).toHaveCount(0)
})
