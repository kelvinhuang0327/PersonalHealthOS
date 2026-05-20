'use client'

/**
 * RecommendationTrustBlock — shared trust UI component (Task 3)
 *
 * Used by:
 *   - health-assistant-panel.tsx (replaces local TrustBadge + TrustSection)
 *   - decision-recommendation-layer.tsx (Actions page)
 *   - daily-assistant-entry.tsx (Dashboard daily entry)
 *
 * Props:
 *   trust            — RecommendationTrust object (from backend)
 *   compact          — if true, renders badge + % only, no expand toggle
 *   showLimitations  — if false, hides the limitations section (default true)
 */

import { useState } from 'react'
import { CheckCircle2, ChevronDown } from 'lucide-react'
import type { RecommendationTrust } from '../../../lib/api'

// ── Style maps ────────────────────────────────────────────────────────────────

const TRUST_STYLE: Record<string, string> = {
  high:   'bg-emerald-50 text-emerald-700 border border-emerald-200',
  medium: 'bg-amber-50 text-amber-700 border border-amber-200',
  low:    'bg-red-50 text-red-600 border border-red-200',
}

const TRUST_LABEL: Record<string, string> = {
  high:   '高可信',
  medium: '中可信',
  low:    '低可信',
}

const TRUST_BAR_COLOR: Record<string, string> = {
  high:   'bg-emerald-500',
  medium: 'bg-amber-400',
  low:    'bg-red-400',
}

// ── TrustBadge ────────────────────────────────────────────────────────────────

export function TrustBadge({ level }: { level: string }) {
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${
        TRUST_STYLE[level] ?? TRUST_STYLE.low
      }`}
    >
      {TRUST_LABEL[level] ?? level}
    </span>
  )
}

// ── Main block ─────────────────────────────────────────────────────────────────

export interface RecommendationTrustBlockProps {
  trust: RecommendationTrust
  /** Show badge + % only, no expand toggle. Default false. */
  compact?: boolean
  /** Show limitations section. Default true. */
  showLimitations?: boolean
}

export function RecommendationTrustBlock({
  trust,
  compact = false,
  showLimitations = true,
}: RecommendationTrustBlockProps) {
  const [expanded, setExpanded] = useState(false)
  const pct = Math.round(trust.confidence * 100)

  const verifiedBadge = trust.verifiedByOutcome ? (
    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded text-[10px] border border-emerald-200">
      <CheckCircle2 className="h-2.5 w-2.5" />
      已驗證
    </span>
  ) : null

  // ── Compact mode ─────────────────────────────────────────────────────────────
  if (compact) {
    return (
      <div className="flex items-center gap-1.5 flex-wrap">
        <TrustBadge level={trust.level} />
        <span className="text-[10px] text-neutral-500">可信度 {pct}%</span>
        {verifiedBadge}
      </div>
    )
  }

  // ── Full expandable mode ──────────────────────────────────────────────────────
  return (
    <div className="mt-2.5 border-t border-neutral-100 pt-2">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between text-xs text-neutral-500 hover:text-neutral-700 transition-colors"
      >
        <div className="flex items-center gap-1.5">
          <TrustBadge level={trust.level} />
          <span>可信度 {pct}%</span>
          {verifiedBadge}
        </div>
        <ChevronDown
          className={`h-3 w-3 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
        />
      </button>

      {expanded && (
        <div className="mt-2 space-y-2">
          {/* Confidence bar */}
          <div className="h-1.5 rounded-full bg-neutral-100 overflow-hidden">
            <div
              className={`h-1.5 rounded-full transition-all duration-500 ${
                TRUST_BAR_COLOR[trust.level] ?? TRUST_BAR_COLOR.low
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>

          {/* Reasons */}
          {trust.reasons.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-neutral-500 mb-1">支持依據</p>
              <ul className="space-y-0.5">
                {trust.reasons.map((r, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-1 text-[10px] text-neutral-600 leading-relaxed"
                  >
                    <span className="text-emerald-500 mt-px flex-shrink-0">✓</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Limitations */}
          {showLimitations && trust.limitations.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-neutral-500 mb-1">資料不足</p>
              <ul className="space-y-0.5">
                {trust.limitations.map((l, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-1 text-[10px] text-neutral-500 leading-relaxed"
                  >
                    <span className="text-amber-400 mt-px flex-shrink-0">!</span>
                    {l}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Next check-in */}
          <p className="text-[10px] text-neutral-400 italic leading-relaxed">
            {trust.nextCheckInSuggestion}
          </p>
        </div>
      )}
    </div>
  )
}
