import { Card } from '../ui/card'

export function AnalyticsKpiCard({ label, value, suffix }: { label: string; value: number | string; suffix?: string }) {
  return (
    <Card className="rounded-2xl p-5 text-sm">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold">
        {value}
        {suffix || ''}
      </p>
    </Card>
  )
}
