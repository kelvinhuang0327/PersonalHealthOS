'use client'

import { ArrowUpRight, AlertCircle, FileText } from 'lucide-react'
import { Card } from '../ui/card'
import { Badge } from '../ui/badge'
import { useActions } from '../../providers/action-context'
import { ActionQuickCreate } from './action-quick-create'
import { ExplainabilityPanel } from './explainability-panel'
import { getActionExpectedEffect } from '../../../lib/actions'

const PRIORITY_LABEL: Record<string, string> = { high: '高', medium: '中', low: '低' }
const PRIORITY_CLS: Record<string, string> = {
  high: 'bg-red-50 text-red-700 border border-red-200',
  medium: 'bg-amber-50 text-amber-700 border border-amber-200',
  low: 'bg-slate-100 text-slate-600',
}

export function RecommendationCard({ recommendation }: { readonly recommendation: any }) {
  const { createFromSource } = useActions()
  const priority = recommendation.priority ?? 'low'
  const whyNow: string | string[] | undefined = recommendation.why_now
  let whyNowLines: string[]
  if (Array.isArray(whyNow)) {
    whyNowLines = whyNow
  } else if (whyNow) {
    whyNowLines = [whyNow]
  } else {
    whyNowLines = []
  }
  const nextAction: string | undefined = recommendation.next_action
  const evidenceSummary: string | undefined = recommendation.evidence_summary
  const dataInsufficiency: string | undefined = recommendation.data_insufficiency_reason
  const evidenceSources: Array<{ type?: string; summary?: string }> =
    Array.isArray(recommendation.evidence_sources) ? recommendation.evidence_sources : []

  return (
    <Card className="rounded-2xl border border-emerald-100 bg-emerald-50/80 p-5 shadow-sm">
      {/* Header row */}
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="bg-emerald-100 text-emerald-700">建議行動</Badge>
        {priority && (
          <Badge className={`border-none text-xs ${PRIORITY_CLS[priority] ?? PRIORITY_CLS.low}`}>
            {PRIORITY_LABEL[priority] ?? priority}優先
          </Badge>
        )}
      </div>

      {/* Title */}
      <div className="mt-3 flex items-start gap-3">
        <div className="rounded-2xl bg-white p-2 text-emerald-600 flex-shrink-0">
          <ArrowUpRight className="h-4 w-4" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-950">{recommendation.title || '先從這項開始改善'}</p>

          {/* Why this appears today */}
          {whyNowLines.length > 0 && (
            <ul className="mt-2 space-y-1">
              {whyNowLines.slice(0, 3).map((line) => (
                <li key={line} className="flex items-start gap-1.5 text-sm text-slate-700">
                  <span className="mt-2 h-1 w-1 flex-shrink-0 rounded-full bg-slate-400" />
                  {line}
                </li>
              ))}
            </ul>
          )}

          {/* Fallback description (legacy field) */}
          {whyNowLines.length === 0 && (recommendation.recommendation || recommendation.text) && (
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {recommendation.recommendation || recommendation.text}
            </p>
          )}
        </div>
      </div>

      {/* Evidence summary */}
      {evidenceSummary && (
        <div className="mt-3 flex items-center gap-1.5 rounded-lg bg-white/70 px-3 py-2">
          <FileText className="h-3.5 w-3.5 flex-shrink-0 text-slate-500" />
          <p className="text-xs text-slate-600">{evidenceSummary}</p>
        </div>
      )}

      {/* Evidence sources (raw tags) — if evidence_summary not shown */}
      {!evidenceSummary && evidenceSources.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {evidenceSources.slice(0, 3).map((src, i) => (
            // eslint-disable-next-line react/no-array-index-key -- evidence sources have no stable id
            <span key={`esrc_${i}`} className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-white/80 rounded text-[11px] text-slate-500">
              <FileText className="h-2.5 w-2.5" />
              {src.summary}
            </span>
          ))}
        </div>
      )}

      {/* Data insufficiency warning */}
      {dataInsufficiency && (
        <div className="mt-2 flex items-start gap-1.5 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2">
          <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 text-amber-600 mt-0.5" />
          <p className="text-xs text-amber-700">{dataInsufficiency}</p>
        </div>
      )}

      {/* Expected impact */}
      {recommendation.expected_health_impact && (
        <p className="mt-2 text-xs text-emerald-700 font-medium">
          預期效果：{recommendation.expected_health_impact}
        </p>
      )}

      {/* Next action CTA */}
      {nextAction && (
        <div className="mt-3 rounded-2xl bg-white/80 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">建議行動</p>
          <p className="mt-1 text-sm text-slate-700">{nextAction}</p>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            預期效果：
            {getActionExpectedEffect({
              action_type: 'lifestyle',
              category: recommendation.category,
            } as any)}
          </p>
        </div>
      )}

      {/* Fallback block (no next_action) */}
      {!nextAction && (
        <div className="mt-4 rounded-2xl bg-white/80 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">開始後會怎麼用</p>
          <p className="mt-1 text-sm text-slate-700">這項建議會轉成可追蹤任務，之後由 streak、提醒與回饋訊號來判斷是否有改善。</p>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            預期效果：
            {getActionExpectedEffect({
              action_type: 'lifestyle',
              category: recommendation.category,
            } as any)}
          </p>
        </div>
      )}

      <ActionQuickCreate onCreate={createFromSource} sourceType="recommendation" source={recommendation} />
      <ExplainabilityPanel explain={recommendation} />
    </Card>
  )
}
