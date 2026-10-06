'use client'

import Link from 'next/link'
import { ArrowRight, CheckCircle2, ChevronRight, Sparkles, TrendingDown, TrendingUp, Minus, Zap } from 'lucide-react'

import type { HealthAction } from '../../../lib/actions'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Card } from '../ui/card'

// ── Mini spark-line ──────────────────────────────────────────────────────────
function SparkLine({ values, positive }: { values: number[]; positive: boolean }) {
  if (!values.length) return null
  const max = Math.max(...values, 1)
  const color = positive ? '#10b981' : '#f43f5e'
  return (
    <svg viewBox={`0 0 ${values.length * 8} 24`} className="h-6 overflow-visible" style={{ width: values.length * 8 }}>
      <polyline
        points={values.map((v, i) => `${i * 8 + 4},${24 - (v / max) * 20}`).join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// ── Feedback outcome pill ────────────────────────────────────────────────────
function OutcomePill({ label }: { label: 'improved' | 'no_change' | 'worse' | string }) {
  if (label === 'improved') return <Badge className="bg-emerald-100 text-emerald-800 border-none">有改善 ↑</Badge>
  if (label === 'worse') return <Badge className="bg-rose-100 text-rose-800 border-none">需注意 ↓</Badge>
  return <Badge className="bg-slate-100 text-slate-600 border-none">無明顯變化</Badge>
}

// ── Types ────────────────────────────────────────────────────────────────────
export type DailyDecisionSurfaceProps = {
  /** Single most important action right now */
  todayFocus: HealthAction | null
  /** Narrative v2/v3 delta_summary */
  deltaText: string
  /** Did we improve or worsen overall? */
  deltaDirection: 'improved' | 'no_change' | 'worse'
  /** Narrative v3 causes – why things changed */
  causes: string[]
  /** Next actions from narrative v3 */
  nextActions: string[]
  /** Missed opportunities */
  missedOpportunities: string[]
  /** Health score number */
  score?: number | null
  onCompleteAction: (id: string) => void
  onStartAction: (id: string) => void
}

export function DailyDecisionSurface({
  todayFocus,
  deltaText,
  deltaDirection,
  causes,
  nextActions,
  missedOpportunities,
  score,
  onCompleteAction,
  onStartAction,
}: DailyDecisionSurfaceProps) {
  const DeltaIcon =
    deltaDirection === 'improved' ? TrendingDown : deltaDirection === 'worse' ? TrendingUp : Minus
  const deltaColor =
    deltaDirection === 'improved' ? 'text-emerald-400' : deltaDirection === 'worse' ? 'text-rose-400' : 'text-slate-300'

  const streak = todayFocus?.streak ?? todayFocus?.streak_count ?? 0
  const sparkValues = streak > 0 ? Array.from({ length: Math.min(streak, 7) }, (_, i) => i + 1) : []

  return (
    <div className="space-y-4">
      {/* ── Section 1: Today's Focus ──────────────────────────────────────── */}
      <Card className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950 p-6 text-white shadow-lg">
        <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-cyan-400/5 blur-3xl" />
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-yellow-300" />
              <p className="text-xs font-semibold uppercase tracking-widest text-yellow-200">Today&apos;s Focus</p>
            </div>
            <p className="mt-1 text-xs text-slate-400">現在最重要的一件事</p>
          </div>
          {typeof score === 'number' && (
            <div className="rounded-xl bg-white/10 px-3 py-1.5 text-right">
              <p className="text-xs text-slate-400">健康分數</p>
              <p className="text-lg font-semibold text-white">{score}<span className="text-xs text-slate-400"> / 100</span></p>
            </div>
          )}
        </div>

        {todayFocus ? (
          <div className="mt-5 rounded-2xl bg-white/10 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className={`border-none text-xs ${todayFocus.priority === 'high' ? 'bg-rose-400/20 text-rose-200' : 'bg-white/15 text-slate-200'}`}>
                    {todayFocus.priority === 'high' ? '高優先' : todayFocus.priority === 'medium' ? '中優先' : '低優先'}
                  </Badge>
                  {streak > 0 && <Badge className="border-none bg-amber-400/20 text-amber-200">連續 {streak} 天 🔥</Badge>}
                  <OutcomePill label={todayFocus.impact_status ?? 'no_change'} />
                </div>
                <p className="mt-2 text-lg font-semibold text-white">{todayFocus.title}</p>
                <p className="mt-1 text-sm text-slate-300">{todayFocus.description}</p>
                {sparkValues.length > 0 && (
                  <div className="mt-3">
                    <SparkLine values={sparkValues} positive={true} />
                  </div>
                )}
              </div>
              <div className="flex flex-col gap-2">
                {todayFocus.status !== 'done' ? (
                  <>
                    <Button
                      className="bg-white text-slate-900 hover:bg-slate-100 py-2 px-3 text-xs"
                      onClick={() => onCompleteAction(todayFocus.id)}
                    >
                      <CheckCircle2 className="mr-1.5 h-4 w-4" />
                      完成
                    </Button>
                    {todayFocus.status === 'todo' && (
                      <Button
                        className="bg-transparent border border-white/20 text-white hover:bg-white/10 py-2 px-3 text-xs"
                        onClick={() => onStartAction(todayFocus.id)}
                      >
                        進行中
                      </Button>
                    )}
                  </>
                ) : (
                  <Badge className="bg-emerald-500/20 text-emerald-300 border-none px-3 py-1.5">
                    <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> 完成
                  </Badge>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-5 rounded-2xl bg-white/10 p-5 text-center">
            <Sparkles className="mx-auto h-6 w-6 text-cyan-300" />
            <p className="mt-2 text-sm text-slate-300">目前沒有待處理行動</p>
            <Link href="/platform/insights">
              <Button className="mt-3 bg-transparent border border-white/20 text-white hover:bg-white/10 py-2 px-3 text-xs">
                從洞察建立行動
              </Button>
            </Link>
          </div>
        )}
      </Card>

      {/* ── Section 2: Delta + Feedback ──────────────────────────────────── */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="rounded-2xl p-5">
          <div className="flex items-center gap-2">
            <DeltaIcon className={`h-4 w-4 ${deltaColor}`} />
            <h3 className="font-semibold text-slate-900">你最近有沒有變好？</h3>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{deltaText || '正在分析變化趨勢...'}</p>
          {causes.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">原因分析</p>
              {causes.slice(0, 2).map((cause, i) => (
                <p key={i} className="rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                  {cause}
                </p>
              ))}
            </div>
          )}
        </Card>

        <Card className="rounded-2xl p-5">
          <div className="flex items-center gap-2">
            <ArrowRight className="h-4 w-4 text-sky-500" />
            <h3 className="font-semibold text-slate-900">下一步該做什麼？</h3>
          </div>
          <div className="mt-3 space-y-2">
            {nextActions.length > 0 ? (
              nextActions.slice(0, 3).map((action, i) => (
                <div key={i} className="flex items-start gap-2 rounded-xl bg-sky-50 p-3">
                  <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-sky-200 text-xs font-bold text-sky-800">
                    {i + 1}
                  </span>
                  <p className="text-xs leading-5 text-slate-700">{action}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">正在計算下一步建議...</p>
            )}
          </div>
          {missedOpportunities.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-600">錯過的機會</p>
              <p className="mt-1.5 rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-800">
                {missedOpportunities[0]}
              </p>
            </div>
          )}
        </Card>
      </div>

      {/* ── Section 3: Quick link to full action center ───────────────────── */}
      <div className="flex items-center justify-end">
        <Link href="/platform/actions" className="flex items-center gap-1 text-sm font-medium text-sky-700 hover:underline">
          查看所有行動 <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  )
}
