import { Card } from '../ui/card'

function fmt(v: number | null) {
  if (v === null || Number.isNaN(v)) return '資料不足'
  return `${(v * 100).toFixed(1)}%`
}

export function RetentionCard({
  day1,
  day7,
  day30,
}: {
  day1: number | null
  day7: number | null
  day30: number | null
}) {
  return (
    <Card>
      <h3 className="font-semibold">Retention</h3>
      <div className="mt-2 grid grid-cols-3 gap-2 text-sm">
        <div className="rounded-lg bg-slate-50 p-2">D1 <strong>{fmt(day1)}</strong></div>
        <div className="rounded-lg bg-slate-50 p-2">D7 <strong>{fmt(day7)}</strong></div>
        <div className="rounded-lg bg-slate-50 p-2">D30 <strong>{fmt(day30)}</strong></div>
      </div>
    </Card>
  )
}
