import type { LabAbnormality } from './document-client'
import { apiRequest, jsonBody } from './http-client'

export type RecommendationTrust = {
  confidence: number
  level: string
  reasons: string[]
  limitations: string[]
  verifiedByOutcome: boolean
  nextCheckInSuggestion: string
}

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
  escalationLevel: 'urgent' | 'warning' | 'watch' | 'none'
  reasons: string[]
  confidence: number
  recommendedAction: string | null
  requiresFollowUp: boolean
}

export type SymptomPattern = {
  patternType: string
  severity: 'low' | 'medium' | 'high'
  symptomType: string
  label: string
  whyDetected: string
  confidence: number
  suggestedAction: string | null
  evidenceSources: Array<{ type: string; id?: string | null; summary?: string }>
  relatedDeviceSignals: string[]
  relatedLabItems: string[]
}

export type OutcomeFeedbackStatus =
  | 'improved'
  | 'unchanged'
  | 'deteriorated'
  | 'insufficient_data'
  | 'tracking'
  | 'not_useful'
  | 'not_applicable'
  | 'snoozed'

export type OutcomeFeedbackItem = {
  action_id: string
  action_title: string
  status: 'completed' | 'tracking' | 'not_useful' | 'not_applicable' | 'snoozed'
  completed_at: string | null
  expected_health_impact: string
  outcome_status: OutcomeFeedbackStatus
  actual_metric_change: {
    metric_type: string
    before_value?: number | null
    after_value?: number | null
    delta: number | null
    direction?: string
  } | null
  adherence_status: string
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
    total_count: number
    improved_count: number
    unchanged_count: number
    deteriorated_count: number
    insufficient_data_count: number
    tracking_count: number
    not_useful_count?: number
    not_applicable_count?: number
    snoozed_count?: number
  }
}

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

export type NotificationCandidate = {
  candidate_id: string
  source_type: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  title: string
  message?: string
  why_now: string
  suggested_action?: string | null
  confidence?: number
  evidence_sources?: Array<{ type: string; id?: string | null; summary: string }>
  notification_id?: string | null
  suppress_reason?: string | null
}

export type IntelligentNotifications = {
  person_id: string
  generated_at: string
  items: NotificationCandidate[]
  suppressed: NotificationCandidate[]
  total_candidates: number
}

export type PersonalizationProfile = {
  id: string
  engagement_score: number | null
  response_style: string
  preferred_notification_timing: Record<string, unknown>
  preferred_notification_types: string[]
  ignored_categories: Record<string, number>
  acted_categories: Record<string, number>
  high_response_categories: string[]
  avg_response_delay_minutes: number | null
  last_updated_at: string | null
}

export type EngagementAnalytics = {
  engagementTrend: 'improving' | 'stable' | 'declining'
  avgResponseDelayMinutes: number | null
  bestNotificationWindows: string[]
  ignoredTimeWindows: string[]
  actionCompletionRate: number
  notificationOpenRate: number
}

export type NarrativeMemoryData = {
  periodType: 'daily' | 'weekly' | 'monthly'
  periodStart: string
  periodEnd: string
  summaryText: string
  topThemes: string[]
  improvingItems: string[]
  worseningItems: string[]
  repeatedRisks: string[]
  effectiveActions: string[]
  ignoredItems: string[]
  confidence: number
  limitations: string[]
}

export type CrossPeriodReasoning = {
  overallTrend: 'improving' | 'stable' | 'mixed' | 'worsening'
  longTermRisks: string[]
  sustainedImprovements: string[]
  unstableAreas: string[]
  repeatedIgnoredRisks: string[]
  effectiveLongTermActions: string[]
  carryOverRecommendations: string[]
  confidence: number
  limitations: string[]
}

export type FamilyContextItem = { text: string; source_pool: string }

export type FamilyHealthContext = {
  relatedProfiles: unknown[]
  sharedRisks: string[]
  caregiverAlerts: string[]
  childAttentionItems: string[]
  familyActionSuggestions: string[]
  confidence: number
  limitations: string[]
  childAttentionDetails: FamilyContextItem[]
  caregiverAlertDetails: FamilyContextItem[]
  sharedRiskDetails: FamilyContextItem[]
}

