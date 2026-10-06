'use client'

/**
 * DecisionRecommendationLayer
 * ────────────────────────────
 * Shows the top 3 items from the backend Decision Engine (decision_items or
 * prioritized_actions fallback) as actionable recommendations on the Actions
 * page.
 *
 * Data source: 100% backend — no local re-ranking, no heuristic override.
 * CTA logic: createFromDecisionItem (deduplicates by source_id / title).
 */

import Link from 'next/link'
import { useState } from 'react'
import { Activity, AlertCircle, ArrowRight, BookOpen, Brain, CheckCircle2, Clock3, ExternalLink, FileText, Plus, Shield, Sparkles, TriangleAlert } from 'lucide-react'
import type { UnifiedDecisionItem } from '../../../lib/decision-support'
import type { HealthAction } from '../../../lib/actions'
import { EVIDENCE_SOURCE_META, getEvidenceHref } from '../../../lib/evidence-source-meta'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Card } from '../ui/card'
import { RecommendationTrustBlock } from './recommendation-trust-block'

// ── Helpers ──────────────────────────────────────────────────────────────────

const SOURCE_META: Record<string, { label: string; icon: React.ElementType; cls: string }> = {
  alert:             { label: '風險警示',   icon: TriangleAlert, cls: 'bg-rose-50 border-rose-200 text-rose-700' },
  risk_alert:        { label: '風險警示',   icon: TriangleAlert, cls: 'bg-rose-50 border-rose-200 text-rose-700' },
  insight:           { label: 'AI 洞察',   icon: Brain,         cls: 'bg-violet-50 border-violet-200 text-violet-700' },
  recommendation:    { label: '系統建議',   icon: Sparkles,     cls: 'bg-sky-50 border-sky-200 text-sky-700' },
  trend:             { label: '趨勢預警',   icon: Shield,       cls: 'bg-amber-50 border-amber-200 text-amber-700' },
  action:            { label: '建議行動',   icon: ArrowRight,   cls: 'bg-emerald-50 border-emerald-200 text-emerald-700' },
  lab_report_item:   { label: '健檢報告',   icon: FileText,     cls: 'bg-teal-50 border-teal-200 text-teal-700' },
  lab_abnormality:   { label: '健檢報告',   icon: FileText,     cls: 'bg-teal-50 border-teal-200 text-teal-700' },
  symptom:           { label: '症狀紀錄',   icon: Activity,     cls: 'bg-orange-50 border-orange-200 text-orange-700' },
  long_term_symptom: { label: '持續症狀',   icon: Activity,     cls: 'bg-orange-50 border-orange-200 text-orange-700' },
}


const PRIORITY_META = {
  high:   { label: '高', cls: 'bg-rose-100 text-rose-700' },
  medium: { label: '中', cls: 'bg-amber-100 text-amber-700' },
  low:    { label: '低', cls: 'bg-slate-100 text-slate-600' },
}

function evidenceLabel(lvl: string) {
  if (lvl === 'A') return '臨床A級'
  if (lvl === 'B') return '臨床B級'
  return null
}

// ── Item card ─────────────────────────────────────────────────────────────────

