'use client'

import { useState } from 'react'
import type { NotificationItem } from '../../../lib/decision-support'
import { Badge } from '../ui/badge'
import { Card } from '../ui/card'
import { NotificationCard } from './notification-card'
import { StateCard } from './state-card'

export function NotificationsSection({
  title,
  description,
  items,
  tone = 'default',
  collapsible = false,
  defaultCollapsed = false,
  emptyText,
  onStart,
  onTrack,
  onSnooze,
  testId,
}: {
  title: string
  description: string
  items: NotificationItem[]
  tone?: 'urgent' | 'attention' | 'low' | 'default'
  collapsible?: boolean
  defaultCollapsed?: boolean
  emptyText: string
  onStart: (item: NotificationItem) => Promise<void> | void
  onTrack: (item: NotificationItem) => Promise<void> | void
  onSnooze: (item: NotificationItem) => void
  testId?: string
}) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed)
  const toneClass =
    tone === 'urgent'
      ? 'border-rose-200 bg-rose-50/60'
      : tone === 'attention'
      ? 'border-amber-200 bg-amber-50/60'
      : tone === 'low'
      ? 'border-slate-200 bg-slate-50/70'
      : 'border-slate-200 bg-white'

  return (
    <Card className={`rounded-3xl border p-5 shadow-sm ${toneClass}`} data-testid={testId}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-xl font-semibold text-slate-950">{title}</h3>
            <Badge>{items.length}</Badge>
          </div>
          <p className="mt-1 text-sm text-slate-500">{description}</p>
        </div>
        {collapsible ? (
          <button
            type="button"
            className="text-sm font-medium text-slate-600 transition hover:text-slate-900"
            onClick={() => setCollapsed((current) => !current)}
          >
            {collapsed ? '展開' : '收合'}
          </button>
        ) : null}
      </div>

      {!collapsed ? (
        <div className="mt-4 space-y-3">
          {items.length === 0 ? (
            <StateCard tone="neutral" compact title={title} description={emptyText} badgeText="目前沒有項目" />
          ) : null}
          {items.map((item) => (
            <NotificationCard key={`${item.sourceType}-${item.id}`} item={item} onStart={onStart} onTrack={onTrack} onSnooze={onSnooze} />
          ))}
        </div>
      ) : (
        <div className="mt-4 rounded-2xl border border-dashed border-slate-200 bg-white/80 px-4 py-4 text-sm text-slate-500">
          這一區已收合，避免低優先事項干擾你先處理更重要的事。
        </div>
      )}
    </Card>
  )
}
