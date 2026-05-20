'use client';

import { AlertTriangle, TrendingUp, Activity, FlaskConical, Repeat, Info } from 'lucide-react';
import type { SymptomPattern } from '../../../lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SymptomInsightCardProps {
  patterns: SymptomPattern[];
  loading?: boolean;
}

// ---------------------------------------------------------------------------
// Style maps
// ---------------------------------------------------------------------------

const SEVERITY_BADGE: Record<string, string> = {
  high:   'bg-red-100 text-red-700 border border-red-200',
  medium: 'bg-amber-100 text-amber-700 border border-amber-200',
  low:    'bg-blue-100 text-blue-700 border border-blue-200',
};

const SEVERITY_LABEL: Record<string, string> = {
  high:   '高風險',
  medium: '中風險',
  low:    '低風險',
};

const SEVERITY_CARD_BG: Record<string, string> = {
  high:   'border-red-200 bg-red-50',
  medium: 'border-amber-200 bg-amber-50',
  low:    'border-blue-200 bg-blue-50',
};

const PATTERN_ICON: Record<string, React.ReactNode> = {
  recurring_symptom:                <Repeat className="w-4 h-4 shrink-0" />,
  worsening_symptom:                <TrendingUp className="w-4 h-4 shrink-0" />,
  symptom_with_device_signal:       <Activity className="w-4 h-4 shrink-0" />,
  symptom_with_lab_risk:            <FlaskConical className="w-4 h-4 shrink-0" />,
  unresolved_high_severity_symptom: <AlertTriangle className="w-4 h-4 shrink-0" />,
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const barColor =
    pct >= 80 ? 'bg-red-400' : pct >= 65 ? 'bg-amber-400' : 'bg-blue-400';
  return (
    <div className="flex items-center gap-2 text-xs text-gray-500">
      <span>信心度</span>
      <div className="flex-1 bg-gray-200 rounded-full h-1.5 max-w-24">
        <div
          className={`${barColor} h-1.5 rounded-full transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-medium">{pct}%</span>
    </div>
  );
}

function TagList({ label, items, chipClass }: { label: string; items: string[]; chipClass: string }) {
  if (!items.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-1 text-xs">
      <span className="text-gray-500">{label}：</span>
      {items.map((it, i) => (
        <span key={i} className={`px-2 py-0.5 rounded-full text-xs font-medium ${chipClass}`}>
          {it}
        </span>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function SymptomInsightCard({ patterns, loading }: SymptomInsightCardProps) {
  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3 animate-pulse">
        <div className="h-4 w-40 bg-gray-200 rounded" />
        <div className="h-16 bg-gray-100 rounded-lg" />
        <div className="h-16 bg-gray-100 rounded-lg" />
      </div>
    );
  }

  // ── Empty state ───────────────────────────────────────────────────────────
  if (!patterns || patterns.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <Info className="w-4 h-4 text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-700">症狀模式分析</h3>
        </div>
        <p className="text-sm text-gray-400 text-center py-4">尚無明顯症狀模式</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-violet-600" />
          <h3 className="text-sm font-semibold text-gray-800">症狀模式分析</h3>
        </div>
        <span className="text-xs text-gray-400">{patterns.length} 項模式</span>
      </div>

      {/* Pattern cards */}
      <div className="space-y-2">
        {patterns.map((pattern, idx) => {
          const cardBg  = SEVERITY_CARD_BG[pattern.severity]  ?? SEVERITY_CARD_BG.medium;
          const badgeCls = SEVERITY_BADGE[pattern.severity]   ?? SEVERITY_BADGE.medium;
          const icon     = PATTERN_ICON[pattern.patternType]  ?? <Info className="w-4 h-4 shrink-0" />;

          return (
            <div key={idx} className={`rounded-lg border p-3 space-y-2 ${cardBg}`}>
              {/* Pattern header row */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-gray-600">{icon}</span>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-gray-800 truncate">
                      {pattern.label}
                    </p>
                    <p className="text-xs text-gray-600">{pattern.symptomType}</p>
                  </div>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium shrink-0 ${badgeCls}`}>
                  {SEVERITY_LABEL[pattern.severity] ?? pattern.severity}
                </span>
              </div>

              {/* Why detected */}
              <p className="text-xs text-gray-700 leading-relaxed">{pattern.whyDetected}</p>

              {/* Confidence */}
              <ConfidenceBar value={pattern.confidence} />

              {/* Related signals & labs */}
              <TagList
                label="相關裝置訊號"
                items={pattern.relatedDeviceSignals}
                chipClass="bg-blue-100 text-blue-700"
              />
              <TagList
                label="相關檢驗指標"
                items={pattern.relatedLabItems}
                chipClass="bg-purple-100 text-purple-700"
              />

              {/* Suggested action */}
              {pattern.suggestedAction && (
                <div className="text-xs text-gray-600 bg-white/70 rounded-md px-3 py-2 border border-gray-200">
                  <span className="font-medium text-gray-700">建議行動：</span>
                  {pattern.suggestedAction}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Medical disclaimer */}
      <p className="text-xs text-gray-400 leading-relaxed border-t border-gray-100 pt-2">
        以上分析由 AI 根據您的症狀記錄自動產生，僅供個人健康管理參考，不構成醫療診斷或治療建議。
        如有疑慮，請諮詢專業醫療人員。
      </p>
    </div>
  );
}
