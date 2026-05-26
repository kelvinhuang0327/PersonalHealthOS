'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { api } from '../../../lib/api'
import { trackEvent } from '../../../lib/analytics'

const QUICK_SYMPTOMS = ['頭痛', '疲勞', '失眠', '胸悶', '呼吸困難', '消化不良', '關節疼痛', '背痛', '頭暈', '心悸', '水腫']

const DURATION_OPTIONS = [
  { value: 'today', label: '今天才有' },
  { value: 'days', label: '持續幾天' },
  { value: 'week_plus', label: '超過一週' },
  { value: 'chronic', label: '長期慢性' },
]

export default function SymptomsPage() {
  const [logs, setLogs] = useState<any[]>([])
  const [metrics, setMetrics] = useState<any[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [other, setOther] = useState('')
  const [severity, setSeverity] = useState(2)
  const [durationCategory, setDurationCategory] = useState('today')
  const [notes, setNotes] = useState('')
  const [activeDate, setActiveDate] = useState<string | null>(null)

  const refresh = () => {
    api.listSymptoms().then(setLogs).catch(() => setLogs([]))
    api.listMetrics().then((rows: any) => setMetrics(rows || [])).catch(() => setMetrics([]))
  }

  useEffect(() => {
    trackEvent('view_symptoms', { page: '/platform/symptoms' })
    refresh()
  }, [])

  const toggleSymptom = (symptom: string) => {
    setSelected((prev) => (prev.includes(symptom) ? prev.filter((item) => item !== symptom) : [...prev, symptom]))
  }

  const submit = async () => {
    const symptomNames = [...selected]
    if (other.trim()) symptomNames.push(other.trim())
    if (symptomNames.length === 0) return
    await api.createSymptom({
      symptom_names: symptomNames,
      severity,
      duration_category: durationCategory,
      notes: notes || undefined,
      note: notes || undefined,
      occurred_at: new Date().toISOString(),
    })
    setSelected([])
    setOther('')
    setNotes('')
    setSeverity(2)
    setDurationCategory('today')
    refresh()
  }

  const recentLogs = useMemo(() => logs.slice(0, 20), [logs])

  const chronic = useMemo(() => {
    const twoWeeksAgo = Date.now() - 14 * 24 * 60 * 60 * 1000
    const counts = new Map<string, number>()
    for (const row of logs) {
      const ts = new Date(row.occurred_at).getTime()
      if (Number.isNaN(ts) || ts < twoWeeksAgo) continue
      counts.set(row.symptom, (counts.get(row.symptom) || 0) + 1)
    }
    const top = Array.from(counts.entries()).sort((a, b) => b[1] - a[1])[0]
    if (!top || top[1] < 3) return null
    return { symptom: top[0], count: top[1] }
  }, [logs])

  const abnormalMetricDates = useMemo(() => {
    const map = new Set<string>()
    for (const row of metrics) {
      const abnormal = (row.systolic_bp && row.systolic_bp >= 140) || (row.diastolic_bp && row.diastolic_bp >= 90) || (row.blood_glucose && row.blood_glucose >= 126)
      if (!abnormal || !row.recorded_at) continue
      map.add(new Date(row.recorded_at).toISOString().slice(0, 10))
    }
    return map
  }, [metrics])

  const heatmap = useMemo(() => {
    const days = 42
    const counts: Record<string, number> = {}
    for (const row of logs) {
      const key = new Date(row.occurred_at).toISOString().slice(0, 10)
      counts[key] = (counts[key] || 0) + 1
    }
    const result: Array<{ date: string; count: number; hasAbnormal: boolean }> = []
    for (let i = days - 1; i >= 0; i -= 1) {
      const date = new Date(Date.now() - i * 24 * 60 * 60 * 1000)
      const key = date.toISOString().slice(0, 10)
      result.push({ date: key, count: counts[key] || 0, hasAbnormal: abnormalMetricDates.has(key) })
    }
    return result
  }, [logs, abnormalMetricDates])

  const logsByDay = useMemo(() => {
    const map: Record<string, any[]> = {}
    for (const row of logs) {
      const key = new Date(row.occurred_at).toISOString().slice(0, 10)
      if (!map[key]) map[key] = []
      map[key].push(row)
    }
    return map
  }, [logs])

  return (
    <div className="space-y-4" data-testid="symptoms-page">
      {chronic ? (
        <Card className="border-amber-200 bg-amber-50">
          <p className="text-sm text-amber-800">{chronic.symptom} 已持續記錄 {chronic.count} 次（過去 2 週），建議追蹤</p>
          <Link href="/platform/insights" className="mt-1 inline-flex text-xs font-medium text-amber-700 hover:underline">查看洞察</Link>
        </Card>
      ) : null}

      <Card data-testid="symptoms-input-section">
        <h2 className="text-2xl font-semibold">快速症狀記錄</h2>
        <p className="mt-1 text-sm text-slate-500">點選常見症狀，快速完成每日紀錄。</p>

        <div className="mt-3 grid gap-2 sm:grid-cols-4">
          {QUICK_SYMPTOMS.map((symptom) => (
            <button
              key={symptom}
              type="button"
              onClick={() => toggleSymptom(symptom)}
              className={`min-h-11 rounded-xl border px-3 py-2 text-sm ${selected.includes(symptom) ? 'border-sky-300 bg-sky-50 text-sky-700' : 'border-slate-200 hover:bg-slate-50'}`}
            >
              {symptom}
            </button>
          ))}
          <input
            className="min-h-11 rounded-xl border px-3 py-2 text-sm"
            placeholder="其他..."
            value={other}
            onChange={(e) => setOther(e.target.value)}
          />
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <label className="text-sm">
            <span className="text-slate-600">嚴重程度</span>
            <select className="mt-1 w-full min-h-11 rounded-xl border px-3 py-2" value={severity} onChange={(e) => setSeverity(Number(e.target.value))}>
              <option value={1}>輕微</option>
              <option value={2}>中等</option>
              <option value={3}>嚴重</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="text-slate-600">持續時間</span>
            <select className="mt-1 w-full min-h-11 rounded-xl border px-3 py-2" value={durationCategory} onChange={(e) => setDurationCategory(e.target.value)}>
              {DURATION_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>

          <label className="text-sm md:col-span-1">
            <span className="text-slate-600">補充備註</span>
            <input className="mt-1 w-full min-h-11 rounded-xl border px-3 py-2" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </label>
        </div>

        <Button className="mt-4 min-h-11" onClick={() => void submit()}>儲存症狀</Button>
      </Card>

      <Card data-testid="symptoms-insight-section">
        <h3 className="font-semibold">症狀熱度日曆（近 6 週）</h3>
        <div className="mt-3 grid grid-cols-7 gap-1">
          {heatmap.map((day) => {
            const level = day.count >= 3 ? 'bg-rose-500' : day.count === 2 ? 'bg-amber-400' : day.count === 1 ? 'bg-emerald-300' : 'bg-slate-100'
            return (
              <button
                key={day.date}
                type="button"
                onClick={() => setActiveDate(day.date)}
                className={`min-h-11 rounded-md border ${level} ${day.hasAbnormal ? 'ring-2 ring-rose-300' : ''}`}
                title={`${day.date}: ${day.count} 次`}
              />
            )
          })}
        </div>
        {activeDate ? (
          <div className="mt-3 rounded-xl border bg-slate-50 p-3 text-sm">
            <p className="font-medium">{activeDate}</p>
            <ul className="mt-1 space-y-1 text-slate-600">
              {(logsByDay[activeDate] || []).map((row, idx) => <li key={`${row.id || idx}`}>• {row.symptom}（嚴重度 {row.severity}）</li>)}
              {(logsByDay[activeDate] || []).length === 0 ? <li>當日無症狀紀錄</li> : null}
            </ul>
          </div>
        ) : null}
      </Card>

      <Card data-testid="symptoms-list-section">
        <h3 className="font-semibold">近期症狀紀錄</h3>
        <div className="mt-2 space-y-2">
          {recentLogs.map((row) => (
            <div key={row.id} className="rounded-xl border p-3">
              <p className="font-medium">{row.symptom}</p>
              <p className="text-xs text-slate-500">{new Date(row.occurred_at).toLocaleString('zh-TW')} · 嚴重度 {row.severity}</p>
              {row.note ? <p className="mt-1 text-sm text-slate-600">{row.note}</p> : null}
            </div>
          ))}
          {recentLogs.length === 0 ? <p className="py-6 text-center text-sm text-slate-400">尚無症狀紀錄</p> : null}
        </div>
      </Card>
    </div>
  )
}
