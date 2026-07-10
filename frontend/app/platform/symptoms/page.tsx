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

function asArray(value: any): any[] {
  return Array.isArray(value) ? value : []
}

function firstText(...values: any[]) {
  const found = values.find((value) => typeof value === 'string' && value.trim().length > 0)
  return found ? found.trim() : ''
}

function formatLocalDateTime(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  const yyyy = date.getFullYear()
  const MM = pad(date.getMonth() + 1)
  const dd = pad(date.getDate())
  const hh = pad(date.getHours())
  const mm = pad(date.getMinutes())
  return `${yyyy}-${MM}-${dd}T${hh}:${mm}`
}

function parseLocalDateTime(localStr: string): Date | null {
  if (!localStr) return null
  const parts = localStr.split('T')
  if (parts.length !== 2) return null
  const [datePart, timePart] = parts
  const dateSplit = datePart.split('-')
  const timeSplit = timePart.split(':')
  if (dateSplit.length !== 3 || timeSplit.length < 2) return null
  const year = parseInt(dateSplit[0], 10)
  const month = parseInt(dateSplit[1], 10)
  const day = parseInt(dateSplit[2], 10)
  const hour = parseInt(timeSplit[0], 10)
  const minute = parseInt(timeSplit[1], 10)
  if (isNaN(year) || isNaN(month) || isNaN(day) || isNaN(hour) || isNaN(minute)) return null
  return new Date(year, month - 1, day, hour, minute)
}

