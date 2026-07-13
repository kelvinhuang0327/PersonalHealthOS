import { expect, test, Page } from '@playwright/test';

// Standard mock entities
const MOCK_ORC_SUMMARY = {
  project_name: 'PersonalHealthOS',
  project_slug: 'personal-health-os',
  today: '20260713',
  scheduler_enabled: true,
  scheduler: {
    enabled: true,
    loop_running: true,
    planner_interval_minutes: 60,
    worker_interval_minutes: 60,
    next_planner_run_at: '2026-07-13T12:00:00Z',
    next_worker_run_at: '2026-07-13T12:00:00Z',
    planner_provider: 'codex',
    worker_provider: 'codex',
  },
  task_counts: {},
  total_today: 0,
  total_running: 0,
  total_completed: 0,
  worker_busy: false,
  worker_pid: null,
  worker_task_id: null,
  worker_state: 'idle',
  planner_provider: 'codex',
  worker_provider: 'codex',
  combo_label: 'codex / codex',
  llm_control: {
    mode: 'safe-run',
    scheduler_enabled: true,
    effective_background_run_allowed: true,
    safe_run: true,
    hard_off: false,
    last_decision_at: null,
    last_source: null,
    last_decision_code: null,
    last_allowed: true,
    last_blocked_at: null,
    blocked_count: 0,
    last_call_at: null,
    call_count: 0,
    last_provider: null,
    last_model: null,
    last_call_source: null,
  },
  copilot_daemon_running: false,
  copilot_daemon_pid: null,
  copilot_daemon_status: '未啟動',
  copilot_daemon_task_id: null,
  next_planner_tick_estimate: null,
  next_worker_tick_estimate: null,
  latest_task: null,
};

const MOCK_ORC_DASHBOARD_VALID = {
  scheduler_active: true,
  today_total: 0,
  today_completed: 0,
  today_running: 0,
  today_failed: 0,
  today_replan: 0,
  latest_task: null,
  top_categories: [
    { category: 'behavior_loop_optimization', label: '行為改變循環', completed_count: 1 }
  ],
  recent_completed: [
    {
      id: 1,
      title: 'Optimize daily habit loops',
      category: 'behavior_loop_optimization',
      category_label: '行為改變循環',
      gate_verdict: 'PASS',
      finished_at: '2026-07-13T10:00:00Z',
    }
  ],
};

const MOCK_PROVIDERS = {
  planner_provider: 'codex',
  planner_provider_label: 'Codex Planner',
  worker_provider: 'codex',
  worker_provider_label: 'Codex Worker',
  combo_label: 'codex / codex',
  planner_options: [{ value: 'codex', label: 'Codex Planner' }],
  worker_options: [{ value: 'codex', label: 'Codex Worker' }],
  worker_copilot_model: null,
  worker_copilot_model_presets: [],
};

const MOCK_TASKS = {
  items: [],
  count: 0,
  total: 0,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const MOCK_RUNS = {
  runs: [],
  items: [],
  limit: 10,
};

const MOCK_TASK_POOL = {
  categories: ['behavior_loop_optimization'],
  pool: [
    {
      category: 'behavior_loop_optimization',
      title: 'Optimize daily habit loops',
      duplicate_signature: 'sig',
      focus_keys: ['habit'],
      is_active: false,
    }
  ],
  active_count: 0,
  available_count: 1,
};

// CTO Review Mock Entities
const MOCK_CTO_SUMMARY = {
  frequency_mode: 'daily',
  scheduler_enabled: true,
  planner_provider: 'codex',
  planner_model: null,
  latest_run_at: null,
  next_run_at: null,
  next_run_estimate: null,
  pending_count: 0,
  approved_count: 0,
  merged_count: 0,
  rejected_count: 0,
  deferred_count: 0,
  superseded_count: 0,
  duplicate_count: 0,
  total_reviews: 0,
  health_score: null,
  verdict: null,
  summary: null,
  latest_run: null,
};

const MOCK_CTO_RUNS = {
  items: [],
  runs: [],
  count: 0,
};

const MOCK_CTO_PROVIDERS = {
  planner_provider: 'codex',
  planner_provider_label: 'Codex Planner',
  planner_model: null,
  planner_options: [{ value: 'codex', label: 'Codex Planner' }],
  planner_model_presets: [],
};

const MOCK_ADAPTIVE_POLICY = {
  intent_merge_rates: {},
  policy_adjustments: {
    retry_coverage_limit: 10,
    category_priority_boosts: {},
  },
  suggestions: [],
};

const MOCK_EXECUTION_POLICY = {
  mode: 'balanced',
  consecutive_high: 0,
  consecutive_category: null,
  consecutive_category_count: 0,
  recent_selections: [],
  updated_at: '2026-07-13T10:00:00Z',
};

const MOCK_PRIORITIZED_BACKLOG_VALID = {
  items: [],
  by_level: {
    P0: [],
    P1: [],
    P2: [],
    P3: [],
  },
  counts: {
    P0: 0,
    P1: 0,
    P2: 0,
    P3: 0,
  },
  total: 0,
};

async function stubBaseRoutes(page: Page, overrides: {
  dashboardSummary?: any;
  prioritizedBacklog?: any;
} = {}) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'e2e-mock-token');
    localStorage.setItem('person_id', 'person-self');
    localStorage.setItem('onboarding_completed', '1');
  });

  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;

    if (path.endsWith('/persons')) {
      return route.fulfill({ json: [{ id: 'person-self', display_name: '本人', relationship: 'self', is_default: true }] });
    }
    if (path.endsWith('/profile/me')) {
      return route.fulfill({ json: { id: 'person-self', onboarding_completed: true } });
    }

    // Orchestrator
    if (path.endsWith('/orchestrator/summary')) {
      return route.fulfill({ json: MOCK_ORC_SUMMARY });
    }
    if (path.endsWith('/orchestrator/dashboard-summary')) {
      const resp = overrides.dashboardSummary !== undefined ? overrides.dashboardSummary : MOCK_ORC_DASHBOARD_VALID;
      return route.fulfill({ json: resp });
    }
    if (path.endsWith('/orchestrator/providers')) {
      return route.fulfill({ json: MOCK_PROVIDERS });
    }
    if (path.endsWith('/orchestrator/tasks')) {
      return route.fulfill({ json: MOCK_TASKS });
    }
    if (path.endsWith('/orchestrator/runs')) {
      return route.fulfill({ json: MOCK_RUNS });
    }
    if (path.endsWith('/orchestrator/task-pool')) {
      return route.fulfill({ json: MOCK_TASK_POOL });
    }

    // CTO
    if (path.endsWith('/orchestrator/cto/summary')) {
      return route.fulfill({ json: MOCK_CTO_SUMMARY });
    }
    if (path.endsWith('/orchestrator/cto/runs')) {
      return route.fulfill({ json: MOCK_CTO_RUNS });
    }
    if (path.endsWith('/orchestrator/cto/providers')) {
      return route.fulfill({ json: MOCK_CTO_PROVIDERS });
    }
    if (path.endsWith('/orchestrator/cto/adaptive-policy')) {
      return route.fulfill({ json: MOCK_ADAPTIVE_POLICY });
    }
    if (path.endsWith('/orchestrator/cto/backlog/policy')) {
      return route.fulfill({ json: MOCK_EXECUTION_POLICY });
    }
    if (path.endsWith('/orchestrator/cto/backlog/prioritized')) {
      const resp = overrides.prioritizedBacklog !== undefined ? overrides.prioritizedBacklog : MOCK_PRIORITIZED_BACKLOG_VALID;
      return route.fulfill({ json: resp });
    }

    return route.fulfill({ json: {} });
  });
}