function RecommendationItem({
  item,
  existingAction,
  onAdd,
  onSnooze,
  onDismiss,
}: {
  item: UnifiedDecisionItem
  existingAction: HealthAction | null
  onAdd: (item: UnifiedDecisionItem) => Promise<void>
  onSnooze: (item: UnifiedDecisionItem) => void
  onDismiss?: (item: UnifiedDecisionItem, reason: 'not_useful' | 'not_applicable') => void
}) {
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)

  const sm = SOURCE_META[item.source_type] ?? SOURCE_META['recommendation']
  const pm = PRIORITY_META[item.priority] ?? PRIORITY_META['low']
  const SourceIcon = sm.icon
  const evLabel = evidenceLabel(item.evidence_level)

  const handleAdd = async () => {
    if (busy || done) return
    setBusy(true)
    try {
      await onAdd(item)
      setDone(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={`rounded-2xl border p-4 ${sm.cls} transition-all`}>
      {/* Header row */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <SourceIcon className="h-4 w-4 flex-shrink-0" />
          <span className="text-xs font-semibold tracking-wide">{sm.label}</span>
          <Badge className={`border-none text-xs ${pm.cls}`}>{pm.label}優先</Badge>
          {evLabel && (
            <Badge className="border-none bg-white/70 text-xs text-slate-600">
              <BookOpen className="mr-1 h-3 w-3" />
              {evLabel}
            </Badge>
          )}
          {item.guideline_source && (
            <Badge className="border-none bg-white/60 text-xs text-slate-500">{item.guideline_source}</Badge>
          )}
        </div>
        {existingAction ? (
          <Badge className="border-none bg-emerald-100 text-emerald-700 text-xs flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            已追蹤中
          </Badge>
        ) : null}
      </div>

      {/* Title + why_now */}
      <p className="mt-2 font-semibold text-slate-950">{item.title}</p>
      {item.why_now && item.why_now.length > 0 && (
        <ul className="mt-1 space-y-0.5">
          {item.why_now.slice(0, 2).map((reason, i) => (
            <li key={i} className="text-sm text-slate-700 flex items-start gap-1.5">
              <span className="mt-1.5 h-1 w-1 flex-shrink-0 rounded-full bg-current opacity-60" />
              {reason}
            </li>
          ))}
        </ul>
      )}

      {/* Next action */}
      {item.next_action && (
        <p className="mt-2 text-xs text-slate-600 italic">建議行動：{item.next_action}</p>
      )}

      {/* P51/P52: evidence_summary badge */}
      {item.evidence_summary && (
        <div className="mt-2 flex items-start gap-1.5 rounded bg-white/60 px-2 py-1.5 text-[11px] text-slate-500">
          <FileText className="h-3 w-3 flex-shrink-0 mt-0.5" />
          <span className="flex-1">{item.evidence_summary}</span>
          {EVIDENCE_SOURCE_META[item.source_type]?.href && (
            <Link
              href={getEvidenceHref(item.source_type, item)!}
              data-testid="p89-source-page-link"
              className="ml-1 flex items-center gap-0.5 shrink-0 text-[11px] text-slate-400 hover:text-blue-600 transition-colors"
            >
              <ExternalLink className="h-2.5 w-2.5" />
              {EVIDENCE_SOURCE_META[item.source_type]!.label}
            </Link>
          )}
        </div>
      )}

      {/* P51/P52: data_insufficiency_reason warning */}
      {item.data_insufficiency_reason && (
        <div className="mt-2 flex items-start gap-1.5 rounded-md border border-amber-200 bg-amber-50 px-2 py-1.5 text-[11px] text-amber-700">
          <AlertCircle className="h-3 w-3 flex-shrink-0 mt-0.5" />
          <span>{item.data_insufficiency_reason}</span>
        </div>
      )}

      {/* Trust block — compact inline display, same source as HealthAssistantPanel */}
      {item.trust && (
        <div className="mt-2">
          <RecommendationTrustBlock trust={item.trust} compact />
        </div>
      )}

      {/* CTAs */}
      <div className="mt-3 flex flex-wrap gap-2">
        {existingAction ? (
          <Button
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 text-xs"
            onClick={() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })}
          >
            查看追蹤中的任務
          </Button>
        ) : (
          <Button
            disabled={busy || done}
            className="bg-slate-900 hover:bg-slate-800 text-white px-3 py-1.5 text-xs"
            onClick={() => void handleAdd()}
          >
            {done ? (
              <>
                <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                已加入
              </>
            ) : busy ? (
              '加入中...'
            ) : (
              <>
                <Plus className="mr-1 h-3.5 w-3.5" />
                加入追蹤
              </>
            )}
          </Button>
        )}
        <Button
          className="bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 px-3 py-1.5 text-xs"
          onClick={() => onSnooze(item)}
        >
          <Clock3 className="mr-1 h-3.5 w-3.5" />
          稍後提醒
        </Button>
        {onDismiss && (
          <>
            <Button
              className="bg-orange-50 border border-orange-200 text-orange-700 hover:bg-orange-100 px-3 py-1.5 text-xs"
              onClick={() => onDismiss(item, 'not_useful')}
            >
              沒有用
            </Button>
            <Button
              className="bg-slate-50 border border-slate-200 text-slate-500 hover:bg-slate-100 px-3 py-1.5 text-xs"
              onClick={() => onDismiss(item, 'not_applicable')}
            >
              不適合我
            </Button>
          </>
        )}
      </div>
    </div>
  )
}

