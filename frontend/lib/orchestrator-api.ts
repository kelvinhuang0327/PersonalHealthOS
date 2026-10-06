/**
 * orchestrator-api.ts — Typed client for all orchestrator API endpoints.
 * All paths resolve under the shared API_BASE_URL (/api/v1/orchestrator/...).
 */

const API_BASE_URL = (() => {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
  return raw.replace(/\/$/, '').endsWith('/api/v1')
    ? raw.replace(/\/$/, '')
    : `${raw.replace(/\/$/, '')}/api/v1`;
})();

// ── Types ─────────────────────────────────────────────────────────────────────

export type TaskStatus =
  | 'QUEUED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'FAILED_RATE_LIMIT'
  | 'REPLAN_REQUIRED'
  | 'CANCELLED';

export type GateVerdict =
  | 'PASS'
  | 'INVALID_DELIVERY'
  | 'FAILED_ACCEPTANCE'
  | 'POLICY_VIOLATION'
  | 'RATE_LIMIT'
  | 'WORKER_RUNTIME_FAILED';

export type CtoDecision = 'PASS' | 'NEEDS_REPLAN' | 'DEFERRED' | 'CLOSED';
export type CtoVerdict = 'GO' | 'CAUTION' | 'STOP';
export type BacklogLevel = 'P0' | 'P1' | 'P2' | 'P3';
export type PolicyMode = 'balanced' | 'strict_priority' | 'fairness';
export type RunIntent = 'retry' | 'compare' | 'override';

