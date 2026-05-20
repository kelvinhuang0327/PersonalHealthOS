'use client'

/**
 * NotificationPreview — P5 Notification Intelligence Foundation
 * =============================================================
 * Self-fetching card that shows the most urgent active notification candidate.
 * Displays priority badge, why_now explanation, suggested_action, and
 * a count of suppressed (de-duped / on cooldown) notifications.
 *
 * No diagnosis wording. Grounded in evidence only.
 */

import { Bell, BellOff } from 'lucide-react'
import { useEffect, useState } from 'react'

import { api, type IntelligentNotifications, type NotificationCandidate } from '../../../lib/api'

// ---------------------------------------------------------------------------
// Priority badge helpers
// ---------------------------------------------------------------------------

const PRIORITY_CONFIG: Record<
  NotificationCandidate['priority'],
  { label: string; badgeCls: string; borderCls: string; iconCls: string }
> = {
  urgent: {
    label: '緊急',
    badgeCls: 'bg-rose-100 text-rose-700 border border-rose-300',
    borderCls: 'border-l-4 border-rose-400',
    iconCls: 'text-rose-500',
  },
  high: {
    label: '重要',
    badgeCls: 'bg-amber-100 text-amber-700 border border-amber-300',
    borderCls: 'border-l-4 border-amber-400',
    iconCls: 'text-amber-500',
  },
  medium: {
    label: '提醒',
    badgeCls: 'bg-blue-100 text-blue-700 border border-blue-300',
    borderCls: 'border-l-4 border-blue-400',
    iconCls: 'text-blue-500',
  },
  low: {
    label: '一般',
    badgeCls: 'bg-slate-100 text-slate-600 border border-slate-300',
    borderCls: 'border-l-4 border-slate-300',
    iconCls: 'text-slate-400',
  },
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PriorityBadge({ priority }: { priority: NotificationCandidate['priority'] }) {
  const { label, badgeCls } = PRIORITY_CONFIG[priority] ?? PRIORITY_CONFIG.low
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${badgeCls}`}>
      {label}
    </span>
  )
}

function CandidateCard({ candidate }: { candidate: NotificationCandidate }) {
  const { borderCls } = PRIORITY_CONFIG[candidate.priority] ?? PRIORITY_CONFIG.low
  return (
    <div className={`rounded-lg bg-white p-4 shadow-sm ${borderCls}`}>
      <div className="flex items-start gap-3">
        <Bell className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" aria-hidden />
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <PriorityBadge priority={candidate.priority} />
            <p className="text-sm font-semibold text-slate-800">{candidate.title}</p>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">{candidate.why_now}</p>
          {candidate.suggested_action && (
            <p className="text-xs text-slate-700 font-medium">
              建議：{candidate.suggested_action}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-2 py-6 text-slate-400">
      <BellOff className="h-8 w-8" aria-hidden />
      <p className="text-sm">目前無待處理提醒</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function NotificationPreview() {
  const [data, setData] = useState<IntelligentNotifications | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .getIntelligentNotifications()
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const topCandidate: NotificationCandidate | undefined = data?.items?.[0]
  const suppressedCount = data?.suppressed?.length ?? 0

  return (
    <section aria-label="今日提醒" className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-700">
          <Bell className="h-4 w-4" aria-hidden />
          今日提醒
        </h3>
        {suppressedCount > 0 && (
          <span className="text-xs text-slate-400">
            {suppressedCount} 則已靜音
          </span>
        )}
      </div>

      {loading && (
        <div className="h-16 animate-pulse rounded-lg bg-slate-100" aria-busy="true" />
      )}

      {!loading && error && (
        <p className="text-xs text-slate-400">提醒載入失敗，請稍後再試</p>
      )}

      {!loading && !error && !topCandidate && <EmptyState />}

      {!loading && !error && topCandidate && (
        <>
          <CandidateCard candidate={topCandidate} />
          {(data?.items?.length ?? 0) > 1 && (
            <p className="text-xs text-slate-400 text-right">
              +{(data!.items.length) - 1} 則其他提醒
            </p>
          )}
        </>
      )}
    </section>
  )
}
