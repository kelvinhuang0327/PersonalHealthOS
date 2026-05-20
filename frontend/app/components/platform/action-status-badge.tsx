import { Badge } from '../ui/badge'

export function ActionStatusBadge({ status }: { status: string }) {
  const label =
    status === 'done'
      ? '已完成'
      : status === 'in_progress'
      ? '進行中'
      : status === 'snoozed'
      ? '已延後'
      : '待處理'
  const className =
    status === 'done'
      ? 'bg-emerald-100 text-emerald-700'
      : status === 'in_progress'
      ? 'bg-amber-100 text-amber-700'
      : status === 'snoozed'
      ? 'bg-slate-200 text-slate-700'
      : 'bg-sky-100 text-sky-700'
  return <Badge className={className}>{label}</Badge>
}
