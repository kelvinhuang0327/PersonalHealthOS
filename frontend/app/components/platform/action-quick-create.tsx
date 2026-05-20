'use client'

import { HealthAction } from '../../../lib/actions'
import { Button } from '../ui/button'

export function ActionQuickCreate({
  onCreate,
  sourceType,
  source,
}: {
  onCreate: (sourceType: HealthAction['source_type'], source: Record<string, unknown>, status?: HealthAction['status']) => Promise<void> | void
  sourceType: HealthAction['source_type']
  source: Record<string, unknown>
}) {
  return (
    <div className="mt-3 space-y-2">
      <div className="flex flex-wrap gap-2">
        <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={() => onCreate(sourceType, source, 'in_progress')}>開始改善</Button>
        <Button className="bg-sky-600 hover:bg-sky-700" onClick={() => onCreate(sourceType, source, 'todo')}>加入追蹤</Button>
        <Button className="bg-slate-600 hover:bg-slate-700" onClick={() => onCreate(sourceType, source, 'snoozed')}>稍後提醒</Button>
      </div>
      <p className="text-xs text-slate-500">建立任務時會保留來源、優先級、頻率與 explainability metadata。</p>
    </div>
  )
}
