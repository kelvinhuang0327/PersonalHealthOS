import type { HealthAction } from './actions'

export type RiskSeverityLevel = 'high' | 'medium' | 'low'
export type TrendDirectionLevel = 'worsening' | 'stable' | 'improving'
export type OverdueLevel = 'overdue' | 'due_soon' | 'on_track'
export type ClinicalWeightLevel = 'cardiovascular' | 'metabolic' | 'liver' | 'lifestyle' | 'general'
export type TimeSensitivityLevel = 'recent' | 'medium' | 'old'
export type UserImpactLevel = 'high' | 'medium' | 'low'

export type DecisionFactorInputs = {
  riskSeverity: RiskSeverityLevel
  trend: TrendDirectionLevel
  overdue: OverdueLevel
  confidence: number
  clinicalWeight: ClinicalWeightLevel
  timeSensitivity: TimeSensitivityLevel
  userImpact: UserImpactLevel
  hints?: Partial<Record<keyof Omit<DecisionFactorInputs, 'confidence' | 'hints'> | 'confidence', string>>
}

export type DecisionCandidate = {
  id: string
  title: string
  reason: string
  sourceType: HealthAction['source_type'] | 'action'
  source: Record<string, unknown>
  category: string
  ctaLabel: string
  factors: DecisionFactorInputs
}

export type DecisionBreakdownEntry = {
  value: number
  weight: number
  contribution: number
  label: string
  reason: string
}

export type DecisionBreakdown = {
  risk_severity: DecisionBreakdownEntry
  trend: DecisionBreakdownEntry
  overdue: DecisionBreakdownEntry
  confidence: DecisionBreakdownEntry
  clinical_weight: DecisionBreakdownEntry
  time_sensitivity: DecisionBreakdownEntry
  user_impact: DecisionBreakdownEntry
}

export type ScoredDecisionItem = DecisionCandidate & {
  score: number
  priority: 'high' | 'medium' | 'low'
  breakdown: DecisionBreakdown
  whyNow: string[]
}

const FACTOR_WEIGHTS = {
  risk_severity: 0.25,
  trend: 0.2,
  overdue: 0.2,
  confidence: 0.15,
  clinical_weight: 0.1,
  time_sensitivity: 0.05,
  user_impact: 0.05,
} as const

const RISK_MAP: Record<RiskSeverityLevel, number> = {
  high: 1,
  medium: 0.6,
  low: 0.3,
}

const TREND_MAP: Record<TrendDirectionLevel, number> = {
  worsening: 1,
  stable: 0.5,
  improving: 0.2,
}

const OVERDUE_MAP: Record<OverdueLevel, number> = {
  overdue: 1,
  due_soon: 0.7,
  on_track: 0.3,
}

const CLINICAL_MAP: Record<ClinicalWeightLevel, number> = {
  cardiovascular: 1,
  metabolic: 0.9,
  liver: 0.8,
  lifestyle: 0.5,
  general: 0.6,
}

const TIME_MAP: Record<TimeSensitivityLevel, number> = {
  recent: 1,
  medium: 0.6,
  old: 0.3,
}

const USER_IMPACT_MAP: Record<UserImpactLevel, number> = {
  high: 1,
  medium: 0.6,
  low: 0.3,
}

function clampConfidence(value: number) {
  if (Number.isNaN(value)) return 0.6
  return Math.max(0, Math.min(1, value))
}

function getPriority(score: number): ScoredDecisionItem['priority'] {
  if (score >= 75) return 'high'
  if (score >= 55) return 'medium'
  return 'low'
}

function buildRiskReason(level: RiskSeverityLevel, hint?: string) {
  if (hint) return hint
  if (level === 'high') return '風險高，現在處理能最快降低後續惡化機率。'
  if (level === 'medium') return '風險已進入需要追蹤的區間。'
  return '目前風險不算最高，但提早處理成本最低。'
}

function buildTrendReason(level: TrendDirectionLevel, hint?: string) {
  if (hint) return hint
  if (level === 'worsening') return '最近走勢在惡化，這不是單次波動。'
  if (level === 'stable') return '趨勢還沒有改善，需要持續觀察。'
  return '趨勢有改善，但需要持續守住。'
}

function buildOverdueReason(level: OverdueLevel, hint?: string) {
  if (hint) return hint
  if (level === 'overdue') return '這項行動已經拖延，越晚處理越難看出改善。'
  if (level === 'due_soon') return '這項行動快到需要處理的時間點。'
  return '目前進度還算在軌道上。'
}

function buildConfidenceReason(value: number, hint?: string) {
  if (hint) return hint
  if (value >= 0.8) return '依據明確，規則與資料訊號一致。'
  if (value >= 0.6) return '可信度中高，足夠作為優先排序依據。'
  return '目前是早期訊號，仍建議先追蹤。'
}

