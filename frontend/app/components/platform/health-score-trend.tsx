'use client'

import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { TrendingDown, TrendingUp, Minus } from 'lucide-react'
import { Card } from '../ui/card'
import { api } from '../../../lib/api'

interface HistoryPoint {
  date?: string
  calculated_at?: string
  overall_score: number
  cardiovascular_score?: number
  metabolic_score?: number
  weight_score?: number
  sleep_score?: number
  score_detail?: Record<string, unknown>
}

interface Props {
  currentScore?: number | null
  /** Pre-fetched history; if omitted, component fetches itself */
  history?: HistoryPoint[]
}

const COMPONENT_LABELS: Array<{ key: keyof HistoryPoint; label: string; color: string }> = [
  { key: 'cardiovascular_score', label: '心血管', color: '#ef4444' },
  { key: 'metabolic_score',      label: '代謝',   color: '#f59e0b' },
  { key: 'weight_score',         label: '活動',   color: '#3b82f6' },
  { key: 'sleep_score',          label: '睡眠',   color: '#8b5cf6' },
]

function scoreColor(score: number): string {
  if (score >= 75) return 'text-emerald-500'
  if (score >= 50) return 'text-amber-500'
  return 'text-rose-500'
}

function barColor(score: number): string {
  if (score >= 75) return 'bg-emerald-400'
  if (score >= 50) return 'bg-amber-400'
  return 'bg-rose-400'
}

export function HealthScoreTrend({ currentScore, history: propHistory }: Props) {
  const [history, setHistory] = useState<HistoryPoint[]>(propHistory ?? [])
  const [loading, setLoading] = useState(!propHistory)

  useEffect(() => {
    if (propHistory) return
    setLoading(true)
    api
      .getHealthScoreHistory(30)
      .then((data: unknown) => setHistory((data as HistoryPoint[]).slice().reverse()))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false))
  }, [propHistory])

  // Derive current score from history if not explicitly passed
  const latest = history[history.length - 1]
  const score = currentScore ?? latest?.overall_score ?? null
  const prevWeek = history.length >= 7 ? history[history.length - 7].overall_score : null
  const delta = score !== null && prevWeek !== null ? score - prevWeek : null

  const chartData = history.map((h) => ({
    date: new Date(h.calculated_at ?? h.date ?? '').toLocaleDateString('zh-TW', {
      month: 'numeric',
      day: 'numeric',
    }),
    score: h.overall_score,
  }))

  const hasEnoughData = history.length >= 7

  return (
    <Card className="space-y-4">
      {/* Top: score + trend arrow */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">健康分數</p>
          <div className="mt-1 flex items-end gap-2">
            <span className={`mono-data text-4xl font-bold ${score !== null ? scoreColor(score) : 'text-slate-300'}`}>
              {loading ? '…' : (score ?? '--')}
            </span>
            {delta !== null && (
              <div
                className={`mb-1 flex items-center gap-1 text-sm font-medium ${
                  delta > 0 ? 'text-emerald-500' : delta < 0 ? 'text-rose-500' : 'text-slate-400'
                }`}
              >
                {delta > 0 ? (
                  <TrendingUp className="h-4 w-4" />
                ) : delta < 0 ? (
                  <TrendingDown className="h-4 w-4" />
                ) : (
                  <Minus className="h-4 w-4" />
                )}
                {delta > 0 ? '+' : ''}{delta} 較上週
              </div>
            )}
          </div>
        </div>
        <p className="text-xs text-slate-400">近 30 天</p>
      </div>

      {/* Chart */}
      {!hasEnoughData ? (
        <div className="flex h-24 items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-400">
          繼續記錄以查看趨勢（需至少 7 筆資料）
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={96} className="sm:!h-[120px]">
          <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -28 }}>
            <defs>
              <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickLine={false} hide={typeof window !== 'undefined' ? window.innerWidth < 640 : false} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} tickLine={false} />
            <Tooltip
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
              formatter={(v: unknown) => [`${v} 分`, '健康分數']}
            />
            <Area
              type="monotone"
              dataKey="score"
              stroke="#06b6d4"
              strokeWidth={2}
              fill="url(#scoreGrad)"
              isAnimationActive
              animationDuration={800}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}

      {/* Component bars */}
      {latest && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {COMPONENT_LABELS.map(({ key, label, color }) => {
            const val = typeof latest[key] === 'number' ? (latest[key] as number) : null
            if (val === null) return null
            return (
              <div key={key} className="space-y-1">
                <div className="flex justify-between text-xs text-slate-500">
                  <span>{label}</span>
                  <span className={`font-semibold ${scoreColor(val)}`}>{val}</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full transition-all ${barColor(val)}`}
                    style={{ width: `${val}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}
