import type { HealthAction } from './actions'
import type { RecommendationTrust } from './api'
import { getTopDecisions, type ClinicalWeightLevel, type DecisionCandidate, type DecisionFactorInputs, type ScoredDecisionItem } from './decision-scoring'
import { isResurfacedToday, isSnoozeActive, type NotificationSnoozeRecord } from './notification-snooze'

// ---------------------------------------------------------------------------
// Backend contract: UnifiedDecisionItem
// This type mirrors backend app/schemas/decision.py UnifiedDecisionItem.
// When the dashboard API returns `decision_items`, the frontend uses them
// directly instead of re-computing priority locally.
// ---------------------------------------------------------------------------
export type UnifiedDecisionItem = {
  id: string
  source_type: string
  source_id: string
  title: string
  description?: string
  priority: 'high' | 'medium' | 'low'
  why_now: string[]
  next_action: string
  category: string
  status?: string | null
  due_date?: string | null
  confidence: number
  evidence_level: string
  guideline_source?: string | null
  related_metric_types: string[]
  outcome_hint?: string | null
  feedback_state: string
  score: number
  /** Backend trust score — present when data comes from health-assistant/recommendations. */
  trust?: RecommendationTrust
}

/** Map a backend UnifiedDecisionItem → frontend ScoredDecisionItem. */
function fromBackendDecisionItem(item: UnifiedDecisionItem): ScoredDecisionItem {
  const whyNow = Array.isArray(item.why_now) && item.why_now.length > 0
    ? item.why_now
    : [item.description || item.title]
  const priority = item.priority as ScoredDecisionItem['priority']
  const priorityVal = priority === 'high' ? 1 : priority === 'medium' ? 0.6 : 0.3
  const conf = Math.max(0, Math.min(1, item.confidence ?? 0.65))

  return {
    id: item.id,
    title: item.title,
    reason: item.description || whyNow[0] || '',
    priority,
    whyNow,
    sourceType: item.source_type as HealthAction['source_type'],
    source: {
      id: item.source_id,
      title: item.title,
      description: item.description,
      category: item.category,
      confidence: item.confidence,
      evidence_level: item.evidence_level,
      guideline_source: item.guideline_source,
      rule_id: item.source_id,
      recommendation: item.next_action,
    },
    category: item.category,
    ctaLabel: item.next_action || '開始行動',
    breakdown: {
      risk_severity: { value: priorityVal, weight: 0.25, contribution: priorityVal * 0.25, label: item.priority, reason: whyNow[0] || '' },
      trend: { value: 0.5, weight: 0.2, contribution: 0.1, label: 'stable', reason: '' },
      overdue: { value: 0.3, weight: 0.2, contribution: 0.06, label: 'on_track', reason: '' },
      confidence: { value: conf, weight: 0.15, contribution: conf * 0.15, label: conf >= 0.8 ? 'high' : 'medium', reason: '' },
      clinical_weight: { value: 0.6, weight: 0.1, contribution: 0.06, label: 'general', reason: '' },
      time_sensitivity: { value: 0.6, weight: 0.05, contribution: 0.03, label: 'medium', reason: '' },
      user_impact: { value: 0.3, weight: 0.05, contribution: 0.015, label: 'low', reason: '' },
    },
    score: item.score,
    factors: {
      riskSeverity: priority,
      trend: 'stable',
      overdue: 'on_track',
      confidence: conf,
      clinicalWeight: 'general',
      timeSensitivity: 'medium',
      userImpact: 'low',
      hints: { riskSeverity: whyNow[0] },
    },
  }
}

type MetricPoint = {
  recorded_at?: string
  value?: number
}

type DashboardSource = {
  id?: string
  title?: string
  description?: string
  summary?: string
  recommendation?: string
  text?: string
  reasoning?: string
  severity?: string
  category?: string
  priority?: number | string
  confidence?: number
  evidence_level?: string
  guideline_source?: string
  rule_id?: string
  evidence_json?: Record<string, unknown>
  generated_at?: string
  created_at?: string
  recorded_at?: string
}

type SymptomLike = {
  symptom?: string
  title?: string
  severity?: number | string
  impact?: number | string
  note?: string
  created_at?: string
  started_at?: string
}

