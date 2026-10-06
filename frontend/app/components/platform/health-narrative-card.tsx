'use client'

import Link from 'next/link'
import { useState } from 'react'
import { ArrowRight, BrainCircuit, ChevronDown } from 'lucide-react'
import { Card } from '../ui/card'
import { Badge } from '../ui/badge'
import type { HealthAction } from '../../../lib/actions'

type HealthNarrativeBase = {
  summary: string
  risks: string[]
  trends: string[]
  reasons: string[]
  actions: string[]
}

type HealthNarrativeV2 = HealthNarrativeBase & {
  delta_summary?: string
  improvements?: string[]
  deteriorations?: string[]
  adherence?: string[]
  missed_risks?: string[]
}

export function HealthNarrativeCard({
  narrative,
  riskLevel,
  score,
  actions,
}: {
  narrative: HealthNarrativeV2
  riskLevel?: string
  score?: number | null
  actions?: HealthAction[]
}) {
  const [expanded, setExpanded] = useState(false)
  const normalizedRisk = String(riskLevel || 'stable').toLowerCase()
  const useV2 = Boolean(
    narrative.delta_summary || narrative.improvements?.length || narrative.deteriorations?.length || narrative.adherence?.length || narrative.missed_risks?.length
  )
  const riskTone =
    normalizedRisk === 'high' || normalizedRisk === 'elevated'
      ? 'bg-rose-100 text-rose-700'
      : normalizedRisk === 'moderate'
      ? 'bg-amber-100 text-amber-700'
      : 'bg-emerald-100 text-emerald-700'
  const actionAdherence = [
    ...(narrative.adherence || []),
    ...(actions || [])
      .filter((action) => action.status === 'done' || action.status === 'in_progress')
      .slice(0, 3)
      .map((action) =>
        action.status === 'done'
          ? `已完成「${action.title}」${action.streak ? `，連續 ${action.streak} 天` : ''}`
          : `「${action.title}」目前正在執行中`
      ),
  ]
  const deltaSummary = narrative.delta_summary || narrative.summary
  const improvements = narrative.improvements || narrative.actions.slice(0, 2)
  const deteriorations = narrative.deteriorations || narrative.risks.slice(0, 2)
  const missedRisks = narrative.missed_risks || narrative.reasons.slice(0, 2)

  return (
    <Card className="rounded-3xl border border-slate-200/80 bg-gradient-to-br from-white to-sky-50/70 p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-3 py-1 text-xs font-medium text-white">
            <BrainCircuit className="h-3.5 w-3.5" />
            Health Narrative
          </div>
          <h3 className="mt-3 text-xl font-semibold text-slate-950">你的健康正在發生什麼</h3>
          <p className="mt-1 text-sm text-slate-500">先看結論、再看原因，最後直接轉成今天可以做的事。</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={riskTone}>風險 {normalizedRisk.toUpperCase()}</Badge>
          {typeof score === 'number' ? <Badge>健康分數 {score} / 100</Badge> : null}
          {useV2 ? <Badge className="bg-sky-100 text-sky-700">追蹤變化中</Badge> : null}
        </div>
      </div>

      {useV2 ? (
        <>
          <div className="mt-5 rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">本次變化</p>
            <p className="mt-2 text-lg font-semibold leading-8 text-slate-950">{deltaSummary}</p>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div className="rounded-3xl border border-emerald-100 bg-emerald-50/70 p-5 shadow-sm">
              <div className="flex items-center justify-between gap-2">
                <h4 className="font-semibold text-emerald-950">有變好的地方</h4>
                <Badge className="bg-emerald-100 text-emerald-700">{Math.min(2, improvements.length)} 項</Badge>
              </div>
              <div className="mt-4 space-y-3">
                {improvements.slice(0, 2).map((item, index) => (
                  <div key={`${index}-${item}`} className="rounded-2xl border border-emerald-100 bg-white/80 px-4 py-3">
                    <p className="text-sm leading-6 text-slate-700">{item}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-3xl border border-rose-100 bg-rose-50/70 p-5 shadow-sm">
              <div className="flex items-center justify-between gap-2">
                <h4 className="font-semibold text-rose-950">還要留意的地方</h4>
                <Badge className="bg-rose-100 text-rose-700">{Math.min(2, deteriorations.length)} 項</Badge>
              </div>
              <div className="mt-4 space-y-3">
                {deteriorations.slice(0, 2).map((item, index) => (
                  <div key={`${index}-${item}`} className="rounded-2xl border border-rose-100 bg-white/80 px-4 py-3">
                    <p className="text-sm leading-6 text-slate-700">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-4 rounded-3xl border border-slate-200 bg-slate-950 p-5 text-white shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <h4 className="font-semibold">現在最該做的 3 件事</h4>
              <Badge className="bg-white/10 text-white">{Math.min(3, narrative.actions.length)} actions</Badge>
            </div>
            <div className="mt-4 space-y-3">
              {narrative.actions.slice(0, 3).map((action, index) => (
                <div key={`${index}-${action}`} className="rounded-2xl bg-white/10 px-4 py-3">
                  <div className="flex gap-3">
                    <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-900">
                      {index + 1}
                    </div>
                    <p className="text-sm leading-6 text-slate-100">{action}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <>
          <div className="mt-5 rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Summary</p>
            <p className="mt-2 text-lg font-semibold leading-8 text-slate-950">{narrative.summary}</p>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <div className="flex items-center justify-between gap-2">
                <h4 className="font-semibold text-slate-950">你現在最需要留意的風險</h4>
                <Badge>{Math.min(2, narrative.risks.length)} 項重點</Badge>
              </div>
              <div className="mt-4 space-y-3">
                {narrative.risks.slice(0, 2).map((risk, index) => (
                  <div key={`${index}-${risk}`} className="rounded-2xl border border-rose-100 bg-rose-50/70 px-4 py-3">
                    <p className="text-sm leading-6 text-slate-700">{risk}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-slate-950 p-5 text-white shadow-sm">
              <div className="flex items-center justify-between gap-2">
                <h4 className="font-semibold">現在最該做的 3 件事</h4>
                <Badge className="bg-white/10 text-white">{Math.min(3, narrative.actions.length)} actions</Badge>
              </div>
              <div className="mt-4 space-y-3">
                {narrative.actions.slice(0, 3).map((action, index) => (
                  <div key={`${index}-${action}`} className="rounded-2xl bg-white/10 px-4 py-3">
                    <div className="flex gap-3">
                      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-900">
                        {index + 1}
                      </div>
                      <p className="text-sm leading-6 text-slate-100">{action}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      <div className="mt-4 rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-sm">
        <button
          type="button"
          className="flex w-full items-center justify-between text-left"
          onClick={() => setExpanded((current) => !current)}
        >
          <div>
            <h4 className="font-semibold text-slate-950">為什麼系統會這樣判斷</h4>
            <p className="mt-1 text-sm text-slate-500">展開後會看到最近變化與背後原因，幫你理解這段健康故事。</p>
          </div>
          <ChevronDown className={`h-5 w-5 text-slate-400 transition ${expanded ? 'rotate-180' : ''}`} />
        </button>

        {expanded ? (
          useV2 ? (
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Adherence</p>
                <div className="mt-3 space-y-3">
                  {actionAdherence.slice(0, 3).map((item, index) => (
                    <div key={`${index}-${item}`} className="rounded-2xl border border-emerald-100 bg-emerald-50/60 px-4 py-3">
                      <p className="text-sm leading-6 text-slate-700">{item}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">被忽略的風險</p>
                <div className="mt-3 space-y-3">
                  {missedRisks.slice(0, 3).map((item, index) => (
                    <div key={`${index}-${item}`} className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
                      <p className="text-sm leading-6 text-slate-700">{item}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Trends</p>
                <div className="mt-3 space-y-3">
                  {narrative.trends.map((item, index) => (
                    <div key={`${index}-${item}`} className="rounded-2xl border border-sky-100 bg-sky-50/60 px-4 py-3">
                      <p className="text-sm leading-6 text-slate-700">{item}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Reasons</p>
                <div className="mt-3 space-y-3">
                  {narrative.reasons.map((item, index) => (
                    <div key={`${index}-${item}`} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <p className="text-sm leading-6 text-slate-700">{item}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )
        ) : null}
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-slate-950 px-4 py-4 text-white">
        <div>
          <p className="text-sm font-semibold">先把敘事裡的行動做出來，系統才會形成真正的回饋閉環。</p>
          <p className="mt-1 text-sm text-slate-300">完成任務後，我們會再比對風險、趨勢與提醒狀態是否有改善。</p>
        </div>
        <Link
          href="/platform/actions"
          className="inline-flex items-center justify-center rounded-2xl bg-white px-4 py-3 text-sm font-semibold text-slate-900 shadow-sm transition hover:bg-slate-100"
        >
          查看今日行動
          <ArrowRight className="ml-2 h-4 w-4" />
        </Link>
      </div>
    </Card>
  )
}