export default function SymptomsPage() {
  const [logs, setLogs] = useState<any[]>([])
  const [metrics, setMetrics] = useState<any[]>([])
  const [evidenceBundle, setEvidenceBundle] = useState<any>(null)
  const [dailySummary, setDailySummary] = useState<any>(null)
  const [assistantContext, setAssistantContext] = useState<any>(null)
  const [nearTermActions, setNearTermActions] = useState<any[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [other, setOther] = useState('')
  const [severity, setSeverity] = useState(2)
  const [durationCategory, setDurationCategory] = useState('today')
  const [notes, setNotes] = useState('')
  const [activeDate, setActiveDate] = useState<string | null>(null)
  const [occurredAt, setOccurredAt] = useState<string>('')
  const [maxDateTime, setMaxDateTime] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const refresh = () => {
    api.listSymptoms().then(setLogs).catch(() => setLogs([]))
    api.listMetrics().then((rows: any) => {
      const arr = Array.isArray(rows) ? rows : (rows && Array.isArray(rows.items) ? rows.items : [])
      setMetrics(arr)
    }).catch(() => setMetrics([]))
    api.getEvidenceBundle().then(setEvidenceBundle).catch(() => setEvidenceBundle(null))
    api.getDailySummary().then(setDailySummary).catch(() => setDailySummary(null))
    api.getRecommendations().then(setAssistantContext).catch(() => setAssistantContext(null))
    api.getActions(undefined, 2).then((rows: any) => {
      setNearTermActions(Array.isArray(rows) ? rows : [])
    }).catch(() => setNearTermActions([]))
  }

  useEffect(() => {
    trackEvent('view_symptoms', { page: '/platform/symptoms' })
    refresh()
    const now = new Date()
    setOccurredAt(formatLocalDateTime(now))
    setMaxDateTime(formatLocalDateTime(now))
  }, [])

  const toggleSymptom = (symptom: string) => {
    setSelected((prev) => (prev.includes(symptom) ? prev.filter((item) => item !== symptom) : [...prev, symptom]))
    setError(null)
  }

  const submit = async () => {
    const symptomNames = [...selected]
    if (other.trim()) symptomNames.push(other.trim())
    if (symptomNames.length === 0) return
    setError(null)
    if (!occurredAt) {
      setError('請選擇發生的日期與時間')
      return
    }
    const parsedDate = parseLocalDateTime(occurredAt)
    if (!parsedDate || isNaN(parsedDate.getTime())) {
      setError('請輸入有效的日期與時間')
      return
    }
    if (parsedDate.getTime() > Date.now()) {
      setError('不能選擇未來的時間')
      return
    }
    await api.createSymptom({
      symptom_names: symptomNames,
      severity,
      duration_category: durationCategory,
      notes: notes || undefined,
      note: notes || undefined,
      occurred_at: parsedDate.toISOString(),
    })
    setSelected([])
    setOther('')
    setNotes('')
    setSeverity(2)
    setDurationCategory('today')
    const now = new Date()
    setOccurredAt(formatLocalDateTime(now))
    setMaxDateTime(formatLocalDateTime(now))
    setError(null)
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
    if (!Array.isArray(metrics)) return map
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

  const reportSignals = useMemo(() => {
    const seen = new Set<string>()
    return [
      ...asArray(assistantContext?.lab_abnormalities),
      ...asArray(evidenceBundle?.lab_abnormalities),
    ].filter((item) => {
      const key = `${item.rule_id || item.id || item.labItemName || item.lab_item_name}-${item.reportId || item.report_id || ''}`
      if (seen.has(key)) return false
      seen.add(key)
      return firstText(item.labItemName, item.lab_item_name, item.item_name)
    }).slice(0, 3)
  }, [assistantContext, evidenceBundle])

  const symptomPatterns = useMemo(() => {
    const seen = new Set<string>()
    return [
      ...asArray(assistantContext?.symptom_patterns),
      ...asArray(evidenceBundle?.symptom_patterns),
    ].filter((item) => {
      const key = `${item.patternType || item.pattern_type || item.label || item.symptomType || item.symptom_type}`
      if (seen.has(key)) return false
      seen.add(key)
      return firstText(item.label, item.whyDetected, item.why_detected, item.symptomType, item.symptom_type)
    }).slice(0, 2)
  }, [assistantContext, evidenceBundle])

  const topRecommendation = useMemo(() => asArray(assistantContext?.recommendations)[0] || null, [assistantContext])
  const currentAction = useMemo(() => nearTermActions.find((action) => action.status !== 'done' && action.status !== 'completed') || nearTermActions[0] || null, [nearTermActions])
  const hasDailyActionContext = Boolean(
    firstText(dailySummary?.todayAction, dailySummary?.topRisk, topRecommendation?.title, topRecommendation?.next_action, currentAction?.title, currentAction?.action_title)
  )
  const hasIntegratedContext = hasDailyActionContext || reportSignals.length > 0 || symptomPatterns.length > 0

  return (
    <div className="space-y-4" data-testid="symptoms-page">
      {chronic ? (
        <Card className="border-amber-200 bg-amber-50">
          <p className="text-sm text-amber-800">{chronic.symptom} 已持續記錄 {chronic.count} 次（過去 2 週），建議追蹤</p>
          <Link href="/platform/insights" className="mt-1 inline-flex text-xs font-medium text-amber-700 hover:underline">查看洞察</Link>
        </Card>
      ) : null}

      {hasIntegratedContext ? (
        <Card data-testid="symptoms-integrated-context" className="border-sky-100 bg-sky-50/60">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">症狀整合脈絡</h2>
              <p className="mt-1 text-sm text-slate-600">把症狀紀錄、報告異常與今天建議放在同一頁追蹤。</p>
            </div>
            {assistantContext?.generated_at ? (
              <span className="rounded-full bg-white px-3 py-1 text-xs text-slate-500">
                {new Date(assistantContext.generated_at).toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })} 更新
              </span>
            ) : null}
          </div>

          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            {reportSignals.length > 0 ? (
              <div data-testid="symptoms-report-signal-context" className="rounded-xl border border-rose-100 bg-white p-3">
                <p className="text-xs font-semibold text-rose-700">報告異常訊號</p>
                <div className="mt-2 space-y-2">
                  {reportSignals.map((item, idx) => {
                    const name = firstText(item.labItemName, item.lab_item_name, item.item_name)
                    const value = item.currentValue ?? item.current_value ?? item.value_num ?? item.value_text ?? null
                    const range = item.referenceRange ?? item.reference_range ?? item.ref_range ?? null
                    return (
                      <div key={`${name}-${idx}`} className="rounded-lg bg-rose-50/60 p-2">
                        <p className="text-sm font-medium text-slate-900">{name}</p>
                        {value || range ? <p className="mt-0.5 text-xs text-slate-500">{value ? `目前 ${value}` : ''}{range ? ` · 參考 ${range}` : ''}</p> : null}
                        <p className="mt-1 text-xs text-slate-600">{firstText(item.suggestedAction, item.suggested_action, item.whyDetected, item.why_detected)}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : null}

            {hasDailyActionContext ? (
              <div data-testid="symptoms-daily-action-context" className="rounded-xl border border-emerald-100 bg-white p-3">
                <p className="text-xs font-semibold text-emerald-700">今日建議與行動</p>
                <p className="mt-2 text-sm font-medium text-slate-900">
                  {firstText(dailySummary?.todayAction, topRecommendation?.next_action, currentAction?.title, currentAction?.action_title, topRecommendation?.title)}
                </p>
                {firstText(dailySummary?.whyNow, topRecommendation?.why_now, topRecommendation?.evidence_summary, dailySummary?.topRisk) ? (
                  <p className="mt-1 text-xs text-slate-600">
                    {firstText(dailySummary?.whyNow, topRecommendation?.why_now, topRecommendation?.evidence_summary, dailySummary?.topRisk)}
                  </p>
                ) : null}
                <Link href="/platform/actions" className="mt-2 inline-flex text-xs font-medium text-emerald-700 hover:underline">查看行動中心</Link>
              </div>
            ) : null}

            {symptomPatterns.length > 0 ? (
              <div data-testid="symptoms-pattern-context" className="rounded-xl border border-amber-100 bg-white p-3">
                <p className="text-xs font-semibold text-amber-700">症狀模式</p>
                <div className="mt-2 space-y-2">
                  {symptomPatterns.map((item, idx) => (
                    <div key={`${item.label || item.symptomType || idx}`} className="rounded-lg bg-amber-50/70 p-2">
                      <p className="text-sm font-medium text-slate-900">{firstText(item.label, item.symptomType, item.symptom_type)}</p>
                      <p className="mt-1 text-xs text-slate-600">{firstText(item.whyDetected, item.why_detected, item.suggestedAction, item.suggested_action)}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
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

        <div className="mt-4 grid gap-3 sm:grid-cols-2 md:grid-cols-4">
          <label className="text-sm" htmlFor="occurred-at-input">
            <span className="text-slate-600 font-medium">症狀發生日期與時間</span>
            <input
              id="occurred-at-input"
              data-testid="occurred-at-input"
              type="datetime-local"
              className="mt-1 w-full min-h-11 rounded-xl border px-3 py-2 font-sans"
              value={occurredAt}
              max={maxDateTime}
              onChange={(e) => {
                setOccurredAt(e.target.value)
                setError(null)
              }}
            />
          </label>

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

        {error && (
          <p className="text-sm text-rose-500 mt-2" data-testid="symptoms-error-message">
            {error}
          </p>
        )}

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