type DashboardData = {
  alerts?: DashboardSource[]
  insights?: DashboardSource[]
  recommendations?: DashboardSource[]
  recent_symptoms?: SymptomLike[]
  recent_metrics?: Array<Record<string, unknown>>
  recent_labs?: Array<Record<string, unknown>>
  trends?: Record<string, MetricPoint[]>
  risk_level?: string
  health_score?: {
    overall_score?: number
  }
}

export type DecisionItem = ScoredDecisionItem
export type NotificationItem = DecisionItem & {
  snoozed_until?: string
  snoozed_at?: string
  snooze_reason?: string
  resurface_count?: number
  resurfaced?: boolean
  resurfaced_today?: boolean
}
export type DecisionContext = DashboardData
export type RankedNotificationsResult = {
  activeItems: NotificationItem[]
  snoozedItems: NotificationItem[]
  totalPendingCount: number
  snoozedCount: number
  resurfacedTodayCount: number
}

type TrendSignal = {
  key: string
  label: string
  delta: number
  direction: 'up' | 'down' | 'stable'
  isWorsening: boolean
  summary: string
  recommendation: string
  firstRecordedAt?: string
  lastRecordedAt?: string
}

const METRIC_CONFIG: Record<string, { label: string; worseningWhen: 'up' | 'down'; threshold: number; keywords: string[] }> = {
  systolic_bp: { label: '血壓', worseningWhen: 'up', threshold: 5, keywords: ['blood pressure', 'bp', 'cardio', '血壓', '心'] },
  blood_glucose: { label: '血糖', worseningWhen: 'up', threshold: 8, keywords: ['glucose', 'sugar', 'metabolic', '血糖', '糖'] },
  weight_kg: { label: '體重', worseningWhen: 'up', threshold: 1.2, keywords: ['weight', 'bmi', '體重'] },
  sleep_hours: { label: '睡眠', worseningWhen: 'down', threshold: 0.7, keywords: ['sleep', '睡眠'] },
}

function toNumber(value: unknown, fallback = 0) {
  const num = Number(value)
  return Number.isFinite(num) ? num : fallback
}

function shortText(value: string, max = 96) {
  if (value.length <= max) return value
  return `${value.slice(0, max - 1).trimEnd()}...`
}

function normalizePriority(source: DashboardSource, fallback: number) {
  const numericPriority = toNumber(source.priority, fallback)
  const severity = String(source.severity || '').toLowerCase()
  if (severity === 'high' || severity === 'warning') {
    return Math.max(numericPriority, 9)
  }
  return numericPriority
}

function parseDate(value?: string) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function getDaysAgo(value?: string) {
  const date = parseDate(value)
  if (!date) return null
  return Math.max(0, Math.floor((Date.now() - date.getTime()) / (24 * 60 * 60 * 1000)))
}

function getTrendSignal(metric: string, points: MetricPoint[] = []): TrendSignal | null {
  if (points.length < 2) return null
  const config = METRIC_CONFIG[metric]
  if (!config) return null

  const first = toNumber(points[0]?.value)
  const last = toNumber(points[points.length - 1]?.value)
  const delta = Number((last - first).toFixed(1))
  const absDelta = Math.abs(delta)
  if (absDelta < config.threshold) return null

  const direction: TrendSignal['direction'] = delta > 0 ? 'up' : 'down'
  const isWorsening = direction === config.worseningWhen
  const movement = direction === 'up' ? '上升' : '下降'
  const summary = `${config.label}在最近一段時間${movement} ${absDelta}`
  const recommendation = isWorsening
    ? `先把 ${config.label} 納入本週追蹤，避免風險繼續累積。`
    : `${config.label} 方向正在改善，持續追蹤能確認變化是否穩定。`

  return {
    key: metric,
    label: config.label,
    delta,
    direction,
    isWorsening,
    summary,
    recommendation,
    firstRecordedAt: points[0]?.recorded_at,
    lastRecordedAt: points[points.length - 1]?.recorded_at,
  }
}

function getTrendSignals(data: DashboardData) {
  return Object.entries(data.trends || {})
    .map(([metric, points]) => getTrendSignal(metric, points || []))
    .filter((signal): signal is TrendSignal => Boolean(signal))
}

