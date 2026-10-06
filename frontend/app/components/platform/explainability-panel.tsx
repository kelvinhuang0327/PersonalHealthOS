'use client'

import { useState } from 'react'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Card } from '../ui/card'
import { Tooltip } from '../ui/tooltip'

type Explain = {
  rule_id?: string
  category?: string
  priority?: number
  confidence?: number
  evidence_level?: string
  guideline_source?: string
}

function humanizeConfidence(confidence?: number) {
  if (typeof confidence !== 'number') return '未提供'
  if (confidence >= 0.8) return '高'
  if (confidence >= 0.65) return '中'
  return '低'
}

function humanizeEvidence(level?: string) {
  const value = String(level || '').toUpperCase()
  if (value === 'A') return '較強'
  if (value === 'B') return '中等'
  if (value === 'C') return '基礎'
  return '未標示'
}

export function ExplainabilityPanel({ explain }: { explain?: Explain }) {
  const [open, setOpen] = useState(false)
  if (!explain) return null

  return (
    <Card className="mt-2 bg-slate-50">
      <div className="flex flex-wrap items-center gap-2">
        <Tooltip trigger={<Badge>規則 {explain.rule_id || '-'}</Badge>} content="規則來源" />
        <Badge>類別 {explain.category || '未知'}</Badge>
        <Badge>建議優先 {explain.priority != null && explain.priority >= 8 ? '高' : explain.priority != null && explain.priority >= 5 ? '中' : '低'}</Badge>
        <Badge>可信度 {humanizeConfidence(explain.confidence)}</Badge>
        <Badge>證據 {humanizeEvidence(explain.evidence_level)}</Badge>
        <Badge>依據 {explain.guideline_source || '系統規則'}</Badge>
        <Button type="button" className="ml-auto bg-slate-700 hover:bg-slate-800" onClick={() => setOpen((v) => !v)}>
          {open ? '收合說明' : '展開說明'}
        </Button>
      </div>
      {open ? <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(explain, null, 2)}</pre> : null}
    </Card>
  )
}
