'use client'

/**
 * Actions Page — Decision Engine Execution Hub
 * ─────────────────────────────────────────────
 * Layout (top → bottom):
 *
 * 1. Recommendation Layer  – Backend Decision Engine top 3 (no local re-rank)
 * 2. Page Header + Summary Stats
 * 3. Today's Focus         – Single highest-priority active action
 * 4. Execution Layer       – Actions grouped & sorted by backend priority
 * 5. Feedback Loop         – Completed actions with 7/14/30-day outcome cards
 */

import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, Clock3, Plus, Target, Zap } from 'lucide-react'
import { ActionList } from '../../components/platform/action-list'
import { ActionFeedbackBadge } from '../../components/platform/action-feedback-badge'
import { ActionFeedbackCard } from '../../components/platform/action-feedback-card'
import RecommendationHistoryCard from '../../components/platform/recommendation-history-card'
import { DecisionRecommendationLayer } from '../../components/platform/decision-recommendation-layer'
import { StateCard } from '../../components/platform/state-card'
import { UpcomingActionsBanner } from '../../components/platform/upcoming-actions-banner'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { ErrorBoundary } from '../../components/ui/error-boundary'
import { Skeleton } from '../../components/ui/skeleton'
import { useActions } from '../../providers/action-context'
import { usePerson } from '../../providers/person-context'
import { api } from '../../../lib/api'
import type { OutcomeFeedback } from '../../../lib/api'
import { trackEvent } from '../../../lib/analytics'
import type { UnifiedDecisionItem } from '../../../lib/decision-support'

function defaultDueDate(priority: string): string {
  const days = priority === 'high' ? 7 : 14
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().split('T')[0]
}

const EMPTY_OUTCOME_SUMMARY: OutcomeFeedback['summary'] = {
  improved_count: 0,
  unchanged_count: 0,
  deteriorated_count: 0,
  insufficient_data_count: 0,
  tracking_count: 0,
  not_useful_count: 0,
  not_applicable_count: 0,
  snoozed_count: 0,
  total_count: 0,
}

// ── Recommendation feedback localStorage helpers ───────────────────────────
type RecFeedback = Record<string, 'snoozed' | 'not_useful' | 'not_applicable'>
function recFeedbackKey(personId: string) { return `rec_feedback_${personId}` }
function loadRecFeedback(personId: string): RecFeedback {
  if (typeof window === 'undefined') return {}
  try { return JSON.parse(localStorage.getItem(recFeedbackKey(personId)) ?? '{}') } catch { return {} }
}
function saveRecFeedback(personId: string, data: RecFeedback) {
  if (typeof window === 'undefined') return
  localStorage.setItem(recFeedbackKey(personId), JSON.stringify(data))
}


