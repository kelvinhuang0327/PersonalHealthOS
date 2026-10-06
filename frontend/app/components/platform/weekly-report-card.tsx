import { Card } from '../ui/card'
import { AchievementBadge } from './achievement-badge'
import { StreakBadge } from './streak-badge'

export function WeeklyReportCard({
  scoreDelta,
  riskTrend,
  completionRate,
  topInsights,
  suggestions,
  streakBest,
}: {
  scoreDelta: number
  riskTrend: 'up' | 'down' | 'flat'
  completionRate: number
  topInsights: string[]
  suggestions: string[]
  streakBest: number
}) {
  return (
    <Card>
      <h3 className="font-semibold">每週健康報告</h3>
      <div className="mt-2 grid gap-2 text-sm sm:grid-cols-3">
        <div className="rounded-lg bg-sky-50 p-2">健康分數變化 <strong>{scoreDelta > 0 ? `+${scoreDelta}` : scoreDelta}</strong></div>
        <div className="rounded-lg bg-rose-50 p-2">風險趨勢 <strong>{riskTrend}</strong></div>
        <div className="rounded-lg bg-emerald-50 p-2">完成率 <strong>{completionRate.toFixed(0)}%</strong></div>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        <StreakBadge streak={streakBest} />
        <AchievementBadge achieved={streakBest >= 7} label="連續 7 天" />
        <AchievementBadge achieved={completionRate >= 80} label="每週完成 80%" />
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-sm font-medium">重點洞察</p>
          <ul className="mt-1 list-disc pl-5 text-xs text-slate-600">
            {topInsights.map((row) => <li key={row}>{row}</li>)}
          </ul>
        </div>
        <div>
          <p className="text-sm font-medium">改善建議</p>
          <ul className="mt-1 list-disc pl-5 text-xs text-slate-600">
            {suggestions.map((row) => <li key={row}>{row}</li>)}
          </ul>
        </div>
      </div>
    </Card>
  )
}
