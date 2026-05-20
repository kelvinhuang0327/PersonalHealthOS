import { evaluateImpactStatus, evaluateReminderStatus, type HealthAction } from './actions';

// ── Recommendation Trust types (P1 Recommendation Trust Layer) ───────────────
export type RecommendationTrust = {
  confidence: number
  level: 'low' | 'medium' | 'high'
  reasons: string[]
  limitations: string[]
  verifiedByOutcome: boolean
  nextCheckInSuggestion: string
}

export type EvidenceSource = {
  type: string
  id: string | null
  summary: string
}

// ── Outcome Feedback types (P1 Outcome Feedback Loop) ──────────────────────────
export type OutcomeFeedbackItem = {
  action_id: string
  action_title: string
  status: 'completed' | 'tracking'
  completed_at: string | null
  expected_health_impact: string
  outcome_status: 'improved' | 'unchanged' | 'deteriorated' | 'insufficient_data' | 'tracking'
  actual_metric_change: {
    metric_type: string
    before_value: number | null
    after_value: number | null
    delta: number | null
    direction: 'improved' | 'worsened' | 'stable' | null
  } | null
  adherence_status: 'completed' | 'tracking'
  evidence_sources: string[]
  confidence: number
  explanation: string
  next_check_in: string | null
}

export type OutcomeFeedback = {
  person_id: string
  generated_at: string
  window_days: number
  outcomes: OutcomeFeedbackItem[]
  summary: {
    improved_count: number
    unchanged_count: number
    deteriorated_count: number
    insufficient_data_count: number
    tracking_count: number
    total_count: number
  }
}

// ── Device Signal types (P2 Device Signal Intelligence) ─────────────────────
export type DeviceSignal = {
  signal_type: string
  severity: 'low' | 'medium' | 'high'
  metric_type: string
  current_value: number
  baseline_value: number | null
  trend: string | null
  why_detected: string
  suggested_action: string | null
  confidence: number
  freshness: 'fresh' | 'stale' | 'unknown'
}

export type EscalationDecision = {
  escalationLevel: 'none' | 'watch' | 'warning' | 'urgent'
  reasons: string[]
  confidence: number
  recommendedAction: string | null
  requiresFollowUp: boolean
}

// ── Symptom Intelligence types (P3) ──────────────────────────────────────────
export type SymptomPattern = {
  patternType:
    | 'recurring_symptom'
    | 'worsening_symptom'
    | 'symptom_with_device_signal'
    | 'symptom_with_lab_risk'
    | 'unresolved_high_severity_symptom'
  severity: 'low' | 'medium' | 'high'
  symptomType: string
  label: string
  whyDetected: string
  confidence: number
  suggestedAction: string | null
  evidenceSources: EvidenceSource[]
  relatedDeviceSignals: string[]
  relatedLabItems: string[]
}

// ── Lab Intelligence types (P4 Report-to-Action Bridge) ──────────────────────
export type LabEvidenceSource = {
  type: 'lab_report_item' | 'risk_alert'
  id: string | null
  reportId?: string | null
  summary: string
  recency?: string | null
}

export type LabAbnormality = {
  abnormalityType:
    | 'lipid_abnormality'
    | 'glucose_abnormality'
    | 'blood_pressure'
    | 'kidney_function'
    | 'liver_function'
    | 'fatty_liver_marker'
    | 'thyroid_function'
    | 'anemia_marker'
    | 'uric_acid'
    | 'kidney_stone_related_marker'
    | 'inflammation_marker'
    | 'lab_abnormality'
  severity: 'low' | 'medium' | 'high'
  labItemName: string
  currentValue: number | string | null
  referenceRange: string | null
  reportId: string | null
  detectedAt: string | null
  whyDetected: string
  suggestedAction: string
  confidence: number
  evidenceSources: LabEvidenceSource[]
  recurrenceCount: number
  rule_id: string
}

// ── Daily Health Summary type (Task 5 — P1) ──────────────────────────────────
export type DailyHealthSummary = {
  person_id: string
  generated_at: string
  topRisk: string
  biggestChange: string
  todayAction: string
  whyNow: string
  confidence: number
  missingData?: string[]
  encouragement?: string
  escalation?: EscalationDecision
}
// ── Notification Intelligence types (P5 Foundation) ─────────────────────
export type NotificationCandidate = {
  candidate_id: string
  source_type: 'device_escalation' | 'lab_abnormality' | 'symptom_pattern' | 'risk_alert' | 'recommendation'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  title: string
  message: string
  why_now: string
  suggested_action: string | null
  confidence: number
  evidence_sources: Array<{ type: string; id: string | null; summary: string }>
  cooldown_key: string
  suppress_reason: string | null
}