export default function ActionsPage() {
  const { actions, updateStatus, createFromDecisionItem, dismissFromDecisionItem, snoozeFromDecisionItem } = useActions()
  const { currentPerson, personId } = usePerson()
  const [dashboardData, setDashboardData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [assistantRecs, setAssistantRecs] = useState<any>(null)
  const [historyData, setHistoryData] = useState<OutcomeFeedback | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newPriority, setNewPriority] = useState<'high' | 'medium' | 'low'>('medium')
  const [newDueDate, setNewDueDate] = useState(defaultDueDate('medium'))
  const [addingAction, setAddingAction] = useState(false)
  const [recFeedback, setRecFeedback] = useState<RecFeedback>({})

  // Load persisted recommendation feedback on person change
  useEffect(() => {
    if (personId) setRecFeedback(loadRecFeedback(personId))
  }, [personId])

  // Sync server-persisted dismissals/snoozes into recFeedback so hidden recs stay
  // hidden even after localStorage is cleared (server state wins for known entries).
  useEffect(() => {
    const now = Date.now()
    const serverFeedback: RecFeedback = {}
    actions.forEach((a) => {
      if (!a.source_id) return
      if (a.status === 'not_useful' || a.status === 'not_applicable') {
        serverFeedback[a.source_id] = a.status as 'not_useful' | 'not_applicable'
      } else if (
        a.status === 'snoozed' &&
        a.snoozed_until != null &&
        new Date(a.snoozed_until).getTime() > now
      ) {
        serverFeedback[a.source_id] = 'snoozed'
      }
    })
    if (Object.keys(serverFeedback).length > 0) {
      setRecFeedback((prev) => ({ ...serverFeedback, ...prev }))
    }
  }, [actions])

  useEffect(() => {
    trackEvent('view_actions', { page: '/platform/actions' })
    api.getDashboard().then(setDashboardData).catch(() => setDashboardData(null)).finally(() => setLoading(false))
    // Also fetch health-assistant recommendations (same backend source as Dashboard panel)
    api.getRecommendations().then(setAssistantRecs).catch(() => setAssistantRecs(null))
    // Fetch 30-day outcome feedback for recommendation history timeline (P62)
    api.getOutcomeFeedback(30).then((d) => setHistoryData(d as OutcomeFeedback)).catch(() => setHistoryData(null))
  }, [])

  // ── Decision items from backend (single source of truth) ─────────────────
  const decisionItems = useMemo<UnifiedDecisionItem[]>(() => {
    // Prefer health-assistant recommendations (same source as HealthAssistantPanel)
    if (assistantRecs && Array.isArray(assistantRecs.recommendations) && assistantRecs.recommendations.length > 0) {
      return assistantRecs.recommendations.map((r: any, i: number) => ({
        id: r.action_id ? String(r.action_id) : `ha_${i}`,
        source_type: r.source_type ?? 'recommendation',
        source_id: r.source_id ? String(r.source_id) : (r.action_id ? String(r.action_id) : `ha_rec_${r.rule_id ?? i}`),
        title: String(r.title ?? ''),
        description: String(r.why_now ?? ''),
        priority: (r.priority as 'high' | 'medium' | 'low') ?? 'medium',
        why_now: r.why_now ? [String(r.why_now)] : [],
        next_action: String(r.next_action ?? ''),
        category: 'health',
        status: r.is_tracking ? 'in_progress' : null,
        due_date: null,
        confidence: r.evidence_sources?.[0]?.confidence ?? 0.7,
        evidence_level: r.evidence_level ?? r.evidence_sources?.[0]?.evidence_level ?? 'B',
        guideline_source: null,
        related_metric_types: [],
        outcome_hint: r.expected_health_impact ?? null,
        feedback_state: r.is_tracking ? 'tracking' : 'none',
        score: (3 - (r.rank ?? i)) * 20 + 50,
        trust: r.trust ?? undefined,
        evidence_summary: r.evidence_summary ?? undefined,
        data_insufficiency_reason: r.data_insufficiency_reason ?? undefined,
        document_id: r.document_id ?? undefined,
      }))
    }
    // Fallback: derive from dashboard data
    if (!dashboardData) return []
    if (Array.isArray(dashboardData.decision_items) && dashboardData.decision_items.length > 0) {
      return dashboardData.decision_items as UnifiedDecisionItem[]
    }
    if (Array.isArray(dashboardData.prioritized_actions) && dashboardData.prioritized_actions.length > 0) {
      return (dashboardData.prioritized_actions as Record<string, any>[]).map((a, i) => ({
        id: String(a.id ?? `pa_${i}`),
        source_type: String(a.source_type ?? 'recommendation'),
        source_id: String(a.source_id ?? a.id ?? ''),
        title: String(a.title ?? ''),
        description: String(a.description ?? ''),
        priority: (a.priority as 'high' | 'medium' | 'low') ?? 'medium',
        why_now: Array.isArray(a.why_now) ? a.why_now : [],
        next_action: String(a.next_action ?? a.recommendation ?? a.title ?? ''),
        category: String(a.category ?? ''),
        status: a.status ? String(a.status) : null,
        due_date: a.due_date ? String(a.due_date) : null,
        confidence: typeof a.confidence === 'number' ? a.confidence : 0.65,
        evidence_level: String(a.evidence_level ?? 'C'),
        guideline_source: a.guideline_source ? String(a.guideline_source) : null,
        related_metric_types: Array.isArray(a.related_metric_types) ? a.related_metric_types : [],
        outcome_hint: a.outcome_hint ? String(a.outcome_hint) : null,
        feedback_state: String(a.feedback_state ?? 'none'),
        score: typeof a.score === 'number' ? a.score : 50,
      }))
    }
    return []
  }, [assistantRecs, dashboardData])

  // ── Grouped + prioritised actions ─────────────────────────────────────────
  const grouped = useMemo(() => {
    const isSystem = (a: (typeof actions)[0]) =>
      a.source_type === 'alert' || a.source_type === 'insight' || a.source_type === 'recommendation'
    const isActive = (a: (typeof actions)[0]) =>
      a.status !== 'not_useful' && a.status !== 'not_applicable'
    const byPriority = (arr: typeof actions) =>
      [...arr].sort((a, b) => {
        const o = { high: 0, medium: 1, low: 2 } as Record<string, number>
        return (o[a.priority] ?? 2) - (o[b.priority] ?? 2)
      })

    const dismissed   = actions.filter((a) => !isActive(a))
    const overdue     = byPriority(actions.filter((a) => a.reminder_status === 'overdue' && a.status !== 'done' && isActive(a)))
    const riskUp      = byPriority(actions.filter((a) => a.reminder_status === 'risk_up' && a.status !== 'done' && isActive(a) && !overdue.includes(a)))
    const streakBreak = byPriority(actions.filter((a) => a.reminder_status === 'streak_break' && a.status !== 'done' && isActive(a) && !overdue.includes(a) && !riskUp.includes(a)))
    const urgent      = [...overdue, ...riskUp]
    const todo        = byPriority(actions.filter((a) => a.status === 'todo' && !urgent.includes(a) && !streakBreak.includes(a)))
    const inProgress  = byPriority(actions.filter((a) => a.status === 'in_progress' && !urgent.includes(a)))
    const completed   = [...actions.filter((a) => a.status === 'done')].sort(
      (a, b) => new Date(b.completed_at ?? b.created_at).getTime() - new Date(a.completed_at ?? a.created_at).getTime()
    )
    const snoozed     = actions.filter((a) => a.status === 'snoozed')
    const systemRec   = actions.filter((a) => isSystem(a) && a.status !== 'done' && isActive(a))
    const userCreated = actions.filter((a) => !isSystem(a) && a.status !== 'done' && isActive(a))
    const improved    = actions.filter((a) => a.impact_status === 'improved' && isActive(a))
    const noChange    = actions.filter((a) => a.impact_status === 'no_change' && isActive(a))
    const worse       = actions.filter((a) => (a.impact_status === 'worse' || a.reminder_status === 'risk_up') && isActive(a))

    return { overdue, riskUp, streakBreak, urgent, todo, inProgress, completed, snoozed, systemRec, userCreated, improved, noChange, worse, dismissed }
  }, [actions])

  // ── Today's Focus ─────────────────────────────────────────────────────
  const todayFocus = useMemo(() => {
    const topSourceId = decisionItems[0]?.source_id
    if (topSourceId) {
      const found = actions.find((a) => a.source_id === topSourceId && a.status !== 'done')
      if (found) return found
    }
    return grouped.overdue[0] ?? grouped.riskUp[0] ?? grouped.streakBreak[0] ?? grouped.todo[0] ?? grouped.inProgress[0] ?? null
  }, [actions, grouped, decisionItems])

  const todayFocusReason = useMemo(() => {
    if (!todayFocus) return ''
    if (todayFocus.reminder_status === 'overdue') return '這項任務已經逾期，現在補做最能阻止風険繼續累積。'
    if (todayFocus.reminder_status === 'risk_up') return '這項任務的相關指標仍在上升，越快執行越能控制風険。'
    if (todayFocus.reminder_status === 'streak_break') return '連續記錄剛中斷，今天重新開始可以挽回趨勢。'
    if (todayFocus.impact_status === 'improved') return '這項行動已開始有效，今天持續完成可以把改善延續下去。'
    return '這是目前最値得先完成的一項，完成後才有足夠資料形成回饵。'
  }, [todayFocus])

  // ── Recommendation feedback filter ────────────────────────────────────────
  const filteredDecisionItems = useMemo(
    () => decisionItems.filter((item) => !recFeedback[item.source_id]),
    [decisionItems, recFeedback]
  )

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleAddFromDecision = async (item: UnifiedDecisionItem) => {
    await createFromDecisionItem(item)
    trackEvent('recommendation_to_action', {
      page: '/platform/actions',
      metadata: { source_id: item.source_id, source_type: item.source_type, priority: item.priority },
    })
  }
  const handleSnooze = (item: UnifiedDecisionItem) => {
    trackEvent('snooze_recommendation', { page: '/platform/actions', metadata: { source_id: item.source_id } })
    const updated = { ...recFeedback, [item.source_id]: 'snoozed' as const }
    setRecFeedback(updated)
    if (personId) saveRecFeedback(personId, updated)
    // Best-effort server persistence — localStorage is the fallback if this fails
    void snoozeFromDecisionItem(item).catch(() => {})
  }
  const handleDismissRecommendation = (item: UnifiedDecisionItem, reason: 'not_useful' | 'not_applicable') => {
    trackEvent('dismiss_recommendation', { page: '/platform/actions', metadata: { source_id: item.source_id, reason } })
    const updated = { ...recFeedback, [item.source_id]: reason }
    setRecFeedback(updated)
    if (personId) saveRecFeedback(personId, updated)
    // Best-effort server persistence — localStorage is the fallback if this fails
    void dismissFromDecisionItem(item, reason).catch(() => {})
  }

  const handleAddAction = async () => {
    if (!newTitle.trim()) return
    setAddingAction(true)
    try {
      await api.createAction({
        title: newTitle.trim(),
        priority: newPriority,
        due_date: newDueDate || null,
        source_type: 'manual',
        status: 'todo',
      })
      setNewTitle('')
      setNewPriority('medium')
      setNewDueDate(defaultDueDate('medium'))
      setShowAddForm(false)
      // Refresh actions via context
      await api.getActions()
      trackEvent('create_action', { page: '/platform/actions', metadata: { priority: newPriority } })
    } finally {
      setAddingAction(false)
    }
  }

  if (loading) {
    return (
      <div data-testid="actions-loading" className="space-y-3">
        <Skeleton variant="card" className="h-20" />
        <Skeleton variant="card" className="h-36" />
        <Skeleton variant="card" className="h-36" />
      </div>
    )
  }

  return (
    <ErrorBoundary><div data-testid="actions-page" className="space-y-6">

      {/* ── Upcoming actions reminder banner ─────────────────────────────────── */}
      <UpcomingActionsBanner />

      {/* ── 1. Recommendation Layer ───────────────────────────────────────────── */}
      <DecisionRecommendationLayer
        decisionItems={filteredDecisionItems}
        actions={actions}
        onAddAction={handleAddFromDecision}
        onSnooze={handleSnooze}
        onDismiss={handleDismissRecommendation}
      />

      {/* ── 2. Page Header + Summary Stats ────────────────────────────────────── */}
      <Card className="rounded-3xl border border-slate-200/80 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold">執行中心</h2>
            {currentPerson && currentPerson.relationship !== 'self' ? <p className="mt-1 text-xs text-sky-700">目前查看：{currentPerson.display_name}</p> : null}
            <p className="text-sm text-slate-600">把 Decision Engine 建議變成每天真的會完成的行動，並且回看它有沒有帶來改善。</p>
          </div>
          <Badge className="bg-slate-900 text-white">Decision → Action → Feedback</Badge>
        </div>
        <div className="mt-4 grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
          {/* Today's Focus */}
          <div className="rounded-2xl bg-slate-50 p-4">
            <div className="flex items-center gap-1.5 mb-2">
              <Zap className="h-4 w-4 text-amber-500" />
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">今日重點</p>
            </div>
            {todayFocus ? (
              <div>
                <p className="text-lg font-semibold text-slate-950">{todayFocus.title}</p>
                <p className="mt-1 text-sm text-slate-600">{todayFocus.description}</p>
                <p className="mt-2 text-sm text-slate-700">{todayFocusReason}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {todayFocus.status !== 'done' && (
                    <Button className="bg-emerald-500 hover:bg-emerald-600 text-white" onClick={() => void updateStatus(todayFocus.id, 'done')}>
                      <CheckCircle2 className="mr-1.5 h-4 w-4" />
                      立即完成
                    </Button>
                  )}
                  {todayFocus.status === 'todo' && (
                    <Button className="bg-white border border-slate-200 text-slate-700 hover:bg-slate-50" onClick={() => void updateStatus(todayFocus.id, 'in_progress')}>
                      開始進行
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <StateCard
                tone="info"
                compact
                title="目前還沒有任務"
                description="先從上方「系統現在建議你先做」加入一項追蹤，或到 Notifications Center 挑一個最該處理的項目。"
                actionLabel="前往通知中心"
                href="/platform/notifications"
                badgeText="空狀態"
              />
            )}
          </div>
          {/* Improvement stats */}
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">改善狀態</p>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-sm">
              <div className="rounded-xl bg-emerald-50 p-3">
                <p className="text-slate-500">有改善</p>
                <p className="mt-1 text-2xl font-semibold text-slate-950">{grouped.improved.length}</p>
              </div>
              <div className="rounded-xl bg-slate-100 p-3">
                <p className="text-slate-500">沒變化</p>
                <p className="mt-1 text-2xl font-semibold text-slate-950">{grouped.noChange.length}</p>
              </div>
              <div className="rounded-xl bg-rose-50 p-3">
                <p className="text-slate-500">需要注意</p>
                <p className="mt-1 text-2xl font-semibold text-slate-950">{grouped.worse.length}</p>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* ── Metric Summary Cards ─────────────────────────────────────────────────────── */}
      <div className="grid gap-3 sm:grid-cols-3">
        <Card className="rounded-2xl p-5 text-sm">
          <div className="flex items-center justify-between text-slate-500"><span>習慣連續天數總和</span><Target className="h-4 w-4 text-sky-500" /></div>
          <p className="mt-2 text-3xl font-semibold">{actions.reduce((acc, a) => acc + (a.streak ?? 0), 0)}</p>
        </Card>
        <Card className="rounded-2xl p-5 text-sm">
          <div className="flex items-center justify-between text-slate-500"><span>逾期提醒</span><Clock3 className="h-4 w-4 text-amber-500" /></div>
          <p className="mt-2 text-3xl font-semibold">{grouped.overdue.length}</p>
        </Card>
        <Card className="rounded-2xl p-5 text-sm">
          <div className="flex items-center justify-between text-slate-500"><span>已改善影響</span><CheckCircle2 className="h-4 w-4 text-emerald-500" /></div>
          <p className="mt-2 text-3xl font-semibold">{grouped.improved.length}</p>
        </Card>
      </div>

      {/* ── Add Action Form ──────────────────────────────────────────────────────── */}
      <div>
        {!showAddForm ? (
          <button
            onClick={() => setShowAddForm(true)}
            className="flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-300 py-3 text-sm text-slate-500 hover:border-sky-300 hover:bg-sky-50/40 hover:text-sky-600"
          >
            <Plus className="h-4 w-4" />
            新增自訂行動
          </button>
        ) : (
          <Card className="rounded-2xl p-4">
            <h3 className="mb-3 text-sm font-semibold text-slate-700">新增行動</h3>
            <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto]">
              <input
                className="rounded-xl border px-3 py-2 text-sm focus:border-sky-400 focus:outline-none"
                placeholder="行動標題，例如：每天走路 30 分鐘"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') void handleAddAction() }}
                autoFocus
              />
              <select
                className="rounded-xl border px-3 py-2 text-sm"
                value={newPriority}
                onChange={(e) => {
                  const p = e.target.value as 'high' | 'medium' | 'low'
                  setNewPriority(p)
                  setNewDueDate(defaultDueDate(p))
                }}
              >
                <option value="high">高優先</option>
                <option value="medium">中優先</option>
                <option value="low">低優先</option>
              </select>
              <input
                type="date"
                className="rounded-xl border px-3 py-2 text-sm"
                value={newDueDate}
                onChange={(e) => setNewDueDate(e.target.value)}
              />
            </div>
            <div className="mt-3 flex gap-2 justify-end">
              <Button variant="ghost" size="sm" onClick={() => setShowAddForm(false)}>取消</Button>
              <Button size="sm" onClick={() => void handleAddAction()} disabled={!newTitle.trim() || addingAction}>
                新增
              </Button>
            </div>
          </Card>
        )}
      </div>

      {/* ── 3. Execution Layer ──────────────────────────────────────────────────── */}

      {/* 3a. Urgent: overdue + risk_up ──────────────────────────────────── */}
      {grouped.urgent.length > 0 && (
        <Card className="rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <Clock3 className="h-4 w-4 text-amber-500" />
            <h3 className="text-lg font-semibold">需要立即處理</h3>
            <Badge className="border-none bg-amber-100 text-amber-700 text-xs">逾期 / 風険上升</Badge>
          </div>
          <p className="mb-4 text-sm text-slate-500">先補做逾期任務，最能避免資料中斷與風険堆積。</p>
          <div className="space-y-3">
            {grouped.urgent.map((action) => (
              <div key={action.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-start justify-between gap-2 flex-wrap">
                  <div>
                    <p className="font-semibold text-slate-950">{action.title}</p>
                    <p className="mt-0.5 text-xs text-amber-700">
                      {action.reminder_status === 'overdue' ? '已逾期' : '風険上升中'}
                    </p>
                  </div>
                  <Button className="bg-slate-900 hover:bg-slate-800" onClick={() => void updateStatus(action.id, 'done')}>立即打卡</Button>
                </div>
                <div className="mt-3">
                  <ActionFeedbackBadge action={action} compact />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 3b. System-recommended vs User-created ───────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="h-4 w-4 text-violet-500" />
            <h3 className="text-lg font-semibold">系統建議行動</h3>
            <Badge className="border-none bg-violet-100 text-violet-700 text-xs">{grouped.systemRec.length}</Badge>
          </div>
          <p className="mb-3 text-sm text-slate-500">從 Alert / Insight / Recommendation 自動轉成的行動，帶有決策依據。</p>
          <ActionList actions={grouped.systemRec} onChangeStatus={updateStatus} />
        </Card>
        <Card className="rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <Target className="h-4 w-4 text-sky-500" />
            <h3 className="text-lg font-semibold">你自己建立的行動</h3>
            <Badge className="border-none bg-sky-100 text-sky-700 text-xs">{grouped.userCreated.length}</Badge>
          </div>
          <p className="mb-3 text-sm text-slate-500">你手動建立或自訂的習慣追蹤項目。</p>
          <ActionList actions={grouped.userCreated} onChangeStatus={updateStatus} />
        </Card>
      </div>

      {/* 3c. Status board ───────────────────────────────────────────────────────── */}
      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="rounded-2xl p-5">
          <h3 className="mb-2 text-lg font-semibold">今日待辦</h3>
          <ActionList actions={grouped.todo} onChangeStatus={updateStatus} />
        </Card>
        <Card className="rounded-2xl p-5">
          <h3 className="mb-2 text-lg font-semibold">進行中</h3>
          <ActionList actions={grouped.inProgress} onChangeStatus={updateStatus} />
        </Card>
        <Card className="rounded-2xl p-5">
          <h3 className="mb-2 text-lg font-semibold">已完成</h3>
          <ActionList actions={grouped.completed.slice(0, 5)} onChangeStatus={updateStatus} />
        </Card>
        {grouped.snoozed.length > 0 && (
          <Card data-testid="actions-snoozed-section" className="rounded-2xl p-5 xl:col-span-3">
            <h3 className="mb-2 text-lg font-semibold">稍後提醒</h3>
            <ActionList actions={grouped.snoozed} onChangeStatus={updateStatus} />
          </Card>
        )}
        {grouped.dismissed.length > 0 && (
          <Card className="rounded-2xl p-5 xl:col-span-3 border-dashed border-slate-200">
            <h3 className="mb-1 text-base font-semibold text-slate-500">使用者標記</h3>
            <p className="mb-3 text-xs text-slate-400">你標記為「沒有用」或「不適合我」的項目。累積足夠回饋後，系統將優化未來建議。這為使用者回饋，不代表醫學證明。可隨時點「改回待辦」恢復追蹤。</p>
            <ActionList actions={grouped.dismissed} onChangeStatus={updateStatus} />
          </Card>
        )}
      </div>

      {/* ── 4. Feedback Loop ────────────────────────────────────────────────────────── */}
      {grouped.completed.length > 0 && (
        <Card data-testid="actions-feedback-loop" className="rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            <h3 className="text-lg font-semibold">行動效果回饵</h3>
            <Badge className="bg-emerald-100 text-emerald-700 border-none text-xs">閉環分析</Badge>
          </div>
          <p className="mb-4 text-sm text-slate-500">
            每個完成的行動都會在 7、14、30 天後自動計算指標變化，讓你知道這件事到底有沒有用。
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {grouped.completed.slice(0, 4).map((action) => (
              <ActionFeedbackCard key={action.id} action={action} />
            ))}
          </div>
        </Card>
      )}

      {/* ── 5. Recommendation History Timeline (P62) ─────────────────────────── */}
      {historyData && (
        <RecommendationHistoryCard
          outcomes={historyData.outcomes ?? []}
          summary={historyData.summary ?? EMPTY_OUTCOME_SUMMARY}
        />
      )}
    </div></ErrorBoundary>
  )
}
