import { expect, test } from '@playwright/test';

type Person = { id: string; display_name: string; relationship: string; is_default: boolean };
type Symptom = {
  id: string;
  person_id: string;
  symptom: string;
  occurred_at: string;
  duration_minutes: number;
  severity: number;
  note: string;
};

function personIdFromUrl(url: URL, fallback: string) {
  return url.searchParams.get('person_id') || fallback;
}

test.describe('health platform e2e', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'e2e-token');
      localStorage.setItem('onboarding_completed', '1');
      if (!localStorage.getItem('person_id')) {
        localStorage.setItem('person_id', 'person-self');
      }
    });

      const state: {
      persons: Person[];
      symptoms: Symptom[];
      documents: Array<Record<string, unknown>>;
      profile: Record<string, unknown>;
      account: Record<string, unknown>;
      externalHistory: Array<Record<string, unknown>>;
        alerts: Array<Record<string, unknown>>;
        insights: Array<Record<string, unknown>>;
      } = {
      persons: [
        { id: 'person-self', display_name: '本人', relationship: 'self', is_default: true },
        { id: 'person-child', display_name: '小孩', relationship: 'child', is_default: false },
      ],
      symptoms: [],
      documents: [],
      profile: {
        id: 'person-self',
        user_id: 'user-1',
        full_name: '測試使用者',
        birth_date: '1990-01-01',
        gender: 'male',
        height_cm: 170,
        weight_kg: 65,
        allergies: '',
        family_history: '',
        chronic_conditions: '',
      },
      account: {
        id: 'user-1',
        email: 'user@example.com',
        account_settings: { locale: 'zh-TW' },
      },
      externalHistory: [],
        alerts: [],
        insights: [],
      };

    await page.route('**/api/v1/**', async (route) => {
      const req = route.request();
      const url = new URL(req.url());
      const method = req.method();
      const path = url.pathname;
      const personId = personIdFromUrl(url, 'person-self');

      if (path.endsWith('/actions/prioritized') && method === 'GET') {
        return route.fulfill({ json: [] });
      }
      if (path.endsWith('/actions') && method === 'GET') {
        return route.fulfill({ json: [] });
      }
      if (path.endsWith('/actions') && method === 'POST') {
        return route.fulfill({ status: 201, json: { id: `action-${Date.now()}`, status: 'todo' } });
      }

      if (path.endsWith('/persons') && method === 'GET') {
        return route.fulfill({ json: state.persons });
      }
      if (path.endsWith('/persons') && method === 'POST') {
        const body = req.postDataJSON() as Record<string, string>;
        const newPerson = {
          id: `person-${state.persons.length + 1}`,
          display_name: body.display_name,
          relationship: body.relationship || 'family',
          is_default: false,
        };
        state.persons.push(newPerson);
        return route.fulfill({ json: newPerson });
      }

      if (path.endsWith('/symptoms') && method === 'GET') {
        return route.fulfill({ json: state.symptoms.filter((s) => s.person_id === personId) });
      }
      if (path.endsWith('/symptoms') && method === 'POST') {
        const body = req.postDataJSON() as Omit<Symptom, 'id' | 'person_id'>;
        const symptom = { id: `sym-${state.symptoms.length + 1}`, person_id: personId, ...body };
        state.symptoms.unshift(symptom);
        return route.fulfill({ json: { ...symptom, user_id: 'user-1', subject_profile_id: personId } });
      }
      if (/\/api\/v1\/symptoms\/[^/]+$/.test(path) && method === 'PUT') {
        const targetId = path.split('/').pop() as string;
        const body = req.postDataJSON() as Partial<Symptom>;
        const found = state.symptoms.find((s) => s.id === targetId);
        if (!found) return route.fulfill({ status: 404, json: { detail: 'not found' } });
        Object.assign(found, body);
        return route.fulfill({ json: { ...found, user_id: 'user-1', subject_profile_id: found.person_id } });
      }

      if (path.endsWith('/documents') && method === 'GET') {
        if (state.documents.length === 0) {
          state.documents.push({
            id: 'doc-seed',
            category: '健檢',
            subject_profile_id: personId,
            original_filename: 'report.pdf',
            file_type: 'pdf',
            mime_type: 'application/pdf',
            file_size: 128,
            storage_bucket: 'bucket',
            storage_key: 'key',
            parse_status: 'pending',
            uploaded_at: new Date().toISOString(),
          });
        }
        return route.fulfill({
          json: state.documents.filter((d) => String(d.subject_profile_id) === personId),
        });
      }
      if (path.endsWith('/documents/upload') && method === 'POST') {
        const id = `doc-${state.documents.length + 1}`;
        const row = {
          id,
          category: '健檢',
          subject_profile_id: personId,
          original_filename: 'report.pdf',
          file_type: 'pdf',
          mime_type: 'application/pdf',
          file_size: 128,
          storage_bucket: 'bucket',
          storage_key: 'key',
          parse_status: 'pending',
          uploaded_at: new Date().toISOString(),
        };
        state.documents.unshift(row);
        return route.fulfill({ json: row });
      }
      if (/\/api\/v1\/documents\/[^/]+\/parse$/.test(path) && method === 'POST') {
        const targetId = path.split('/').slice(-2)[0];
        const row = state.documents.find((d) => d.id === targetId);
        if (row) row.parse_status = 'parsed';
        return route.fulfill({
          json: {
            document_id: targetId,
            report_id: 'report-1',
            extracted_items: 1,
            abnormal_items: 1,
            parsed_items_preview: [{ item_name: 'Glucose', value_num: 110, unit: 'mg/dL', abnormal_flag: 'H' }],
          },
        });
      }
      if (/\/api\/v1\/documents\/[^/]+\/confirm$/.test(path) && method === 'PUT') {
        const targetId = path.split('/').slice(-2)[0];
        const body = req.postDataJSON() as { confirmed_data: Record<string, unknown> };
        const row = state.documents.find((d) => d.id === targetId);
        if (row) {
          row.parse_status = 'confirmed';
          row.confirmed_data = body.confirmed_data;
          row.confirmed_at = new Date().toISOString();
        }
        return route.fulfill({ json: row });
      }

      if (path.endsWith('/profile/me') && method === 'GET') return route.fulfill({ json: { ...state.profile, onboarding_completed: true } });
      if (path.endsWith('/profile/me') && method === 'PUT') {
        Object.assign(state.profile, req.postDataJSON());
        return route.fulfill({ json: state.profile });
      }
      if (path.endsWith('/profile/account') && method === 'GET') return route.fulfill({ json: state.account });
      if (path.endsWith('/profile/account') && method === 'PUT') {
        Object.assign(state.account, req.postDataJSON());
        return route.fulfill({ json: state.account });
      }
      if (path.endsWith('/auth/change-password') && method === 'POST') return route.fulfill({ json: { status: 'ok' } });

      if (path.endsWith('/analytics/health-analysis') && method === 'GET') {
        return route.fulfill({
          json: {
            person_id: personId,
            analyzed_at: new Date().toISOString(),
            data_sufficient: false,
            abnormal_indicators: [],
            long_term_symptoms: [],
            potential_risks: ['資料不足，無法提供可靠分析。'],
            follow_up_items: ['請先補充近期症狀、健檢報告或身體指數資料。'],
            recommendations: ['完成至少一筆症狀與一筆身體指數後再分析。'],
            disclaimer: '本平台僅供健康資訊參考，非醫療診斷。',
          },
        });
      }

      if (path.endsWith('/external-metrics/sync') && method === 'POST') {
        state.externalHistory = [
          { source: 'external_api', steps: 5000, recorded_at: new Date().toISOString() },
          { source: 'external_api', heart_rate: 72, recorded_at: new Date().toISOString() },
        ];
        return route.fulfill({ json: { synced_count: state.externalHistory.length, source: 'external_api' } });
      }
      if (path.endsWith('/external-metrics/history') && method === 'GET') {
        return route.fulfill({ json: state.externalHistory });
      }
      if (path.endsWith('/external-metrics/trends') && method === 'GET') {
        return route.fulfill({
          json: {
            metric: url.searchParams.get('metric') || 'steps',
            points: [{ recorded_at: new Date().toISOString(), value: 5000 }],
          },
        });
      }
      if (path.endsWith('/risk-alerts') && method === 'GET') {
        return route.fulfill({ json: state.alerts });
      }
      if (path.endsWith('/risk-alerts/monitor') && method === 'POST') {
        state.alerts = [
          {
            id: 'alert-1',
            risk_type: 'bp_high_3times',
            source_type: 'risk_monitor',
            source_id: null,
            rule_code: 'BP_HIGH_3TIMES',
            severity: 'warning',
            title: '血壓偏高',
            message: '最近三次血壓測量超過140/90',
            description: '最近三次血壓測量超過140/90',
            recommendation: '建議就醫評估',
            status: 'active',
            created_at: new Date().toISOString(),
          },
        ];
        return route.fulfill({ json: state.alerts });
      }
      if (path.endsWith('/insights') && method === 'GET') {
        return route.fulfill({ json: state.insights });
      }
      if (path.endsWith('/insights/generate') && method === 'POST') {
        state.insights = [
          {
            id: 'insight-1',
            insight_type: 'trend',
            severity: 'info',
            title: '血壓趨勢洞察',
            summary: '最近三次平均收縮壓約 130 mmHg。',
            recommendation: '建議持續量測並配合作息管理。',
            generated_at: new Date().toISOString(),
          },
        ];
        return route.fulfill({ json: state.insights });
      }
      if (/\/api\/v1\/insights\/[^/]+\/dismiss$/.test(path) && method === 'POST') {
        state.insights = [];
        return route.fulfill({
          json: {
            id: 'insight-1',
            insight_type: 'trend',
            severity: 'info',
            title: '血壓趨勢洞察',
            summary: '最近三次平均收縮壓約 130 mmHg。',
            recommendation: '建議持續量測並配合作息管理。',
            generated_at: new Date().toISOString(),
            is_active: false,
          },
        });
      }
      if (path.endsWith('/dashboard') && method === 'GET') {
        return route.fulfill({
          json: {
            health_score: { overall_score: 78, components: { blood_pressure: 80, bmi: 82, lab_results: 75 } },
            alerts: state.alerts,
            insights: state.insights,
            recommendations: [
              {
                recommendation: '建議連續三天記錄早晚血壓',
                rule_id: 'rec-bp-home',
                category: 'cardio',
                priority: 9,
                confidence: 0.82,
                evidence_level: 'A',
                guideline_source: 'ACC/AHA',
              },
            ],
            recent_symptoms: state.symptoms.filter((s) => s.person_id === personId).slice(0, 5),
            recent_metrics: [
              {
                id: 'm1',
                recorded_at: new Date().toISOString(),
                systolic_bp: 130,
                diastolic_bp: 85,
                heart_rate: 72,
                blood_glucose: 98,
                weight_kg: 65,
                sleep_hours: 7,
              },
            ],
            recent_labs: [{ id: 'l1', report_type: 'health_check', report_date: '2026-01-01', created_at: new Date().toISOString(), abnormal_items: 1 }],
            trends: { systolic_bp: [{ recorded_at: new Date().toISOString(), value: 130 }] },
            risk_level: 'elevated',
            explainability_summary: '最近的血壓與健檢資料顯示需要持續追蹤。',
            medical_disclaimer: '本平台提供健康資訊整理與一般追蹤建議，非醫療診斷。',
          },
        });
      }
      if (path.includes('/family-relationships') && method === 'GET') {
        return route.fulfill({ json: { relationships: [], total: 0 } });
      }
      if (path.includes('/family-health-context') && method === 'GET') {
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
        });
      }
      if (path.includes('/family-recommendations') && method === 'GET') {
        return route.fulfill({ json: { recommendations: [], total: 0 } });
      }
      if (path.endsWith('/metrics') && method === 'GET') {
        return route.fulfill({ json: [] });
      }

      return route.fulfill({ status: 200, json: {} });
    });
  });

  test('person switch + symptoms add/edit/history isolation', async ({ page }) => {
    await page.goto('/symptoms');
    await page.getByPlaceholder('請直接描述過去或平常的症狀（不需要填日期）').fill('頭痛');
    await page.getByRole('button', { name: '儲存症狀自述' }).click();
    await expect(page.getByText('頭痛')).toBeVisible();

    await page.locator('nav select').selectOption('person-child');
    await expect(page).toHaveURL(/\/symptoms/);
    // Wait for page to reflect person-child data AND for React to hydrate after reload
    await expect(page.getByRole('heading', { name: '歷史症狀' })).toBeVisible({ timeout: 10000 });
    // Wait for JS bundle to load and React to finish hydration (SSR heading is visible before hydration)
    await page.waitForLoadState('load', { timeout: 30000 });
    await expect(page.getByText('頭痛')).toHaveCount(0);
    await page.getByPlaceholder('請直接描述過去或平常的症狀（不需要填日期）').fill('咳嗽');
    await page.getByRole('button', { name: '儲存症狀自述' }).click();
    await expect(page.getByText('咳嗽')).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: '修改' }).first().click();
    await page.getByPlaceholder('請直接描述過去或平常的症狀（不需要填日期）').fill('咳嗽(更新)');
    await page.getByRole('button', { name: '更新症狀自述' }).click();
    await expect(page.getByText('咳嗽(更新)')).toBeVisible({ timeout: 10000 });

    // Second person switch also needs load-state wait
    await page.locator('nav select').selectOption('person-self');
    await expect(page).toHaveURL(/\/symptoms/);
    await expect(page.getByRole('heading', { name: '歷史症狀' })).toBeVisible({ timeout: 10000 });
    await page.waitForLoadState('load', { timeout: 30000 });
    await expect(page.getByText('頭痛')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('咳嗽')).toHaveCount(0);
  });

  test('document upload -> confirmation -> save', async ({ page }) => {
    await page.goto('/documents');
    await page.setInputFiles('input[type="file"]', {
      name: 'report.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('fake pdf'),
    });
    await page.getByRole('button', { name: '上傳', exact: true }).click();
    await page.getByRole('button', { name: '解析並確認' }).first().click();
    await expect(page).toHaveURL(/documents-confirmation/);
    await expect(page.getByRole('heading', { name: '健檢報告確認' })).toBeVisible();
    await page.getByRole('button', { name: '確認資料' }).click();
    await expect(page).toHaveURL(/documents$/);
    await expect(page.getByText('已確認', { exact: true }).first()).toBeVisible();
  });

  test('profile update + account settings + dashboard actions + health analysis + external metrics + alerts', async ({ page }) => {
    await page.goto('/profile');
    await page.getByPlaceholder('姓名').fill('王小明');
    await page.getByRole('button', { name: '儲存基本資料' }).click();
    await page.getByPlaceholder('電子郵件').fill('new@example.com');
    await page.getByRole('button', { name: '儲存帳號設定' }).click();

    await page.goto('/health-analysis');
    await expect(page.getByRole('heading', { name: '健康分析' })).toBeVisible();
    await expect(page.getByText('資料不足：請補充症狀、健檢或身體指數後再分析。')).toBeVisible();

    await page.goto('/external-metrics');
    await page.getByRole('button', { name: '手動同步' }).click();
    await expect(page.getByText('external_api')).toBeVisible();
    await expect(page.locator('pre').filter({ hasText: '5000' }).first()).toBeVisible();

    await page.goto('/health-alerts');
    await page.getByRole('button', { name: '執行風險監控' }).click();
    await expect(page.getByText('血壓偏高')).toBeVisible();

    await page.goto('/platform/dashboard');
    await expect(page.getByRole('heading', { name: '儀表板' })).toBeVisible();
    await expect(page.getByText('健康分數').first()).toBeVisible();
    await page.goto('/platform/notifications');
    await expect(page).toHaveURL(/notifications/);
    await page.getByRole('button', { name: '加入追蹤' }).first().click();
  });
});
