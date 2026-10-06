'use client'

import { useEffect, useState } from 'react'
import { HealthAction } from '../../../lib/actions'
import { Card } from '../ui/card'
import { ExplainabilityPanel } from './explainability-panel'
import { ActionFeedbackBadge } from './action-feedback-badge'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export function ActionDrawer({ action }: { action: HealthAction | null }) {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    setReady(true)
  }, [])

  if (!action) return null
  const recentTrend = Array.from({ length: 7 }).map((_, i) => ({
    day: `D-${6 - i}`,
    value:
      action.impact_status === 'improved'
        ? 70 + i * 3
        : action.impact_status === 'worse'
        ? 88 - i * 2
        : 80 + (i % 2 === 0 ? 1 : -1),
  }))

  return (
    <Card className="mt-2 bg-slate-50">
      <h4 className="font-semibold">任務細節與回饋</h4>
      <p className="text-sm text-slate-700">{action.description}</p>
      <div className="mt-3">
        <ActionFeedbackBadge action={action} />
      </div>
      <div className="mt-2 text-xs text-slate-600">
        <p>來源: {action.source_type}</p>
        <p>類型: {action.action_type}</p>
        <p>到期: {action.due_date || '-'}</p>
        <p>頻率: {action.frequency || '-'}</p>
        <p>連續完成: {action.streak || 0}</p>
        <p>影響狀態: {action.impact_status || 'no_change'}</p>
        <p>提醒狀態: {action.reminder_status || 'none'}</p>
      </div>
      <div className="mt-2 h-40 w-full rounded-xl border border-slate-200 bg-white p-2">
        <p className="mb-1 text-xs text-slate-500">最近任務影響趨勢</p>
        {!ready ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-400">正在準備圖表...</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={recentTrend}>
              <XAxis dataKey="day" />
              <YAxis domain={['auto', 'auto']} />
              <Tooltip />
              <Line dataKey="value" stroke="#0ea5e9" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
      <ExplainabilityPanel
        explain={{
          rule_id: action.rule_id,
          category: action.category,
          priority: action.priority === 'high' ? 9 : action.priority === 'medium' ? 6 : 3,
          confidence: action.confidence,
          evidence_level: action.evidence_level,
          guideline_source: action.guideline_source,
        }}
      />
    </Card>
  )
}
