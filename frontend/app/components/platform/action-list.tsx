import { HealthAction } from '../../../lib/actions'

import { StateCard } from './state-card'
import { ActionCard } from './action-card'

export function ActionList({
  actions,
  onChangeStatus,
}: {
  actions: HealthAction[]
  onChangeStatus: (id: string, status: HealthAction['status']) => void
}) {
  if (actions.length === 0) {
    return (
      <StateCard
        tone="info"
        compact
        title="目前沒有任務"
        description="先把一則洞察或提醒轉成行動，系統就會開始追蹤完成狀態與改善回饋。"
        actionLabel="前往洞察"
        href="/health-insights"
        badgeText="空狀態"
      />
    )
  }
  return (
    <div className="space-y-2">
      {actions.map((action) => (
        <ActionCard key={action.id} action={action} onChangeStatus={onChangeStatus} />
      ))}
    </div>
  )
}