export interface OrcTask {
  id: number;
  task_uid: string;
  title: string;
  objective: string;
  status: TaskStatus;
  gate_verdict: GateVerdict | null;
  gate_reason: string;
  planner_provider: string;
  worker_provider: string;
  task_dir: string;
  latest_progress_summary: string | null;
  last_output_at: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface OrcRun {
  id: number;
  runner: string;
  tick_at: string;
  outcome: string;
  request_id: string | null;
  task_id: number | null;
  message: string;
  run_type: string;
  started_at: string;
  finished_at: string | null;
}

export interface SchedulerState {
  enabled: boolean;
  loop_running?: boolean;
  planner_interval_minutes: number;
  worker_interval_minutes: number;
  next_planner_run_at: string | null;
  next_worker_run_at: string | null;
  planner_provider: string;
  worker_provider: string;
}

export interface LlmControlState {
  mode: 'safe-run' | 'hard-off';
  scheduler_enabled: boolean;
  effective_background_run_allowed: boolean;
  safe_run: boolean;
  hard_off: boolean;
  last_decision_at: string | null;
  last_source: string | null;
  last_decision_code: string | null;
  last_allowed: boolean;
  last_blocked_at: string | null;
  blocked_count: number;
  last_call_at: string | null;
  call_count: number;
  last_provider: string | null;
  last_model: string | null;
  last_call_source: string | null;
}

export interface OrcSummary {
  project_name: string;
  project_slug: string;
  today: string;
  scheduler: SchedulerState;
  scheduler_enabled: boolean;
  task_counts: Record<string, number>;
  total_today: number;
  total_running: number;
  total_completed: number;
  worker_busy: boolean;
  worker_pid: number | null;
  worker_task_id: number | null;
  worker_state: string;
  planner_provider: string;
  worker_provider: string;
  combo_label: string;
  llm_control: LlmControlState;
  copilot_daemon_running: boolean;
  copilot_daemon_pid: number | null;
  copilot_daemon_status: string;
  copilot_daemon_task_id: number | null;
  next_planner_tick_estimate: string | null;
  next_worker_tick_estimate: string | null;
  latest_task: OrcTask | null;
}

export interface ProvidersResponse {
  planner_provider: string;
  planner_provider_label: string;
  worker_provider: string;
  worker_provider_label: string;
  combo_label: string;
  planner_options: { value: string; label: string; available?: boolean; reason?: string }[];
  worker_options: { value: string; label: string; available?: boolean; reason?: string }[];
  worker_copilot_model: string | null;
  worker_copilot_model_presets: { value: string; label: string }[];
}

export interface TasksResponse {
  items: OrcTask[];
  tasks?: OrcTask[];
  count: number;
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface RunsResponse {
  runs: OrcRun[];
  items: OrcRun[];
  limit: number;
}

export interface RunStatusResponse {
  status: string;
  run: OrcRun | null;
  final: boolean;
}

export interface RunNowResponse {
  ok?: boolean;
  runner?: string;
  pid?: number;
  mode?: string;
  status: string;
  request_id: string;
  triggered_at: string;
  role?: string;
}

export interface CtoSummary {
  frequency_mode: string;
  scheduler_enabled: boolean;
  planner_provider: string;
  planner_model: string | null;
  latest_run_at: string | null;
  next_run_at: string | null;
  next_run_estimate: string | null;
  pending_count: number;
  approved_count: number;
  merged_count: number;
  rejected_count: number;
  deferred_count: number;
  superseded_count: number;
  duplicate_count: number;
  total_reviews: number;
  health_score: number | null;
  verdict: CtoVerdict | null;
  summary: string | null;
  latest_run: CtoReviewRun | null;
}

export interface CtoReviewRun {
  id: number;
  run_id: string;
  frequency_mode: string;
  is_manual: boolean;
  is_force_run: boolean;
  run_intent: RunIntent | null;
  parent_run_id: string | null;
  dedupe_key: string | null;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  checked_from: string | null;
  checked_until: string | null;
  candidate_count: number;
  pass_count: number;
  approved_count: number;
  merged_count: number;
  replan_count: number;
  rejected_count: number;
  deferred_count: number;
  superseded_count: number;
  duplicate_count: number;
  health_score: number | null;
  verdict: CtoVerdict | null;
  summary: string | null;
}

export interface TaskReview {
  id: number;
  task_id: number;
  task_uid: string;
  task_title?: string;
  cto_run_id: string;
  decision: CtoDecision;
  severity: string;
  impact_score: number;
  urgency: string;
  category: string;
  reason: string;
  suggested_action: string;
  create_followup_task: boolean;
  changed_files: string[];
  created_at: string;
}

export interface CtoRunDetail {
  run: CtoReviewRun;
  reviews: TaskReview[];
  intelligence: CtoIntelligence;
}

export interface CtoIntelligence {
  health_score?: number;
  verdict?: CtoVerdict;
  regime?: string;
  top_risks?: TopRisk[];
  top_actions?: TopAction[];
  roadmap?: string[];
  summary?: string;
}

export interface TopRisk {
  task_id: number;
  severity: string;
  impact: number;
  urgency: string;
  description: string;
  category: string;
}

export interface TopAction {
  priority: string;
  action: string;
  expected_benefit: string;
  create_task: boolean;
}

export interface BacklogItem {
  id: number;
  finding_id: string;
  cto_run_id: string;
  task_id: number | null;
  category: string;
  severity: string;
  impact_score: number;
  urgency: string;
  suggested_action: string;
  status: string;
  priority_score: number;
  priority_level: BacklogLevel;
  selection_count: number;
  aging_bonus: number;
  created_at: string;
  updated_at: string;
}

export interface PrioritizedBacklog {
  items: BacklogItem[];
  by_level: Record<BacklogLevel, BacklogItem[]>;
  counts: Record<BacklogLevel, number>;
  total: number;
}

export interface ExecutionPolicy {
  mode: PolicyMode;
  consecutive_high: number;
  consecutive_category: string | null;
  consecutive_category_count: number;
  recent_selections: unknown[];
  updated_at: string;
}

export interface AdaptivePolicy {
  intent_merge_rates: Record<string, number>;
  policy_adjustments: {
    retry_coverage_limit: number;
    category_priority_boosts: Record<string, number>;
  };
  suggestions: unknown[];
}

export interface CtoProviders {
  planner_provider: string;
  planner_provider_label: string;
  planner_model: string | null;
  planner_options: { value: string; label: string }[];
  planner_model_presets: string[];
}

export interface OrcDashboardSummary {
  scheduler_active: boolean;
  today_total: number;
  today_completed: number;
  today_running: number;
  today_failed: number;
  today_replan: number;
  latest_task: {
    id: number;
    title: string;
    category: string;
    category_label: string;
    status: string;
    gate_verdict: string | null;
  } | null;
  top_categories: { category: string; label: string; completed_count: number }[];
  recent_completed: {
    id: number;
    title: string;
    category: string;
    category_label: string;
    gate_verdict: string | null;
    finished_at: string | null;
  }[];
}

// ── Fetch helper ──────────────────────────────────────────────────────────────

function getAuthToken(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('token') || '';
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const authHeader: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...authHeader, ...init.headers },
    ...init,
  });
  if (!res.ok) {
    if (res.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('token');
      window.location.href = '/platform/login';
      throw new Error('Unauthenticated');
    }
    const text = await res.text().catch(() => res.statusText);
    const err = Object.assign(new Error(text), { status: res.status });
    throw err;
  }
  return res.json() as Promise<T>;
}

