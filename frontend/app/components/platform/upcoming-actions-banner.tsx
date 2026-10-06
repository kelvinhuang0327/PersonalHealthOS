'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import { HealthAction } from '../../../lib/actions'
import { api } from '../../../lib/api'

const SESSION_KEY = 'upcoming_actions_banner_dismissed'

interface Props {
  /** Pre-filtered list; if omitted, component fetches due_within_days=2 */
  actions?: HealthAction[]
}

export function UpcomingActionsBanner({ actions: propActions }: Props) {
  const [actions, setActions] = useState<HealthAction[]>(propActions ?? [])
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    if (sessionStorage.getItem(SESSION_KEY)) setDismissed(true)
  }, [])

  useEffect(() => {
    if (propActions) return
    api
      .getActions(undefined, 2)
      .then((all: unknown) => setActions(all as HealthAction[]))
      .catch(() => setActions([]))
  }, [propActions])

  if (dismissed || actions.length === 0) return null

  const dismiss = () => {
    sessionStorage.setItem(SESSION_KEY, '1')
    setDismissed(true)
  }

  return (
    <div className="flex items-start justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
        <div>
          <p className="text-sm font-medium text-amber-900">
            你有 {actions.length} 個行動即將到期
          </p>
          <ul className="mt-1 space-y-0.5">
            {actions.slice(0, 3).map((a) => (
              <li key={a.id} className="text-xs text-amber-700">
                · {a.title}
                {a.due_date && (
                  <span className="ml-1 text-amber-500">
                    （{new Date(a.due_date).toLocaleDateString('zh-TW', { month: 'numeric', day: 'numeric' })}）
                  </span>
                )}
              </li>
            ))}
            {actions.length > 3 && (
              <li className="text-xs text-amber-500">還有 {actions.length - 3} 個…</li>
            )}
          </ul>
        </div>
      </div>
      <button onClick={dismiss} className="rounded p-1 hover:bg-amber-100">
        <X className="h-4 w-4 text-amber-500" />
      </button>
    </div>
  )
}
