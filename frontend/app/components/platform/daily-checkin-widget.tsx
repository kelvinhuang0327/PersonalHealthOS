'use client'

import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, Plus, X } from 'lucide-react'
import { Button } from '../ui/button'
import { api } from '../../../lib/api'

type Draft = {
  systolic_bp: string
  diastolic_bp: string
  weight_kg: string
  blood_glucose: string
  sleep_hours: string
}

const EMPTY_DRAFT: Draft = {
  systolic_bp: '',
  diastolic_bp: '',
  weight_kg: '',
  blood_glucose: '',
  sleep_hours: '',
}

function isAbnormal(field: keyof Draft, raw: string): boolean {
  if (!raw) return false
  const value = Number(raw)
  if (!Number.isFinite(value)) return false
  if (field === 'systolic_bp') return value >= 140
  if (field === 'diastolic_bp') return value >= 90
  if (field === 'weight_kg') return value < 35 || value > 120
  if (field === 'blood_glucose') return value >= 126
  if (field === 'sleep_hours') return value < 6 || value > 10
  return false
}

function abnormalText(field: keyof Draft, raw: string): string | null {
  if (!isAbnormal(field, raw)) return null
  const labelMap: Record<keyof Draft, string> = {
    systolic_bp: '收縮壓',
    diastolic_bp: '舒張壓',
    weight_kg: '體重',
    blood_glucose: '血糖',
    sleep_hours: '睡眠時數',
  }
  return `你的${labelMap[field]} ${raw} 偏離參考範圍，已加入今日分析`
}

export function DailyCheckinWidget() {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState<1 | 2>(1)
  const [saving, setSaving] = useState(false)
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT)

  useEffect(() => {
    if (!open) return
    api
      .getLatestMetric()
      .then((row: any) => {
        if (!row) return
        setDraft({
          systolic_bp: row?.systolic_bp != null ? String(row.systolic_bp) : '',
          diastolic_bp: row?.diastolic_bp != null ? String(row.diastolic_bp) : '',
          weight_kg: row?.weight_kg != null ? String(row.weight_kg) : '',
          blood_glucose: row?.blood_glucose != null ? String(row.blood_glucose) : '',
          sleep_hours: row?.sleep_hours != null ? String(row.sleep_hours) : '',
        })
      })
      .catch(() => setDraft(EMPTY_DRAFT))
  }, [open])

  const warnings = useMemo(() => {
    return (Object.keys(draft) as Array<keyof Draft>)
      .map((key) => abnormalText(key, draft[key]))
      .filter(Boolean) as string[]
  }, [draft])

  const submit = async () => {
    setSaving(true)
    try {
      const payload: Record<string, unknown> = { recorded_at: new Date().toISOString() }
      for (const [key, value] of Object.entries(draft)) {
        if (!value.trim()) continue
        const num = Number(value)
        if (!Number.isFinite(num)) continue
        payload[key] = num
      }
      await api.createMetric(payload)
      setStep(2)
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true)
          setStep(1)
        }}
        className="fixed bottom-5 right-4 z-40 flex min-h-11 items-center gap-2 rounded-full bg-sky-600 px-4 py-3 text-sm font-semibold text-white shadow-lg hover:bg-sky-700 sm:bottom-6"
      >
        <Plus className="h-4 w-4" />
        記錄今日
      </button>

      {open ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <div className="relative w-full max-w-lg rounded-t-3xl bg-white p-4 shadow-2xl sm:rounded-3xl sm:p-5">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-lg font-semibold">每日快速量測</h3>
              <button type="button" className="rounded-lg p-2 hover:bg-slate-100" onClick={() => setOpen(false)}>
                <X className="h-4 w-4" />
              </button>
            </div>

            {step === 1 ? (
              <form
                className="space-y-3"
                onSubmit={(e) => {
                  e.preventDefault()
                  void submit()
                }}
              >
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <Field label="收縮壓" value={draft.systolic_bp} setValue={(v) => setDraft((d) => ({ ...d, systolic_bp: v }))} />
                  <Field label="舒張壓" value={draft.diastolic_bp} setValue={(v) => setDraft((d) => ({ ...d, diastolic_bp: v }))} />
                  <Field label="體重" value={draft.weight_kg} setValue={(v) => setDraft((d) => ({ ...d, weight_kg: v }))} />
                  <Field label="血糖" value={draft.blood_glucose} setValue={(v) => setDraft((d) => ({ ...d, blood_glucose: v }))} />
                  <Field label="睡眠時數" value={draft.sleep_hours} setValue={(v) => setDraft((d) => ({ ...d, sleep_hours: v }))} />
                </div>
                <p className="text-xs text-slate-500">欄位可留白，只填今天有量測的數值即可。</p>
                <Button type="submit" className="w-full min-h-11" disabled={saving}>
                  {saving ? '儲存中...' : '送出今日記錄'}
                </Button>
              </form>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-emerald-700">
                  <CheckCircle2 className="h-5 w-5" />
                  <p className="font-semibold">記錄完成！</p>
                </div>
                <ul className="space-y-1 text-sm text-slate-700">
                  {(Object.entries(draft) as Array<[keyof Draft, string]>).filter(([, v]) => v.trim()).map(([k, v]) => (
                    <li key={k}>• {labelOf(k)}：{v}</li>
                  ))}
                </ul>
                {warnings.length > 0 ? (
                  <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                    {warnings.map((text) => (
                      <p key={text}>{text}</p>
                    ))}
                  </div>
                ) : null}
                <Button className="w-full min-h-11" onClick={() => setOpen(false)}>
                  完成
                </Button>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </>
  )
}

function Field({ label, value, setValue }: { label: string; value: string; setValue: (next: string) => void }) {
  return (
    <label className="space-y-1 text-sm">
      <span className="text-slate-600">{label}</span>
      <input
        type="number"
        inputMode="decimal"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="w-full min-h-11 rounded-xl border px-3 py-2"
      />
    </label>
  )
}

function labelOf(key: keyof Draft): string {
  const labels: Record<keyof Draft, string> = {
    systolic_bp: '收縮壓',
    diastolic_bp: '舒張壓',
    weight_kg: '體重',
    blood_glucose: '血糖',
    sleep_hours: '睡眠時數',
  }
  return labels[key]
}
