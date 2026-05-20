'use client'

import { Card } from '../ui/card'

export function GrowthBanner({
  hasStreakBreak,
  hasOverdue,
  hasRiskUp,
  inactiveDays,
}: {
  hasStreakBreak: boolean
  hasOverdue: boolean
  hasRiskUp: boolean
  inactiveDays: number
}) {
  const messages: string[] = []
  if (hasRiskUp) messages.push('風險升高提醒：建議優先處理高風險行動')
  if (hasOverdue) messages.push('你有逾期未完成任務，今天完成一項即可回到軌道')
  if (hasStreakBreak) messages.push('習慣連續中斷，現在完成一次 check-in 可重啟 streak')
  if (inactiveDays >= 3) messages.push(`你已 ${inactiveDays} 天未開啟系統，回來查看最新健康變化`)
  if (messages.length === 0) return null
  return (
    <Card className="border-amber-200 bg-amber-50">
      <h3 className="font-semibold text-amber-800">Growth Reminder</h3>
      <ul className="mt-1 list-disc pl-5 text-sm text-amber-700">
        {messages.map((m) => (
          <li key={m}>{m}</li>
        ))}
      </ul>
    </Card>
  )
}
