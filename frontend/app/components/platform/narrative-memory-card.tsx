'use client'

import { useEffect, useRef, useState } from 'react'
import { api, type NarrativeMemoryData, type CrossPeriodReasoning } from '../../../lib/api'
import {
  BookOpen,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  EyeOff,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Minus,
  Activity,
  ArrowRight,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type PeriodType = 'daily' | 'weekly' | 'monthly'

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  let color = 'bg-amber-100 text-amber-700'
  if (pct >= 70) color = 'bg-green-100 text-green-700'
  else if (pct < 40) color = 'bg-red-100 text-red-700'
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${color}`}>
      可信度 {pct}%
    </span>
  )
}

function PeriodSelector({
  value,
  onChange,
}: {
  value: PeriodType
  onChange: (v: PeriodType) => void
}) {
  const options: { v: PeriodType; label: string }[] = [
    { v: 'daily', label: '今日' },
    { v: 'weekly', label: '本週' },
    { v: 'monthly', label: '本月' },
  ]
  return (
    <div className="flex gap-1">
      {options.map((o) => (
        <button
          key={o.v}
          onClick={() => onChange(o.v)}
          className={`text-xs px-2.5 py-1 rounded-full transition-colors ${
            value === o.v
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

function SectionRow({
  icon,
  label,
  items,
  accent,
}: {
  icon: React.ReactNode
  label: string
  items: string[]
  accent: string
}) {
  if (!items || items.length === 0) return null
  return (
    <div className="flex items-start gap-2">
      <span className={`mt-0.5 flex-shrink-0 ${accent}`}>{icon}</span>
      <div>
        <span className="text-xs font-medium text-gray-500">{label}</span>
        <div className="flex flex-wrap gap-1 mt-0.5">
          {items.map((item, i) => (
            <span
              key={i}
              className="text-xs bg-gray-50 border border-gray-200 text-gray-700 px-2 py-0.5 rounded-full"
            >
              {item}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

const _TREND_CONFIG = {
  improving: {
    label: '持續改善',
    Icon: TrendingUp,
    classes: 'text-green-700 bg-green-50 border-green-200',
  },
  worsening: {
    label: '需要關注',
    Icon: TrendingDown,
    classes: 'text-red-700 bg-red-50 border-red-200',
  },
  mixed: {
    label: '部分改善',
    Icon: ArrowRight,
    classes: 'text-amber-700 bg-amber-50 border-amber-200',
  },
  stable: {
    label: '目前穩定',
    Icon: Minus,
    classes: 'text-gray-600 bg-gray-50 border-gray-200',
  },
} as const

function TrendIndicator({
  trend,
  confidence,
}: {
  trend: CrossPeriodReasoning['overallTrend']
  confidence: number
}) {
  const cfg = _TREND_CONFIG[trend] ?? _TREND_CONFIG.stable
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-sm font-medium ${cfg.classes}`}>
      <cfg.Icon className="w-4 h-4 flex-shrink-0" />
      <span>健康方向：{cfg.label}</span>
      <span className="ml-auto text-xs font-normal opacity-70">
        可信度 {Math.round(confidence * 100)}%
      </span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main card
// ---------------------------------------------------------------------------

export default function NarrativeMemoryCard() {
  const [periodType, setPeriodType] = useState<PeriodType>('weekly')
  const [memory, setMemory] = useState<NarrativeMemoryData | null>(null)
  const [found, setFound] = useState(false)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const fetchRef = useRef(0)

  // Cross-period state
  const [crossPeriod, setCrossPeriod] = useState<CrossPeriodReasoning | null>(null)
  const [crossExpanded, setCrossExpanded] = useState(false)

  const fetchMemory = async (period: PeriodType) => {
    const id = ++fetchRef.current
    setLoading(true)
    setError(null)
    try {
      const res = await api.getNarrativeMemory(period)
      if (id !== fetchRef.current) return
      setFound(res.found)
      setMemory(res.memory)
    } catch {
      if (id !== fetchRef.current) return
      setError('無法載入健康記憶資料，請稍後再試。')
    } finally {
      if (id === fetchRef.current) setLoading(false)
    }
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setError(null)
    try {
      const res = await api.generateNarrativeMemory(periodType)
      setFound(true)
      setMemory(res.memory)
    } catch {
      setError('生成記憶失敗，請稍後再試。')
    } finally {
      setGenerating(false)
    }
  }

  useEffect(() => {
    fetchMemory(periodType)
  }, [periodType])

  // Fetch cross-period reasoning once on mount (period-independent)
  useEffect(() => {
    api.getCrossPeriodReasoning()
      .then((res) => setCrossPeriod(res.reasoning))
      .catch(() => {/* silently skip — cross-period is supplementary */})
  }, [])

  const periodLabel = { daily: '今日', weekly: '本週', monthly: '本月' }[periodType]

  // Determine if cross-period has meaningful data
  const hasCrossData =
    crossPeriod !== null &&
    (crossPeriod.confidence > 0 ||
      crossPeriod.longTermRisks.length > 0 ||
      crossPeriod.sustainedImprovements.length > 0 ||
      crossPeriod.repeatedIgnoredRisks.length > 0 ||
      crossPeriod.carryOverRecommendations.length > 0)

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-indigo-600" />
          <h2 className="text-base font-semibold text-gray-900">健康敘事記憶</h2>
        </div>
        <div className="flex items-center gap-2">
          <PeriodSelector value={periodType} onChange={setPeriodType} />
          <button
            onClick={() => fetchMemory(periodType)}
            disabled={loading}
            title="重新載入"
            className="text-gray-400 hover:text-gray-600 disabled:opacity-40 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Body */}
      {loading ? (
        <div className="space-y-2 animate-pulse">
          <div className="h-3 bg-gray-100 rounded w-3/4" />
          <div className="h-3 bg-gray-100 rounded w-1/2" />
        </div>
      ) : error ? (
        <p className="text-sm text-red-500">{error}</p>
      ) : !found || !memory ? (
        <div className="text-center py-6 space-y-3">
          <p className="text-sm text-gray-500">
            {periodLabel}尚未生成健康記憶摘要。
          </p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-1.5 text-sm bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white px-4 py-2 rounded-xl transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${generating ? 'animate-spin' : ''}`} />
            {generating ? '生成中…' : `生成${periodLabel}記憶`}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Confidence + dates */}
          <div className="flex items-center gap-2 flex-wrap">
            <ConfidenceBadge value={memory.confidence} />
            <span className="text-xs text-gray-400">
              {memory.periodStart} — {memory.periodEnd}
            </span>
          </div>

          {/* Summary text */}
          <p className="text-sm text-gray-700 leading-relaxed">{memory.summaryText}</p>

          {/* Improving / worsening */}
          <div className="space-y-2">
            <SectionRow
              icon={<TrendingUp className="w-4 h-4" />}
              label="改善項目"
              items={memory.improvingItems}
              accent="text-green-500"
            />
            <SectionRow
              icon={<TrendingDown className="w-4 h-4" />}
              label="需留意項目"
              items={memory.worseningItems}
              accent="text-amber-500"
            />
            <SectionRow
              icon={<AlertTriangle className="w-4 h-4" />}
              label="重複出現風險"
              items={memory.repeatedRisks}
              accent="text-red-500"
            />
          </div>

          {/* Expand toggle for more detail */}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 transition-colors"
          >
            {expanded ? (
              <>
                <ChevronUp className="w-3.5 h-3.5" /> 收起詳情
              </>
            ) : (
              <>
                <ChevronDown className="w-3.5 h-3.5" /> 展開詳情
              </>
            )}
          </button>

          {expanded && (
            <div className="space-y-2 pt-1 border-t border-gray-100">
              <SectionRow
                icon={<CheckCircle2 className="w-4 h-4" />}
                label="有效行動"
                items={memory.effectiveActions}
                accent="text-blue-500"
              />
              <SectionRow
                icon={<EyeOff className="w-4 h-4" />}
                label="已忽略提醒類型"
                items={memory.ignoredItems}
                accent="text-gray-400"
              />
              {memory.topThemes.length > 0 && (
                <SectionRow
                  icon={<Minus className="w-4 h-4" />}
                  label="主要健康主題"
                  items={memory.topThemes}
                  accent="text-indigo-400"
                />
              )}
              {memory.limitations.length > 0 && (
                <div className="mt-2 text-xs text-gray-400 bg-gray-50 rounded-xl p-3 space-y-1">
                  <p className="font-medium text-gray-500 mb-1">資料限制說明</p>
                  {memory.limitations.map((l: string, i: number) => (
                    <p key={i}>• {l}</p>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Regenerate button */}
          <div className="pt-1">
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-indigo-600 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${generating ? 'animate-spin' : ''}`} />
              {generating ? '更新中…' : '重新生成記憶'}
            </button>
          </div>
        </div>
      )}

      {/* ── Cross-Period Long-term Trend Analysis ─────────────────────── */}
      {hasCrossData && (
        <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs font-medium text-gray-500">
              <Activity className="w-3.5 h-3.5" />
              長期趨勢分析
            </span>
            <button
              onClick={() => setCrossExpanded((v) => !v)}
              className="flex items-center gap-0.5 text-xs text-indigo-500 hover:text-indigo-700 transition-colors"
            >
              {crossExpanded ? (
                <><ChevronUp className="w-3.5 h-3.5" /> 收起</>
              ) : (
                <><ChevronDown className="w-3.5 h-3.5" /> 展開</>
              )}
            </button>
          </div>

          <TrendIndicator
            trend={crossPeriod!.overallTrend}
            confidence={crossPeriod!.confidence}
          />

          {crossExpanded && (
            <div className="space-y-2 pt-1">
              <SectionRow
                icon={<TrendingUp className="w-4 h-4" />}
                label="跨期持續改善"
                items={crossPeriod!.sustainedImprovements}
                accent="text-green-500"
              />
              <SectionRow
                icon={<AlertTriangle className="w-4 h-4" />}
                label="長期反覆風險"
                items={crossPeriod!.longTermRisks}
                accent="text-red-500"
              />
              <SectionRow
                icon={<EyeOff className="w-4 h-4" />}
                label="重複忽略的提醒"
                items={crossPeriod!.repeatedIgnoredRisks}
                accent="text-amber-500"
              />
              <SectionRow
                icon={<CheckCircle2 className="w-4 h-4" />}
                label="建議持續追蹤"
                items={crossPeriod!.carryOverRecommendations}
                accent="text-indigo-500"
              />
              {crossPeriod!.unstableAreas.length > 0 && (
                <SectionRow
                  icon={<Minus className="w-4 h-4" />}
                  label="波動不穩定項目"
                  items={crossPeriod!.unstableAreas}
                  accent="text-gray-400"
                />
              )}
              {crossPeriod!.limitations.length > 0 && (
                <div className="mt-2 text-xs text-gray-400 bg-gray-50 rounded-xl p-3 space-y-1">
                  <p className="font-medium text-gray-500 mb-1">跨期分析限制</p>
                  {crossPeriod!.limitations.map((l: string, i: number) => (
                    <p key={i}>• {l}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Empty state for cross-period */}
      {crossPeriod !== null && !hasCrossData && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <p className="text-xs text-gray-400 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5" />
            累積更多期間記憶後將顯示長期趨勢分析。
          </p>
        </div>
      )}
    </div>
  )
}
