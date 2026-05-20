'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { AlertCard } from '../../components/platform/alert-card'
import { DailyDecisionSurface } from '../../components/platform/daily-decision-surface'
import { DailyHealthCard } from '../../components/platform/daily-health-card'
import { DecisionPanel } from '../../components/platform/decision-panel'
import { GrowthBanner } from '../../components/platform/growth-banner'
import { HealthScoreTrend } from '../../components/platform/health-score-trend'
import { HealthNarrativeCard } from '../../components/platform/health-narrative-card'
import { InsightCard } from '../../components/platform/insight-card'
import { OrchestrationSummaryPanel } from '../../components/platform/orchestration-summary-panel'
import { QuickCheckInPanel } from '../../components/platform/quick-check-in-panel'
import { RecommendationCard } from '../../components/platform/recommendation-card'
import { TodaySummaryCard } from '../../components/platform/today-summary-card'
import { TrendChart } from '../../components/platform/trend-chart'
import { TodayActionsPanel } from '../../components/platform/today-actions-panel'
import { ReportExportModal } from '../../components/platform/report-export-modal'
import { DailyAssistantEntry } from '../../components/platform/daily-assistant-entry'
import HealthAssistantPanel from '../../components/platform/health-assistant-panel'
import OutcomeFeedbackCard from '../../components/platform/outcome-feedback-card'
import NarrativeMemoryCard from '../../components/platform/narrative-memory-card'
import { Card } from '../../components/ui/card'
import { ErrorBoundary } from '../../components/ui/error-boundary'
import { Skeleton } from '../../components/ui/skeleton'
import { useActions } from '../../providers/action-context'
import { usePerson } from '../../providers/person-context'
import { api } from '../../../lib/api'
import { trackEvent } from '../../../lib/analytics'
import { getActionExpectedEffect } from '../../../lib/actions'
import { buildDecisionItems, buildHealthNarrative, getRankedAlerts, getRankedInsights, getRankedNotifications } from '../../../lib/decision-support'
import { hydrateNotificationSnoozeRecords, type NotificationSnoozeRecord } from '../../../lib/notification-snooze'