function inferClinicalWeight(source: DashboardSource, fallbackCategory?: string): ClinicalWeightLevel {
  const text = `${source.category || ''} ${source.title || ''} ${source.summary || ''} ${source.description || ''} ${fallbackCategory || ''}`.toLowerCase()
  if (text.includes('cardio') || text.includes('heart') || text.includes('blood pressure') || text.includes('血壓') || text.includes('心')) return 'cardiovascular'
  if (text.includes('metabolic') || text.includes('glucose') || text.includes('sugar') || text.includes('bmi') || text.includes('weight') || text.includes('血糖') || text.includes('體重')) return 'metabolic'
  if (text.includes('liver') || text.includes('ast') || text.includes('alt') || text.includes('肝')) return 'liver'
  if (text.includes('sleep') || text.includes('diet') || text.includes('exercise') || text.includes('habit') || text.includes('生活') || text.includes('睡眠')) return 'lifestyle'
  return 'general'
}

function findRelatedTrendSignal(source: DashboardSource, signals: TrendSignal[]) {
  const haystack = `${source.category || ''} ${source.title || ''} ${source.summary || ''} ${source.description || ''} ${source.rule_id || ''}`.toLowerCase()
  return signals.find((signal) => METRIC_CONFIG[signal.key]?.keywords.some((keyword) => haystack.includes(keyword))) || null
}

function findRelatedAction(actions: HealthAction[], source: DashboardSource, sourceType: HealthAction['source_type']) {
  const targetIds = [source.id, source.rule_id].filter(Boolean).map(String)
  return (
    actions.find((action) => action.source_type === sourceType && targetIds.includes(action.source_id)) ||
    actions.find((action) => action.rule_id && source.rule_id && action.rule_id === source.rule_id) ||
    actions.find((action) => action.title.trim().toLowerCase() === String(source.title || '').trim().toLowerCase()) ||
    null
  )
}

function inferRiskSeverity(source: DashboardSource, data: DashboardData, relatedSignal: TrendSignal | null) {
  const severity = String(source.severity || '').toLowerCase()
  const priority = normalizePriority(source, 5)
  const riskLevel = String(data.risk_level || 'stable').toLowerCase()
  const healthScore = toNumber(data.health_score?.overall_score, 80)

  if (severity === 'high' || severity === 'warning' || priority >= 9) return 'high' as const
  if (riskLevel === 'high' || riskLevel === 'elevated') return 'high' as const
  if (relatedSignal?.isWorsening && Math.abs(relatedSignal.delta) >= 10) return 'high' as const
  if (riskLevel === 'moderate' || priority >= 6 || healthScore < 75) return 'medium' as const
  return 'low' as const
}

function inferTrendLevel(relatedSignal: TrendSignal | null) {
  if (!relatedSignal) return 'stable' as const
  if (relatedSignal.isWorsening) return 'worsening' as const
  if (relatedSignal.direction !== 'stable') return 'improving' as const
  return 'stable' as const
}

function inferOverdueLevel(relatedAction: HealthAction | null, riskSeverity: DecisionFactorInputs['riskSeverity']) {
  if (!relatedAction) return riskSeverity === 'high' ? 'due_soon' as const : 'on_track' as const
  if (relatedAction.reminder_status === 'overdue') return 'overdue' as const
  if (relatedAction.reminder_status === 'risk_up' || relatedAction.status === 'todo' || relatedAction.status === 'in_progress') return 'due_soon' as const
  return 'on_track' as const
}

function inferConfidence(source: DashboardSource) {
  if (typeof source.confidence === 'number') return Math.max(0, Math.min(1, source.confidence))
  if (source.evidence_level === 'A') return 0.9
  if (source.evidence_level === 'B') return 0.75
  if (source.evidence_level === 'C') return 0.6
  return 0.65
}

function inferTimeSensitivity(source: DashboardSource, relatedSignal: TrendSignal | null) {
  const daysAgo =
    getDaysAgo(source.generated_at) ??
    getDaysAgo(source.created_at) ??
    getDaysAgo(source.recorded_at) ??
    getDaysAgo(relatedSignal?.lastRecordedAt)

  if (daysAgo === null) return 'medium' as const
  if (daysAgo <= 7) return 'recent' as const
  if (daysAgo <= 30) return 'medium' as const
  return 'old' as const
}

