'use client'

/**
 * DailyAssistantEntry — Task 1: Daily Assistant Entry UI
 *
 * Integrates:
 *   1. Daily Summary  (topRisk / biggestChange / todayAction)
 *   2. Top recommendation with Trust Layer
 *   3. Missing data hints
 *   4. Outcome feedback summary (7-day)
 *   5. Next check-in suggestion
 *
 * Acceptance criteria coverage:
 *   ✓ Daily Summary enters Dashboard UI (not just an API)
 *   ✓ low confidence → "建議可信度有限" amber warning
 *   ✓ high confidence → "已基於多項資料驗證" emerald banner
 *   ✓ empty state does not mislead
 *   ✓ outcome feedback summary with graceful fallback
 *   ✓ missing data surfaced with action links
 *
 * Data flow:
 *   - `data` prop  : health-assistant recommendations (already fetched by parent)
 *   - Internally fetches: getDailySummary(), getOutcomeFeedback(7)
 */

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileText,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react'
import { Card } from '../ui/card'
import { Skeleton } from '../ui/skeleton'
import { RecommendationTrustBlock } from './recommendation-trust-block'
import { api, type DailyHealthSummary, type OutcomeFeedback } from '../../../lib/api'
import type { HealthAssistantData } from './health-assistant-panel'
import { EVIDENCE_SOURCE_META, getEvidenceHref } from '../../../lib/evidence-source-meta'


// ── Missing data action links ─────────────────────────────────────────────────

const MISSING_DATA_LINKS: Record<string, { href: string; label: string }> = {
  '症狀記錄':                           { href: '/platform/symptoms',       label: '記錄症狀'   },
  '健康指標（血壓、血糖、體重等）':      { href: '/platform/quick-check-in', label: '填入指標'   },
  '健檢報告（或無異常項目）':            { href: '/platform/documents',      label: '上傳報告'   },
  '個人健康檔案（性別、年齡等）':        { href: '/platform/profile',        label: '完善檔案'   },
}

/** Items expected to be absent — not meaningful as limitations. */
const TRIVIAL_MISSING = new Set([
  '風險警示（目前無主動警示）',
  '健康洞察（建議先執行健康分析）',
])

/** Short user-facing explanation of what each data type unlocks for the assistant. */
const MISSING_DATA_GAINS: Record<string, string> = {
  '症狀記錄':                           '幫助偵測症狀模式與風險關聯',
  '健康指標（血壓、血糖、體重等）':      '讓血壓、血糖趨勢更準確可信',
  '健檢報告（或無異常項目）':            '啟用報告異常自動比對分析',
  '個人健康檔案（性別、年齡等）':        '提升年齡性別個人化建議精度',
}

function getMissingLink(item: string): { href: string; label: string } {
  return MISSING_DATA_LINKS[item] ?? { href: '/platform/profile', label: '補充資料' }
}

function getMissingGain(item: string): string {
  return MISSING_DATA_GAINS[item] ?? '補齊後可提升建議準確度'
}

// ── Component ─────────────────────────────────────────────────────────────────

interface DailyAssistantEntryProps {
  /** Health-assistant recommendation data (already fetched by the parent). */
  data: HealthAssistantData | null
  loading?: boolean
}

