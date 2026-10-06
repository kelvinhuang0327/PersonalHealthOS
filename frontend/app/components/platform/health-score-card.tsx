import { Card } from '../ui/card'

export function HealthScoreCard({ score }: { score?: { overall_score?: number; components?: Record<string, number> } }) {
  return (
    <Card>
      <h3 className="text-lg font-semibold">健康分數</h3>
      <p className="mono-data neon-value text-3xl font-bold text-emerald-400">{score?.overall_score ?? '--'}</p>
      <div className="mt-2 text-sm text-slate-600">
        {Object.entries(score?.components || {}).map(([k, v]) => (
          <div key={k}>{k}: {v}</div>
        ))}
      </div>
    </Card>
  )
}
