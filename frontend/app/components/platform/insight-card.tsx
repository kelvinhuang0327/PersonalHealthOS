'use client'

import { useState } from 'react'
import { ChevronDown, Sparkles } from 'lucide-react'
import { Card } from '../ui/card'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { useActions } from '../../providers/action-context'
import { ActionQuickCreate } from './action-quick-create'
import { ExplainabilityPanel } from './explainability-panel'

export function InsightCard({ insight }: { insight: any }) {
  const [expanded, setExpanded] = useState(false)
  const { createFromSource } = useActions()
  const severity = String(insight.severity || 'info').toLowerCase()
  const severityClass = severity === 'high' || severity === 'warning' ? 'bg-rose-100 text-rose-700' : 'bg-sky-100 text-sky-700'
  const priority = insight.priority === 'high' || insight.priority === 'medium' || insight.priority === 'low'
    ? insight.priority
    : severity === 'high' || severity === 'warning'
    ? 'high'
    : Number(insight.priority || 0) >= 6
    ? 'medium'
    : 'low'
  const priorityClass = priority === 'high' ? 'bg-rose-100 text-rose-700' : priority === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-slate-200 text-slate-700'
  const confidence = typeof insight.confidence === 'number' ? insight.confidence : null
  const confidenceLabel = confidence == null ? '可信度未標示' : confidence >= 0.8 ? '可信度高' : confidence >= 0.65 ? '可信度中' : '可信度低'
  const severityLabel = severity === 'high' || severity === 'warning' ? '高風險' : severity === 'medium' ? '中風險' : '一般'
  const evidenceLabel = insight.evidence_level === 'A' ? '較強' : insight.evidence_level === 'B' ? '中等' : insight.evidence_level === 'C' ? '基礎' : '未標示'
  const whyNow = insight.whyNow?.[0] || insight.recommendation || insight.summary || '這則洞察已整理成可執行方向。'
  const summaryText = insight.summary || insight.reason || insight.reasoning || '這則洞察已整理成可執行方向。'
  return (
    <Card className="rounded-2xl p-5 transition hover:shadow-md">
      <div className="flex flex-wrap items-center gap-2">
        <Badge>洞察</Badge>
        {insight.severity ? <Badge className={severityClass}>{severityLabel}</Badge> : null}
        <Badge className={priorityClass}>{priority === 'high' ? '優先處理' : priority === 'medium' ? '建議本週' : '可後續安排'}</Badge>
        <p className="font-semibold text-slate-950">{insight.title}</p>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{summaryText}</p>
      <div className="mt-4 rounded-2xl bg-sky-50 px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">為什麼現在要做</p>
        <p className="mt-1 text-sm text-sky-950">{whyNow}</p>
      </div>
      {expanded ? (
        <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
          <p>類型: {insight.insight_type || '-'}</p>
          <p>生成時間: {insight.generated_at || '-'}</p>
          {insight.whyNow?.length > 1 ? <p>排序依據: {insight.whyNow.slice(1).join(' / ')}</p> : null}
        </div>
      ) : null}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <span>{confidenceLabel}</span>
        <span>證據等級：{evidenceLabel}</span>
      </div>
      <ActionQuickCreate onCreate={createFromSource} sourceType="insight" source={insight} />
      <Button type="button" className="mt-3 rounded-xl bg-slate-900 hover:bg-slate-800" onClick={() => setExpanded((v) => !v)}>
        <ChevronDown className="mr-2 h-4 w-4" />
        {expanded ? '收合說明' : '查看說明'}
      </Button>
      <div className="mt-2 inline-flex items-center gap-1 text-xs text-slate-500">
        <Sparkles className="h-3.5 w-3.5" />
        可展開依據說明
      </div>
      <ExplainabilityPanel explain={insight} />
    </Card>
  )
}