function inferUserImpact(symptoms: SymptomLike[] = [], clinicalWeight: ClinicalWeightLevel) {
  if (symptoms.length === 0) return 'low' as const
  const keywordMap: Record<ClinicalWeightLevel, string[]> = {
    cardiovascular: ['胸', '心', '暈', '喘', '血壓'],
    metabolic: ['渴', '累', '血糖', '體重', '糖'],
    liver: ['腹', '肝', '疲倦'],
    lifestyle: ['睡', '壓力', '疲勞'],
    general: [],
  }
  const matched = symptoms.filter((symptom) => {
    const haystack = `${symptom.symptom || ''} ${symptom.title || ''} ${symptom.note || ''}`
    return keywordMap[clinicalWeight].some((keyword) => haystack.includes(keyword))
  })
  const sourcePool = matched.length > 0 ? matched : symptoms
  const highestSeverity = sourcePool.reduce((max, symptom) => Math.max(max, toNumber(symptom.severity, toNumber(symptom.impact, 0))), 0)
  if (highestSeverity >= 7) return 'high' as const
  if (highestSeverity >= 4) return 'medium' as const
  return 'low' as const
}

function buildFactorHints(
  source: DashboardSource,
  riskSeverity: DecisionFactorInputs['riskSeverity'],
  trend: DecisionFactorInputs['trend'],
  overdue: DecisionFactorInputs['overdue'],
  confidence: number,
  clinicalWeight: ClinicalWeightLevel,
  timeSensitivity: DecisionFactorInputs['timeSensitivity'],
  userImpact: DecisionFactorInputs['userImpact'],
  relatedSignal: TrendSignal | null,
  relatedAction: HealthAction | null,
  sourceType: HealthAction['source_type']
) {
  const actionAgeDays = relatedAction?.created_at ? getDaysAgo(relatedAction.created_at) : null
  const signalDays = relatedSignal?.firstRecordedAt && relatedSignal?.lastRecordedAt
    ? Math.max(1, Math.floor((new Date(relatedSignal.lastRecordedAt).getTime() - new Date(relatedSignal.firstRecordedAt).getTime()) / (24 * 60 * 60 * 1000)))
    : null

  return {
    riskSeverity:
      riskSeverity === 'high'
        ? `風險高（${source.title || source.description || '目前指標偏高'}）`
        : riskSeverity === 'medium'
        ? `這項問題已進入需要追蹤的區間`
        : `這項問題目前可提早介入，避免後續升高`,
    trend:
      trend === 'worsening' && relatedSignal
        ? `最近惡化（過去 ${signalDays || 14} 天 ${relatedSignal.label}${relatedSignal.direction === 'up' ? '上升' : '下降'}）`
        : trend === 'improving'
        ? '趨勢正在改善，但仍需要持續守住'
        : '目前趨勢還沒有真正回到穩定狀態',
    overdue:
      overdue === 'overdue'
        ? `已逾期（未處理 ${actionAgeDays || 3} 天）`
        : overdue === 'due_soon'
        ? relatedAction
          ? '已有任務但尚未完成，現在處理最有效'
          : sourceType === 'alert'
          ? '這項提醒尚未轉成穩定行動，建議盡快開始'
          : '這項行動需要盡快建立追蹤節奏'
        : '目前處理節奏仍在可接受範圍',
    confidence: confidence >= 0.8 ? '可信度高，規則與資料訊號一致' : confidence >= 0.65 ? '可信度中高，足以支撐優先排序' : '目前是早期訊號，建議先追蹤',
    clinicalWeight:
      clinicalWeight === 'cardiovascular'
        ? '屬於心血管風險，醫療重要性最高'
        : clinicalWeight === 'metabolic'
        ? '屬於代謝風險，容易累積成長期問題'
        : clinicalWeight === 'liver'
        ? '屬於肝功能相關指標，值得優先留意'
        : clinicalWeight === 'lifestyle'
        ? '屬於生活型態風險，會影響長期基線'
        : '這項問題會影響整體健康基線',
    timeSensitivity:
      timeSensitivity === 'recent'
        ? '最近 7 天內才出現或變差，時間敏感度高'
        : timeSensitivity === 'medium'
        ? '這是最近幾週持續存在的訊號'
        : '這項問題已存在一段時間，值得重新處理',
    userImpact:
      userImpact === 'high'
        ? '最近症狀對生活影響明顯'
        : userImpact === 'medium'
        ? '這件事已開始影響日常感受'
        : '目前主觀影響不高，但提早處理成本最低',
  }
}