export function DailyAssistantEntry({ data, loading = false }: DailyAssistantEntryProps) {
  const [summary, setSummary]           = useState<DailyHealthSummary | null>(null)
  const [sumLoading, setSumLoading]     = useState(true)
  const [feedback, setFeedback]         = useState<OutcomeFeedback | null>(null)
  const [documents, setDocuments]       = useState<Array<{ parse_status?: string }>>([])
  const [symptoms, setSymptoms]         = useState<Array<{ id?: string }>>([])
  const [journeyLoading, setJourneyLoading] = useState(true)

  useEffect(() => {
    api
      .getDailySummary()
      .then((d) => setSummary(d as DailyHealthSummary))
      .catch(() => setSummary(null))
      .finally(() => setSumLoading(false))

    api
      .getOutcomeFeedback(7)
      .then((d) => setFeedback(d as OutcomeFeedback))
      .catch(() => setFeedback(null))

    Promise.all([
      api.listDocuments().catch(() => []),
      api.listSymptoms().catch(() => []),
    ])
      .then(([docs, syms]) => {
        setDocuments(Array.isArray(docs) ? (docs as Array<{ parse_status?: string }>) : [])
        setSymptoms(Array.isArray(syms) ? (syms as Array<{ id?: string }>) : [])
      })
      .finally(() => setJourneyLoading(false))
  }, [])

  // Derived values
  const topRec          = data?.recommendations?.[0] ?? null
  const trust           = topRec?.trust ?? null
  const isLowConf       = trust?.level === 'low'
  const isHighConf      = trust?.level === 'high'
  const missingItems    = (data?.missing_data ?? []).filter((m) => !TRIVIAL_MISSING.has(m))
  const isFullyLoading  = loading || sumLoading
  const hasDailySummary = !!(summary?.topRisk || summary?.biggestChange || summary?.todayAction)

  const fbSummary = feedback?.summary
  const hasFeedback = fbSummary && fbSummary.total_count > 0
  const hasConfirmedReport = documents.some((doc) => doc.parse_status === 'confirmed')
  const hasSymptomLog = symptoms.length > 0
  const hasAssistantSurface = hasDailySummary || Boolean(topRec)
  const isJourneyCompleted = hasConfirmedReport && hasSymptomLog && hasAssistantSurface
  const isJourneyEmpty = !hasConfirmedReport && !hasSymptomLog && !hasAssistantSurface
  const journeyState: 'empty' | 'in_progress' | 'completed' = isJourneyCompleted ? 'completed' : (isJourneyEmpty ? 'empty' : 'in_progress')
  const nextStep: 'documents' | 'symptoms' | 'dashboard' | 'actions' =
    !hasConfirmedReport ? 'documents' :
    !hasSymptomLog ? 'symptoms' :
    !hasAssistantSurface ? 'dashboard' :
    'actions'
  const suppressedNotJudgedDetected = (() => {
    const candidates = [
      topRec?.evidence_summary,
      summary?.topRisk,
      summary?.whyNow,
      summary?.topRiskRef?.summary,
      summary?.todayActionRef?.summary,
    ]
      .filter(Boolean)
      .map((v) => String(v).toLowerCase())
    return candidates.some((text) => text.includes('suppressed_unit_scale_mismatch') || text.includes('暫不判斷異常'))
  })()

  return (
    <Card data-testid="daily-assistant-entry" className="rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50/60 via-white to-emerald-50/30 p-5 shadow-sm">

      {/* ── Header ───────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-blue-600" />
          <h3 className="text-base font-semibold text-slate-800">今日健康入口</h3>
        </div>
        {summary?.generated_at && (
          <div className="flex items-center gap-1 text-[11px] text-slate-400">
            <Clock className="h-3 w-3" />
            {new Date(summary.generated_at).toLocaleTimeString('zh-TW', {
              hour: '2-digit',
              minute: '2-digit',
            })}{' '}
            更新
          </div>
        )}
      </div>

      {/* ── Loading ───────────────────────────────────────────────────────────── */}
      {isFullyLoading ? (
        <div data-testid="daily-assistant-loading" className="space-y-3">
          <Skeleton variant="card" className="h-14" />
          <Skeleton variant="card" className="h-10" />
          <Skeleton variant="card" className="h-8" />
        </div>
      ) : (
        <div className="space-y-4">

          {/* ── First-run journey checklist (P123) ─────────────────────────── */}
          {!journeyLoading && (
            <div data-testid="first-run-journey-card" className="rounded-xl border border-sky-100 bg-sky-50/50 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold text-sky-700">首次使用引導</p>
                <span className="text-[11px] text-sky-600">報告 → 症狀 → 每日建議 → 行動</span>
              </div>

              {journeyState === 'empty' && (
                <p data-testid="first-run-journey-empty" className="mt-2 text-[11px] text-sky-700 leading-relaxed">
                  先完成兩個基礎步驟：上傳並確認健檢報告、記錄最近症狀。完成後即可看到更完整的每日建議。
                </p>
              )}

              {journeyState === 'in_progress' && (
                <p data-testid="first-run-journey-in-progress" className="mt-2 text-[11px] text-sky-700 leading-relaxed">
                  你已經完成部分資料整理，繼續補齊下一步即可讓小助手提供更清楚的追蹤建議。
                </p>
              )}

              {journeyState === 'completed' && (
                <p data-testid="first-run-journey-completed" className="mt-2 text-[11px] text-emerald-700 leading-relaxed">
                  首次使用流程已就緒，接下來可直接查看今日建議並執行行動追蹤。
                </p>
              )}

              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                <Link data-testid="first-run-link-documents" href="/platform/documents" className="rounded-lg border border-white bg-white px-2.5 py-2 text-[11px] text-slate-700 hover:bg-slate-50">
                  1. 健檢報告（上傳/確認）{hasConfirmedReport ? ' ✓' : ''}
                </Link>
                <Link data-testid="first-run-link-symptoms" href="/platform/symptoms" className="rounded-lg border border-white bg-white px-2.5 py-2 text-[11px] text-slate-700 hover:bg-slate-50">
                  2. 症狀記錄{hasSymptomLog ? ' ✓' : ''}
                </Link>
                <Link data-testid="first-run-link-dashboard" href="/platform/dashboard" className="rounded-lg border border-white bg-white px-2.5 py-2 text-[11px] text-slate-700 hover:bg-slate-50">
                  3. 每日建議{hasAssistantSurface ? ' ✓' : ''}
                </Link>
                <Link data-testid="first-run-link-actions" href="/platform/actions" className="rounded-lg border border-white bg-white px-2.5 py-2 text-[11px] text-slate-700 hover:bg-slate-50">
                  4. 行動追蹤
                </Link>
              </div>

              {journeyState === 'in_progress' && nextStep === 'documents' && (
                <p data-testid="first-run-next-step-documents" className="mt-2 text-[11px] text-sky-700">
                  下一步：先完成健檢報告上傳或確認，讓系統有可追蹤的檢驗依據。
                </p>
              )}
              {journeyState === 'in_progress' && nextStep === 'symptoms' && (
                <p data-testid="first-run-next-step-symptoms" className="mt-2 text-[11px] text-sky-700">
                  下一步：補上症狀記錄，讓建議可結合你的主觀不適與檢驗資料。
                </p>
              )}
              {journeyState === 'in_progress' && nextStep === 'dashboard' && (
                <p data-testid="first-run-next-step-dashboard" className="mt-2 text-[11px] text-sky-700">
                  下一步：回到儀表板查看今日建議，確認目前的追蹤重點。
                </p>
              )}
              {journeyState === 'completed' && (
                <p data-testid="first-run-next-step-actions" className="mt-2 text-[11px] text-emerald-700">
                  建議下一步：前往行動頁，把今天最重要的一項建議加入追蹤。
                </p>
              )}
            </div>
          )}

          {suppressedNotJudgedDetected && (
            <div data-testid="first-run-suppression-not-judged-note" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2">
              <p className="text-[11px] text-amber-700 leading-relaxed">
                偵測到「暫不判斷異常」資料。這類資料代表目前證據不足，請搭配後續追蹤作為就醫討論參考，避免直接下臨床結論。
              </p>
            </div>
          )}

          {/* ── Confidence context banner (Task 4: low / high copy) ─────────── */}
          {isLowConf && (
            <div className="flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 p-3">
              <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-700 leading-relaxed">
                <span className="font-semibold">建議可信度有限</span> —
                目前健康資料不足，以下建議僅作參考，補充資料後可信度將自動提升。
              </p>
            </div>
          )}
          {isHighConf && (
            <div className="flex items-start gap-2 rounded-xl bg-emerald-50 border border-emerald-200 p-3">
              <ShieldCheck className="h-4 w-4 text-emerald-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-emerald-700 leading-relaxed">
                <span className="font-semibold">已基於多項資料驗證</span> —
                此建議整合多種健康指標，可信度高。
                {trust?.verifiedByOutcome && ' 並已由實際成效資料驗證。'}
              </p>
            </div>
          )}

          {/* ── Escalation notice (P72) ───────────────────────────────────────── */}
          {summary?.escalation != null && summary.escalation.escalationLevel !== 'none' && (
            <div
              data-testid="daily-summary-escalation-notice"
              className="flex items-start gap-2 rounded-xl bg-amber-50 border border-amber-200 p-3"
            >
              <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-xs font-semibold text-amber-800">
                  需要留意
                  {summary.escalation.escalationLevel === 'urgent' && ' — 緊急'}
                  {summary.escalation.escalationLevel === 'warning' && ' — 警告'}
                  {summary.escalation.escalationLevel === 'watch' && ' — 觀察'}
                </p>
                {summary.escalation.reasons[0] && (
                  <p className="mt-0.5 text-[11px] text-amber-700 leading-relaxed">
                    {summary.escalation.reasons[0]}
                  </p>
                )}
                {summary.escalation.recommendedAction && (
                  <p className="mt-0.5 text-[11px] text-amber-600 leading-relaxed">
                    建議：{summary.escalation.recommendedAction}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* ── Daily summary 3-grid ─────────────────────────────────────────── */}
          {hasDailySummary || topRec ? (
            <div className="grid gap-3 sm:grid-cols-3">
              {/* Today's top risk */}
              <div data-testid="daily-summary-top-risk" className="rounded-xl bg-white border border-slate-100 p-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 text-rose-500" />
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    今日最重要風險
                  </p>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed line-clamp-3">
                  {summary?.topRisk || topRec?.why_now || '暫無風險資料'}
                </p>
                {summary?.whyNow && (
                  <p
                    data-testid="daily-summary-why-now"
                    className="mt-1.5 text-[11px] text-slate-500 leading-relaxed italic border-t border-slate-50 pt-1.5 line-clamp-2"
                  >
                    為什麼重要：{summary.whyNow}
                  </p>
                )}
                {summary?.topRiskRef && (
                  <div
                    data-testid="p94-top-risk-ref-badge"
                    className="mt-1.5 flex items-center gap-1 text-[10px] text-slate-400 border-t border-slate-50 pt-1.5"
                  >
                    <FileText className="h-2.5 w-2.5 flex-shrink-0" />
                    <span className="flex-1 truncate">
                      {summary.topRiskRef.summary || EVIDENCE_SOURCE_META[summary.topRiskRef.source_type]?.label || '參考依據'}
                    </span>
                    {EVIDENCE_SOURCE_META[summary.topRiskRef.source_type]?.href && (
                      <Link
                        href={getEvidenceHref(summary.topRiskRef.source_type, summary.topRiskRef)!}
                        data-testid="p94-top-risk-ref-link"
                        className="shrink-0 text-slate-400 hover:text-blue-600"
                      >
                        <ExternalLink className="h-2.5 w-2.5" />
                      </Link>
                    )}
                  </div>
                )}
              </div>

              {/* Biggest change */}
              <div data-testid="daily-summary-biggest-change" className="rounded-xl bg-white border border-slate-100 p-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <TrendingUp className="h-3.5 w-3.5 text-sky-500" />
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    今日最大變化
                  </p>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed line-clamp-3">
                  {summary?.biggestChange || '尚無明顯變化資料'}
                </p>
                {summary?.biggestChange && (
                  <p
                    data-testid="daily-summary-biggest-change-context"
                    className="mt-1.5 text-[11px] text-slate-500 leading-relaxed italic border-t border-slate-50 pt-1.5 line-clamp-2"
                  >
                    此為近 7 天最顯著的健康趨勢變化。
                  </p>
                )}
                {summary?.biggestChangeRef && (
                  <div
                    data-testid="p94-biggest-change-ref-badge"
                    className="mt-1.5 flex items-center gap-1 text-[10px] text-slate-400 border-t border-slate-50 pt-1.5"
                  >
                    <FileText className="h-2.5 w-2.5 flex-shrink-0" />
                    <span className="flex-1 truncate">
                      {summary.biggestChangeRef.summary || EVIDENCE_SOURCE_META[summary.biggestChangeRef.source_type]?.label || '參考依據'}
                    </span>
                    {EVIDENCE_SOURCE_META[summary.biggestChangeRef.source_type]?.href && (
                      <Link
                        href={getEvidenceHref(summary.biggestChangeRef.source_type, summary.biggestChangeRef)!}
                        data-testid="p94-biggest-change-ref-link"
                        className="shrink-0 text-slate-400 hover:text-blue-600"
                      >
                        <ExternalLink className="h-2.5 w-2.5" />
                      </Link>
                    )}
                  </div>
                )}
              </div>

              {/* Today's primary action */}
              <div data-testid="daily-summary-next-action" className="rounded-xl bg-white border border-slate-100 p-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    今日主要行動
                  </p>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed line-clamp-3">
                  {summary?.todayAction || topRec?.next_action || '先從建議清單選一項開始'}
                </p>
                {summary?.todayAction && (
                  <p
                    data-testid="daily-summary-action-impact"
                    className="mt-1.5 text-[11px] text-slate-500 leading-relaxed italic border-t border-slate-50 pt-1.5 line-clamp-2"
                  >
                    完成後，小助手可以把今日行動與後續結果連起來追蹤。
                  </p>
                )}
                {summary?.todayActionRef && (
                  <div
                    data-testid="p94-today-action-ref-badge"
                    className="mt-1.5 flex items-center gap-1 text-[10px] text-slate-400 border-t border-slate-50 pt-1.5"
                  >
                    <FileText className="h-2.5 w-2.5 flex-shrink-0" />
                    <span className="flex-1 truncate">
                      {summary.todayActionRef.summary || EVIDENCE_SOURCE_META[summary.todayActionRef.source_type]?.label || '參考依據'}
                    </span>
                    {EVIDENCE_SOURCE_META[summary.todayActionRef.source_type]?.href && (
                      <Link
                        href={getEvidenceHref(summary.todayActionRef.source_type, summary.todayActionRef)!}
                        data-testid="p94-today-action-ref-link"
                        className="shrink-0 text-slate-400 hover:text-blue-600"
                      >
                        <ExternalLink className="h-2.5 w-2.5" />
                      </Link>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            // Empty state — does not mislead
            <div data-testid="daily-summary-empty" className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-5 text-center">
              <RefreshCw className="mx-auto h-6 w-6 text-slate-300 mb-2" />
              <p className="text-sm font-medium text-slate-500">今日摘要尚未生成</p>
              <p className="mt-1 text-xs text-slate-400 max-w-sm mx-auto">
                補充健康資料後，系統將自動為你生成每日摘要與個人化建議。
              </p>
              <Link
                href="/platform/quick-check-in"
                className="mt-3 inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 font-medium"
              >
                填入今日健康指標 <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          )}

          {/* ── Summary confidence signal (P70) ──────────────────────────────── */}
          {typeof summary?.confidence === 'number' && summary.confidence > 0 && (
            <div
              data-testid="daily-summary-confidence-signal"
              className="flex items-center gap-1.5 px-1"
            >
              <span className="text-[10px] text-slate-400">
                可信度 {Math.round(summary.confidence * 100)}%
              </span>
            </div>
          )}

          {/* ── Encouragement message (P71) ───────────────────────────────────── */}
          {typeof summary?.encouragement === 'string' && summary.encouragement.trim().length > 0 && (
            <div
              data-testid="daily-summary-encouragement"
              className="rounded-xl bg-emerald-50 border border-emerald-100 px-3 py-2"
            >
              <p className="text-[10px] font-medium text-emerald-600 mb-0.5">小助手鼓勵</p>
              <p className="text-[11px] text-emerald-800 leading-relaxed">
                {summary.encouragement.trim()}
              </p>
            </div>
          )}

          {/* ── Top recommendation + trust ───────────────────────────────────── */}
          {topRec && (
            <div className="rounded-xl bg-white border border-slate-100 p-3">
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-slate-800">{topRec.title}</p>
                  <p className="mt-0.5 text-[11px] text-slate-500 leading-relaxed">
                    {topRec.why_now}
                  </p>
                  {/* P91: evidence badge — renders only when evidence_summary exists */}
                  {topRec.evidence_summary && (
                    <div
                      data-testid="daily-toprec-evidence-badge"
                      className="mt-1.5 flex items-start gap-1.5 rounded bg-slate-50 border border-slate-100 px-2 py-1 text-[11px] text-slate-500"
                    >
                      <FileText className="h-3 w-3 flex-shrink-0 mt-0.5" />
                      <span className="flex-1">參考依據：{topRec.evidence_summary}</span>
                      {EVIDENCE_SOURCE_META[topRec.source_type]?.href && (
                        <Link
                          href={EVIDENCE_SOURCE_META[topRec.source_type]!.href!}
                          data-testid="p91-daily-source-page-link"
                          className="ml-1 flex items-center gap-0.5 shrink-0 text-[11px] text-slate-400 hover:text-blue-600 transition-colors"
                        >
                          <ExternalLink className="h-2.5 w-2.5" />
                          {EVIDENCE_SOURCE_META[topRec.source_type]!.label}
                        </Link>
                      )}
                    </div>
                  )}
                </div>
                <Link
                  href="/platform/actions"
                  className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-medium rounded-md transition-colors"
                >
                  行動 <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
              {trust && <RecommendationTrustBlock trust={trust} showLimitations />}
            </div>
          )}

          {/* ── Missing data hints (Task 4: missing data 顯示) ───────────────── */}
          {missingItems.length > 0 && (
            <div data-testid="daily-summary-missing-data" className="rounded-xl bg-amber-50/60 border border-amber-100 p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <AlertCircle className="h-3.5 w-3.5 text-amber-500" />
                <p className="text-[10px] font-semibold text-amber-700">
                  補充以下資料可提升可信度
                </p>
              </div>
              <p className="text-[11px] text-amber-600 mb-2">目前資料不足，建議補充最近紀錄</p>
              <div className="flex flex-col gap-1.5">
                {missingItems.slice(0, 3).map((item) => {
                  const link = getMissingLink(item)
                  const gain = getMissingGain(item)
                  return (
                    <div key={item} className="flex items-center gap-2">
                      <Link
                        href={link.href}
                        className="inline-flex items-center gap-1 px-2.5 py-1 bg-white border border-amber-200 rounded-lg text-[11px] text-amber-700 hover:bg-amber-50 transition-colors shrink-0"
                      >
                        {link.label}
                        <ArrowRight className="h-2.5 w-2.5" />
                      </Link>
                      <span className="text-[10px] text-amber-500 leading-tight">— {gain}</span>
                    </div>
                  )
                })}
              </div>
              <p
                data-testid="daily-summary-missing-data-explanation"
                className="mt-2 text-[10px] text-amber-600 italic"
              >
                補齊後，小助手可以更準確判斷風險變化與下一步建議。
              </p>
            </div>
          )}

          {/* ── Outcome feedback summary (Task 4: 正常 fallback) ─────────────── */}
          {hasFeedback ? (
            <div data-testid="daily-summary-outcome-section" className="rounded-xl bg-white border border-slate-100 p-3">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2">
                近 7 天成效回饋
              </p>
              <div className="flex items-center gap-4 flex-wrap">
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 shrink-0" />
                  <span className="text-xs text-slate-600">
                    已改善 {fbSummary!.improved_count}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-slate-300 shrink-0" />
                  <span className="text-xs text-slate-600">
                    持平 {fbSummary!.unchanged_count}
                  </span>
                </div>
                {fbSummary!.deteriorated_count > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-rose-400 shrink-0" />
                    <span className="text-xs text-slate-600">
                      需關注 {fbSummary!.deteriorated_count}
                    </span>
                  </div>
                )}
                {fbSummary!.tracking_count > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-sky-400 shrink-0" />
                    <span className="text-xs text-slate-600">
                      追蹤中 {fbSummary!.tracking_count}
                    </span>
                  </div>
                )}
                <Link
                  href="/platform/actions"
                  className="ml-auto text-[11px] text-blue-600 hover:text-blue-700 font-medium"
                >
                  查看詳情 →
                </Link>
              </div>
              {fbSummary!.improved_count > 0 && (
                <div
                  data-testid="daily-summary-outcome-improved-badge"
                  className="mt-2 flex items-center gap-1.5 rounded-lg bg-emerald-50 border border-emerald-100 px-2.5 py-1"
                >
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                  <span className="text-[11px] font-medium text-emerald-700">
                    已改善 {fbSummary!.improved_count} 項，持續追蹤中
                  </span>
                </div>
              )}
              {(fbSummary!.tracking_count > 0 || fbSummary!.insufficient_data_count > 0) && (
                <p data-testid="daily-summary-outcome-unknown" className="mt-2 text-[11px] text-slate-400">
                  目前尚無足夠後續資料判斷效果
                </p>
              )}
              <p className="mt-2 text-[11px] text-slate-400 italic">這是使用者回饋，不是醫療效果證明</p>
            </div>
          ) : feedback !== null && fbSummary?.total_count === 0 ? (
            // Graceful fallback — empty outcome state
            <p className="text-[11px] text-slate-400 text-center py-1">
              尚無成效資料 — 完成第一項行動後，系統將開始追蹤改善效果。
            </p>
          ) : null}

          {/* ── Next check-in (P73) ───────────────────────────────────────────── */}
          {(trust?.nextCheckInSuggestion || summary) && (
            <p data-testid="daily-summary-next-checkin" className="text-[11px] text-slate-400 italic text-right">
              {trust?.nextCheckInSuggestion
                ? trust.nextCheckInSuggestion
                : summary?.todayAction
                  ? '完成今日行動後，回來更新記錄。'
                  : '今日資料已更新，明天繼續追蹤。'}
            </p>
          )}
        </div>
      )}

      {/* ── Footer links ────────────────────────────────────────────────────── */}
      <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-3">
        <Link
          href="/platform/actions"
          className="text-xs text-blue-600 hover:text-blue-700 font-medium"
        >
          全部建議 →
        </Link>
        <Link href="/platform/symptoms" className="text-xs text-slate-500 hover:text-slate-700">
          記錄症狀
        </Link>
        <Link href="/platform/documents" className="text-xs text-slate-500 hover:text-slate-700">
          上傳報告
        </Link>
        <Link
          href="/platform/quick-check-in"
          className="text-xs text-slate-500 hover:text-slate-700"
        >
          填入指標
        </Link>
      </div>
    </Card>
  )
}
