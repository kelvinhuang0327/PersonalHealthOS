'use client'

import { useEffect, useMemo, useState } from 'react'
import { BellRing, Clock3, Siren, Sparkles } from 'lucide-react'
import { NotificationsSection } from '../../components/platform/notifications-section'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { StateCard } from '../../components/platform/state-card'
import { useActions } from '../../providers/action-context'
import { usePerson } from '../../providers/person-context'
import { api } from '../../../lib/api'
import { trackEvent } from '../../../lib/analytics'
import { getRankedNotifications, type NotificationItem } from '../../../lib/decision-support'
import {
  clearNotificationSnooze,
  getNotificationStorageKey,
  hydrateNotificationSnoozeRecords,
  saveNotificationSnooze,
  type NotificationSnoozeRecord,
} from '../../../lib/notification-snooze'

function getNotificationKey(item: NotificationItem) {
  return `${item.sourceType}:${item.id}`
}

export default function NotificationsPage() {
  const { actions, createFromSource, updateStatus } = useActions()
  const { personId } = usePerson()
  const [dashboardData, setDashboardData] = useState<any>(null)
  const [insights, setInsights] = useState<any[]>([])
  const [snoozeRecords, setSnoozeRecords] = useState<NotificationSnoozeRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    trackEvent('view_notifications_center', { page: '/platform/notifications' })
    setLoading(true)
    Promise.all([api.getDashboard().catch(() => null), api.listInsights().catch(() => [])])
      .then(([dashboard, insightItems]) => {
        setDashboardData(dashboard)
        setInsights(Array.isArray(insightItems) ? insightItems : [])
      })
      .catch(() => {
        setDashboardData(null)
        setInsights([])
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    if (!personId) {
      setSnoozeRecords([])
      return
    }
    setSnoozeRecords(hydrateNotificationSnoozeRecords(personId))
  }, [personId])

  const rankingContext = useMemo(
    () => ({
      ...(dashboardData || {}),
      insights,
    }),
    [dashboardData, insights]
  )

  // getRankedNotifications will use backend decision_items (from dashboardData)
  // when available, falling back to local scoring.  Snooze lifecycle is always
  // applied client-side (it is a pure UX interaction concern, not business logic).
  const notifications = useMemo(
    () => getRankedNotifications(rankingContext, actions, snoozeRecords),
    [actions, rankingContext, snoozeRecords]
  )

  const visibleNotifications = notifications.activeItems
  const snoozedItems = notifications.snoozedItems
  const topItem = visibleNotifications[0] || null

  const urgentItems = useMemo(
    () =>
      visibleNotifications.filter(
        (item) =>
          item.priority === 'high' ||
          item.sourceType === 'action' ||
          item.breakdown.overdue.label === 'overdue' ||
          item.breakdown.risk_severity.label === 'high'
      ),
    [visibleNotifications]
  )
  const needsAttentionItems = useMemo(
    () =>
      visibleNotifications.filter(
        (item) =>
          !urgentItems.some((urgent) => urgent.id === item.id && urgent.sourceType === item.sourceType) &&
          (item.priority === 'medium' || item.breakdown.time_sensitivity.label === 'recent' || item.breakdown.overdue.label === 'due_soon')
      ),
    [urgentItems, visibleNotifications]
  )
  const lowPriorityItems = useMemo(
    () =>
      visibleNotifications.filter(
        (item) =>
          !urgentItems.some((urgent) => urgent.id === item.id && urgent.sourceType === item.sourceType) &&
          !needsAttentionItems.some((attention) => attention.id === item.id && attention.sourceType === item.sourceType)
      ),
    [needsAttentionItems, urgentItems, visibleNotifications]
  )

  const refreshLifecycle = () => {
    if (!personId) return
    setSnoozeRecords(hydrateNotificationSnoozeRecords(personId))
  }

  const handleStart = async (item: NotificationItem) => {
    if (personId) {
      setSnoozeRecords(clearNotificationSnooze(personId, getNotificationKey(item)))
    }
    if (item.sourceType === 'action') {
      await updateStatus(item.id, 'in_progress')
      return
    }
    await createFromSource(item.sourceType, item.source, 'in_progress')
  }

  const handleTrack = async (item: NotificationItem) => {
    if (personId) {
      setSnoozeRecords(clearNotificationSnooze(personId, getNotificationKey(item)))
    }
    if (item.sourceType === 'action') {
      await updateStatus(item.id, 'todo')
      return
    }
    await createFromSource(item.sourceType, item.source, 'todo')
  }

  const handleSnooze = (item: NotificationItem) => {
    if (!personId) return
    const next = saveNotificationSnooze(personId, {
      key: getNotificationKey(item),
      title: item.title,
      source_type: item.sourceType,
      source_id: item.id,
      snoozeReason: item.whyNow[0],
    })
    setSnoozeRecords(next)
  }

  return (
    <div className="space-y-6">
      {loading ? (
        <StateCard
          tone="loading"
          title="正在整理待處理事項"
          description="系統正在彙整 Alerts、Insights、Actions 與 Snooze 狀態，請稍候。"
          badgeText="頁面載入中"
        />
      ) : null}
      <Card className="rounded-3xl border border-slate-200/80 bg-gradient-to-br from-slate-950 to-slate-800 p-6 text-white shadow-md">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-slate-100">
              <BellRing className="h-3.5 w-3.5" />
              健康待處理中心
            </div>
            <h2 className="mt-3 text-3xl font-semibold">你目前有 {notifications.totalPendingCount} 件需要處理的健康事項</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-300">
              這裡不是一般通知列表，而是由 Decision Engine 排序後的健康待處理中心，幫你先看最該現在處理的事。
            </p>
          </div>
          <div className="rounded-2xl bg-white/10 px-4 py-3 text-right">
            <p className="text-xs text-slate-300">優先隊列</p>
            <p className="mt-1 text-2xl font-semibold">{urgentItems.length}</p>
          </div>
        </div>

        <div className="mt-5 rounded-3xl bg-white/10 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="bg-rose-100 text-rose-700">Top 1</Badge>
                <Badge className="bg-white/15 text-slate-100">Decision Engine 承接頁</Badge>
                {notifications.resurfacedTodayCount > 0 ? (
                  <Badge className="bg-amber-100 text-amber-800">今日重新出現 {notifications.resurfacedTodayCount}</Badge>
                ) : null}
              </div>
              <p className="mt-3 text-xl font-semibold">{topItem?.title || '目前沒有需要立即處理的通知'}</p>
              <p className="mt-2 text-sm text-slate-200">
                {topItem?.whyNow[0] || '先維持目前節奏，若有新風險或逾期任務，這裡會第一時間更新。'}
              </p>
            </div>
            {topItem ? (
              <Button className="bg-white text-slate-900 hover:bg-slate-100" onClick={() => void handleStart(topItem)}>
                先處理這一件
              </Button>
            ) : null}
          </div>
        </div>
      </Card>

      {topItem ? (
        <Card
          className="rounded-3xl border border-slate-200/80 bg-white p-5 shadow-sm"
          data-testid={`notification-card-preview-${topItem.sourceType}-${topItem.id}`}
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className={topItem.priority === 'high' ? 'bg-rose-100 text-rose-700' : topItem.priority === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-slate-200 text-slate-700'}>
                  {topItem.priority === 'high' ? '最優先' : topItem.priority === 'medium' ? '需要注意' : '低優先'}
                </Badge>
                <Badge>{topItem.sourceType}</Badge>
                {topItem.resurfaced ? <Badge className="bg-sky-100 text-sky-700">已重新提醒</Badge> : null}
              </div>
              <h3 className="mt-3 text-xl font-semibold text-slate-950">{topItem.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{topItem.reason}</p>
              <p className="mt-3 text-sm text-slate-700">
                <span className="font-medium text-slate-950">為什麼現在要處理：</span>
                {topItem.whyNow[0] || '這項事情現在值得先處理。'}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={() => void handleStart(topItem)}>
                開始改善
              </Button>
              <Button className="bg-sky-600 hover:bg-sky-700" onClick={() => void handleTrack(topItem)}>
                加入追蹤
              </Button>
              <Button className="bg-slate-600 hover:bg-slate-700" onClick={() => handleSnooze(topItem)}>
                稍後提醒
              </Button>
            </div>
          </div>
        </Card>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-4">
        <Card className="rounded-2xl p-5 text-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span>最優先</span>
            <Siren className="h-4 w-4 text-rose-500" />
          </div>
          <p className="mt-2 text-3xl font-semibold">{urgentItems.length}</p>
        </Card>
        <Card className="rounded-2xl p-5 text-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span>需要注意</span>
            <BellRing className="h-4 w-4 text-amber-500" />
          </div>
          <p className="mt-2 text-3xl font-semibold">{needsAttentionItems.length}</p>
        </Card>
        <Card className="rounded-2xl p-5 text-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span>稍後提醒</span>
            <Clock3 className="h-4 w-4 text-slate-500" />
          </div>
          <p className="mt-2 text-3xl font-semibold">{notifications.snoozedCount}</p>
        </Card>
        <Card className="rounded-2xl p-5 text-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span>今日回彈</span>
            <Sparkles className="h-4 w-4 text-sky-500" />
          </div>
          <p className="mt-2 text-3xl font-semibold">{notifications.resurfacedTodayCount}</p>
        </Card>
      </div>

      <NotificationsSection
        title="最優先"
        description="高風險、已逾期、或需要你立刻接手的事項。"
        items={urgentItems.slice(0, 5)}
        tone="urgent"
        emptyText="目前沒有 urgent 項目，可以先往下看 needs attention。"
        onStart={handleStart}
        onTrack={handleTrack}
        onSnooze={handleSnooze}
        testId="notifications-section-urgent"
      />

      <NotificationsSection
        title="需要注意"
        description="中等風險、最近新出現、或值得本週安排的健康事項。"
        items={needsAttentionItems}
        tone="attention"
        emptyText="目前沒有需要特別注意的中等優先事項。"
        onStart={handleStart}
        onTrack={handleTrack}
        onSnooze={handleSnooze}
        testId="notifications-section-attention"
      />

      <NotificationsSection
        title="稍後提醒"
        description="尚未到恢復提醒時間的事項會先留在這裡，不干擾你處理更重要的事。"
        items={snoozedItems}
        tone="low"
        emptyText="目前沒有 snoozed 項目。"
        onStart={handleStart}
        onTrack={handleTrack}
        onSnooze={handleSnooze}
        testId="notifications-section-snoozed"
      />

      <NotificationsSection
        title="低優先"
        description="低風險或長期優化項目，預設收合避免干擾。"
        items={lowPriorityItems}
        tone="low"
        collapsible
        defaultCollapsed
        emptyText="目前沒有低優先事項。"
        onStart={handleStart}
        onTrack={handleTrack}
        onSnooze={handleSnooze}
        testId="notifications-section-low"
      />

      <Card className="rounded-2xl border border-slate-200 p-5">
        <div className="flex items-start gap-3">
          <Sparkles className="mt-1 h-4 w-4 text-sky-600" />
          <div>
            <h3 className="font-semibold text-slate-950">決策引擎與稍後提醒生命週期</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              這個頁面會整合 `getRankedAlerts()`、`getRankedInsights()`、既有逾期/風險上升的行動，以及惡化趨勢，全部都經過同一套決策分數排序。
              若某個項目被稍後提醒，它會先移到稍後提醒區，等時間到後再自動回到待處理中心並重新參與排序。
            </p>
            {personId ? (
              <p className="mt-2 text-xs text-slate-500">本地生命週期儲存在 `{getNotificationStorageKey(personId)}`，每位家庭成員彼此隔離。</p>
            ) : null}
            <div className="mt-3">
              <Button className="bg-white text-slate-900 hover:bg-slate-100" onClick={refreshLifecycle}>
                重新整理通知生命週期
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}
