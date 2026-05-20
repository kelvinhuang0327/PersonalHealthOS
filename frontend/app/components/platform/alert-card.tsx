'use client'

import { ShieldAlert } from 'lucide-react'
import { Card } from '../ui/card'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { useActions } from '../../providers/action-context'
import { ActionQuickCreate } from './action-quick-create'
import { ExplainabilityPanel } from './explainability-panel'

export function AlertCard({ alert }: { alert: any }) {
  const { createFromSource } = useActions()
  const urgency = alert.priority === 'high' || alert.priority === 'medium' || alert.priority === 'low'
    ? alert.priority
    : Number(alert.priority || 0) >= 9 || String(alert.severity || '').toLowerCase() === 'high'
    ? 'high'
    : Number(alert.priority || 0) >= 6
    ? 'medium'
    : 'low'
  const urgencyBadge = urgency === 'high' ? 'bg-rose-100 text-rose-700' : urgency === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-slate-200 text-slate-700'
  const whyNow = alert.whyNow?.[0] || alert.description || '這項風險提醒來自近期異常指標與規則判斷。'
  const bodyText = alert.description || alert.reason || alert.summary || '這項提醒需要優先處理。'
  return (
    <Card className="rounded-2xl border border-rose-100 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="bg-rose-100 text-rose-700">風險提醒</Badge>
        <Badge className={urgencyBadge}>{urgency === 'high' ? '最優先' : urgency === 'medium' ? '需要注意' : '一般提醒'}</Badge>
      </div>
      <div className="mt-3 flex items-start gap-3">
        <div className="rounded-2xl bg-rose-50 p-2 text-rose-600">
          <ShieldAlert className="h-4 w-4" />
        </div>
        <div className="flex-1">
          <p className="font-semibold text-slate-950">{alert.title}</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">{bodyText}</p>
        </div>
      </div>
      <div className="mt-4 rounded-2xl bg-rose-50 px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-rose-700">為什麼現在要處理</p>
        <p className="mt-1 text-sm text-rose-900">{whyNow}</p>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button className="bg-slate-900 hover:bg-slate-800" onClick={() => void createFromSource('alert', alert, 'in_progress')}>
          立即處理
        </Button>
      </div>
      <ActionQuickCreate onCreate={createFromSource} sourceType="alert" source={alert} />
      <ExplainabilityPanel explain={alert} />
    </Card>
  )
}