export type FamilyRelationshipRecord = {
  id: string
  owner_user_id: string
  subject_profile_id: string
  related_profile_id: string
  relationship_type: string
  permission_level: string
  related_display_name: string
  created_at: string | null
}

export type FamilyRecommendation = {
  text: string
  target_profile_id: string | null
  audience: 'caregiver' | 'member' | 'family'
  urgency: 'high' | 'medium' | 'low'
  evidence_source: string
  source_type: string
}

export type HealthRecommendationsResponse = {
  person_id: string
  generated_at: string
  recommendations: Array<Record<string, unknown> & { trust?: RecommendationTrust }>
  device_signals: DeviceSignal[]
  device_escalation: EscalationDecision
  symptom_patterns: SymptomPattern[]
  lab_abnormalities: LabAbnormality[]
  lab_not_judged_items: unknown[]
  evidence_bundle_summary: Record<string, number>
  missing_data: string[]
}

export const healthAssistantApi = {
  getEvidenceBundle: () => apiRequest<Record<string, unknown>>('/health-assistant/evidence-bundle', {}, { personScoped: true }),
  getRecommendations: () => apiRequest<HealthRecommendationsResponse>('/health-assistant/recommendations', {}, { personScoped: true }),
  getDeviceSignals: () => apiRequest<{ signals: DeviceSignal[]; person_id: string; generated_at: string; signal_count: number }>('/health-assistant/device-signals', {}, { personScoped: true }),
  getOutcomeFeedback: (windowDays = 7) => apiRequest<OutcomeFeedback>(`/health-assistant/outcome-feedback?window_days=${windowDays}`, {}, { personScoped: true }),
  getDailySummary: () => apiRequest<DailyHealthSummary>('/health-assistant/daily-summary', {}, { personScoped: true }),
  getIntelligentNotifications: () => apiRequest<IntelligentNotifications>('/health-assistant/notifications/intelligent', {}, { personScoped: true }),
  snoozeNotification: (id: string, hours = 24) => apiRequest<Record<string, unknown>>(`/health-assistant/notifications/${encodeURIComponent(id)}/snooze`, { method: 'POST', body: jsonBody({ hours }) }, { personScoped: true }),
  ignoreNotification: (id: string) => apiRequest<Record<string, unknown>>(`/health-assistant/notifications/${encodeURIComponent(id)}/ignore`, { method: 'POST' }, { personScoped: true }),
  getPersonalizationProfile: () => apiRequest<PersonalizationProfile>('/health-assistant/personalization-profile', {}, { personScoped: true }),
  getEngagementAnalytics: (days = 30) => apiRequest<EngagementAnalytics>(`/health-assistant/engagement-analytics?days=${days}`, {}, { personScoped: true }),
  syncPersonalizationProfile: (days = 30) => apiRequest<PersonalizationProfile>(`/health-assistant/personalization-profile/sync?days=${days}`, { method: 'POST' }, { personScoped: true }),
  getNarrativeMemory: (periodType: NarrativeMemoryData['periodType'] = 'weekly') => apiRequest<{ found: boolean; memory: NarrativeMemoryData | null }>(`/health-assistant/narrative-memory?period_type=${periodType}`, {}, { personScoped: true }),
  generateNarrativeMemory: (periodType: NarrativeMemoryData['periodType'] = 'weekly') => apiRequest<{ generated: boolean; memory: NarrativeMemoryData }>(`/health-assistant/narrative-memory/generate?period_type=${periodType}`, { method: 'POST' }, { personScoped: true }),
  getCrossPeriodReasoning: () => apiRequest<{ reasoning: CrossPeriodReasoning }>('/health-assistant/narrative-memory/cross-period', {}, { personScoped: true }),
  getFamilyHealthContext: () => apiRequest<{ person_id: string; context: FamilyHealthContext }>('/health-assistant/family-health-context', {}, { personScoped: true }),
  getFamilyRelationships: () => apiRequest<{ person_id: string; relationships: FamilyRelationshipRecord[]; total: number }>('/health-assistant/family-relationships', {}, { personScoped: true }),
  getFamilyRecommendations: () => apiRequest<{ person_id: string; recommendations: FamilyRecommendation[]; total: number }>('/health-assistant/family-recommendations', {}, { personScoped: true }),
}
