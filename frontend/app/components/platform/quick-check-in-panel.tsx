'use client'

import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, Loader2, Sparkles, XCircle } from 'lucide-react'

import { appendQuickCheckIn, getTodayQuickCheckInCount } from '../../../lib/quick-checkin'
import { api } from '../../../lib/api'
import { useActions } from '../../providers/action-context'
import { usePerson } from '../../providers/person-context'
import { FlowBanner } from './flow-banner'
import { Button } from '../ui/button'
import { Card } from '../ui/card'
import { Badge } from '../ui/badge'

const symptomOptions = [
  { key: '腰痛', label: '腰痛', severity: 4 },
  { key: '血壓偏高感', label: '血壓偏高感', severity: 5 },
  { key: '睡不好', label: '睡不好', severity: 4 },
  { key: '疲勞', label: '疲勞', severity: 3 },
  { key: '胃口不舒服', label: '胃口不舒服', severity: 3 },
] as const

type PanelTone = 'loading' | 'success' | 'warning' | 'error' | 'info'

export function QuickCheckInPanel({ onChanged }: { onChanged?: () => Promise<void> | void }) {
  const { personId } = usePerson()
  const { actions, updateStatus, refreshActions } = useActions()
  const [selectedState, setSelectedState] = useState<'ok' | 'not_ok' | null>(null)
  const [busyKey, setBusyKey] = useState<string | null>(null)
  const [message, setMessage] = useState<{ tone: PanelTone; title: string; message: string } | null>(null)
  const [todayCount, setTodayCount] = useState(0)

  const topAction = useMemo(() => actions.find((action) => action.status === 'todo' || action.status === 'in_progress') || null, [actions])
  const quickSummary = useMemo(() => {
    if (selectedState === 'ok') return '今天先確認狀況，讓系統知道你目前穩定。'
    if (selectedState === 'not_ok') return '先點一個最接近的症狀，讓接下來的提醒更準。'
    return '先用 1 個點擊完成今日打卡。'
  }, [selectedState])

  useEffect(() => {
    setSelectedState(null)
    setMessage(null)
  }, [personId])

  useEffect(() => {
    if (!personId) {
      setTodayCount(0)
      return
    }
    setTodayCount(getTodayQuickCheckInCount(personId))
  }, [personId, actions])

  const refresh = async () => {
    await refreshActions()
    await onChanged?.()
  }

  const recordLocal = (type: 'ok' | 'not_ok' | 'symptom' | 'action', label: string) => {
    if (!personId) return
    appendQuickCheckIn(personId, {
      id: `qc_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      type,
      label,
      created_at: new Date().toISOString(),
    })
    setTodayCount(getTodayQuickCheckInCount(personId))
  }

  const handleOk = async () => {
    if (!personId) return
    setBusyKey('ok')
    try {
      recordLocal('ok', '今天狀況 OK')
      setSelectedState('ok')
      setMessage({
        tone: 'success',
        title: '已完成今日打卡',
        message: '系統已記住你今天目前狀況穩定，明天再進來看變化即可。',
      })
      await onChanged?.()
    } catch {
      setMessage({
        tone: 'error',
        title: '打卡失敗',
        message: '目前無法完成打卡，請稍後再試一次。',
      })
    } finally {
      setBusyKey(null)
    }
  }

  const handleNotOk = async () => {
    setSelectedState('not_ok')
    recordLocal('not_ok', '今天狀況不 OK')
    setMessage({
      tone: 'info',
      title: '請選一個最接近的症狀',
      message: '你只要多點一下最接近的症狀，系統就能把後續提醒排得更準。',
    })
  }

  const handleSymptom = async (key: string, severity: number) => {
    if (!personId) return
    setBusyKey(key)
    try {
      await api.createSymptom({
        symptom: key,
        occurred_at: new Date().toISOString(),
        severity,
        note: `快速打卡：${key}`,
      })
      recordLocal('symptom', key)
      setMessage({
        tone: 'success',
        title: '症狀已記錄',
        message: `我們已經把「${key}」加入今天的健康紀錄。`,
      })
      await refresh()
    } catch {
      setMessage({
        tone: 'error',
        title: '症狀記錄失敗',
        message: '目前無法送出症狀紀錄，請稍後再試。',
      })
    } finally {
      setBusyKey(null)
    }
  }

  const handleActionComplete = async () => {
    if (!topAction) return
    setBusyKey(topAction.id)
    try {
      await updateStatus(topAction.id, 'done')
      recordLocal('action', topAction.title)
      setMessage({
        tone: 'success',
        title: '第一個行動已完成',
        message: `這會幫你把「${topAction.title}」納入回饋閉環，後續系統會看是否真的有改善。`,
      })
      await refresh()
    } finally {
      setBusyKey(null)
    }
  }

  return (
    <Card className="rounded-3xl border border-slate-200/80 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-1 text-xs font-medium text-sky-700">
            <Sparkles className="h-3.5 w-3.5" />
            Quick Check-in
          </div>
          <h3 className="mt-3 text-xl font-semibold text-slate-950">今天狀況怎麼樣？</h3>
          <p className="mt-1 text-sm text-slate-500">1 到 3 次點擊就能完成，沒有文字輸入壓力。</p>
        </div>
        <Badge className="bg-slate-100 text-slate-700">今天已打卡 {todayCount} 次</Badge>
      </div>

      {message ? <FlowBanner tone={message.tone} title={message.title} message={message.message} className="mt-4" compact /> : null}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <Button className="h-auto rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-left text-slate-950 hover:bg-emerald-100" onClick={handleOk} disabled={busyKey === 'ok'}>
          <div className="flex w-full items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-emerald-800">今天 OK</p>
              <p className="mt-1 text-xs leading-5 text-slate-600">目前沒有明顯不舒服，快速打卡就好。</p>
            </div>
            {busyKey === 'ok' ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-5 w-5 text-emerald-600" />}
          </div>
        </Button>
        <Button className="h-auto rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-left text-slate-950 hover:bg-rose-100" onClick={handleNotOk} disabled={busyKey === 'ok'}>
          <div className="flex w-full items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-rose-700">今天不 OK</p>
              <p className="mt-1 text-xs leading-5 text-slate-600">有一點不舒服，先選一個最接近的症狀。</p>
            </div>
            <XCircle className="h-5 w-5 text-rose-600" />
          </div>
        </Button>
      </div>

      {selectedState === 'not_ok' ? (
        <div className="mt-4 rounded-3xl border border-rose-100 bg-rose-50/70 p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-rose-900">快速症狀</p>
            <p className="text-xs text-rose-700">{quickSummary}</p>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {symptomOptions.map((option) => (
              <Button
                key={option.key}
                className="rounded-full border border-rose-200 bg-white text-rose-700 hover:bg-rose-100"
                onClick={() => void handleSymptom(option.key, option.severity)}
                disabled={busyKey === option.key}
              >
                {busyKey === option.key ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {option.label}
              </Button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-4 rounded-3xl border border-slate-200 bg-slate-950 p-4 text-white">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-slate-300">Impact-driven action</p>
            <p className="mt-1 text-sm font-semibold">完成今天最重要的一個行動</p>
            <p className="mt-2 text-sm text-slate-300">{topAction ? topAction.title : '目前還沒有待完成任務，先去加入追蹤或看待處理事項。'}</p>
            {topAction ? <p className="mt-2 text-xs leading-5 text-slate-400">預期效果：{topAction.description}</p> : null}
          </div>
          <Badge className="bg-white/10 text-white">{topAction ? topAction.status : 'no action'}</Badge>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button className="bg-white text-slate-950 hover:bg-slate-100" onClick={handleActionComplete} disabled={!topAction || busyKey === topAction?.id}>
            {busyKey === topAction?.id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            完成第一個行動
          </Button>
          <Button
            className="border border-white/20 bg-white/10 text-white hover:bg-white/15"
            onClick={async () => {
              setSelectedState('ok')
              setMessage({
                tone: 'info',
                title: '已同步最新狀態',
                message: '今天的打卡與行動回饋已同步，系統會重新整理你的待處理事項。',
              })
              await onChanged?.()
            }}
          >
            同步最新狀態
          </Button>
        </div>
      </div>
    </Card>
  )
}
