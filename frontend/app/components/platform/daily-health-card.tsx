'use client'

import Link from 'next/link'
import { ArrowRight, CalendarCheck2, Gauge, Minus, TrendingDown, TrendingUp } from 'lucide-react'

import type { HealthAction } from '../../../lib/actions'
import { getActionExpectedEffect } from '../../../lib/actions'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Card } from '../ui/card'

type DailyHealthCardProps = {
  score?: number | null
  riskText: string
  deltaText: string
  actionText: string
  actionEffect?: string
  action?: HealthAction | null
  onPrimaryAction: () => void
  onSecondaryAction?: () => void
  secondaryActionLabel?: string
}

export function DailyHealthCard({
  score,
  riskText,
  deltaText,
  actionText,
  actionEffect,
  action,
  onPrimaryAction,
  onSecondaryAction,
  secondaryActionLabel = '加入追蹤',
}: DailyHealthCardProps) {
  const trendIcon = deltaText.includes('變好') || deltaText.includes('改善') ? TrendingDown : deltaText.includes('變差') || deltaText.includes('上升') ? TrendingUp : Minus
  const TrendIcon = trendIcon

  return (
    <Card className="rounded-[28px] border border-slate-200/80 bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-900 p-6 text-white shadow-md">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="border-none bg-white/15 text-white">Daily Health Card</Badge>
            <Badge className="border-none bg-emerald-400/15 text-emerald-100">{typeof score === 'number' ? `${score} / 100` : '健康分數未更新'}</Badge>
            <Badge className="border-none bg-sky-400/15 text-sky-100">1 分鐘版本</Badge>
          </div>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight">今天先看這 3 件事</h2>
          <p className="mt-2 text-sm text-slate-300">5 秒看懂重點，10 秒決定要不要處理，30 秒內完成第一步。</p>

          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl bg-white/10 p-4">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-cyan-100">
                <Gauge className="h-3.5 w-3.5" />
                最重要風險
              </div>
              <p className="mt-2 text-sm leading-6 text-white">{riskText}</p>
            </div>
            <div className="rounded-2xl bg-white/10 p-4">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-cyan-100">
                <TrendIcon className="h-3.5 w-3.5" />
                與上次相比
              </div>
              <p className="mt-2 text-sm leading-6 text-white">{deltaText}</p>
            </div>
            <div className="rounded-2xl bg-white/10 p-4">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.14em] text-cyan-100">
                <CalendarCheck2 className="h-3.5 w-3.5" />
                現在先做
              </div>
              <p className="mt-2 text-sm leading-6 text-white">{actionText}</p>
              <p className="mt-2 text-xs leading-5 text-slate-200">{actionEffect || (action ? getActionExpectedEffect(action) : '先把今天最重要的健康行動完成。')}</p>
            </div>
          </div>
        </div>

        <div className="w-full max-w-xs rounded-[24px] border border-white/10 bg-white/10 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-300">今天先從這裡開始</p>
          <div className="mt-3 space-y-3">
            <Button className="w-full bg-white text-slate-900 hover:bg-slate-100" onClick={onPrimaryAction}>
              開始這一件
            </Button>
            {onSecondaryAction ? (
              <Button className="w-full border border-white/20 bg-white/10 text-white hover:bg-white/15" onClick={onSecondaryAction}>
                {secondaryActionLabel}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            ) : (
              <Link
                href="/platform/notifications"
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-white/20 px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
              >
                {secondaryActionLabel}
                <ArrowRight className="h-4 w-4" />
              </Link>
            )}
          </div>
          <p className="mt-3 text-xs leading-5 text-slate-200">每天打開先看這一張，就能快速判斷今天該不該採取行動。</p>
        </div>
      </div>
    </Card>
  )
}
