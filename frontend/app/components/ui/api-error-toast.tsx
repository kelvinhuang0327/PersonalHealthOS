'use client'

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

const ApiToastContext = createContext<{ push: (message: string) => void } | null>(null)

export function ApiErrorToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('')

  useEffect(() => {
    const handler = (event: Event) => {
      const customEvent = event as CustomEvent<{ message?: string }>
      setMessage(customEvent.detail?.message || '服務暫時無法連線，部分資料可能不是最新')
      window.setTimeout(() => setMessage(''), 4000)
    }
    window.addEventListener('api-error-toast', handler)
    return () => window.removeEventListener('api-error-toast', handler)
  }, [])

  const value = useMemo(() => ({ push: (nextMessage: string) => setMessage(nextMessage) }), [])

  return (
    <ApiToastContext.Provider value={value}>
      {children}
      {message ? (
        <div className="pointer-events-none fixed bottom-4 left-1/2 z-[60] -translate-x-1/2 rounded-full bg-slate-900 px-4 py-2 text-sm text-white shadow-lg">
          {message}
        </div>
      ) : null}
    </ApiToastContext.Provider>
  )
}

export function useApiErrorToast() {
  return useContext(ApiToastContext)
}
