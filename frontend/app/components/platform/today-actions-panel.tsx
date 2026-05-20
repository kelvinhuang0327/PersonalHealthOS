'use client'

import Link from 'next/link'
import { useMemo } from 'react'
import { useActions } from '../../providers/action-context'
import { Card } from '../ui/card'
import { ActionStatusBadge } from './action-status-badge'
import { ActionFeedbackBadge } from './action-feedback-badge'

export function TodayActionsPanel({ notificationsCount = 0 }: { notificationsCount?: number }) {
  const { actions } = useActions()
  const todayActions = useMemo(
    () => actions.filter((a) => a.status === 'todo' || a.status === 'in_progress').slice(0, 5),
    [actions]
  )
  const habitStreakSummary = useMemo(() => actions.filter((a) => (a.streak || 0) > 0).reduce((acc, a) => acc + (a.streak || 0), 0), [actions])
  const overdueCount = useMemo(() => actions.filter((a) => a.reminder_status === 'overdue').length, [actions])
  const improvedCount = useMemo(() => actions.filter((a) => a.impact_status === 'improved').length, [actions])
  return (
    <Card className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">今日任務</h3>
        <div className="flex items-center gap-3 text-sm">
          <Link href="/platform/notifications" className="text-sky-600 hover:underline">
            查看全部待處理事項{notificationsCount > 0 ? `（${notificationsCount}）` : ''}
          </Link>
          <Link href="/platform/actions" className="text-slate-600 hover:underline">查看全部任務</Link>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
          <div className="rounded-xl bg-sky-50 p-3">今日任務 <strong className="block text-lg text-slate-950">{todayActions.length}</strong></div>
        <div className="rounded-xl bg-amber-50 p-3">逾期任務 <strong className="block text-lg text-slate-950">{overdueCount}</strong></div>
        <div className="rounded-xl bg-emerald-50 p-3">改善狀態 <strong className="block text-lg text-slate-950">{improvedCount}</strong></div>
      </div>
      <div className="mt-2 rounded-xl bg-slate-50 p-3 text-xs text-slate-600">
        習慣 streak 總數 <strong>{habitStreakSummary}</strong>，完成任務後系統會用 impact 與 reminder 訊號更新回饋。
      </div>
      <div className="mt-2 space-y-2">
        {todayActions.length === 0 ? <p className="text-sm text-slate-500">今天沒有待處理任務</p> : null}
        {todayActions.map((a) => (
          <div key={a.id} className="rounded-xl border border-slate-200 p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium">{a.title}</p>
              <ActionStatusBadge status={a.status} />
            </div>
            <p className="text-xs text-slate-500">{a.description}</p>
            <p className="mt-1 text-xs text-slate-500">連續完成 {a.streak || 0} 次 / 頻率 {a.frequency || '-'}</p>
            <div className="mt-3">
              <ActionFeedbackBadge action={a} compact />
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
