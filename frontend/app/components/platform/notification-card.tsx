'use client'

import { useState } from 'react'
import { ChevronDown, CircleAlert } from 'lucide-react'
import type { NotificationItem } from '../../../lib/decision-support'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Card } from '../ui/card'

const sourceLabelMap = {
  alert: '提醒',
  insight: '洞察',
  recommendation: '建議',
  action: '任務',
} as const

export function NotificationCard({
  item,
  onStart,
  onTrack,
  onSnooze,
}: {
  item: NotificationItem
  onStart: (item: NotificationItem) => Promise<void> | void
  onTrack: (item: NotificationItem) => Promise<void> | void
  onSnooze: (item: NotificationItem) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const priorityTone =
    item.priority === 'high'
      ? 'border-rose-200 bg-rose-50/70'
      : item.priority === 'medium'
      ? 'border-amber-200 bg-amber-50/70'
      : 'border-slate-200 bg-white'
  const priorityBadge =
    item.priority === 'high'
      ? 'bg-rose-100 text-rose-700'
      : item.priority === 'medium'
      ? 'bg-amber-100 text-amber-700'
      : 'bg-slate-200 text-slate-700'
  const snoozedUntilLabel = item.snoozed_until ? new Date(item.snoozed_until).toLocaleString('zh-TW') : null

  return (
    <Card className={`rounded-2xl border p-5 shadow-sm ${priorityTone}`} data-testid={`notification-card-${item.sourceType}-${item.id}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge className={priorityBadge}>{item.priority === 'high' ? '最優先' : item.priority === 'medium' ? '需要注意' : '低優先'}</Badge>
            <Badge>{sourceLabelMap[item.sourceType]}</Badge>
            {item.resurfaced ? <Badge className="bg-sky-100 text-sky-700">已重新提醒</Badge> : null}
            {item.snoozed_until ? <Badge className="bg-slate-200 text-slate-700">已暫停提醒</Badge> : null}
          </div>
          <p className="mt-3 text-lg font-semibold text-slate-950">{item.title}</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">{item.reason}</p>
        </div>
        <CircleAlert className={`mt-1 h-4 w-4 shrink-0 ${item.priority === 'high' ? 'text-rose-400' : item.priority === 'medium' ? 'text-amber-400' : 'text-slate-300'}`} />
      </div>

      <div className="mt-4 rounded-2xl bg-white/85 px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">為什麼現在要處理</p>
        <p className="mt-1 text-sm text-slate-800">{item.whyNow[0] || '這項事情現在值得先處理。'}</p>
        {snoozedUntilLabel ? <p className="mt-2 text-xs text-slate-500">恢復提醒時間：{snoozedUntilLabel}</p> : null}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={() => onStart(item)}>開始改善</Button>
        <Button className="bg-sky-600 hover:bg-sky-700" onClick={() => onTrack(item)}>加入追蹤</Button>
        <Button className="bg-slate-600 hover:bg-slate-700" onClick={() => onSnooze(item)}>稍後提醒</Button>
      </div>

      <div className="mt-3">
        <button
          type="button"
          className="text-sm font-medium text-sky-700 transition hover:text-sky-800"
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? '收合原因' : '查看原因'}
        </button>
        {expanded ? (
          <div className="mt-3 rounded-2xl border border-slate-200 bg-white/85 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Explainability</p>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p>風險來源：{item.breakdown.risk_severity.reason}</p>
              <p>趨勢：{item.breakdown.trend.reason}</p>
              <p>是否逾期：{item.breakdown.overdue.reason}</p>
              {item.snoozed_until ? <p>恢復提醒：{snoozedUntilLabel}</p> : null}
              {item.resurfaced ? <p>重新提醒：稍後提醒時間已到，所以它回到待處理中心。</p> : null}
            </div>
          </div>
        ) : null}
      </div>
    </Card>
  )
}
