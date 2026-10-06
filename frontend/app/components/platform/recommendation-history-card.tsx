'use client'

import { AlertCircle, CheckCircle2, Clock, Minus, XCircle } from 'lucide-react'
import type { OutcomeFeedback, OutcomeFeedbackItem } from '../../../lib/api'
import { Card } from '../ui/card'

// ── Config ───────────────────────────────────────────────────────────────────

const FEEDBACK_STATUS_CONFIG: Record<
  OutcomeFeedbackItem['status'],
  { icon: React.ElementType; label: string; color: string; bg: string }
> = {
  completed:      { icon: CheckCircle2, label: '已完成',  color: 'text-emerald-600', bg: 'bg-emerald-50' },
  tracking:       { icon: Clock,        label: '追蹤中',  color: 'text-sky-600',     bg: 'bg-sky-50'     },
  not_useful:     { icon: XCircle,      label: '沒有用',  color: 'text-slate-500',   bg: 'bg-slate-50'   },
  not_applicable: { icon: Minus,        label: '不適合我', color: 'text-slate-500',   bg: 'bg-slate-50'   },
  snoozed:        { icon: AlertCircle,  label: '已延後',  color: 'text-amber-500',   bg: 'bg-amber-50'   },
}

const OUTCOME_STATUS_LABEL: Record<OutcomeFeedbackItem['outcome_status'], string> = {
  improved:         '已改善',
  unchanged:        '持平',
  deteriorated:     '需關注',
  insufficient_data:'資料不足',
  tracking:         '追蹤中',
  not_useful:       '沒有用',
  not_applicable:   '不適合',
  snoozed:          '已延後',
}

// ── Sub-components ────────────────────────────────────────────────────────────

function HistoryItem({ item }: { item: OutcomeFeedbackItem }) {
  const cfg = FEEDBACK_STATUS_CONFIG[item.status] ?? FEEDBACK_STATUS_CONFIG.tracking
  const Icon = cfg.icon
  const showOutcomeBadge =
    item.status === 'completed' &&
    item.outcome_status !== 'tracking'

  return (
    <div className={`flex items-start gap-3 rounded-xl p-3 ${cfg.bg}`}>
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${cfg.color}`} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className="truncate text-sm font-medium text-slate-800">{item.action_title}</p>
          <div className="flex shrink-0 gap-1">
            <span
              className={`rounded-full border border-slate-200 px-2 py-0.5 text-xs font-medium ${cfg.color}`}
            >
              {cfg.label}
            </span>
            {showOutcomeBadge && (
              <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-500">
                {OUTCOME_STATUS_LABEL[item.outcome_status]}
              </span>
            )}
          </div>
        </div>
        {item.explanation && (
          <p className="mt-0.5 line-clamp-2 text-xs text-slate-500">{item.explanation}</p>
        )}
        {(item.outcome_status === 'insufficient_data' || item.outcome_status === 'tracking') &&
          item.status === 'completed' && (
            <p className="mt-1 text-xs text-slate-400">目前尚無足夠後續資料判斷效果</p>
          )}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

type Props = {
  outcomes: OutcomeFeedbackItem[]
  summary: OutcomeFeedback['summary']
}

export default function RecommendationHistoryCard({ outcomes, summary }: Props) {
  const {
    improved_count = 0,
    insufficient_data_count = 0,
    not_useful_count = 0,
    not_applicable_count = 0,
    snoozed_count = 0,
    total_count = 0,
  } = summary

  const header = (
    <div>
      <h3 className="font-semibold text-slate-800">建議回饋紀錄</h3>
      <p className="mt-0.5 text-xs text-slate-500">過去 30 天的建議與你的回應</p>
    </div>
  )

  if (outcomes.length === 0) {
    return (
      <Card className="space-y-3 rounded-2xl p-5" data-testid="recommendation-history-card">
        {header}
        <div className="rounded-xl bg-slate-50 px-4 py-6 text-center">
          <p className="text-sm text-slate-500">目前還沒有足夠的建議回饋紀錄</p>
          <p className="mt-1 text-xs text-slate-400">完成或評估建議後，紀錄將顯示在這裡</p>
        </div>
        <p className="text-xs text-slate-400">
          回饋為使用者個人記錄，不代表醫療效果證明
        </p>
      </Card>
    )
  }

  return (
    <Card className="space-y-4 rounded-2xl p-5" data-testid="recommendation-history-card">
      {header}

      {/* Summary counts */}
      {total_count > 0 && (
        <div
          className="flex flex-wrap gap-3 rounded-xl bg-slate-50 px-4 py-2.5 text-sm"
          data-testid="history-summary-bar"
        >
          {improved_count > 0 && (
            <span className="flex items-center gap-1 font-medium text-emerald-600">
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
              改善 {improved_count}
            </span>
          )}
          {not_useful_count > 0 && (
            <span className="flex items-center gap-1 text-slate-500">
              <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
              沒有用 {not_useful_count}
            </span>
          )}
          {not_applicable_count > 0 && (
            <span className="flex items-center gap-1 text-slate-500">
              <Minus className="h-3.5 w-3.5" aria-hidden="true" />
              不適合 {not_applicable_count}
            </span>
          )}
          {snoozed_count > 0 && (
            <span className="flex items-center gap-1 text-amber-500">
              <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />
              延後 {snoozed_count}
            </span>
          )}
          {insufficient_data_count > 0 && (
            <span className="flex items-center gap-1 text-slate-400">
              資料不足 {insufficient_data_count}
            </span>
          )}
        </div>
      )}

      {/* Timeline items */}
      <div className="space-y-2">
        {outcomes.map((item) => (
          <HistoryItem key={item.action_id} item={item} />
        ))}
      </div>

      {/* Safe copy disclaimer */}
      <p className="text-xs text-slate-400">
        回饋為使用者個人記錄，不代表醫療效果證明
      </p>
    </Card>
  )
}
