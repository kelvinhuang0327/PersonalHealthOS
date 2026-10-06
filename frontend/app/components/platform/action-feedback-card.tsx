'use client'

import { useEffect, useState } from 'react'
import { CheckCircle2, TrendingDown, TrendingUp, Minus } from 'lucide-react'
import type { HealthAction } from '../../../lib/actions'
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
  outcome_label: 'improved' | 'no_change' | 'worse'
}

const METRIC_LABELS: Record<string, string> = {
  systolic_bp: '收縮壓',
  diastolic_bp: '舒張壓',
  weight_kg: '體重',
  sleep_hours: '睡眠時間',
  steps: '步數',
  blood_glucose: '血糖',
  heart_rate: '心率',
}

function SparkBar({ value, max, positive }: { value: number; max: number; positive: boolean }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
      <div
        className={`h-full rounded-full transition-all ${positive ? 'bg-emerald-400' : 'bg-rose-400'}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

function OutcomeRow({ outcome }: { outcome: Outcome }) {
  const label = METRIC_LABELS[outcome.metric_type] ?? outcome.metric_type
  const positive = outcome.outcome_label === 'improved'
  const Icon = positive ? TrendingDown : outcome.outcome_label === 'worse' ? TrendingUp : Minus
  const iconColor = positive ? 'text-emerald-500' : outcome.outcome_label === 'worse' ? 'text-rose-500' : 'text-slate-400'
  const delta = outcome.delta != null ? Math.abs(outcome.delta).toFixed(1) : null
  const deltaPct = outcome.delta_pct != null ? Math.abs(outcome.delta_pct).toFixed(1) : null

  return (
    <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-3">
      <Icon className={`h-4 w-4 flex-shrink-0 ${iconColor}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-medium text-slate-700">{label}</span>
          <Badge
            className={`border-none text-xs ${positive ? 'bg-emerald-100 text-emerald-700' : outcome.outcome_label === 'worse' ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-500'}`}
          >
            {outcome.outcome_label === 'improved' ? '改善' : outcome.outcome_label === 'worse' ? '惡化' : '無變化'}
          </Badge>
        </div>
        {delta && (
          <p className="mt-0.5 text-xs text-slate-500">
            變化 {outcome.outcome_label === 'improved' ? '↓' : '↑'} {delta}
            {deltaPct ? ` (${deltaPct}%)` : ''}｜{outcome.time_window_days} 天觀察
          </p>
        )}
        <SparkBar value={deltaPct ? parseFloat(deltaPct) : 50} max={100} positive={positive} />
      </div>
    </div>
  )
}

export function ActionFeedbackCard({ action }: { action: HealthAction }) {
  const [outcomes, setOutcomes] = useState<Outcome[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (action.status !== 'done') return
    setLoading(true)
    api
      .getActionOutcomes(action.id)
      .then((data) => setOutcomes(Array.isArray(data) ? data : []))
      .catch(() => setOutcomes([]))
      .finally(() => setLoading(false))
  }, [action.id, action.status])

  const streak = action.streak ?? action.streak_count ?? 0
  const impact = action.impact_status ?? 'no_change'

  return (
    <Card className="rounded-2xl border border-slate-200/80 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            <span className="font-semibold text-slate-900">{action.title}</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">{action.description}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge
            className={`border-none text-xs ${impact === 'improved' ? 'bg-emerald-100 text-emerald-700' : impact === 'worse' ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-500'}`}
          >
            {impact === 'improved' ? '有改善 ✓' : impact === 'worse' ? '需關注 !' : '無明顯變化'}
          </Badge>
          {streak > 0 && <Badge className="border-none bg-amber-100 text-amber-700 text-xs">連續 {streak} 天 🔥</Badge>}
        </div>
      </div>

      {action.status === 'done' && (
        <div className="mt-4">
          {loading ? (
            <p className="text-xs text-slate-400">正在計算效果...</p>
          ) : outcomes.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">行動效果</p>
              {outcomes.map((o, i) => (
                <OutcomeRow key={`${o.metric_type}-${o.time_window_days}-${i}`} outcome={o} />
              ))}
            </div>
          ) : (
            <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-500">
              行動完成後，系統將在 7 天、14 天、30 天後自動計算指標變化，並在此顯示效果。
            </p>
          )}
        </div>
      )}

      {/* Streak mini-chart */}
      {streak > 0 && (
        <div className="mt-3 flex items-end gap-1" aria-hidden="true">
          {Array.from({ length: Math.min(streak, 7) }, (_, i) => (
            <div
              key={i}
              className="w-2 rounded-full bg-amber-300"
              style={{ height: `${8 + i * 2.5}px`, opacity: 0.5 + i * 0.07 }}
            />
          ))}
          <span className="ml-1 text-xs text-slate-400">{streak} 天</span>
        </div>
      )}
    </Card>
  )
}
