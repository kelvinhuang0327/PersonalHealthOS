'use client'

import { useEffect, useMemo, useState } from 'react'
import { CompletionRateChart } from '../../components/platform/completion-rate-chart'
import { WeeklyReportCard } from '../../components/platform/weekly-report-card'
import { Card } from '../../components/ui/card'
import { useActions } from '../../providers/action-context'
import { api } from '../../../lib/api'
import { trackEvent } from '../../../lib/analytics'

export default function WeeklyReportPage() {
  const { actions } = useActions()
  const [dashboard, setDashboard] = useState<any>(null)
  const [insights, setInsights] = useState<any[]>([])

  useEffect(() => {
    trackEvent('view_weekly_report', { page: '/platform/weekly-report' })
    api.getDashboard().then(setDashboard).catch(() => setDashboard(null))
    api.listInsights().then(setInsights).catch(() => setInsights([]))
  }, [])

  const completionRate = useMemo(() => {
    if (!actions.length) return 0
    const done = actions.filter((a) => a.status === 'done').length
    return (done / actions.length) * 100
  }, [actions])

  const scoreDelta = useMemo(() => {
    const score = Number(dashboard?.health_score?.overall_score || 0)
    const improvedCount = actions.filter((a) => a.impact_status === 'improved').length
    return improvedCount - Math.max(0, 80 - score) / 10
  }, [dashboard, actions])

  const riskTrend = useMemo<'up' | 'down' | 'flat'>(() => {
    const alerts = (dashboard?.alerts || []).length
    if (alerts >= 3) return 'up'
    if (alerts === 0) return 'down'
    return 'flat'
  }, [dashboard])

  const topInsights = useMemo(() => insights.slice(0, 3).map((i) => i.title || i.summary || 'Insight'), [insights])
  const suggestions = useMemo(() => {
    const rows = actions.filter((a) => a.status !== 'done').slice(0, 3).map((a) => `優先完成：${a.title}`)
    if (!rows.length) return ['本週維持現有習慣，持續追蹤指標']
    return rows
  }, [actions])
  const streakBest = useMemo(() => actions.reduce((max, a) => Math.max(max, a.streak || 0), 0), [actions])

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="text-2xl font-semibold">每週健康報告</h2>
        <p className="text-sm text-slate-600">每週健康分數、行動完成率、風險變化與行為回饋。</p>
      </Card>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <WeeklyReportCard
            scoreDelta={Number(scoreDelta.toFixed(1))}
            riskTrend={riskTrend}
            completionRate={completionRate}
            topInsights={topInsights}
            suggestions={suggestions}
            streakBest={streakBest}
          />
        </div>
        <CompletionRateChart completionRate={completionRate} />
      </div>
    </div>
  )
}
