'use client'

import { useEffect, useState } from 'react'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card } from '../ui/card'

export function FunnelChart({ data }: { data: Array<{ step: string; count: number; rate: number }> }) {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    setReady(true)
  }, [])

  return (
    <Card>
      <h3 className="mb-2 font-semibold">Funnel</h3>
      <div className="h-64">
        {!ready ? (
          <div className="flex h-full items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-400">正在準備圖表...</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <XAxis dataKey="step" interval={0} angle={-15} textAnchor="end" height={56} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  )
}
