'use client'

import { useEffect, useState } from 'react'
import { Card } from '../ui/card'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export function TrendChart({ title, points }: { title: string; points: Array<{ recorded_at: string; value: number }> }) {
  const [ready, setReady] = useState(false)
  const data = points.map((p) => ({ date: p.recorded_at.slice(5, 10), value: p.value }))

  useEffect(() => {
    setReady(true)
  }, [])

  return (
    <Card>
      <h3 className="mb-2 font-semibold">{title}</h3>
      <div className="h-56 w-full">
        {!ready ? (
          <div className="flex h-full items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-400">正在準備圖表...</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#0ea5e9" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  )
}