test.describe('P210 Cockpit Payload Guardrails - Pre-fix / Post-fix Verification', () => {
  test('Valid Orchestration payload renders correctly without crash', async ({ page }) => {
    await stubBaseRoutes(page);
    await page.goto('/platform/cockpit/orchestration');
    await expect(page.locator('h1').filter({ hasText: 'AI 優化任務中心' })).toBeVisible();
    await expect(page.locator('text=🎯 產品優化視圖')).toBeVisible();
    await expect(page.locator('text=行為改變循環').first()).toBeVisible();
  });

  test('Valid CTO Review payload renders correctly without crash', async ({ page }) => {
    await stubBaseRoutes(page);
    await page.goto('/platform/cockpit/cto-review');
    await expect(page.locator('h1').filter({ hasText: 'CTO 審核系統' })).toBeVisible();
    await expect(page.locator('text=P0 0')).toBeVisible();
  });

  test('Malformed Orchestration (missing top_categories) throws or shows unavailable state', async ({ page }) => {
    await stubBaseRoutes(page, {
      dashboardSummary: {
        ...MOCK_ORC_DASHBOARD_VALID,
        top_categories: undefined,
      }
    });

    let uncaughtError: any = null;
    let consoleErrors: string[] = [];

    page.on('pageerror', (err) => {
      uncaughtError = err;
    });
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('/platform/cockpit/orchestration');
    await page.waitForTimeout(2000);

    console.log('Uncaught Page Errors:', uncaughtError);
    console.log('Console Errors:', consoleErrors);

    if (uncaughtError || consoleErrors.some(e => e.includes('map') || e.includes('undefined'))) {
      const errMsg = uncaughtError?.message || consoleErrors.find(e => e.includes('map') || e.includes('undefined')) || 'Crash detected';
      console.log('Orchestration crash caught successfully:', errMsg);
      expect(errMsg).toMatch(/map|undefined/);
    } else {
      console.log('Orchestration did not crash, checking for fallback message...');
      await expect(page.locator('text=資料暫時無法載入').or(page.locator('text=回傳格式不完整'))).toBeVisible();
    }
  });

  test('Malformed CTO Review (missing by_level) throws or shows unavailable state', async ({ page }) => {
    await stubBaseRoutes(page, {
      prioritizedBacklog: {
        ...MOCK_PRIORITIZED_BACKLOG_VALID,
        by_level: undefined,
      }
    });

    let uncaughtError: any = null;
    let consoleErrors: string[] = [];

    page.on('pageerror', (err) => {
      uncaughtError = err;
    });
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('/platform/cockpit/cto-review');
    await page.waitForTimeout(2000);

    console.log('Uncaught Page Errors:', uncaughtError);
    console.log('Console Errors:', consoleErrors);

    if (uncaughtError || consoleErrors.some(e => e.includes('P0') || e.includes('undefined'))) {
      const errMsg = uncaughtError?.message || consoleErrors.find(e => e.includes('P0') || e.includes('undefined')) || 'Crash detected';
      console.log('CTO Review crash caught successfully:', errMsg);
      expect(errMsg).toMatch(/P0|undefined/);
    } else {
      console.log('CTO Review did not crash, checking for fallback message...');
      await expect(page.locator('text=資料暫時無法載入').or(page.locator('text=回傳格式不完整'))).toBeVisible();
    }
  });
});
