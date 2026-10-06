'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Bell, CheckCircle2, X } from 'lucide-react'
import { api } from '../../../lib/api'

type Alert = {
  id: string
  title: string
  message: string
  severity: string
  status: string
  created_at: string
}

const SEVERITY_CLS: Record<string, string> = {
  high:     'bg-rose-50 border-rose-100 text-rose-800',
  critical: 'bg-rose-100 border-rose-200 text-rose-900',
  medium:   'bg-amber-50 border-amber-100 text-amber-800',
  low:      'bg-slate-50 border-slate-100 text-slate-700',
}

const DOT_CLS: Record<string, string> = {
  high:     'bg-rose-500',
  critical: 'bg-rose-600',
  medium:   'bg-amber-500',
  low:      'bg-slate-400',
}

export function NotificationBell() {
  const [count, setCount] = useState(0)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [open, setOpen] = useState(false)
  const [dismissing, setDismissing] = useState<string | null>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  const fetchCount = useCallback(async () => {
    try {
      const res = await api.getRiskAlertUnreadCount() as { count: number }
      setCount(res.count ?? 0)
    } catch {
      // Silent fail — badge stays at 0
    }
  }, [])

  const fetchAlerts = useCallback(async () => {
    try {
      const data = await api.listRiskAlerts() as Alert[]
      setAlerts(Array.isArray(data) ? data.filter((a) => a.status === 'active').slice(0, 10) : [])
    } catch {
      setAlerts([])
    }
  }, [])

  // Poll count every 5 minutes
  useEffect(() => {
    void fetchCount()
    const timer = setInterval(() => void fetchCount(), 5 * 60 * 1000)
    return () => clearInterval(timer)
  }, [fetchCount])

  // Open → fetch fresh alert list
  const handleOpen = () => {
    setOpen((v) => {
      if (!v) void fetchAlerts()
      return !v
    })
  }

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handle = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [open])

  const handleDismiss = async (id: string) => {
    setDismissing(id)
    try {
      await api.dismissRiskAlert(id)
      setAlerts((prev) => prev.filter((a) => a.id !== id))
      setCount((c) => Math.max(0, c - 1))
    } catch {
      // Ignore
    } finally {
      setDismissing(null)
    }
  }

  const formatDate = (iso: string) => {
    try {
      return new Intl.DateTimeFormat('zh-TW', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(iso))
    } catch {
      return iso
    }
  }

  return (
    <div ref={panelRef} className="relative">
      {/* Bell button */}
      <button
        type="button"
        onClick={handleOpen}
        aria-label={`通知 ${count > 0 ? `(${count} 則未讀)` : ''}`}
        className="relative rounded-xl p-2 text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
      >
        <Bell className="h-4 w-4" />
        {count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white leading-none">
            {count > 9 ? '9+' : count}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 rounded-2xl border border-slate-100 bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <h3 className="text-sm font-semibold text-slate-900">健康通知</h3>
            {count > 0 && (
              <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">
                {count} 則未處理
              </span>
            )}
          </div>

          <div className="max-h-72 overflow-y-auto">
            {alerts.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-slate-400">
                <CheckCircle2 className="h-8 w-8 text-emerald-400" />
                <p className="text-sm">目前沒有未讀通知</p>
              </div>
            ) : (
              <ul className="divide-y divide-slate-50">
                {alerts.map((alert) => {
                  const cls = SEVERITY_CLS[alert.severity] ?? SEVERITY_CLS['low']
                  const dot = DOT_CLS[alert.severity] ?? DOT_CLS['low']
                  return (
                    <li key={alert.id} className={`flex gap-3 px-4 py-3 ${cls}`}>
                      <div className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dot}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold">{alert.title}</p>
                        <p className="mt-0.5 text-xs leading-relaxed opacity-80">{alert.message}</p>
                        <p className="mt-1 text-[10px] opacity-50">{formatDate(alert.created_at)}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => void handleDismiss(alert.id)}
                        disabled={dismissing === alert.id}
                        aria-label="關閉通知"
                        className="shrink-0 rounded-lg p-1 opacity-50 transition hover:opacity-100 disabled:opacity-30"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>

          <div className="border-t border-slate-100 px-4 py-2.5">
            <a href="/platform/notifications" className="text-xs text-sky-600 hover:underline">
              查看全部通知 →
            </a>
          </div>
        </div>
      )}
    </div>
  )
}
