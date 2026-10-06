'use client'

import { useEffect, useState } from 'react'
import { TrendingDown, TrendingUp, Minus, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../../../lib/api'
import { Badge } from '../ui/badge'
import { Card } from '../ui/card'

type Outcome = {
  metric_type: string
  before_value: number | null
  after_value: number | null
  delta: number | null
  delta_pct: number | null
  time_window_days: number
  outcome_label: 'improved' | 'no_change' | 'worse' | string
  computed_at: string
}

const METRIC_LABELS: Record<string, string> = {
  systolic_bp: '收縮壓',
  diastolic_bp: '舒張壓',
  weight_kg: '體重',
  blood_glucose: '血糖',
  heart_rate: '心率',
  sleep_hours: '睡眠時數',
  steps: '每日步數',
}

function OutcomeRow({ outcome }: { outcome: Outcome }) {
  const label = METRIC_LABELS[outcome.metric_type] ?? outcome.metric_type
  const isImproved = outcome.outcome_label === 'improved'
  const isWorse = outcome.outcome_label === 'worse'

  const Icon = isImproved ? TrendingDown : isWorse ? TrendingUp : Minus
  const iconColor = isImproved ? 'text-emerald-500' : isWorse ? 'text-rose-500' : 'text-slate-400'
  const badgeClass = isImproved
    ? 'bg-emerald-50 text-emerald-700 border-emerald-100'
    : isWorse
      ? 'bg-rose-50 text-rose-700 border-rose-100'
      : 'bg-slate-50 text-slate-600 border-slate-100'
  const badgeLabel = isImproved ? '有改善' : isWorse ? '需注意' : '無明顯變化'

  const before = outcome.before_value != null ? outcome.before_value.toFixed(1) : '—'
  const after = outcome.after_value != null ? outcome.after_value.toFixed(1) : '—'
  const deltaPct = outcome.delta_pct != null ? `${outcome.delta_pct > 0 ? '+' : ''}${outcome.delta_pct.toFixed(1)}%` : null

  // Mini inline sparkline: before → after as two-point trend
  const sparkPoints =
    outcome.before_value != null && outcome.after_value != null
      ? [outcome.before_value, outcome.after_value]
      : null

  return (
    <div className="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0">
      <div className="flex items-center gap-2">
        <Icon className={`h-4 w-4 shrink-0 ${iconColor}`} />
        <div>
          <p className="text-sm font-medium text-slate-900">{label}</p>
          {sparkPoints && (
            <p className="text-xs text-slate-400">
              {before} → {after}
              {deltaPct && <span className={`ml-1 font-medium ${isImproved ? 'text-emerald-600' : isWorse ? 'text-rose-600' : ''}`}>{deltaPct}</span>}
            </p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Badge className={`shrink-0 border text-xs ${badgeClass}`}>{badgeLabel}</Badge>
        <span className="text-xs text-slate-400 whitespace-nowrap">{outcome.time_window_days}天</span>
      </div>
    </div>
  )
}

export function ActionOutcomeCard({ actionId }: { actionId: string }) {
  const [outcomes, setOutcomes] = useState<Outcome[]>([])
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    if (!actionId) return
    setLoading(true)
    api
      .getActionOutcomes(actionId)
      .then((data: unknown) => setOutcomes(Array.isArray(data) ? (data as Outcome[]) : []))
      .catch(() => setOutcomes([]))
      .finally(() => setLoading(false))
  }, [actionId])

  if (loading) {
    return (
      <div className="mt-3 rounded-xl border border-slate-100 bg-slate-50 p-4 text-xs text-slate-500 animate-pulse">
        正在載入健康成效…
      </div>
    )
  }

  if (!outcomes.length) return null

  const improved = outcomes.filter((o) => o.outcome_label === 'improved').length
  const total = outcomes.length
  const summary = improved > 0 ? `${improved} / ${total} 項指標有改善` : '目前尚無明顯改善'

  const visible = expanded ? outcomes : outcomes.slice(0, 2)

  return (
    <Card className="mt-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2 mb-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">健康成效追蹤</p>
          <p className="text-sm font-semibold text-slate-800">{summary}</p>
        </div>
        <Badge className={`text-xs border ${improved > 0 ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-slate-50 text-slate-600 border-slate-100'}`}>
          {improved > 0 ? '有成效' : '持續追蹤'}
        </Badge>
      </div>
      <div className="divide-y divide-slate-100">
        {visible.map((o, i) => (
          <OutcomeRow key={`${o.metric_type}-${o.time_window_days}-${i}`} outcome={o} />
        ))}
      </div>
      {outcomes.length > 2 && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 flex w-full items-center justify-center gap-1 text-xs text-sky-600 hover:text-sky-700"
          type="button"
        >
          {expanded ? (
            <>收起 <ChevronUp className="h-3 w-3" /></>
          ) : (
            <>查看全部 {outcomes.length} 項指標 <ChevronDown className="h-3 w-3" /></>
          )}
        </button>
      )}
    </Card>
  )
}