function buildCandidate(
  source: DashboardSource,
  sourceType: HealthAction['source_type'],
  data: DashboardData,
  actions: HealthAction[],
  trendSignals: TrendSignal[],
  fallbackTitle: string,
  fallbackReason: string,
  fallbackCategory: string
): DecisionCandidate {
  const relatedSignal = findRelatedTrendSignal(source, trendSignals)
  const clinicalWeight = inferClinicalWeight(source, fallbackCategory)
  const riskSeverity = inferRiskSeverity(source, data, relatedSignal)
  const relatedAction = findRelatedAction(actions, source, sourceType)
  const trend = inferTrendLevel(relatedSignal)
  const overdue = inferOverdueLevel(relatedAction, riskSeverity)
  const confidence = inferConfidence(source)
  const timeSensitivity = inferTimeSensitivity(source, relatedSignal)
  const userImpact = inferUserImpact(data.recent_symptoms || [], clinicalWeight)
  const hints = buildFactorHints(source, riskSeverity, trend, overdue, confidence, clinicalWeight, timeSensitivity, userImpact, relatedSignal, relatedAction, sourceType)

  return {
    id: String(source.id || source.rule_id || `${sourceType}-${fallbackTitle}`),
    title: String(source.title || source.recommendation || source.text || fallbackTitle),
    reason: shortText(source.recommendation || source.description || source.summary || source.reasoning || fallbackReason),
    sourceType,
    source,
    category: String(source.category || fallbackCategory),
    ctaLabel: '開始行動',
    factors: {
      riskSeverity,
      trend,
      overdue,
      confidence,
      clinicalWeight,
      timeSensitivity,
      userImpact,
      hints,
    },
  }
}

function buildAlertCandidates(data: DashboardData, actions: HealthAction[], trendSignals: TrendSignal[]) {
  return (data.alerts || []).map((alert) =>
    buildCandidate(alert, 'alert', data, actions, trendSignals, '先處理這項風險提醒', '這項指標目前需要優先追蹤。', '風險提醒')
  )
}

function buildInsightCandidates(data: DashboardData, actions: HealthAction[], trendSignals: TrendSignal[]) {
  return (data.insights || []).map((insight) =>
    buildCandidate(insight, 'insight', data, actions, trendSignals, '優先處理這則洞察', '這則洞察已整理成可執行方向。', '健康洞察')
  )
}

function buildRecommendationCandidates(data: DashboardData, actions: HealthAction[], trendSignals: TrendSignal[]) {
  return (data.recommendations || []).map((recommendation, index) =>
    buildCandidate(
      {
        ...recommendation,
        id: recommendation.id || recommendation.rule_id || `recommendation-${index}`,
        title: recommendation.title || recommendation.recommendation || recommendation.text || '開始這項改善建議',
      },
      'recommendation',
      data,
      actions,
      trendSignals,
      '開始這項改善建議',
      '這是目前最容易開始的一步。',
      '改善建議'
    )
  )
}

