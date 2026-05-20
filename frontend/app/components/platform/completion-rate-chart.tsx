'use client'

import { useEffect, useState } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { Card } from '../ui/card'

export function CompletionRateChart({ completionRate }: { completionRate: number }) {
  const [ready, setReady] = useState(false)
  const data = [
    { name: '已完成', value: completionRate },
    { name: '未完成', value: Math.max(0, 100 - completionRate) },
  ]

  useEffect(() => {
    setReady(true)
  }, [])

  return (
    <Card>
      <h3 className="mb-2 font-semibold">Action Completion Rate</h3>
      <div className="h-52 w-full">
        {!ready ? (
          <div className="flex h-full items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-400">正在準備圖表...</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" innerRadius={52} outerRadius={78}>
                <Cell fill="#22c55e" />
                <Cell fill="#e2e8f0" />
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
      <p className="text-center text-sm text-slate-600">{completionRate.toFixed(0)}%</p>
    </Card>
  )
}