function get<T>(path: string) {
  return request<T>(path);
}

function post<T>(path: string, body?: unknown) {
  return request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });
}

// ── Orchestrator (base) ───────────────────────────────────────────────────────

export const orcApi = {
  getSummary: () => get<OrcSummary>('/orchestrator/summary'),

  getProviders: () => get<ProvidersResponse>('/orchestrator/providers'),

  setProviders: (body: { planner_provider?: string; worker_provider?: string; worker_copilot_model?: string }) =>
    post<ProvidersResponse>('/orchestrator/providers', body),

  getTasks: (params: {
    page?: number;
    page_size?: number;
    status?: string;
    date?: string;
  } = {}) => {
    const q = new URLSearchParams();
    if (params.page) q.set('page', String(params.page));
    if (params.page_size) q.set('page_size', String(params.page_size));
    if (params.status) q.set('status', params.status);
    if (params.date) q.set('date', params.date);
    const qs = q.toString();
    return get<TasksResponse>(`/orchestrator/tasks${qs ? `?${qs}` : ''}`);
  },

  getTaskDetail: (id: number) =>
    get<{ task: OrcTask; prompt_markdown: string | null; completed_markdown: string | null; contract_json: unknown; result_json: unknown; worker_log_tail: string[] }>(`/orchestrator/tasks/${id}`),

  getRuns: (params: { limit?: number; runner?: string; since?: string; request_id?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.limit) q.set('limit', String(params.limit));
    if (params.runner) q.set('runner', params.runner);
    if (params.since) q.set('since', params.since);
    if (params.request_id) q.set('request_id', params.request_id);
    const qs = q.toString();
    return get<RunsResponse>(`/orchestrator/runs${qs ? `?${qs}` : ''}`);
  },

  getRunStatus: (requestId: string) =>
    get<RunStatusResponse>(`/orchestrator/run-status?request_id=${encodeURIComponent(requestId)}`),

  runNow: (runner: 'planner' | 'worker', opts: { simulate_invalid_delivery?: boolean } = {}) =>
    post<RunNowResponse>('/orchestrator/run-now', { runner, ...opts }),

  setScheduler: (enabled: boolean, interval_minutes?: number) =>
    post<{ scheduler: SchedulerState; enabled: boolean }>('/orchestrator/scheduler', {
      enabled,
      interval_minutes,
    }),

  getLlmControl: () => get<LlmControlState>('/orchestrator/llm-control'),

  setLlmControl: (mode: 'safe-run' | 'hard-off') =>
    post<LlmControlState>('/orchestrator/llm-control', { mode }),

  getTaskPool: () =>
    get<{
      categories: string[];
      pool: { category: string; title: string; duplicate_signature: string; focus_keys: string[]; is_active: boolean }[];
      active_count: number;
      available_count: number;
    }>('/orchestrator/task-pool'),

  getPlannerCandidates: (limit = 5) =>
    get<{ items: OrcRun[] }>(`/orchestrator/planner-candidates?limit=${limit}`),

  getDashboardSummary: () =>
    get<OrcDashboardSummary>('/orchestrator/dashboard-summary'),

  getBacklog: () =>
    get<{ content: string; path: string }>('/orchestrator/backlog'),
};

