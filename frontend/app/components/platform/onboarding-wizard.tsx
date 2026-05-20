'use client'

import { useState } from 'react'
import { Activity, CheckCircle2, ChevronRight, X } from 'lucide-react'
import { api } from '../../../lib/api'
import { Card } from '../ui/card'

type Step = 1 | 2 | 3

// ─── Step 1: Profile ──────────────────────────────────────────────────────────
function StepProfile({
  onNext,
}: {
  onNext: (data: { name: string; age: string; biological_sex: string }) => void
}) {
  const [name, setName] = useState('')
  const [age, setAge] = useState('')
  const [sex, setSex] = useState('male')

  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">稱呼你什麼名字？</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="例如：小明"
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">年齡</label>
          <input
            value={age}
            onChange={(e) => setAge(e.target.value)}
            placeholder="35"
            type="number"
            min="1"
            max="120"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">生理性別</label>
          <select
            value={sex}
            onChange={(e) => setSex(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
          >
            <option value="male">男</option>
            <option value="female">女</option>
            <option value="other">其他</option>
          </select>
        </div>
      </div>
      <button
        onClick={() => onNext({ name, age, biological_sex: sex })}
        disabled={!name.trim()}
        className="mt-2 w-full rounded-xl bg-sky-500 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-sky-600 disabled:opacity-40"
        type="button"
      >
        繼續 <ChevronRight className="inline h-4 w-4" />
      </button>
    </div>
  )
}

// ─── Step 2: Health Goals ─────────────────────────────────────────────────────
const GOALS = [
  { id: 'bp', label: '🩺 控制血壓', desc: '追蹤收縮壓 / 舒張壓' },
  { id: 'weight', label: '⚖️ 體重管理', desc: '記錄體重趨勢' },
  { id: 'sleep', label: '😴 改善睡眠', desc: '追蹤睡眠時數與品質' },
  { id: 'activity', label: '🏃 增加活動', desc: '每日步數與運動習慣' },
  { id: 'glucose', label: '🩸 血糖監控', desc: '追蹤空腹血糖' },
  { id: 'stress', label: '🧘 壓力管理', desc: '心率與靜息脈搏' },
]

function StepGoals({ onNext }: { onNext: (goals: string[]) => void }) {
  const [selected, setSelected] = useState<string[]>([])

  const toggle = (id: string) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((g) => g !== id) : [...prev, id]))

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">選擇你最想關注的健康目標（可多選）</p>
      <div className="grid grid-cols-2 gap-2">
        {GOALS.map((g) => {
          const active = selected.includes(g.id)
          return (
            <button
              key={g.id}
              type="button"
              onClick={() => toggle(g.id)}
              className={`flex flex-col items-start rounded-xl border p-3 text-left text-sm transition ${
                active
                  ? 'border-sky-300 bg-sky-50 text-sky-800'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
              }`}
            >
              <span className="font-medium">{g.label}</span>
              <span className="mt-0.5 text-xs text-slate-400">{g.desc}</span>
              {active && <CheckCircle2 className="mt-1 h-3.5 w-3.5 text-sky-500" />}
            </button>
          )
        })}
      </div>
      <button
        onClick={() => onNext(selected)}
        disabled={selected.length === 0}
        className="mt-2 w-full rounded-xl bg-sky-500 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-sky-600 disabled:opacity-40"
        type="button"
      >
        繼續 <ChevronRight className="inline h-4 w-4" />
      </button>
    </div>
  )
}

// ─── Step 3: First Metric ─────────────────────────────────────────────────────
function StepFirstMetric({ onFinish }: { onFinish: () => void }) {
  const [systolic, setSystolic] = useState('')
  const [diastolic, setDiastolic] = useState('')
  const [weight, setWeight] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSubmit = async () => {
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {}
      if (systolic) payload.systolic_bp = Number(systolic)
      if (diastolic) payload.diastolic_bp = Number(diastolic)
      if (weight) payload.weight_kg = Number(weight)
      if (Object.keys(payload).length) {
        await api.createMetric({ ...payload, source: 'manual' })
      }
    } catch {
      // Ignore — non-blocking
    } finally {
      setSaving(false)
      onFinish()
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">記錄一筆今天的數據，讓 AI 有基準可以分析（可以跳過）</p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">收縮壓 (mmHg)</label>
          <input
            value={systolic}
            onChange={(e) => setSystolic(e.target.value)}
            placeholder="120"
            type="number"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">舒張壓 (mmHg)</label>
          <input
            value={diastolic}
            onChange={(e) => setDiastolic(e.target.value)}
            placeholder="80"
            type="number"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
          />
        </div>
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">體重 (kg)</label>
        <input
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
          placeholder="70"
          type="number"
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:ring-2 focus:ring-sky-100"
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={handleSubmit}
          disabled={saving}
          className="flex-1 rounded-xl bg-sky-500 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-sky-600 disabled:opacity-40"
          type="button"
        >
          {saving ? '儲存中…' : '完成設定 🎉'}
        </button>
        <button
          onClick={onFinish}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-600 transition hover:bg-slate-50"
          type="button"
        >
          跳過
        </button>
      </div>
    </div>
  )
}

// ─── Main Wizard ──────────────────────────────────────────────────────────────
const STEP_TITLES: Record<Step, string> = {
  1: '建立個人資料',
  2: '選擇健康目標',
  3: '記錄基準數據',
}

export function OnboardingWizard({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState<Step>(1)
  const [profileData, setProfileData] = useState<Record<string, string>>({})

  const handleProfileNext = async (data: { name: string; age: string; biological_sex: string }) => {
    setProfileData(data)
    try {
      await api.updateProfile({ display_name: data.name, age: Number(data.age), biological_sex: data.biological_sex })
    } catch {
      // Non-blocking
    }
    setStep(2)
  }

  const handleGoalsNext = (goals: string[]) => {
    // Store selected goals locally for now
    if (typeof window !== 'undefined') {
      localStorage.setItem('health_goals', JSON.stringify(goals))
    }
    setStep(3)
  }

  const handleFinish = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('onboarding_completed', '1')
    }
    onComplete()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4">
      <Card className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl">
        {/* Header */}
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-2xl bg-sky-100 p-2.5 text-sky-600">
            <Activity className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <p className="text-xs text-slate-400 uppercase tracking-wide">步驟 {step} / 3</p>
            <h2 className="text-base font-semibold text-slate-900">{STEP_TITLES[step]}</h2>
          </div>
          <button
            onClick={handleFinish}
            className="rounded-xl p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
            aria-label="跳過設定"
            type="button"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Progress bar */}
        <div className="mb-5 flex gap-1.5">
          {([1, 2, 3] as Step[]).map((s) => (
            <div
              key={s}
              className={`h-1.5 flex-1 rounded-full transition-colors ${s <= step ? 'bg-sky-500' : 'bg-slate-100'}`}
            />
          ))}
        </div>

        {/* Step content */}
        {step === 1 && <StepProfile onNext={handleProfileNext} />}
        {step === 2 && <StepGoals onNext={handleGoalsNext} />}
        {step === 3 && <StepFirstMetric onFinish={handleFinish} />}
      </Card>
    </div>
  )
}
