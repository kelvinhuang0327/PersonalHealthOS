'use client'

import { useEffect, useState } from 'react'
import { Activity, AlertCircle, CheckCircle2, ChevronRight, Minus, XCircle } from 'lucide-react'
import { Card } from '../ui/card'
import { Skeleton } from '../ui/skeleton'
import { api, type OutcomeFeedback, type OutcomeFeedbackItem } from '../../../lib/api'

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const WINDOWS = [7, 14, 30] as const
type WindowDays = 7 | 14 | 30

const STATUS_CONFIG: Record<
  OutcomeFeedbackItem['outcome_status'],
  { icon: React.ElementType; color: string; bg: string; label: string }
> = {
  improved: { icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50', label: '已改善' },
  unchanged: { icon: Minus, color: 'text-slate-500', bg: 'bg-slate-100', label: '持平' },
  deteriorated: { icon: XCircle, color: 'text-rose-600', bg: 'bg-rose-50', label: '需關注' },
  insufficient_data: { icon: AlertCircle, color: 'text-amber-600', bg: 'bg-amber-50', label: '資料不足' },
  tracking: { icon: Activity, color: 'text-sky-600', bg: 'bg-sky-50', label: '追蹤中' },
  not_useful: { icon: XCircle, color: 'text-slate-400', bg: 'bg-slate-50', label: '沒有用' },
  not_applicable: { icon: Minus, color: 'text-slate-400', bg: 'bg-slate-50', label: '不適合' },
  snoozed: { icon: AlertCircle, color: 'text-amber-500', bg: 'bg-amber-50', label: '已延後' },
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function OutcomeItemRow({ item }: { item: OutcomeFeedbackItem }) {
  const cfg = STATUS_CONFIG[item.outcome_status] ?? STATUS_CONFIG.tracking
  const Icon = cfg.icon

  return (
    <div className={`flex items-start gap-3 rounded-xl p-3 ${cfg.bg}`}>
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${cfg.color}`} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-slate-800">{item.action_title}</p>
        <p className="mt-0.5 text-xs text-slate-500">{item.explanation}</p>
        {item.actual_metric_change?.delta != null && (
          <p className={`mt-1 text-xs font-semibold ${cfg.color}`}>
            數據變化：
            {item.actual_metric_change.delta > 0 ? '+' : ''}
            {item.actual_metric_change.delta.toFixed(1)}
            {' '}（{item.actual_metric_change.metric_type}）
          </p>
        )}
        {item.next_check_in && (
          <p className="mt-1 text-xs text-slate-400">下次評估：{item.next_check_in}</p>
        )}
      </div>
      <span
        className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${cfg.color} border border-slate-200`}
      >
        {cfg.label}
      </span>
    </div>
  )
}

function SummaryBar({ summary }: { summary: OutcomeFeedback['summary'] }) {
  if (summary.total_count === 0) return null
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 px-4 py-2.5 text-sm">
      {summary.improved_count > 0 && (
        <span className="flex items-center gap-1 font-medium text-emerald-600">
          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
          改善 {summary.improved_count}
        </span>
      )}
      {summary.unchanged_count > 0 && (
        <span className="flex items-center gap-1 text-slate-500">
          <Minus className="h-3.5 w-3.5" aria-hidden="true" />
          持平 {summary.unchanged_count}
        </span>
      )}
      {summary.deteriorated_count > 0 && (
        <span className="flex items-center gap-1 font-medium text-rose-600">
          <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
          需關注 {summary.deteriorated_count}
        </span>
      )}
      {summary.insufficient_data_count > 0 && (
        <span className="flex items-center gap-1 text-amber-600">
          <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />
          資料不足 {summary.insufficient_data_count}
        </span>
      )}
      {summary.tracking_count > 0 && (
        <span className="flex items-center gap-1 text-sky-600">
          <Activity className="h-3.5 w-3.5" aria-hidden="true" />
          追蹤中 {summary.tracking_count}
        </span>
      )}
      {(summary.not_useful_count ?? 0) > 0 && (
        <span className="flex items-center gap-1 text-slate-400">
          <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
          沒有用 {summary.not_useful_count}
        </span>
      )}
      {(summary.not_applicable_count ?? 0) > 0 && (
        <span className="flex items-center gap-1 text-slate-400">
          <Minus className="h-3.5 w-3.5" aria-hidden="true" />
          不適合 {summary.not_applicable_count}
        </span>
      )}
      {(summary.snoozed_count ?? 0) > 0 && (
        <span className="flex items-center gap-1 text-amber-500">
          <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />
          延後 {summary.snoozed_count}
        </span>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main card
// ---------------------------------------------------------------------------

export default function OutcomeFeedbackCard() {
  const [windowDays, setWindowDays] = useState<WindowDays>(7)
  const [data, setData] = useState<OutcomeFeedback | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api
      .getOutcomeFeedback(windowDays)
      .then((d) => setData(d as OutcomeFeedback))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [windowDays])

  if (loading) {
    return (
      <Card className="space-y-3 rounded-2xl p-5">
        <Skeleton variant="text" className="h-5 w-36" />
        <Skeleton variant="card" className="h-16" />
        <Skeleton variant="card" className="h-16" />
      </Card>
    )
  }

  const summary = data?.summary
  const outcomes = data?.outcomes ?? []
  const completed = outcomes.filter((o) => o.status === 'completed')
  const tracking = outcomes.filter((o) => o.status === 'tracking')
  const dismissed = outcomes.filter(
    (o) => o.status === 'not_useful' || o.status === 'not_applicable' || o.status === 'snoozed',
  )

  return (
    <Card className="space-y-4 rounded-2xl p-5">
      {/* Header + window toggle */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-800">行動成效回饋</h3>
          <p className="mt-0.5 text-xs text-slate-500">做了有沒有差 — 預期 vs 實際</p>
        </div>
        <div className="flex gap-1">
          {WINDOWS.map((w) => (
            <button
              key={w}
              onClick={() => setWindowDays(w)}
              className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                windowDays === w
                  ? 'bg-sky-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {w}天
            </button>
          ))}
        </div>
      </div>

      {/* Summary bar */}
      {summary && <SummaryBar summary={summary} />}

      {/* Completed outcomes */}
      {completed.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">已完成行動</p>
          {completed.map((item) => (
            <OutcomeItemRow key={item.action_id} item={item} />
          ))}
        </div>
      )}

      {/* Tracking actions */}
      {tracking.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">追蹤中</p>
          {tracking.slice(0, 3).map((item) => (
            <OutcomeItemRow key={item.action_id} item={item} />
          ))}
          {tracking.length > 3 && (
            <button className="flex w-full items-center justify-center gap-1 pt-1 text-xs text-slate-400 hover:text-slate-600">
              還有 {tracking.length - 3} 個行動追蹤中
              <ChevronRight className="h-3 w-3" aria-hidden="true" />
            </button>
          )}
        </div>
      )}

      {/* Dismissed / snoozed feedback */}
      {dismissed.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">已回饋</p>
          {dismissed.map((item) => (
            <OutcomeItemRow key={item.action_id} item={item} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {outcomes.length === 0 && (
        <div className="rounded-xl bg-slate-50 px-4 py-6 text-center">
          <Activity className="mx-auto h-8 w-8 text-slate-300" aria-hidden="true" />
          <p className="mt-2 text-sm text-slate-500">過去 {windowDays} 天沒有需要評估的行動</p>
          <p className="mt-1 text-xs text-slate-400">完成健康行動後，這裡會顯示實際效果</p>
        </div>
      )}
    </Card>
  )
}