function buildActionNotificationCandidates(data: DashboardData, actions: HealthAction[]) {
  return actions
    .filter((action) => action.reminder_status === 'overdue' || action.reminder_status === 'risk_up')
    .map((action) => {
      const source: DashboardSource = {
        id: action.id,
        title: action.title,
        description: action.description,
        category: action.category,
        confidence: action.confidence,
        evidence_level: action.evidence_level,
        guideline_source: action.guideline_source,
        rule_id: action.rule_id,
        created_at: action.created_at,
      }
      const clinicalWeight = inferClinicalWeight(source, action.category)
      const riskSeverity = action.priority === 'high' ? 'high' : action.priority === 'medium' ? 'medium' : 'low'
      const trend = action.impact_status === 'worse' ? 'worsening' : action.impact_status === 'improved' ? 'improving' : 'stable'
      const overdue = action.reminder_status === 'overdue' ? 'overdue' : 'due_soon'
      const confidence = typeof action.confidence === 'number' ? action.confidence : inferConfidence(source)
      const timeSensitivity = inferTimeSensitivity({ created_at: action.created_at }, null)
      const userImpact = inferUserImpact(data.recent_symptoms || [], clinicalWeight)

      return {
        id: action.id,
        title: action.title,
        reason: shortText(action.description || '這項既有任務需要重新拉回優先處理區。'),
        sourceType: 'action' as const,
        source: action as unknown as Record<string, unknown>,
        category: action.category || '既有任務',
        ctaLabel: '開始改善',
        factors: {
          riskSeverity,
          trend,
          overdue,
          confidence,
          clinicalWeight,
          timeSensitivity,
          userImpact,
          hints: {
            riskSeverity: action.priority === 'high' ? '這是高風險任務，拖延會讓風險持續累積' : '這項任務已經進入需要主動處理的區間',
            trend: action.impact_status === 'worse' ? '最近沒有改善，甚至出現惡化跡象' : action.impact_status === 'improved' ? '已有改善，但現在中斷會削弱效果' : '目前還沒有看到明顯改善',
            overdue: action.reminder_status === 'overdue' ? '這項任務已逾期，現在最需要補回節奏' : '這項任務風險正在上升，需要立即接手',
            confidence: confidence >= 0.75 ? '這項任務的依據明確，建議直接接手處理' : '這項任務已有足夠依據進入待處理清單',
            clinicalWeight: clinicalWeight === 'cardiovascular' ? '這是心血管相關任務，醫療重要性高' : clinicalWeight === 'metabolic' ? '這是代謝相關任務，值得優先補做' : '這項任務與整體健康基線有直接關聯',
            timeSensitivity: '這項任務已到需要重新接手的時間點',
            userImpact: userImpact === 'high' ? '最近症狀已明顯影響生活，先把這項拉回來' : '即使主觀影響不高，也應先把處理節奏找回來',
          },
        },
      } satisfies DecisionCandidate
    })
}

function buildTrendNotificationCandidates(data: DashboardData, actions: HealthAction[], trendSignals: TrendSignal[]) {
  return trendSignals
    .filter((signal) => signal.isWorsening)
    .map((signal) =>
      buildCandidate(
        {
          id: `notification-trend-${signal.key}`,
          title: `${signal.label}趨勢正在惡化`,
          summary: signal.summary,
          recommendation: signal.recommendation,
          category: signal.label,
          priority: 8,
          rule_id: `notification_trend_${signal.key}`,
          confidence: 0.72,
          evidence_level: 'B',
          guideline_source: 'Trend Monitor',
          recorded_at: signal.lastRecordedAt,
        },
        'insight',
        data,
        actions,
        trendSignals,
        `${signal.label}趨勢正在惡化`,
        signal.summary,
        signal.label
      )
    )
}

