'use client'

/**
 * PersonalizationInsights — P6 Adaptive Health Assistant
 * =======================================================
 * Self-fetching card showing what the health assistant has learned
 * about the current user's preferences and engagement patterns.
 *
 * Guardrails
 * ----------
 * - No internal scoring numbers shown to the user
 * - No medical conclusions inferred from personalization data
 * - Empty state is clear and non-alarming
 * - All copy is framed as "the assistant is learning", not "you have X condition"
 */

import { Brain, ChevronRight, Clock, RefreshCw, TrendingDown, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'

import { api, type EngagementAnalytics, type PersonalizationProfile } from '../../../lib/api'

// ---------------------------------------------------------------------------
// Label maps (source_type → human-readable)
// ---------------------------------------------------------------------------

const SOURCE_LABELS: Record<string, string> = {
  lab_abnormality: '健檢指標提醒',
  device_escalation: '裝置訊號提醒',
  symptom_pattern: '症狀模式提醒',
  risk_alert: '健康風險提醒',
  recommendation: '健康建議',
  unknown: '其他',
}

function sourceLabel(key: string) {
  return SOURCE_LABELS[key] ?? key
}

const WINDOW_LABELS: Record<string, string> = {
  morning: '早上',
  afternoon: '下午',
  evening: '傍晚',
  night: '夜間',
}

function windowLabel(w: string) {
  return WINDOW_LABELS[w] ?? w
}

// ---------------------------------------------------------------------------
// Trend badge
// ---------------------------------------------------------------------------

function TrendBadge({ trend }: { trend: EngagementAnalytics['engagementTrend'] }) {
  if (trend === 'improving') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
        <TrendingUp className="h-3 w-3" />
        提升中
      </span>
    )
  }
  if (trend === 'declining') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
        <TrendingDown className="h-3 w-3" />
        下降趨勢
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
      穩定
    </span>
  )
}

// ---------------------------------------------------------------------------
// Engagement bar
// ---------------------------------------------------------------------------

function EngagementBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  let color = 'bg-blue-400'
  let label = '互動中'
  if (score >= 0.65) { color = 'bg-emerald-400'; label = '積極互動' }
  else if (score <= 0.30) { color = 'bg-amber-400'; label = '互動較少' }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>提醒互動狀態</span>
        <span className="font-medium text-slate-700">{label}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
          aria-label={`互動率 ${pct}%`}
        />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Category row
// ---------------------------------------------------------------------------

