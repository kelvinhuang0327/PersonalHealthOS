'use client'

import { HealthAction, getActionFeedbackSummary, getActionFeedbackTrend, getActionImpactMeta, getActionReminderMeta } from '../../../lib/actions'
import { Badge } from '../ui/badge'

export function ActionFeedbackBadge({ action, compact = false }: { action: HealthAction; compact?: boolean }) {
  const impact = getActionImpactMeta(action.impact_status)
  const reminder = getActionReminderMeta(action.reminder_status)
  const trend = getActionFeedbackTrend(action)
  const barColor =
    impact.tone === 'positive' ? 'bg-emerald-500' : impact.tone === 'warning' ? 'bg-rose-500' : 'bg-slate-400'

  return (
    <div className={`rounded-2xl border border-slate-200/80 bg-white/80 ${compact ? 'p-3' : 'p-4'}`}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge className={impact.badgeClass}>{impact.label}</Badge>
        {reminder ? <Badge className={reminder.badgeClass}>{reminder.label}</Badge> : null}
        <span className="text-xs text-slate-500">連續 {action.streak || 0} 天</span>
      </div>
      <div className="mt-3 flex items-end gap-1.5" aria-hidden="true">
        {trend.map((value, index) => (
          <span
            key={`${action.id}-${index}`}
            className={`w-2.5 rounded-full ${barColor}`}
            style={{ height: `${value * 0.42}px`, opacity: 0.55 + index * 0.08 }}
          />
        ))}
      </div>
      <p className={`mt-3 text-sm ${impact.tone === 'warning' ? 'text-rose-700' : 'text-slate-700'}`}>{getActionFeedbackSummary(action)}</p>
    </div>
  )
}
