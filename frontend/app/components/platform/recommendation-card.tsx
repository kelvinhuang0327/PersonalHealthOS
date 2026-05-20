'use client'

import { ArrowUpRight } from 'lucide-react'
import { Card } from '../ui/card'
import { Badge } from '../ui/badge'
import { useActions } from '../../providers/action-context'
import { ActionQuickCreate } from './action-quick-create'
import { ExplainabilityPanel } from './explainability-panel'
import { getActionExpectedEffect } from '../../../lib/actions'

export function RecommendationCard({ recommendation }: { recommendation: any }) {
  const { createFromSource } = useActions()
  return (
    <Card className="rounded-2xl border border-emerald-100 bg-emerald-50/80 p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="bg-emerald-100 text-emerald-700">建議行動</Badge>
        {recommendation.priority ? <Badge className="bg-white text-slate-700">priority {recommendation.priority}</Badge> : null}
      </div>
      <div className="mt-3 flex items-start gap-3">
        <div className="rounded-2xl bg-white p-2 text-emerald-600">
          <ArrowUpRight className="h-4 w-4" />
        </div>
        <div className="flex-1">
          <p className="font-semibold text-slate-950">{recommendation.title || '先從這項開始改善'}</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{recommendation.recommendation || recommendation.text}</p>
        </div>
      </div>
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
      <ActionQuickCreate onCreate={createFromSource} sourceType="recommendation" source={recommendation} />
      <ExplainabilityPanel explain={recommendation} />
    </Card>
  )
}
