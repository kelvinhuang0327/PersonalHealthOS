'use client'

import Link from 'next/link'
import { useState } from 'react'
import { ArrowRight, CircleAlert, Sparkles } from 'lucide-react'
import { DecisionItem } from '../../../lib/decision-support'
import { Button } from '../ui/button'
import { Card } from '../ui/card'
import { Badge } from '../ui/badge'

const priorityStyleMap = {
  high: 'bg-rose-100 text-rose-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-slate-200 text-slate-700',
} as const

const sourceLabelMap = {
  alert: '提醒',
  insight: '洞察',
  recommendation: '建議',
  action: '任務',
} as const

export function DecisionPanel({
  items,
  onStart,
  queueCount = 0,
}: {
  items: DecisionItem[]
  onStart: (item: DecisionItem) => Promise<void> | void
  queueCount?: number
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  return (
    <Card className="rounded-3xl border border-slate-200/80 bg-white/90 p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1 text-xs font-medium text-sky-700">
            <Sparkles className="h-3.5 w-3.5" />
            決策層
          </div>
          <h3 className="mt-3 text-xl font-semibold text-slate-950">你現在最該做的 3 件事</h3>
          <p className="mt-1 text-sm text-slate-500">先做最有影響力的事，不用自己判斷哪個比較急。</p>
        </div>
        <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
          <p>每個項目都經過風險、趨勢、拖延、可信度與醫療重要性加權排序。</p>
          <Link href="/platform/notifications" className="mt-2 inline-flex text-sky-700 hover:underline">
            查看全部待處理事項{queueCount > 0 ? `（${queueCount}）` : ''}
          </Link>
        </div>
      </div>

      <div className="mt-5 grid gap-3 xl:grid-cols-3">
        {items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500 xl:col-span-3">
            目前還沒有足夠資料產生優先決策，先新增一筆健康紀錄或上傳報告。
          </div>
        ) : null}
        {items.map((item, index) => (
          <div key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-slate-900 text-sm font-semibold text-white">
                  {index + 1}
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-slate-950">{item.title}</p>
                    <Badge className={priorityStyleMap[item.priority]}>{item.priority === 'high' ? '優先' : item.priority === 'medium' ? '本週' : '可安排'}</Badge>
                    <Badge>{sourceLabelMap[item.sourceType]}</Badge>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{item.reason}</p>
                </div>
              </div>
              <CircleAlert className="mt-1 h-4 w-4 shrink-0 text-slate-300" />
            </div>

            <div className="mt-4 flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-3 py-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">為什麼現在要處理</p>
                <p className="mt-1 text-sm text-slate-700">{item.whyNow[0] || `來自 ${item.category} 的優先訊號，現在處理能最快降低風險累積。`}</p>
              </div>
              <Button className="shrink-0 bg-slate-900 hover:bg-slate-800" onClick={() => onStart(item)}>
                {item.ctaLabel}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
            <div className="mt-3">
              <button
                type="button"
                className="text-sm font-medium text-sky-700 transition hover:text-sky-800"
                onClick={() => setExpandedId((current) => (current === item.id ? null : item.id))}
              >
                {expandedId === item.id ? '收合排序原因' : '查看排序原因'}
              </button>
              {expandedId === item.id ? (
                <div className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Decision explainability</p>
                  <div className="mt-3 space-y-2">
                    {item.whyNow.map((reason, reasonIndex) => (
                      <div key={`${item.id}-reason-${reasonIndex}`} className="flex gap-2 text-sm text-slate-700">
                        <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-700">
                          {reasonIndex + 1}
                        </span>
                        <span>{reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
