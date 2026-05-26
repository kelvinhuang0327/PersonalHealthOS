'use client'

import { useEffect, useMemo, useState } from 'react'
import { Fragment } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../../../lib/api'

type Row = {
  metric: string
  report_date: string | null
  document_id: string
  document_name: string
  value: number | string | null
  unit: string | null
  is_abnormal: boolean
  reference_range: string | null
}

type FilterKey = 'all' | 'abnormal' | 'value_down' | 'value_up'

export function LabComparisonTable() {
  const [rows, setRows] = useState<Row[]>([])
  const [filter, setFilter] = useState<FilterKey>('all')
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    api.getLabHistory(undefined, 5).then((data: any) => setRows((data || []) as Row[])).catch(() => setRows([]))
  }, [])

  const grouped = useMemo(() => {
    const map = new Map<string, Row[]>()
    for (const row of rows) {
      const key = row.metric || 'Unknown'
      const current = map.get(key) || []
      current.push(row)
      map.set(key, current)
    }
    for (const [key, vals] of map.entries()) {
      vals.sort((a, b) => new Date(b.report_date || 0).getTime() - new Date(a.report_date || 0).getTime())
      map.set(key, vals)
    }
    return map
  }, [rows])

  const tableRows = useMemo(() => {
    const base = Array.from(grouped.entries()).map(([metric, values]) => {
      const latest = values[0]
      const prev = values[1]
      const latestNum = typeof latest?.value === 'number' ? latest.value : Number(latest?.value)
      const prevNum = typeof prev?.value === 'number' ? prev.value : Number(prev?.value)
      const hasNumbers = Number.isFinite(latestNum) && Number.isFinite(prevNum)
      const deltaPct = hasNumbers && prevNum !== 0 ? ((latestNum - prevNum) / prevNum) * 100 : null
      const improved = deltaPct !== null ? deltaPct < 0 : null
      return { metric, values, latest, prev, deltaPct, improved }
    })

    if (filter === 'abnormal') return base.filter((r) => r.latest?.is_abnormal)
    if (filter === 'value_down') return base.filter((r) => r.improved === true)
    if (filter === 'value_up') return base.filter((r) => r.improved === false)
    return base
  }, [grouped, filter])

  const deltaClass = (deltaPct: number | null) => {
    if (deltaPct === null) return 'text-slate-400'
    return deltaPct > 0 ? 'text-rose-600' : 'text-emerald-600'
  }

  return (
    <div className="space-y-3" data-testid="lab-comparison-table">
      <div className="flex flex-wrap gap-2">
        {[
          ['all', '全部'],
          ['abnormal', '異常指標'],
          ['value_down', '數值下降'],
          ['value_up', '數值上升'],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key as FilterKey)}
            className={`rounded-full px-3 py-1.5 text-xs ${filter === key ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600'}`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-2xl border">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-3 py-2 text-left">指標</th>
              <th className="px-3 py-2 text-left">最新值</th>
              <th className="px-3 py-2 text-left">上次值</th>
              <th className="px-3 py-2 text-left">變化</th>
              <th className="px-3 py-2 text-left">參考範圍</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {tableRows.map((row) => {
              const expandedNow = expanded === row.metric
              return (
                <Fragment key={row.metric}>
                  <tr key={row.metric} className="border-t">
                    <td className="px-3 py-2 font-medium">{row.metric}</td>
                    <td className="px-3 py-2">{row.latest?.value ?? '—'} {row.latest?.unit || ''}</td>
                    <td className="px-3 py-2">{row.prev?.value ?? '尚無歷史資料'} {row.prev?.unit || ''}</td>
                    <td className={`px-3 py-2 ${deltaClass(row.deltaPct)}`}>
                      {row.deltaPct === null ? '—' : `${row.deltaPct > 0 ? '↑' : '↓'} ${Math.abs(row.deltaPct).toFixed(1)}%`}
                    </td>
                    <td className="px-3 py-2 text-slate-500">{row.latest?.reference_range || '—'}</td>
                    <td className="px-3 py-2 text-right">
                      <button type="button" className="rounded p-1 hover:bg-slate-100" onClick={() => setExpanded(expandedNow ? null : row.metric)}>
                        {expandedNow ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </button>
                    </td>
                  </tr>
                  {expandedNow ? (
                    <tr className="bg-slate-50">
                      <td colSpan={6} className="px-3 py-2 text-xs text-slate-500">
                        <div className="flex flex-wrap gap-3">
                          {row.values.map((v) => (
                            <div key={`${v.metric}_${v.document_id}_${v.report_date}`} className="rounded-lg border bg-white px-2 py-1">
                              {v.report_date || '-'}：{v.value} {v.unit || ''}
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              )
            })}
            {tableRows.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-slate-400">尚無歷史資料</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