function CategoryRow({
  label,
  count,
  icon,
  colorCls,
}: {
  label: string
  count: number
  icon: React.ReactNode
  colorCls: string
}) {
  return (
    <div className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-slate-50">
      <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${colorCls}`}>
        {icon}
      </span>
      <span className="flex-1 text-sm text-slate-700">{label}</span>
      <span className="text-xs font-medium text-slate-500">{count} 次</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-2 py-6 text-center">
      <Brain className="h-8 w-8 text-slate-300" />
      <p className="text-sm font-medium text-slate-500">健康助手正在學習中</p>
      <p className="max-w-xs text-xs text-slate-400">
        繼續使用提醒功能，助手將逐漸了解您的偏好並提供更個人化的建議。
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function PersonalizationInsights() {
  const [profile, setProfile] = useState<PersonalizationProfile | null>(null)
  const [analytics, setAnalytics] = useState<EngagementAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function fetchAll() {
    try {
      setLoading(true)
      const [profileData, analyticsData] = await Promise.allSettled([
        api.getPersonalizationProfile(),
        api.getEngagementAnalytics(30),
      ])
      if (profileData.status === 'fulfilled') setProfile(profileData.value)
      if (analyticsData.status === 'fulfilled') setAnalytics(analyticsData.value)
      if (profileData.status === 'rejected' && analyticsData.status === 'rejected') {
        setError('暫時無法載入個人化資料')
      } else {
        setError(null)
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleSync() {
    try {
      setSyncing(true)
      const [profileData, analyticsData] = await Promise.allSettled([
        api.syncPersonalizationProfile(30),
        api.getEngagementAnalytics(30),
      ])
      if (profileData.status === 'fulfilled') setProfile(profileData.value)
      if (analyticsData.status === 'fulfilled') setAnalytics(analyticsData.value)
    } catch {
      // silent — stale data is still useful
    } finally {
      setSyncing(false)
    }
  }

  useEffect(() => { fetchAll() }, [])

  const actedEntries = profile
    ? Object.entries(profile.acted_categories).sort((a, b) => b[1] - a[1]).slice(0, 3)
    : []
  const ignoredEntries = profile
    ? Object.entries(profile.ignored_categories).sort((a, b) => b[1] - a[1]).slice(0, 3)
    : []

  const hasProfileData = actedEntries.length > 0 || ignoredEntries.length > 0
  const hasAnalytics = analytics !== null
  const hasData = hasProfileData || hasAnalytics

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-violet-500" aria-hidden />
          <span className="text-sm font-semibold text-slate-800">健康助手學習中</span>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing || loading}
          aria-label="重新同步個人化資料"
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 disabled:opacity-40"
        >
          <RefreshCw className={`h-3 w-3 ${syncing ? 'animate-spin' : ''}`} />
          更新
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Loading */}
        {loading && (
          <div className="flex justify-center py-6">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-violet-300 border-t-violet-600" />
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <p className="text-center text-sm text-slate-400">{error}</p>
        )}

        {/* Empty state */}
        {!loading && !error && !hasData && <EmptyState />}

        {/* Data */}
        {!loading && !error && hasData && profile && (
          <>
            {/* Engagement bar */}
            <EngagementBar score={profile.engagement_score} />

            {/* Analytics section */}
            {hasAnalytics && analytics && (
              <div className="space-y-3 rounded-lg bg-slate-50 px-3 py-2.5">
                {/* Trend row */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">近期互動趨勢</span>
                  <TrendBadge trend={analytics.engagementTrend} />
                </div>

                {/* Declining nudge — gentle, non-alarming */}
                {analytics.engagementTrend === 'declining' && (
                  <p className="text-xs text-amber-700 bg-amber-50 rounded-md px-2 py-1.5">
                    助手偵測到近期互動減少，正在調整提醒頻率以更符合您的節奏。
                  </p>
                )}

                {/* Completion rate + open rate */}
                <div className="flex gap-4">
                  <div className="flex-1 text-center">
                    <p className="text-lg font-semibold text-slate-800">
                      {Math.round(analytics.actionCompletionRate * 100)}%
                    </p>
                    <p className="text-xs text-slate-400">採取行動率</p>
                  </div>
                  <div className="flex-1 text-center">
                    <p className="text-lg font-semibold text-slate-800">
                      {Math.round(analytics.notificationOpenRate * 100)}%
                    </p>
                    <p className="text-xs text-slate-400">提醒開啟率</p>
                  </div>
                </div>

                {/* Best windows */}
                {analytics.bestNotificationWindows.length > 0 && (
                  <div className="flex items-start gap-1.5">
                    <Clock className="mt-0.5 h-3 w-3 shrink-0 text-violet-400" />
                    <div>
                      <p className="text-xs text-slate-500">您最常回應的時段</p>
                      <p className="text-xs font-medium text-slate-700">
                        {analytics.bestNotificationWindows.map(windowLabel).join('、')}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Acted categories */}
            {actedEntries.length > 0 && (
              <div className="space-y-1">
                <p className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <TrendingUp className="h-3 w-3 text-emerald-500" />
                  常採取行動的提醒類型
                </p>
                {actedEntries.map(([key, count]) => (
                  <CategoryRow
                    key={key}
                    label={sourceLabel(key)}
                    count={count}
                    icon={<ChevronRight className="h-3 w-3 text-emerald-600" />}
                    colorCls="bg-emerald-50"
                  />
                ))}
              </div>
            )}

            {/* Ignored categories */}
            {ignoredEntries.length > 0 && (
              <div className="space-y-1">
                <p className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <TrendingDown className="h-3 w-3 text-amber-500" />
                  較少回應的提醒類型
                </p>
                {ignoredEntries.map(([key, count]) => (
                  <CategoryRow
                    key={key}
                    label={sourceLabel(key)}
                    count={count}
                    icon={<ChevronRight className="h-3 w-3 text-amber-500" />}
                    colorCls="bg-amber-50"
                  />
                ))}
              </div>
            )}

            {/* Preferred types */}
            {profile.preferred_notification_types.length > 0 && (
              <div className="rounded-md bg-violet-50 px-3 py-2">
                <p className="mb-1 text-xs font-semibold text-violet-700">助手已優先為您排序：</p>
                <p className="text-xs text-violet-600">
                  {profile.preferred_notification_types.map(sourceLabel).join('、')}
                </p>
              </div>
            )}

            {/* Response style badge */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">提醒模式：</span>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                profile.response_style === 'proactive'
                  ? 'bg-emerald-100 text-emerald-700'
                  : profile.response_style === 'minimal'
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-blue-100 text-blue-700'
              }`}>
                {profile.response_style === 'proactive' ? '積極模式'
                  : profile.response_style === 'minimal' ? '精簡模式'
                  : '平衡模式'}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
