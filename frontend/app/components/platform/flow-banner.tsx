'use client'

import { CheckCircle2, CircleAlert, Loader2, Sparkles, TriangleAlert } from 'lucide-react'
import { cn } from '../ui/utils'

type FlowTone = 'loading' | 'success' | 'info' | 'warning' | 'error'

const toneMap: Record<
  FlowTone,
  {
    className: string
    icon: typeof Loader2
    titleClass: string
    messageClass: string
  }
> = {
  loading: {
    className: 'border-sky-200 bg-sky-50/80 text-sky-900',
    icon: Loader2,
    titleClass: 'text-sky-900',
    messageClass: 'text-sky-800',
  },
  success: {
    className: 'border-emerald-200 bg-emerald-50/80 text-emerald-900',
    icon: CheckCircle2,
    titleClass: 'text-emerald-900',
    messageClass: 'text-emerald-800',
  },
  info: {
    className: 'border-cyan-200 bg-cyan-50/80 text-cyan-900',
    icon: Sparkles,
    titleClass: 'text-cyan-900',
    messageClass: 'text-cyan-800',
  },
  warning: {
    className: 'border-amber-200 bg-amber-50/80 text-amber-900',
    icon: CircleAlert,
    titleClass: 'text-amber-900',
    messageClass: 'text-amber-800',
  },
  error: {
    className: 'border-rose-200 bg-rose-50/80 text-rose-900',
    icon: TriangleAlert,
    titleClass: 'text-rose-900',
    messageClass: 'text-rose-800',
  },
}

export function FlowBanner({
  tone = 'info',
  title,
  message,
  compact = false,
  className,
}: {
  tone?: FlowTone
  title: string
  message: string
  compact?: boolean
  className?: string
}) {
  const config = toneMap[tone]
  const Icon = config.icon

  return (
    <div className={cn('rounded-2xl border px-4 py-3 shadow-sm', config.className, className)}>
      <div className="flex items-start gap-3">
        <div className={cn('mt-0.5 rounded-xl bg-white/70 p-2', tone === 'loading' && 'animate-pulse')}>
          <Icon className={cn('h-4 w-4', tone === 'loading' && 'animate-spin')} />
        </div>
        <div className="min-w-0">
          <p className={cn('font-semibold', config.titleClass)}>{title}</p>
          <p className={cn('mt-1 text-sm leading-6', compact ? 'line-clamp-2' : '', config.messageClass)}>{message}</p>
        </div>
      </div>
    </div>
  )
}