function dedupeCandidates(items: DecisionCandidate[]) {
  const seen = new Set<string>()
  return items.filter((item) => {
    const key = `${item.sourceType}:${item.title.trim().toLowerCase()}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function dedupeScoredItemsByTitle(items: DecisionItem[]) {
  const seen = new Set<string>()
  return items.filter((item) => {
    const key = item.title.trim().toLowerCase()
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function getNotificationItemKey(item: DecisionItem) {
  return `${item.sourceType}:${item.id}`
}

function applyNotificationLifecycle(items: DecisionItem[], snoozeRecords: NotificationSnoozeRecord[] = []): RankedNotificationsResult {
  const now = new Date()
  const snoozeMap = new Map(snoozeRecords.map((record) => [record.key, record]))
  const activeItems: NotificationItem[] = []
  const snoozedItems: NotificationItem[] = []

  items.forEach((item) => {
    const record = snoozeMap.get(getNotificationItemKey(item))
    const isActiveSnooze = isSnoozeActive(record, now)
    const resurfaced = !isActiveSnooze && (record?.resurface_count || 0) > 0
    const resurfacedToday = isResurfacedToday(record, now)
    const baseItem: NotificationItem = {
      ...item,
      snoozed_until: record?.snoozed_until,
      snoozed_at: record?.snoozed_at,
      snooze_reason: record?.snooze_reason,
      resurface_count: record?.resurface_count || 0,
      resurfaced,
      resurfaced_today: resurfacedToday,
      whyNow:
        resurfaced || resurfacedToday
          ? ['稍後提醒時間已到，這件事需要再次處理', ...item.whyNow].slice(0, 4)
          : item.whyNow,
    }

    if (isActiveSnooze) {
      snoozedItems.push(baseItem)
      return
    }

    activeItems.push(baseItem)
  })

  snoozedItems.sort((left, right) => {
    const leftTime = new Date(left.snoozed_until || 0).getTime()
    const rightTime = new Date(right.snoozed_until || 0).getTime()
    return leftTime - rightTime
  })

  return {
    activeItems,
    snoozedItems,
    totalPendingCount: activeItems.length,
    snoozedCount: snoozedItems.length,
    resurfacedTodayCount: activeItems.filter((item) => item.resurfaced_today).length,
  }
}

export function getRankedAlerts(data: DecisionContext | null, actions: HealthAction[]): DecisionItem[] {
  if (!data) return []
  // Prefer backend decision_items for alert-type items
  const backendItems = (data as any).decision_items as UnifiedDecisionItem[] | undefined
  if (backendItems && backendItems.length > 0) {
    return backendItems
      .filter((item) => item.source_type === 'alert')
      .map(fromBackendDecisionItem)
  }
  // Fallback: local scoring
  const trendSignals = getTrendSignals(data)
  return getTopDecisions(dedupeCandidates(buildAlertCandidates(data, actions, trendSignals)), (data.alerts || []).length || 0)
}

export function getRankedInsights(data: DecisionContext | null, actions: HealthAction[]): DecisionItem[] {
  if (!data) return []
  // Prefer backend decision_items for insight-type items
  const backendItems = (data as any).decision_items as UnifiedDecisionItem[] | undefined
  if (backendItems && backendItems.length > 0) {
    return backendItems
      .filter((item) => item.source_type === 'insight' || item.source_type === 'recommendation')
      .map(fromBackendDecisionItem)
  }
  // Fallback: local scoring
  const trendSignals = getTrendSignals(data)
  return getTopDecisions(dedupeCandidates(buildInsightCandidates(data, actions, trendSignals)), (data.insights || []).length || 0)
}

export function buildDecisionItems(data: DashboardData | null, actions: HealthAction[]): DecisionItem[] {
  if (!data) return []

  // ── Backend is the single source of truth ──
  // If the dashboard API has returned pre-ranked decision_items, use them.
  // This ensures Dashboard / Notifications / Insights all agree on priority.
  const backendItems = (data as any).decision_items as UnifiedDecisionItem[] | undefined
  if (backendItems && backendItems.length > 0) {
    return backendItems.slice(0, 3).map(fromBackendDecisionItem)
  }

  // ── Local fallback (used when backend data is unavailable) ──────────────

  const trendSignals = getTrendSignals(data)
  const candidates: DecisionCandidate[] = [
    ...buildAlertCandidates(data, actions, trendSignals),
    ...buildInsightCandidates(data, actions, trendSignals),
    ...buildRecommendationCandidates(data, actions, trendSignals),
  ]

  trendSignals.forEach((signal) => {
    if (!signal.isWorsening) return
    candidates.push(
      buildCandidate(
        {
          id: `trend-${signal.key}`,
          title: `${signal.label}趨勢需要先追蹤`,
          summary: signal.summary,
          recommendation: signal.recommendation,
          category: signal.label,
          priority: 8,
          rule_id: `trend_${signal.key}`,
          confidence: 0.72,
          evidence_level: 'B',
          guideline_source: 'Trend Monitor',
          recorded_at: signal.lastRecordedAt,
        },
        'insight',
        data,
        actions,
        trendSignals,
        `${signal.label}趨勢需要先追蹤`,
        signal.summary,
        signal.label
      )
    )
  })

  const healthScore = toNumber(data.health_score?.overall_score, 0)
  if (healthScore > 0 && healthScore < 70) {
    candidates.push(
      buildCandidate(
        {
          id: 'score-stabilize',
          title: '先穩定本週健康基線',
          recommendation: '從血壓、血糖或睡眠任一項開始固定追蹤。',
          category: '健康分數',
          priority: 8,
          rule_id: 'score_stabilize',
          confidence: 0.7,
          evidence_level: 'B',
          guideline_source: 'Health Score Monitor',
        },
        'recommendation',
        data,
        actions,
        trendSignals,
        '先穩定本週健康基線',
        `目前健康分數 ${healthScore}/100，先選一項最容易做到的追蹤任務開始。`,
        '健康分數'
      )
    )
  }

  return getTopDecisions(dedupeCandidates(candidates), 3)
}

export function getRankedNotifications(
  data: DecisionContext | null,
  actions: HealthAction[],
  snoozeRecords: NotificationSnoozeRecord[] = []
): RankedNotificationsResult {
  if (!data) {
    return {
      activeItems: [],
      snoozedItems: [],
      totalPendingCount: 0,
      snoozedCount: 0,
      resurfacedTodayCount: 0,
    }
  }

  let ranked: DecisionItem[]

  // ── Backend is the single source of truth ──
  const backendItems = (data as any).decision_items as UnifiedDecisionItem[] | undefined
  if (backendItems && backendItems.length > 0) {
    ranked = backendItems.map(fromBackendDecisionItem)
  } else {
    // ── Local fallback ───────────────────────────────────────────────────
    const trendSignals = getTrendSignals(data)
    const candidates: DecisionCandidate[] = [
      ...buildActionNotificationCandidates(data, actions),
      ...buildAlertCandidates(data, actions, trendSignals),
      ...buildInsightCandidates(data, actions, trendSignals),
      ...buildTrendNotificationCandidates(data, actions, trendSignals),
    ]
    ranked = dedupeScoredItemsByTitle(getTopDecisions(dedupeCandidates(candidates), candidates.length || 0))
  }

  return applyNotificationLifecycle(ranked, snoozeRecords)
}

export function buildHealthNarrative(data: DashboardData | null, actions: HealthAction[]) {
  if (!data) {
    return [
      '目前還在整理你的健康資料。',
      '先新增一筆量測、症狀或文件，系統才能形成更具體的健康故事。',
    ]
  }

  const score = toNumber(data.health_score?.overall_score, 0)
  const riskLevel = String(data.risk_level || 'stable').toLowerCase()
  const todayCount = actions.filter((action) => action.status === 'todo' || action.status === 'in_progress').length
  const overdueCount = actions.filter((action) => action.reminder_status === 'overdue').length
  const improvedCount = actions.filter((action) => action.impact_status === 'improved').length
  const worseningSignals = Object.entries(data.trends || {})
    .map(([metric, points]) => getTrendSignal(metric, points || []))
    .filter((signal): signal is TrendSignal => Boolean(signal))
    .sort((left, right) => Math.abs(right.delta) - Math.abs(left.delta))

  const lines = [
    score > 0
      ? `目前整體風險偏 ${riskLevel === 'high' || riskLevel === 'elevated' ? '高' : riskLevel === 'moderate' ? '中' : '穩定'}，健康分數為 ${score} / 100。`
      : `目前整體風險狀態偏 ${riskLevel === 'high' || riskLevel === 'elevated' ? '高' : riskLevel === 'moderate' ? '中' : '穩定'}。`,
  ]

  if (worseningSignals.length > 0) {
    lines.push(`${worseningSignals[0].summary}，代表這不是單次波動，值得先列入本週行動。`)
  } else {
    lines.push('最近沒有看到明顯惡化趨勢，現在最重要的是維持穩定紀錄，讓系統能看出更長期的模式。')
  }

  if (todayCount > 0 || overdueCount > 0) {
    lines.push(`你現在有 ${todayCount} 項待執行行動${overdueCount > 0 ? `，其中 ${overdueCount} 項已經延後太久` : ''}，先完成最上面的 1 件最有效。`)
  } else {
    lines.push('目前還沒有待執行行動，建議先把最重要的一則洞察轉成追蹤任務。')
  }

  if (improvedCount > 0) {
    lines.push(`你已經有 ${improvedCount} 項行動出現正向回饋，表示目前的追蹤與改善開始累積效果。`)
  } else {
    lines.push('目前系統還在觀察變化，持續完成任務與打卡後，才看得出你是真的變好、沒變，還是惡化。')
  }

  return lines.slice(0, 4)
}

export function sortInsightsForAction(items: DashboardSource[]) {
  return [...items].sort((left, right) => {
    const leftScore = normalizePriority(left, 5) * 10 + (String(left.severity || '').toLowerCase() === 'high' ? 10 : 0)
    const rightScore = normalizePriority(right, 5) * 10 + (String(right.severity || '').toLowerCase() === 'high' ? 10 : 0)
    return rightScore - leftScore
  })
}