export default function DashboardPage() {
  const router = useRouter()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [trendLimit, setTrendLimit] = useState(4)
  const [inactiveDays, setInactiveDays] = useState(0)
  const [snoozeRecords, setSnoozeRecords] = useState<NotificationSnoozeRecord[]>([])
  const [recommendations, setRecommendations] = useState<any>(null)
  const [recLoading, setRecLoading] = useState(true)
  const { actions, createFromSource, updateStatus } = useActions()
  const { personId, currentPerson } = usePerson()
  const viewingFamilyMember = Boolean(currentPerson && currentPerson.relationship !== 'self')

  useEffect(() => {
    trackEvent('view_dashboard', { page: '/platform/dashboard' })
    api.getDashboard().then(setData).catch(() => setData(null)).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    api.getRecommendations()
      .then(setRecommendations)
      .catch(() => setRecommendations(null))
      .finally(() => setRecLoading(false))
  }, [])

  useEffect(() => {
    const now = Date.now()
    const key = 'growth_last_active_at'
    const prev = localStorage.getItem(key)
    if (prev) {
      const days = Math.floor((now - new Date(prev).getTime()) / (24 * 60 * 60 * 1000))
      setInactiveDays(days)
    }
    localStorage.setItem(key, new Date(now).toISOString())
  }, [])

  useEffect(() => {
    if (!personId) {
      setSnoozeRecords([])
      return
    }
    setSnoozeRecords(hydrateNotificationSnoozeRecords(personId))
  }, [personId, actions])

  const trendEntries = useMemo(() => Object.entries(data?.trends || {}) as Array<[string, any[]]>, [data])
  const hasStreakBreak = useMemo(() => actions.some((a) => a.reminder_status === 'streak_break'), [actions])
  const hasOverdue = useMemo(() => actions.some((a) => a.reminder_status === 'overdue'), [actions])
  const hasRiskUp = useMemo(() => actions.some((a) => a.reminder_status === 'risk_up') || (data?.alerts || []).length > 0, [actions, data])
  const riskLevel = useMemo(() => {
    if (data?.risk_level) return String(data.risk_level).toLowerCase()
    return (data?.alerts || []).length > 0 ? 'elevated' : 'stable'
  }, [data])
  const decisionItems = useMemo(() => buildDecisionItems(data, actions), [actions, data])
  // Alerts and insights from dashboard API are already ranked by backend;
  // getRankedAlerts/getRankedInsights will also prefer data.decision_items when available.
  const rankedAlerts = useMemo(() => getRankedAlerts(data, actions), [actions, data])
  const rankedInsights = useMemo(() => getRankedInsights(data, actions), [actions, data])
  const notificationsSummary = useMemo(() => getRankedNotifications(data, actions, snoozeRecords), [actions, data, snoozeRecords])
  const topAction = useMemo(() => {
    // Backend is authoritative: use the first entry from prioritized_actions
    const topId = data?.prioritized_actions?.[0]?.id
    if (topId) {
      const found = actions.find((a) => a.id === topId)
      if (found) return found
    }
    // Fallback: first active action by local status order
    return (
      actions.find((action) => action.reminder_status === 'overdue') ||
      actions.find((action) => action.reminder_status === 'risk_up') ||
      actions.find((action) => action.status === 'todo' || action.status === 'in_progress') ||
      actions.find((action) => action.status === 'snoozed') ||
      null
    )
  }, [actions, data])
  const healthNarrative = useMemo(() => {
    if (data?.health_narrative_v2) return data.health_narrative_v2
    if (data?.health_narrative) return data.health_narrative
    const fallbackLines = buildHealthNarrative(data, actions)
    return {
      summary: fallbackLines[0] || '目前還在整理你的健康故事。',
      risks: fallbackLines.slice(1, 3),
      trends: fallbackLines.slice(1, 3),
      reasons: ['目前後端健康敘事尚未提供完整原因，先依既有洞察與趨勢判讀。'],
      actions: decisionItems.map((item) => item.title).slice(0, 3),
      delta_summary: fallbackLines[0] || '目前還在整理你的健康故事。',
      improvements: decisionItems.filter((item) => item.priority !== 'high').slice(0, 2).map((item) => item.title),
      deteriorations: decisionItems.filter((item) => item.priority === 'high').slice(0, 2).map((item) => item.title),
      adherence: actions.slice(0, 2).map((action) => `已持續執行「${action.title}」`),
      missed_risks: fallbackLines.slice(1, 3),
    }
  }, [actions, data, decisionItems])
  const urgentAlerts = useMemo(() => rankedAlerts.filter((item) => item.priority === 'high'), [rankedAlerts])
  const normalAlerts = useMemo(() => rankedAlerts.filter((item) => item.priority !== 'high'), [rankedAlerts])
  const dailyRiskText = healthNarrative?.risks?.[0] || decisionItems?.[0]?.reason || '目前還在整理你的健康風險。'
  const dailyDeltaText = healthNarrative?.delta_summary || healthNarrative?.summary || '先看今天和上次相比有沒有變化。'
  const dailyActionText =
    healthNarrative?.actions?.[0] ||
    decisionItems?.[0]?.title ||
    topAction?.title ||
    '先去看今天最重要的健康事項'
  const dailyActionEffect = topAction ? getActionExpectedEffect(topAction) : healthNarrative?.actions?.[0] ? '先把今天最重要的健康行動完成。' : '先把今天最重要的健康行動完成。'

  // Narrative v3 fields (falls back to v2 gracefully)
  const narrativeV3 = useMemo(() => {
    const v3 = data?.health_narrative_v3 ?? data?.health_narrative_v2 ?? healthNarrative ?? {}
    return {
      causes: (v3.causes ?? []) as string[],
      missedOpportunities: (v3.missed_opportunities ?? v3.missedOpportunities ?? []) as string[],
      nextActions: (v3.next_actions ?? v3.nextActions ?? []) as string[],
    }
  }, [data, healthNarrative])

  const deltaDirection = useMemo(() => {
    const delta = dailyDeltaText
    if (delta.includes('改善') || delta.includes('好') || delta.includes('下降') || delta.includes('增加睡眠')) return 'improved' as const
    if (delta.includes('變差') || delta.includes('惡化') || delta.includes('上升') || delta.includes('需要')) return 'worse' as const
    return 'no_change' as const
  }, [dailyDeltaText])

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton variant="card" className="h-40" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton variant="card" className="h-56" />
          <Skeleton variant="card" className="h-56" />
          <Skeleton variant="card" className="h-56" />
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary><div className="space-y-6">
      {/* ── Daily Decision Surface (top-level behavior change loop) ──────── */}
      <DailyDecisionSurface
        todayFocus={topAction}
        deltaText={dailyDeltaText}
        deltaDirection={deltaDirection}
        causes={narrativeV3.causes}
        nextActions={narrativeV3.nextActions}
        missedOpportunities={narrativeV3.missedOpportunities}
        score={typeof data?.health_score?.overall_score === 'number' ? data.health_score.overall_score : null}
        onCompleteAction={(id) => void updateStatus(id, 'done')}
        onStartAction={(id) => void updateStatus(id, 'in_progress')}
      />
      <Card className="tech-wave rounded-[28px] bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-900 p-6 text-white shadow-md">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-300">健康總覽</p>
            <h2 className="mt-1 text-3xl font-semibold">儀表板</h2>
            {viewingFamilyMember ? <p className="mt-1 text-xs text-sky-200">目前查看：{currentPerson?.display_name}</p> : null}
            <p className="text-sm text-slate-300">5 秒看懂現在的健康狀態，1 分鐘完成今天的健康檢查。</p>
            <p className="mt-2 max-w-2xl text-sm text-slate-300">{data?.explainability_summary || '正在整理你的健康摘要...'}</p>
          </div>
          <div className="rounded-2xl bg-white/10 p-4 text-right">
            <p className="text-xs text-slate-300">風險等級</p>
            <p className={`mono-data mt-1 text-lg font-semibold ${riskLevel === 'high' || riskLevel === 'elevated' ? 'text-rose-300' : 'neon-value text-emerald-300'}`}>
              {String(riskLevel).toUpperCase()}
            </p>
            <div className="mt-2">
              <ReportExportModal />
            </div>
          </div>
        </div>
      </Card>
      <OrchestrationSummaryPanel />
      {/* ── 今日健康入口 (Daily Summary + Top Rec + Trust + Outcome) ──────────────────── */}
      <DailyAssistantEntry data={recommendations} loading={recLoading} />
      {/* ── 今日健康小助手 ──────────────────────────────────────────── */}
      <HealthAssistantPanel
        data={recommendations}
        loading={recLoading}
      />
      <OutcomeFeedbackCard />
      <NarrativeMemoryCard />
      <DailyHealthCard
        score={typeof data?.health_score?.overall_score === 'number' ? data.health_score.overall_score : null}
        riskText={dailyRiskText}
        deltaText={dailyDeltaText}
        actionText={dailyActionText}
        actionEffect={dailyActionEffect}
        action={topAction}
        onPrimaryAction={() => {
          if (topAction) {
            void updateStatus(topAction.id, 'in_progress')
            return
          }
          router.push('/platform/notifications')
        }}
        onSecondaryAction={() => router.push('/platform/notifications')}
      />
      <QuickCheckInPanel onChanged={() => api.getDashboard().then(setData).catch(() => setData(null))} />
      <GrowthBanner hasStreakBreak={hasStreakBreak} hasOverdue={hasOverdue} hasRiskUp={hasRiskUp} inactiveDays={inactiveDays} />
      <DecisionPanel
        items={decisionItems}
        queueCount={notificationsSummary.totalPendingCount}
        onStart={(item) => {
          if (item.sourceType === 'action') {
            return updateStatus(item.id, 'in_progress')
          }
          return createFromSource(item.sourceType, item.source, 'in_progress')
        }}
      />
      <HealthNarrativeCard
        narrative={healthNarrative}
        riskLevel={riskLevel}
        score={typeof data?.health_score?.overall_score === 'number' ? data.health_score.overall_score : null}
        actions={actions}
      />
      <div className="grid gap-4 md:grid-cols-3">
        <HealthScoreTrend currentScore={typeof data?.health_score?.overall_score === 'number' ? data.health_score.overall_score : null} />
        <TodaySummaryCard
          actions={actions}
          alertsCount={(data?.alerts || []).length}
          recommendationText={(data?.recommendations || [])[0]?.recommendation || (data?.recommendations || [])[0]?.text}
          onQuickComplete={(id) => void updateStatus(id, 'done')}
          onJoinTracking={() => {
            const recommendation = (data?.recommendations || [])[0]
            if (recommendation) {
              void createFromSource('recommendation', recommendation, 'todo')
              return
            }
            router.push('/platform/notifications')
          }}
        />
        <Card className="rounded-2xl p-5">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-rose-500" />
              <h3 className="font-semibold">提醒</h3>
            </div>
            <span className="text-xs text-slate-500">與決策引擎同步排序</span>
          </div>
          <div className="space-y-3">
            <div>
              <div className="mb-2 flex items-center gap-2">
                <h4 className="text-sm font-semibold text-rose-700">最優先</h4>
                <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">{urgentAlerts.length}</span>
              </div>
              <div className="space-y-2">
                {(urgentAlerts.length > 0 ? urgentAlerts : rankedAlerts.slice(0, 2)).map((a) => <AlertCard key={a.id} alert={a} />)}
              </div>
            </div>
            {normalAlerts.length > 0 ? (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <h4 className="text-sm font-semibold text-slate-700">一般提醒</h4>
                  <span className="rounded-full bg-white px-2 py-0.5 text-xs font-medium text-slate-600">{normalAlerts.length}</span>
                </div>
                <div className="space-y-2">
                  {normalAlerts.slice(0, 2).map((a) => <AlertCard key={a.id} alert={a} />)}
                </div>
              </div>
            ) : null}
            <div className="pt-1">
              <Link href="/platform/notifications" className="text-sm font-medium text-sky-700 hover:underline">
                查看全部待處理事項{notificationsSummary.totalPendingCount > 0 ? `（${notificationsSummary.totalPendingCount}）` : ''}
              </Link>
            </div>
          </div>
        </Card>
      </div>
      <details className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <summary className="cursor-pointer list-none text-sm font-semibold text-slate-900">更多分析</summary>
        <div className="mt-4 space-y-4">
          <Card className="rounded-2xl p-5">
            <h3 className="font-semibold">可行動洞察</h3>
            <p className="text-sm text-slate-500">依照同一套決策分數排序，先處理最有影響的洞察。</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {rankedInsights.map((i) => {
                const insight = i as any
                const title = `${insight?.title || ''} ${insight?.summary || insight?.reason || ''}`.toLowerCase()
                const category =
                  /(blood pressure|bp|心血管|血壓|cardio)/.test(title)
                    ? 'cardiovascular'
                    : /(glucose|metabolic|代謝|血糖|bmi|尿酸)/.test(title)
                    ? 'metabolic'
                    : /(sleep|睡眠)/.test(title)
                    ? 'sleep'
                    : /(steps|walk|exercise|活動|運動)/.test(title)
                    ? 'activity'
                    : 'overall'
                return (
                  <div key={insight.id} className="space-y-2">
                    <InsightCard insight={insight} />
                    <Link href={`/platform/insights?category=${category}`} className="inline-flex text-sm font-medium text-sky-700 hover:underline">
                      深入了解 →
                    </Link>
                  </div>
                )
              })}
            </div>
          </Card>
          <Card className="rounded-2xl p-5">
            <h3 className="font-semibold">建議</h3>
            <p className="text-sm text-slate-500">清楚的 CTA 可以降低決策疲勞。</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {(data?.recommendations || []).map((r: any, idx: number) => <RecommendationCard key={idx} recommendation={r} />)}
            </div>
          </Card>
          <TodayActionsPanel notificationsCount={notificationsSummary.totalPendingCount} />
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="md:col-span-2 rounded-2xl p-5">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">趨勢圖表</h3>
                <select className="rounded-xl border px-3 py-2 text-sm" value={trendLimit} onChange={(e) => setTrendLimit(Number(e.target.value))}>
                  <option value={2}>顯示 2 個</option>
                  <option value={4}>顯示 4 個</option>
                  <option value={6}>顯示 6 個</option>
                </select>
              </div>
            </Card>
            {trendEntries.slice(0, trendLimit).map(([key, points]) => <TrendChart key={key} title={key} points={points || []} />)}
          </div>
        </div>
      </details>
      <p className="text-xs text-slate-500">{data?.medical_disclaimer || ''}</p>
    </div></ErrorBoundary>
  )
}
