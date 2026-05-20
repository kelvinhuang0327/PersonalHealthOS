'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { ArrowRight, Bot, CheckCircle2, RefreshCw, XCircle } from 'lucide-react'
import type { OrcDashboardSummary } from '../../../lib/orchestrator-api'
import { orcApi } from '../../../lib/orchestrator-api'
import { Card } from '../ui/card'

// ── Status chip (product language only) ──────────────────────────────────────

function TaskStatusChip({ status, gate }: Readonly<{ status: string; gate?: string | null }>) {
  if (status === 'COMPLETED' && gate === 'PASS') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
        <CheckCircle2 className="h-3 w-3" />已完成
      </span>
    )
  }
  if (status === 'COMPLETED') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
        <CheckCircle2 className="h-3 w-3" />已完成
      </span>
    )
  }
  if (status === 'RUNNING') {
    return (
      <span className="inline-flex animate-pulse items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
        <RefreshCw className="h-3 w-3" />執行中
      </span>
    )
  }
  if (status === 'REPLAN_REQUIRED') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
        需要重規劃
      </span>
    )
  }
  if (status === 'FAILED' || status === 'FAILED_RATE_LIMIT') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
        <XCircle className="h-3 w-3" />失敗
      </span>
    )
  }
  if (status === 'QUEUED') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
        等待執行
      </span>
    )
  }
  return null
}

// ── Gate verdict badge ────────────────────────────────────────────────────────

function GateBadge({ verdict }: Readonly<{ verdict: string | null | undefined }>) {
  if (!verdict || verdict === 'PASS') return null
  if (verdict === 'RESULT_SHALLOW' || verdict === 'INVALID_DELIVERY') {
    return (
      <span className="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
        需補強
      </span>
    )
  }
  if (verdict === 'FAILED_ACCEPTANCE') {
    return (
      <span className="ml-1 rounded bg-red-100 px-1.5 py-0.5 text-[10px] font-medium text-red-700">
        驗收未過
      </span>
    )
  }
  return null
}

// ── Main panel ────────────────────────────────────────────────────────────────

export function OrchestrationSummaryPanel() {
  const [summary, setSummary] = useState<OrcDashboardSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    orcApi
      .getDashboardSummary()
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <Card className="animate-pulse rounded-3xl border border-cyan-100 bg-gradient-to-r from-cyan-50 via-white to-sky-50 p-5 shadow-sm">
        <div className="h-32 rounded-2xl bg-slate-100" />
      </Card>
    )
  }

  // If API is unreachable (e.g. backend offline), show a static offline card with CTA
  if (!summary) {
    return (
      <Card className="rounded-3xl border border-cyan-100 bg-gradient-to-r from-cyan-50 via-white to-sky-50 p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="rounded-xl bg-cyan-100 p-2 text-cyan-700">
              <Bot className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-cyan-700">AI 優化系統</p>
              <p className="text-sm font-semibold text-slate-800">AI 任務排程中心</p>
              <p className="text-xs text-slate-400">管理 AI 持續優化任務與排程</p>
            </div>
          </div>
          <Link
            href="/platform/cockpit/orchestration"
            className="inline-flex items-center gap-1.5 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-cyan-700"
          >
            前往排程中心
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </Card>
    )
  }

  const isActive = summary.scheduler_active

  return (
    <Card className="rounded-3xl border border-cyan-100 bg-gradient-to-r from-cyan-50 via-white to-sky-50 p-5 shadow-sm">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="rounded-xl bg-cyan-100 p-2 text-cyan-700">
            <Bot className="h-4 w-4" />
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-cyan-700">AI 系統運作狀態</p>
            <p className="text-sm font-semibold text-slate-800">AI 正在持續優化你的健康體驗</p>
          </div>
        </div>
        <div
          className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
            isActive ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${isActive ? 'animate-pulse bg-emerald-500' : 'bg-slate-400'}`}
          />
          {isActive ? '運作中' : '已暫停'}
        </div>
      </div>

      {/* Stats row */}
      <div className="mb-4 grid grid-cols-4 gap-3">
        {[
          { label: '今日任務', value: summary.today_total ?? 0, color: 'text-slate-800' },
          { label: '已完成', value: summary.today_completed ?? 0, color: 'text-emerald-600' },
          { label: '執行中', value: summary.today_running ?? 0, color: 'text-blue-600' },
          {
            label: '需複查',
            value: (summary.today_replan ?? 0) + (summary.today_failed ?? 0),
            color: ((summary.today_replan ?? 0) + (summary.today_failed ?? 0)) > 0 ? 'text-amber-600' : 'text-slate-400',
          },
        ].map((s) => (
          <div key={s.label} className="rounded-2xl bg-white px-3 py-2 text-center shadow-sm">
            <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-slate-500">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Latest task */}
      {summary.latest_task ? (
        <div className="mb-4 rounded-2xl bg-white px-4 py-3 shadow-sm">
          <p className="mb-1 text-xs text-slate-400">最新任務</p>
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-800">{summary.latest_task.title}</p>
              {summary.latest_task.category_label ? (
                <p className="mt-0.5 text-xs text-cyan-600">{summary.latest_task.category_label}</p>
              ) : null}
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <TaskStatusChip status={summary.latest_task.status} gate={summary.latest_task.gate_verdict} />
              <GateBadge verdict={summary.latest_task.gate_verdict} />
            </div>
          </div>
        </div>
      ) : null}

      {/* Top categories */}
      {(summary.top_categories ?? []).length > 0 ? (
        <div className="mb-4">
          <p className="mb-2 text-xs text-slate-400">近期優化焦點</p>
          <div className="flex flex-wrap gap-2">
            {(summary.top_categories ?? []).map((c) => (
              <span
                key={c.category}
                className="rounded-full bg-cyan-100 px-3 py-0.5 text-xs font-medium text-cyan-700"
              >
                {c.label} · {c.completed_count}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {/* CTA */}
      <Link
        href="/platform/cockpit/orchestration"
        className="inline-flex items-center gap-1.5 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-cyan-700"
      >
        查看 AI 優化任務
        <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </Card>
  )
}