// ── Main exported component ───────────────────────────────────────────────────

export type DecisionRecommendationLayerProps = {
  /**
   * Backend decision_items (preferred) or prioritized_actions (fallback).
   * Must come directly from the dashboard API — no local re-ranking.
   */
  decisionItems: UnifiedDecisionItem[]
  /** Current user actions for deduplication display. */
  actions: HealthAction[]
  /** Called when user clicks "加入追蹤". */
  onAddAction: (item: UnifiedDecisionItem) => Promise<void>
  /** Called when user clicks "稍後提醒". */
  onSnooze: (item: UnifiedDecisionItem) => void
  /** Called when user clicks "沒有用" or "不適合我". Persisted by caller. */
  onDismiss?: (item: UnifiedDecisionItem, reason: 'not_useful' | 'not_applicable') => void
}

export function DecisionRecommendationLayer({
  decisionItems,
  actions,
  onAddAction,
  onSnooze,
  onDismiss,
}: DecisionRecommendationLayerProps) {
  if (decisionItems.length === 0) return null

  // Show top 3
  const top3 = decisionItems.slice(0, 3)

  // Build lookup: source_id → existing active action
  const activeBySourceId = new Map(
    actions
      .filter((a) => a.status !== 'done' && a.status !== 'snoozed')
      .map((a) => [a.source_id, a])
  )
  const normalize = (s: string) => s.trim().toLowerCase().replace(/\s+/g, ' ')
  function findExisting(item: UnifiedDecisionItem): HealthAction | null {
    if (activeBySourceId.has(item.source_id)) return activeBySourceId.get(item.source_id)!
    const itemTitle = normalize(item.title)
    return (
      actions.find((a) => {
        if (a.status === 'done' || a.status === 'snoozed') return false
        const aTitle = normalize(a.title)
        if (!aTitle || !itemTitle) return false
        let shared = 0
        for (let i = 0; i < itemTitle.length - 1; i++) {
          if (aTitle.includes(itemTitle.slice(i, i + 2))) shared++
        }
        return (2 * shared) / (aTitle.length + itemTitle.length - 2) >= 0.75
      }) ?? null
    )
  }

  return (
    <Card className="rounded-3xl border border-slate-200/80 p-6">
      {/* Section header */}
      <div className="flex items-center gap-2 mb-1">
        <Sparkles className="h-4 w-4 text-violet-500" />
        <h3 className="text-lg font-semibold">系統現在建議你先做</h3>
        <Badge className="border-none bg-violet-100 text-violet-700 text-xs">Decision Engine</Badge>
      </div>
      <p className="text-sm text-slate-500 mb-4">
        由 Backend Decision Engine 排序，與 Dashboard / Notifications 保持一致。
      </p>

      <div className="space-y-3">
        {top3.map((item) => (
          <RecommendationItem
            key={item.id}
            item={item}
            existingAction={findExisting(item)}
            onAdd={onAddAction}
            onSnooze={onSnooze}
            onDismiss={onDismiss}
          />
        ))}
      </div>
    </Card>
  )
}
