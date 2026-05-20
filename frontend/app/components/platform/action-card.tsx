'use client'

import { useState } from 'react'
import { BookOpen, Brain, Clock, Sparkles, TriangleAlert } from 'lucide-react'
import { HealthAction, getActionExpectedEffect } from '../../../lib/actions'
import { Button } from '../ui/button'
import { Card } from '../ui/card'
import { ActionDrawer } from './action-drawer'
import { ActionOutcomeCard } from './action-outcome-card'
import { ActionStatusBadge } from './action-status-badge'
import { Badge } from '../ui/badge'
import { ActionFeedbackBadge } from './action-feedback-badge'

// ── Due-date urgency helpers ───────────────────────────────────────────────────
function getDueDateUrgency(dueDateStr: string | null | undefined): {
  label: string | null
  borderCls: string
  bgCls: string
  shakeCls: string
} {
  if (!dueDateStr) return { label: null, borderCls: '', bgCls: '', shakeCls: '' }
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(dueDateStr)
  due.setHours(0, 0, 0, 0)
  const diffDays = Math.round((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays < 0) {
    return {
      label: `已逾期 ${Math.abs(diffDays)} 天`,
      borderCls: 'border-rose-400',
      bgCls: 'bg-rose-50/40',
      shakeCls: 'hover:animate-[shake_0.4s_ease-in-out]',
    }
  }
  if (diffDays === 0) {
    return { label: '今天截止', borderCls: 'border-amber-400', bgCls: '', shakeCls: '' }
  }
  if (diffDays <= 3) {
    return { label: `${diffDays} 天後截止`, borderCls: 'border-amber-200', bgCls: 'bg-amber-50/30', shakeCls: '' }
  }
  return { label: null, borderCls: '', bgCls: '', shakeCls: '' }
}

// ── Source metadata ────────────────────────────────────────────────────────────
const SOURCE_META: Record<string, { label: string; icon: React.ElementType; cls: string }> = {
  alert:          { label: '系統建議・風險警示', icon: TriangleAlert, cls: 'bg-rose-50 text-rose-600 border-rose-200' },
  insight:        { label: '系統建議・AI 洞察', icon: Brain,         cls: 'bg-violet-50 text-violet-600 border-violet-200' },
  recommendation: { label: '系統建議',          icon: Sparkles,     cls: 'bg-sky-50 text-sky-600 border-sky-200' },
  manual:         { label: '你自己建立',         icon: BookOpen,     cls: 'bg-slate-100 text-slate-500 border-slate-200' },
}

const PRIORITY_CLS: Record<string, string> = {
  high:   'bg-rose-100 text-rose-700',
  medium: 'bg-amber-100 text-amber-700',
  low:    'bg-slate-100 text-slate-600',
}
const PRIORITY_LABEL: Record<string, string> = { high: '高優先', medium: '本週處理', low: '一般追蹤' }

const REMINDER_CLS: Record<string, string> = {
  overdue:      'bg-amber-100 text-amber-700',
  risk_up:      'bg-rose-100 text-rose-700',
  streak_break: 'bg-orange-100 text-orange-700',
  no_data:      'bg-slate-100 text-slate-600',
}
const REMINDER_LABEL: Record<string, string> = {
  overdue:      '已逾期',
  risk_up:      '風險上升',
  streak_break: '連續中斷',
  no_data:      '待記錄',
}

export function ActionCard({
  action,
  onChangeStatus,
}: {
  action: HealthAction
  onChangeStatus: (id: string, status: HealthAction['status']) => void
}) {
  const [open, setOpen] = useState(false)

  const sm = SOURCE_META[action.source_type] ?? SOURCE_META['manual']
  const SourceIcon = sm.icon
  const priorityCls = PRIORITY_CLS[action.priority] ?? PRIORITY_CLS['low']
  const priorityLabel = PRIORITY_LABEL[action.priority] ?? '一般追蹤'
  const reminderCls = action.reminder_status ? REMINDER_CLS[action.reminder_status] : null
  const reminderLabel = action.reminder_status ? REMINDER_LABEL[action.reminder_status] : null
  const due = getDueDateUrgency(action.due_date)

  return (
    <Card
      className={`rounded-2xl border bg-white p-4 shadow-sm ${due.borderCls || 'border-slate-200/80'} ${due.bgCls} ${due.shakeCls}`}
    >
      {/* Source label + priority + reminder + due-date */}
      <div className="mb-2 flex flex-wrap items-center gap-1.5 sm:gap-2">
        <Badge className={`flex items-center gap-1 border text-xs ${sm.cls}`}>
          <SourceIcon className="h-3 w-3" />
          {sm.label}
        </Badge>
        <Badge className={`border-none text-xs ${priorityCls}`}>{priorityLabel}</Badge>
        {reminderCls && reminderLabel && (
          <Badge className={`border-none text-xs ${reminderCls}`}>{reminderLabel}</Badge>
        )}
        {due.label && (
          <Badge
            className={`flex items-center gap-1 border-none text-xs ${
              due.label.startsWith('已逾期')
                ? 'bg-rose-100 text-rose-700'
                : due.label === '今天截止'
                ? 'bg-amber-100 text-amber-700'
                : 'bg-amber-50 text-amber-600'
            }`}
          >
            <Clock className="h-3 w-3" />
            {due.label}
          </Badge>
        )}
        {action.evidence_level && (
          <Badge className="border-none bg-slate-100 text-xs text-slate-500">臨床{action.evidence_level}級</Badge>
        )}
      </div>

      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-950">{action.title}</p>
          <p className="mt-1 text-sm leading-6 text-slate-600">{action.description}</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">預期效果：{getActionExpectedEffect(action)}</p>
        </div>
        <ActionStatusBadge status={action.status} />
      </div>
      <div className="mt-3">
        <ActionFeedbackBadge action={action} compact />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {action.status !== 'done' ? <Button className="min-h-11 bg-emerald-500 hover:bg-emerald-600" onClick={() => onChangeStatus(action.id, 'done')}>打卡</Button> : null}
        {action.status === 'todo' ? <Button className="min-h-11 bg-amber-600 hover:bg-amber-700" onClick={() => onChangeStatus(action.id, 'in_progress')}>進行中</Button> : null}
        {action.status !== 'snoozed' ? <Button className="min-h-11 bg-slate-600 hover:bg-slate-700" onClick={() => onChangeStatus(action.id, 'snoozed')}>稍後提醒</Button> : null}
        {action.status !== 'todo' ? <Button className="min-h-11 bg-sky-600 hover:bg-sky-700" onClick={() => onChangeStatus(action.id, 'todo')}>改回待辦</Button> : null}
        <Button className="min-h-11 bg-slate-700 hover:bg-slate-800 sm:ml-auto" onClick={() => setOpen((v) => !v)}>{open ? '收合細節' : '查看細節'}</Button>
      </div>
      {open ? <ActionDrawer action={action} /> : null}
      {action.status === 'done' ? <ActionOutcomeCard actionId={action.id} /> : null}
    </Card>
  )
}
