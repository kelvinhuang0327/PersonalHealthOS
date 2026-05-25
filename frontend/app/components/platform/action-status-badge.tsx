import { Badge } from '../ui/badge'

export function ActionStatusBadge({ status }: { status: string }) {
  const label =
    status === 'done'
      ? '已完成'
      : status === 'in_progress'
      ? '進行中'
      : status === 'snoozed'
      ? '已延後'
      : status === 'not_useful'
      ? '沒有用'
      : status === 'not_applicable'
      ? '不適合我'
      : '待處理'
  const className =
    status === 'done'
      ? 'bg-emerald-100 text-emerald-700'
      : status === 'in_progress'
      ? 'bg-amber-100 text-amber-700'
      : status === 'snoozed'
      ? 'bg-slate-200 text-slate-700'
      : status === 'not_useful'
      ? 'bg-orange-100 text-orange-700'
      : status === 'not_applicable'
      ? 'bg-slate-100 text-slate-500'
      : 'bg-sky-100 text-sky-700'
  return <Badge className={className}>{label}</Badge>
}