export type IntelligentNotifications = {
  person_id: string
  generated_at: string
  items: NotificationCandidate[]
  suppressed: NotificationCandidate[]
  total_candidates: number
}

const API_BASE_URL = normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1');

function normalizeApiBaseUrl(url: string) {
  const trimmed = url.replace(/\/$/, '');
  if (trimmed.endsWith('/api/v1')) return trimmed;
  return `${trimmed}/api/v1`;
}

function getToken() {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('token') || '';
}

function getPersonId() {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('person_id') || '';
}

function getActionsStorageKey(personId: string) {
  return `health_actions_${personId || 'default'}`;
}

function readActions(personId: string): HealthAction[] {
  if (typeof window === 'undefined') return [];
  const raw = localStorage.getItem(getActionsStorageKey(personId));
  if (!raw) return [];
  try {
    const actions = JSON.parse(raw) as HealthAction[];
    return actions.map((a) => ({
      ...a,
      streak: a.streak || 0,
      impact_status: a.impact_status || 'no_change',
      reminder_status: a.reminder_status || 'none',
    }));
  } catch {
    return [];
  }
}

function writeActions(personId: string, actions: HealthAction[]) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(getActionsStorageKey(personId), JSON.stringify(actions));
}

async function request(path: string, options: RequestInit = {}, auth = true) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const personId = getPersonId();
  const finalPath = auth && personId ? `${path}${path.includes('?') ? '&' : '?'}person_id=${personId}` : path;
  const res = await fetch(`${API_BASE_URL}${finalPath}`, { ...options, headers });
  if (!res.ok) {
    if (typeof window !== 'undefined' && (res.status === 500 || res.status === 503)) {
      window.dispatchEvent(
        new CustomEvent('api-error-toast', {
          detail: { message: '服務暫時無法連線，部分資料可能不是最新' },
        }),
      );
    }
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return res.json();
  }
  return res.text();
}

