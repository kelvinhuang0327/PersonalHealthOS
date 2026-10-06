'use client'

import { ResponsiveContainer, LineChart, Line, XAxis, Tooltip } from 'recharts'

interface Point {
  recorded_at: string
  value: number
}

export function CategoryMiniTrend({ points, color = '#0ea5e9' }: { points: Point[]; color?: string }) {
  if (!points.length) {
    return <div className="flex h-20 items-center justify-center rounded-xl bg-slate-50 text-xs text-slate-400">目前沒有趨勢資料</div>
  }

  const data = points.map((point) => ({
    label: new Date(point.recorded_at).toLocaleDateString('zh-TW', { month: 'numeric', day: 'numeric' }),
    value: point.value,
  }))

  return (
    <div className="h-20 w-full rounded-xl bg-slate-50 px-2 py-1">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <XAxis dataKey="label" hide />
          <Tooltip formatter={(value: any) => [String(value), '數值']} />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} isAnimationActive />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