function buildClinicalReason(level: ClinicalWeightLevel, hint?: string) {
  if (hint) return hint
  if (level === 'cardiovascular') return '屬於心血管風險，醫療重要性較高。'
  if (level === 'metabolic') return '屬於代謝風險，容易累積成長期問題。'
  if (level === 'liver') return '屬於肝功能相關指標，值得優先留意。'
  if (level === 'lifestyle') return '雖然偏生活型態，但對後續趨勢影響明顯。'
  return '這項指標與整體健康基線有直接關聯。'
}

function buildTimeReason(level: TimeSensitivityLevel, hint?: string) {
  if (hint) return hint
  if (level === 'recent') return '最近 7 天內才出現或加重，具有時間敏感性。'
  if (level === 'medium') return '這是最近幾週持續存在的訊號。'
  return '這項問題不是最新事件，但仍值得排入追蹤。'
}

function buildUserImpactReason(level: UserImpactLevel, hint?: string) {
  if (hint) return hint
  if (level === 'high') return '它已明顯影響到你的日常狀態。'
  if (level === 'medium') return '它對生活已有感受上的影響。'
  return '目前主觀影響不高，但仍值得提早介入。'
}

export function normalizeFactors(item: DecisionCandidate): DecisionBreakdown {
  const riskSeverity = RISK_MAP[item.factors.riskSeverity]
  const trend = TREND_MAP[item.factors.trend]
  const overdue = OVERDUE_MAP[item.factors.overdue]
  const confidence = clampConfidence(item.factors.confidence)
  const clinicalWeight = CLINICAL_MAP[item.factors.clinicalWeight]
  const timeSensitivity = TIME_MAP[item.factors.timeSensitivity]
  const userImpact = USER_IMPACT_MAP[item.factors.userImpact]

  return {
    risk_severity: {
      value: riskSeverity,
      weight: FACTOR_WEIGHTS.risk_severity,
      contribution: riskSeverity * FACTOR_WEIGHTS.risk_severity,
      label: item.factors.riskSeverity,
      reason: buildRiskReason(item.factors.riskSeverity, item.factors.hints?.riskSeverity),
    },
    trend: {
      value: trend,
      weight: FACTOR_WEIGHTS.trend,
      contribution: trend * FACTOR_WEIGHTS.trend,
      label: item.factors.trend,
      reason: buildTrendReason(item.factors.trend, item.factors.hints?.trend),
    },
    overdue: {
      value: overdue,
      weight: FACTOR_WEIGHTS.overdue,
      contribution: overdue * FACTOR_WEIGHTS.overdue,
      label: item.factors.overdue,
      reason: buildOverdueReason(item.factors.overdue, item.factors.hints?.overdue),
    },
    confidence: {
      value: confidence,
      weight: FACTOR_WEIGHTS.confidence,
      contribution: confidence * FACTOR_WEIGHTS.confidence,
      label: confidence >= 0.8 ? 'high' : confidence >= 0.6 ? 'medium' : 'low',
      reason: buildConfidenceReason(confidence, item.factors.hints?.confidence),
    },
    clinical_weight: {
      value: clinicalWeight,
      weight: FACTOR_WEIGHTS.clinical_weight,
      contribution: clinicalWeight * FACTOR_WEIGHTS.clinical_weight,
      label: item.factors.clinicalWeight,
      reason: buildClinicalReason(item.factors.clinicalWeight, item.factors.hints?.clinicalWeight),
    },
    time_sensitivity: {
      value: timeSensitivity,
      weight: FACTOR_WEIGHTS.time_sensitivity,
      contribution: timeSensitivity * FACTOR_WEIGHTS.time_sensitivity,
      label: item.factors.timeSensitivity,
      reason: buildTimeReason(item.factors.timeSensitivity, item.factors.hints?.timeSensitivity),
    },
    user_impact: {
      value: userImpact,
      weight: FACTOR_WEIGHTS.user_impact,
      contribution: userImpact * FACTOR_WEIGHTS.user_impact,
      label: item.factors.userImpact,
      reason: buildUserImpactReason(item.factors.userImpact, item.factors.hints?.userImpact),
    },
  }
}

export function calculateDecisionScore(item: DecisionCandidate): ScoredDecisionItem {
  const breakdown = normalizeFactors(item)
  const score = Math.round(
    100 *
      (breakdown.risk_severity.contribution +
        breakdown.trend.contribution +
        breakdown.overdue.contribution +
        breakdown.confidence.contribution +
        breakdown.clinical_weight.contribution +
        breakdown.time_sensitivity.contribution +
        breakdown.user_impact.contribution)
  )

  const whyNow = Object.values(breakdown)
    .sort((left, right) => right.contribution - left.contribution)
    .slice(0, 3)
    .map((entry) => entry.reason)

  return {
    ...item,
    score,
    priority: getPriority(score),
    breakdown,
    whyNow,
  }
}

export function getTopDecisions(items: DecisionCandidate[], limit = 3) {
  return [...items]
    .map((item) => calculateDecisionScore(item))
    .sort((left, right) => right.score - left.score)
    .slice(0, limit)
}