export const api = {
  register: (email: string, password: string) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }, false),
  login: (email: string, password: string) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }, false),
  getProfile: () => request('/profile/me'),
  updateProfile: (payload: Record<string, unknown>) => request('/profile/me', { method: 'PUT', body: JSON.stringify(payload) }),
  getAccount: () => request('/profile/account'),
  updateAccount: (payload: Record<string, unknown>) => request('/profile/account', { method: 'PUT', body: JSON.stringify(payload) }),
  changePassword: (payload: Record<string, unknown>) => request('/auth/change-password', { method: 'POST', body: JSON.stringify(payload) }),
  listPersons: () => request('/persons'),
  createPerson: (payload: Record<string, unknown>) => request('/persons', { method: 'POST', body: JSON.stringify(payload) }),
  updatePerson: (id: string, payload: Record<string, unknown>) => request(`/persons/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deletePerson: (id: string) => request(`/persons/${id}`, { method: 'DELETE' }),
  createMetric: (payload: Record<string, unknown>) => request('/metrics', { method: 'POST', body: JSON.stringify(payload) }),
  listMetrics: () => request('/metrics'),
  getLatestMetric: () => request('/metrics/latest'),
  createSymptom: (payload: Record<string, unknown>) => request('/symptoms', { method: 'POST', body: JSON.stringify(payload) }),
  updateSymptom: (id: string, payload: Record<string, unknown>) => request(`/symptoms/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  listSymptoms: () => request('/symptoms'),
  listDocuments: () => request('/documents'),
  createDocument: (category: string, file: File) => uploadDocument(category, file),
  parseDocument: (id: string) => request(`/documents/${id}/parse`, { method: 'POST' }),
  getDocumentParsedItems: (id: string) => request(`/documents/${id}/parsed-items`),
  getLabHistory: (metric?: string, limit = 5) =>
    request(`/documents/lab-history?${metric ? `metric=${encodeURIComponent(metric)}&` : ''}limit=${limit}`),
  updateParsedItem: (docId: string, itemId: string, payload: Record<string, unknown>) =>
    request(`/documents/${docId}/parsed-items/${itemId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  confirmDocumentPost: (id: string) => request(`/documents/${id}/confirm`, { method: 'POST' }),
  confirmDocument: (id: string, payload: Record<string, unknown>) =>
    request(`/documents/${id}/confirm`, { method: 'PUT', body: JSON.stringify(payload) }),
  listRiskAlerts: () => request('/risk-alerts'),
  getRiskAlertUnreadCount: () => request('/risk-alerts/unread-count'),
  dismissRiskAlert: (id: string) => request(`/risk-alerts/${id}/dismiss`, { method: 'POST' }),
  runRiskMonitor: () => request('/risk-alerts/monitor', { method: 'POST' }),
  getDashboard: () => request('/dashboard'),
  dashboardOverview: () => request('/dashboard/overview'),
  dashboardTrends: (days = 30) => request(`/dashboard/trends?days=${days}`),
  getTimeline: (days = 180, limit = 200) => request(`/timeline?days=${days}&limit=${limit}`),
  getTrendAnalysis: (days = 90) => request(`/analytics/trends?days=${days}`),
  getHealthAnalysis: () => request('/analytics/health-analysis'),
  syncExternalMetrics: () => request('/external-metrics/sync', { method: 'POST' }),
  listExternalMetrics: (days = 30) => request(`/external-metrics/history?days=${days}`),
  getExternalMetrics: (days = 30) => request(`/external-metrics/history?days=${days}`),
  getExternalMetricTrends: (metric = 'steps', days = 30) => request(`/external-metrics/trends?metric=${metric}&days=${days}`),
  calculateHealthScore: (days = 30) =>
    request('/health-score/calculate', { method: 'POST', body: JSON.stringify({ days }) }),
  getLatestHealthScore: () => request('/health-score/latest'),
  getHealthScoreHistory: (limit = 20) => request(`/health-score/history?limit=${limit}`),
  aiHealthCheckInterpretation: (payload: Record<string, unknown>) =>
    request('/ai-modules/health-check-interpretation', { method: 'POST', body: JSON.stringify(payload) }),
  aiSymptomAnalysis: (payload: Record<string, unknown>) =>
    request('/ai-modules/symptom-analysis', { method: 'POST', body: JSON.stringify(payload) }),
  aiRiskPrediction: (payload: Record<string, unknown>) =>
    request('/ai-modules/risk-prediction', { method: 'POST', body: JSON.stringify(payload) }),
  aiEvaluateModule: (moduleName: string, payload: Record<string, unknown>) =>
    request(`/ai-modules/evaluate/${moduleName}`, { method: 'POST', body: JSON.stringify(payload) }),
  generateAISummary: () => request('/ai-summary/generate', { method: 'POST', body: JSON.stringify({}) }),
  listAISummary: () => request('/ai-summary'),
  listInsights: () => request('/insights'),
  generateInsights: () => request('/insights/generate', { method: 'POST' }),
  dismissInsight: (id: string) => request(`/insights/${id}/dismiss`, { method: 'POST' }),
  generateReport: (payload: Record<string, unknown>) =>
    request('/reports/generate', { method: 'POST', body: JSON.stringify(payload) }),
  getReportStatus: (reportId: string) => request(`/reports/${reportId}`),

  // ── Actions: API-backed (backend as source of truth) ──────────────────────
    getActions: (personId?: string, dueWithinDays?: number) =>
      request(`/actions${dueWithinDays !== undefined ? `?due_within_days=${dueWithinDays}` : ''}`),
  getPrioritizedActions: () => request('/actions/prioritized'),
  createAction: (payload: Record<string, unknown>) =>
    request('/actions', { method: 'POST', body: JSON.stringify(payload) }),
  updateAction: (id: string, payload: Record<string, unknown>) =>
    request(`/actions/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  completeAction: (id: string) =>
    request(`/actions/${id}/complete`, { method: 'POST' }),
  deleteAction: (id: string) =>
    request(`/actions/${id}`, { method: 'DELETE' }),
  getActionOutcomes: (id: string) => request(`/actions/${id}/outcomes`),

  // ── Health Assistant (Tasks 1, 2, 4) ─────────────────────────────────────
  getEvidenceBundle: () => request('/health-assistant/evidence-bundle'),
  getRecommendations: () => request('/health-assistant/recommendations'),
  getDeviceSignals: () => request('/health-assistant/device-signals'),
  getProductSignals: (days = 30) =>
    request(`/health-assistant/product-signals?days=${days}`),
  getDailySummary: () => request('/health-assistant/daily-summary'),
  getOutcomeFeedback: (windowDays: 7 | 14 | 30 = 7) =>
    request(`/health-assistant/outcome-feedback?window_days=${windowDays}`),
  getIntelligentNotifications: (): Promise<IntelligentNotifications> =>
    request('/health-assistant/notifications/intelligent'),
};

export async function uploadDocument(category: string, file: File) {
  const token = getToken();
  const personId = getPersonId();
  const formData = new FormData();
  formData.append('category', category);
  formData.append('file', file);

  const path = personId ? `/documents/upload?person_id=${personId}` : '/documents/upload';
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Upload failed');
  }
  return res.json();
}

export async function getLatestMetricByPerson(personId: string) {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}/metrics/latest?person_id=${personId}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) return null;
  const contentType = res.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) return null;
  return res.json();
}
