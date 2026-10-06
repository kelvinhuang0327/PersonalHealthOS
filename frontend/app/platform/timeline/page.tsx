'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { CalendarDays, Filter, Search } from 'lucide-react'
import { StateCard } from '../../components/platform/state-card'
import { ExplainabilityPanel } from '../../components/platform/explainability-panel'
import { Card } from '../../components/ui/card'
import { api } from '../../../lib/api'
import { trackEvent } from '../../../lib/analytics'

export default function TimelinePage() {
  const [items, setItems] = useState<any[]>([])
  const [days, setDays] = useState(180)
  const [type, setType] = useState('all')
  const [keyword, setKeyword] = useState('')
  const [order, setOrder] = useState<'desc' | 'asc'>('desc')

  const load = useCallback(() => {
    api.getTimeline(days, 300).then((r: any) => setItems(r.items || [])).catch(() => setItems([]))
  }, [days])

  useEffect(() => {
    trackEvent('view_timeline', { page: '/platform/timeline' })
    load()
  }, [load])

  const typeCounts = useMemo(() => {
    return items.reduce(
      (acc, item) => {
        const k = item.type || 'other'
        acc[k] = (acc[k] || 0) + 1
        return acc
      },
      {} as Record<string, number>
    )
  }, [items])

  const filteredItems = useMemo(() => {
    const q = keyword.trim().toLowerCase()
    const list = items
      .filter((i) => type === 'all' || i.type === type)
      .filter((i) => {
        if (!q) return true
        const text = `${i.title || ''} ${i.label || ''} ${i.description || ''}`.toLowerCase()
        return text.includes(q)
      })
    return [...list].sort((a, b) => {
      const av = new Date(a.start_date || a.end_date || 0).getTime()
      const bv = new Date(b.start_date || b.end_date || 0).getTime()
      return order === 'desc' ? bv - av : av - bv
    })
  }, [items, keyword, order, type])

  const latestNarrative = useMemo(() => items.find((item) => item.type === 'narrative_summary') || null, [items])

  return (
    <div className="space-y-6">
      <Card className="rounded-2xl p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold">健康時間軸</h2>
            <p className="text-sm text-slate-500">以事件流方式檢視症狀、指標、報告與洞察的變化。</p>
          </div>
          <div className="rounded-xl bg-slate-100 px-3 py-2 text-sm text-slate-600">{filteredItems.length} 筆事件</div>
        </div>
        {latestNarrative ? (
          <div className="mt-4">
            <StateCard
              tone="info"
              title="健康敘事更新"
              description={latestNarrative.description || '系統已整理最近一次健康變化，現在可以先看 summary 與 delta。'}
              badgeText="Narrative"
            />
          </div>
        ) : null}
        <div className="mt-4 grid gap-2 md:grid-cols-4">
          <label className="flex items-center gap-2 rounded-xl border bg-white px-3 py-2 text-sm text-slate-500">
            <CalendarDays className="h-4 w-4" />
            <input className="w-full border-none bg-transparent outline-none" type="number" value={days} onChange={(e) => setDays(Number(e.target.value))} />
          </label>
          <label className="flex items-center gap-2 rounded-xl border bg-white px-3 py-2 text-sm text-slate-500">
            <Filter className="h-4 w-4" />
            <select className="w-full border-none bg-transparent outline-none" value={type} onChange={(e) => setType(e.target.value)}>
              <option value="all">全部類型</option>
              <option value="symptom">症狀</option>
              <option value="metric">指標</option>
              <option value="lab">檢驗</option>
              <option value="alert">提醒</option>
              <option value="insight">洞察</option>
            </select>
          </label>
          <label className="flex items-center gap-2 rounded-xl border bg-white px-3 py-2 text-sm text-slate-500 md:col-span-2">
            <Search className="h-4 w-4" />
            <input className="w-full border-none bg-transparent outline-none" placeholder="搜尋時間軸..." value={keyword} onChange={(e) => setKeyword(e.target.value)} />
          </label>
          <select className="rounded-xl border px-3 py-2 text-sm md:col-span-1" value={order} onChange={(e) => setOrder(e.target.value as 'desc' | 'asc')}>
            <option value="desc">最新優先</option>
            <option value="asc">最早優先</option>
          </select>
        </div>
      </Card>
      <div className="grid gap-2 sm:grid-cols-3">
        <Card className="rounded-2xl text-sm">全部事件 <p className="text-2xl font-semibold">{items.length}</p></Card>
        <Card className="rounded-2xl text-sm">目前顯示 <p className="text-2xl font-semibold">{filteredItems.length}</p></Card>
        <Card className="rounded-2xl text-sm">提醒 + 洞察 <p className="text-2xl font-semibold">{(typeCounts.alert || 0) + (typeCounts.insight || 0)}</p></Card>
      </div>
      <div className="relative space-y-3 border-l border-slate-200 pl-4">
        {filteredItems.map((item, idx) => (
          <div key={`${idx}-${item.type}`} className="relative">
            <span className="absolute -left-[22px] top-6 h-3 w-3 rounded-full border-2 border-white bg-sky-500 shadow-sm" />
            <Card className="rounded-2xl p-5">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-base font-semibold">{item.title || item.label}</h3>
                <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">{item.type}</span>
              </div>
              <p className="mt-1 text-xs text-slate-500">{item.start_date || item.event_time} {item.end_date ? `~ ${item.end_date}` : ''}</p>
              <p className="mt-2 text-sm text-slate-700">{item.description || '-'}</p>
              {(item.type === 'insight' || item.type === 'alert') ? (
                <ExplainabilityPanel
                  explain={{
                    rule_id: item?.data?.rule_id,
                    category: item?.data?.category || item.type,
                    priority: item?.data?.priority,
                    confidence: item?.data?.confidence,
                    evidence_level: item?.data?.evidence_level,
                    guideline_source: item?.data?.guideline_source,
                  }}
                />
              ) : null}
            </Card>
          </div>
        ))}
      </div>
    </div>
  )
}