// ── CTO ───────────────────────────────────────────────────────────────────────

export const ctoApi = {
  getSummary: () => get<CtoSummary>('/orchestrator/cto/summary'),

  getScheduler: () =>
    get<{ enabled: boolean; planner_provider: string; planner_provider_label: string; planner_model: string | null; planner_options: { value: string; label: string }[] }>('/orchestrator/cto/scheduler'),

  getPending: (params: { limit?: number; offset?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.limit) q.set('limit', String(params.limit));
    if (params.offset) q.set('offset', String(params.offset));
    const qs = q.toString();
    return get<{ items: TaskReview[] }>(`/orchestrator/cto/pending${qs ? `?${qs}` : ''}`);
  },

  getRuns: (params: { limit?: number; offset?: number; date?: string; status?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.limit) q.set('limit', String(params.limit));
    if (params.offset) q.set('offset', String(params.offset));
    if (params.date) q.set('date', params.date);
    if (params.status) q.set('status', params.status);
    const qs = q.toString();
    return get<{ items: CtoReviewRun[]; runs?: CtoReviewRun[]; count: number }>(`/orchestrator/cto/runs${qs ? `?${qs}` : ''}`);
  },

  getRunDetail: (runId: string) =>
    get<CtoRunDetail>(`/orchestrator/cto/runs/${runId}`),

  getReport: (runId: string) =>
    get<{ markdown: string | null; json: unknown }>(`/orchestrator/cto/reports/${runId}`),

  getBacklog: (params: { status?: string; cto_run_id?: string; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.status) q.set('status', params.status);
    if (params.cto_run_id) q.set('cto_run_id', params.cto_run_id);
    if (params.limit) q.set('limit', String(params.limit));
    const qs = q.toString();
    return get<{ items: BacklogItem[] }>(`/orchestrator/cto/backlog${qs ? `?${qs}` : ''}`);
  },

  getPrioritizedBacklog: () =>
    get<PrioritizedBacklog>('/orchestrator/cto/backlog/prioritized'),

  addBacklogItem: (body: {
    cto_run_id: string;
    task_id?: number;
    category?: string;
    severity?: string;
    impact_score?: number;
    urgency?: string;
    suggested_action?: string;
    finding_id?: string;
  }) => post<{ item: BacklogItem; finding_id: string }>('/orchestrator/cto/backlog', body),

  batchAddBacklog: (body: { cto_run_id: string; min_severity?: string; min_impact?: number }) =>
    post<{ added: number; cto_run_id: string }>('/orchestrator/cto/backlog/batch', body),

  rescoreBacklog: () => post<{ updated: number }>('/orchestrator/cto/backlog/rescore'),

  applyAging: () => post<{ updated: number }>('/orchestrator/cto/backlog/aging'),

  getBacklogPolicy: () => get<ExecutionPolicy>('/orchestrator/cto/backlog/policy'),

  setBacklogPolicy: (mode: PolicyMode) =>
    post<ExecutionPolicy>('/orchestrator/cto/backlog/policy', { mode }),

  getAdaptivePolicy: () => get<AdaptivePolicy>('/orchestrator/cto/adaptive-policy'),

  refreshAdaptivePolicy: () => post<AdaptivePolicy>('/orchestrator/cto/adaptive-policy/refresh'),

  getProviders: () => get<CtoProviders>('/orchestrator/cto/providers'),

  setProviders: (body: { planner_provider?: string; planner_model?: string }) =>
    post<CtoProviders>('/orchestrator/cto/providers', body),

  setScheduler: (enabled: boolean) =>
    post<{ enabled: boolean }>('/orchestrator/cto/scheduler', { enabled }),

  runNow: (opts: { force?: boolean; run_intent?: RunIntent; parent_run_id?: string } = {}) =>
    post<{ status: string; request_id: string; triggered_at: string }>('/orchestrator/cto/run-now', opts),

  getRunStatus: (requestId: string) =>
    get<RunStatusResponse>(`/orchestrator/cto/run-status?request_id=${encodeURIComponent(requestId)}`),
};
