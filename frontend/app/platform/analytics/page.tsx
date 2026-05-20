'use client'

import { useEffect, useMemo } from 'react'
import { BarChart3, Users } from 'lucide-react'
import { AnalyticsKpiCard } from '../../components/platform/analytics-kpi-card'
import { Card } from '../../components/ui/card'
import { FunnelChart } from '../../components/platform/funnel-chart'
import { RecentEventsList } from '../../components/platform/recent-events-list'
import { RetentionCard } from '../../components/platform/retention-card'
import { TopEventsTable } from '../../components/platform/top-events-table'
import { getAnalyticsSummary, trackEvent } from '../../../lib/analytics'

export default function AnalyticsPage() {
  const summary = useMemo(() => getAnalyticsSummary(), [])
  useEffect(() => {
    trackEvent('view_analytics', { page: '/platform/analytics' })
  }, [])

  return (
    <div className="space-y-6">
      <Card className="rounded-2xl p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">產品分析</h1>
            <p className="text-sm text-slate-500">快速查看 DAU / WAU / MAU、留存與漏斗轉換。</p>
          </div>
          <div className="flex items-center gap-2 rounded-xl bg-slate-100 px-3 py-2 text-sm text-slate-600">
            <Users className="h-4 w-4" />
            本地分析資料
          </div>
        </div>
      </Card>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <AnalyticsKpiCard label="DAU" value={summary.kpi.dau} />
        <AnalyticsKpiCard label="WAU" value={summary.kpi.wau} />
        <AnalyticsKpiCard label="MAU" value={summary.kpi.mau} />
        <AnalyticsKpiCard label="黏著度" value={(summary.kpi.stickiness * 100).toFixed(1)} suffix="%" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <FunnelChart data={summary.funnel} />
        <RetentionCard day1={summary.retention.day1} day7={summary.retention.day7} day30={summary.retention.day30} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <TopEventsTable events={summary.topEvents} />
        <RecentEventsList events={summary.recentEvents} />
      </div>
      <Card className="rounded-2xl p-4 text-sm text-slate-500">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          漏斗順序：開啟 App → 儀表板 → 洞察 → 建立行動 → 回報 → 完成
        </div>
      </Card>
    </div>
  )
}
