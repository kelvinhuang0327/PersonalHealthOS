'use client'

import { HealthAction, getActionExpectedEffect } from '../../../lib/actions'
import { Button } from '../ui/button'
import { Card } from '../ui/card'

export function TodaySummaryCard({
  actions,
  alertsCount,
  recommendationText,
  onQuickComplete,
  onJoinTracking,
}: {
  actions: HealthAction[]
  alertsCount: number
  recommendationText?: string
  onQuickComplete: (id: string) => void
  onJoinTracking?: () => void
}) {
  const completed = actions.filter((a) => a.status === 'done').length
  const pending = actions.filter((a) => a.status !== 'done').length
  const quickTasks = actions.filter((a) => a.status === 'todo' || a.status === 'in_progress').slice(0, 2)

  return (
    <Card>
      <h3 className="font-semibold">今日摘要</h3>
      <div className="mt-2 flex flex-wrap gap-2">
        {onJoinTracking ? (
          <Button className="bg-slate-900 hover:bg-slate-800" onClick={onJoinTracking}>
            加入追蹤
          </Button>
        ) : null}
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-lg bg-sky-50 p-2">今日任務: <strong>{actions.length}</strong></div>
        <div className="rounded-lg bg-emerald-50 p-2">已完成: <strong>{completed}</strong></div>
        <div className="rounded-lg bg-slate-100 p-2">未完成: <strong>{pending}</strong></div>
        <div className="rounded-lg bg-rose-50 p-2">今日風險: <strong>{alertsCount}</strong></div>
      </div>
      <p className="mt-2 text-xs text-slate-600">今日建議：{recommendationText || '先完成一項追蹤任務'}</p>
      <div className="mt-2 space-y-2">
        {quickTasks.map((task) => (
          <div key={task.id} className="flex items-center justify-between rounded-xl border border-slate-200 p-2">
            <div>
              <span className="text-sm">{task.title}</span>
              <p className="mt-1 text-xs text-slate-500">預期效果：{getActionExpectedEffect(task)}</p>
            </div>
            <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={() => onQuickComplete(task.id)}>
              快速完成
            </Button>
          </div>
        ))}
      </div>
    </Card>
  )
}
