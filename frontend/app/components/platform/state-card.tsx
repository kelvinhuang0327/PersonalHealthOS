'use client'

import Link from 'next/link'
import { CheckCircle2, CircleAlert, Loader2, Sparkles, TriangleAlert, Inbox, ArrowRight } from 'lucide-react'

import { Button } from '../ui/button'
import { Card } from '../ui/card'
import { cn } from '../ui/utils'

type StateTone = 'loading' | 'success' | 'info' | 'warning' | 'error' | 'neutral'

const toneMap: Record<
  StateTone,
  {
    className: string
    icon: typeof Inbox
    iconClassName: string
    pillClassName: string
  }
> = {
  loading: {
    className: 'border-sky-200 bg-sky-50/80',
    icon: Loader2,
    iconClassName: 'text-sky-700',
    pillClassName: 'bg-sky-100 text-sky-800',
  },
  success: {
    className: 'border-emerald-200 bg-emerald-50/80',
    icon: CheckCircle2,
    iconClassName: 'text-emerald-700',
    pillClassName: 'bg-emerald-100 text-emerald-800',
  },
  info: {
    className: 'border-cyan-200 bg-cyan-50/80',
    icon: Sparkles,
    iconClassName: 'text-cyan-700',
    pillClassName: 'bg-cyan-100 text-cyan-800',
  },
  warning: {
    className: 'border-amber-200 bg-amber-50/80',
    icon: CircleAlert,
    iconClassName: 'text-amber-700',
    pillClassName: 'bg-amber-100 text-amber-800',
  },
  error: {
    className: 'border-rose-200 bg-rose-50/80',
    icon: TriangleAlert,
    iconClassName: 'text-rose-700',
    pillClassName: 'bg-rose-100 text-rose-800',
  },
  neutral: {
    className: 'border-slate-200 bg-slate-50',
    icon: Inbox,
    iconClassName: 'text-slate-600',
    pillClassName: 'bg-slate-100 text-slate-700',
  },
}

export function StateCard({
  tone = 'neutral',
  title,
  description,
  actionLabel,
  href,
  onAction,
  secondaryActionLabel,
  onSecondaryAction,
  className,
  compact = false,
  badgeText,
}: {
  tone?: StateTone
  title: string
  description: string
  actionLabel?: string
  href?: string
  onAction?: () => void
  secondaryActionLabel?: string
  onSecondaryAction?: () => void
  className?: string
  compact?: boolean
  badgeText?: string
}) {
  const config = toneMap[tone]
  const Icon = config.icon

  return (
    <Card className={cn('rounded-3xl border p-5 shadow-sm', config.className, className)}>
      <div className={cn('flex gap-4', compact ? 'items-start' : 'items-center')}>
        <div className={cn('rounded-2xl bg-white/80 p-3', tone === 'loading' && 'animate-pulse')}>
          <Icon className={cn('h-5 w-5', config.iconClassName, tone === 'loading' && 'animate-spin')} />
        </div>
        <div className="min-w-0 flex-1">
          {badgeText ? (
            <p className={cn('inline-flex rounded-full px-3 py-1 text-xs font-semibold', config.pillClassName)}>{badgeText}</p>
          ) : null}
          <h3 className={cn('font-["Figtree"] text-xl font-semibold text-slate-950', badgeText ? 'mt-3' : '')}>{title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
        </div>
      </div>

      {actionLabel ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {href ? (
            <Link href={href} className="inline-flex items-center gap-2 rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800">
              {actionLabel}
              <ArrowRight className="h-4 w-4" />
            </Link>
          ) : onAction ? (
            <Button onClick={onAction} className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800">
              {actionLabel}
            </Button>
          ) : null}
          {secondaryActionLabel && onSecondaryAction ? (
            <Button
              onClick={onSecondaryAction}
              className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
            >
              {secondaryActionLabel}
            </Button>
          ) : null}
        </div>
      ) : null}
    </Card>
  )
}
