'use client';

import { FlaskConical, ChevronDown, ChevronUp, AlertTriangle, RotateCcw, Lightbulb, Clock } from 'lucide-react';
import { useState } from 'react';
import type { LabAbnormality } from '../../../lib/api';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface LabInsightCardProps {
  abnormalities: LabAbnormality[];
  loading?: boolean;
}

// ---------------------------------------------------------------------------
// Style helpers
// ---------------------------------------------------------------------------

const SEVERITY_BADGE: Record<string, string> = {
  high:   'bg-red-100 text-red-700 border border-red-200',
  medium: 'bg-amber-100 text-amber-700 border border-amber-200',
  low:    'bg-blue-100 text-blue-700 border border-blue-200',
};

const SEVERITY_LABEL: Record<string, string> = {
  high:   '高度異常',
  medium: '中度異常',
  low:    '輕度異常',
};

const SEVERITY_CARD_BG: Record<string, string> = {
  high:   'border-red-200 bg-red-50',
  medium: 'border-amber-200 bg-amber-50',
  low:    'border-blue-200 bg-blue-50',
};

const TYPE_LABEL: Record<string, string> = {
  lipid_abnormality:    '血脂',
  glucose_abnormality:  '血糖',
  blood_pressure:       '血壓',
  kidney_function:      '腎功能',
  liver_function:       '肝功能',
  thyroid_function:     '甲狀腺',
  anemia_marker:        '血液',
  uric_acid:            '尿酸',
  inflammation_marker:  '發炎指標',
  lab_abnormality:      '其他指標',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 75 ? 'bg-green-500' :
    pct >= 55 ? 'bg-amber-500' :
                'bg-gray-400';
  return (
    <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
      <span className="shrink-0">AI 信心度</span>
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="shrink-0 font-medium">{pct}%</span>
    </div>
  );
}

function RecurrencePill({ count }: { count: number }) {
  if (count <= 1) return null;
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 border border-purple-200">
      <RotateCcw className="w-3 h-3" />
      {count} 份報告均異常
    </span>
  );
}

function StaleBadge({ sources }: { sources: LabAbnormality['evidenceSources'] }) {
  const hasStale = sources.some(s => s.recency === 'older');
  if (!hasStale) return null;
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-yellow-50 text-yellow-700 border border-yellow-200">
      <Clock className="w-3 h-3" />
      舊資料
    </span>
  );
}

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 animate-pulse space-y-3">
      <div className="h-4 bg-gray-200 rounded w-1/3" />
      <div className="h-3 bg-gray-100 rounded w-2/3" />
      <div className="h-3 bg-gray-100 rounded w-full" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Card for a single abnormality
// ---------------------------------------------------------------------------

function AbnormalityCard({ abn }: { abn: LabAbnormality }) {
  const [expanded, setExpanded] = useState(false);

  const typeBadge = TYPE_LABEL[abn.abnormalityType] ?? '指標';
  const valueStr =
    abn.currentValue !== null && abn.currentValue !== undefined
      ? `${abn.currentValue}${abn.referenceRange ? ` （參考範圍：${abn.referenceRange}）` : ''}`
      : abn.referenceRange ? `（參考範圍：${abn.referenceRange}）` : '';

  return (
    <div className={`rounded-xl border p-4 space-y-2 ${SEVERITY_CARD_BG[abn.severity] ?? 'border-gray-200 bg-white'}`}>
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <FlaskConical className="w-4 h-4 shrink-0 text-gray-500 mt-0.5" />
          <span className="font-semibold text-gray-800 text-sm">{abn.labItemName}</span>
          <span className="text-xs px-1.5 py-0.5 rounded bg-white/70 text-gray-500 border border-gray-200">
            {typeBadge}
          </span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${SEVERITY_BADGE[abn.severity] ?? ''}`}>
            {SEVERITY_LABEL[abn.severity] ?? abn.severity}
          </span>
          <RecurrencePill count={abn.recurrenceCount} />
          <StaleBadge sources={abn.evidenceSources} />
        </div>
        <button
          onClick={() => setExpanded(v => !v)}
          className="text-gray-400 hover:text-gray-600 transition-colors shrink-0 mt-0.5"
          aria-label={expanded ? '收起' : '展開詳情'}
        >
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Current value */}
      {valueStr && (
        <p className="text-xs text-gray-600 pl-6">{valueStr}</p>
      )}

      {/* Confidence */}
      <div className="pl-6">
        <ConfidenceBar value={abn.confidence} />
      </div>

      {/* Suggested action — always visible */}
      <div className="pl-6 flex items-start gap-1.5 text-sm text-gray-700 bg-white/60 rounded-lg p-2 border border-white/80">
        <Lightbulb className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
        <span>{abn.suggestedAction}</span>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="pl-6 space-y-3 pt-1">
          {/* Why detected */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">為何偵測到</p>
            <p className="text-xs text-gray-600 leading-relaxed">{abn.whyDetected}</p>
          </div>

          {/* Evidence sources */}
          {abn.evidenceSources.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                證據來源 ({abn.evidenceSources.length})
              </p>
              <ul className="space-y-1">
                {abn.evidenceSources.map((src, idx) => (
                  <li key={idx} className="flex items-start gap-1.5 text-xs text-gray-500">
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-gray-400 mt-1.5 shrink-0" />
                    <span>{src.summary || src.type}</span>
                    {src.recency && (
                      <span className="text-gray-400 shrink-0">· {src.recency}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

export default function LabInsightCard({ abnormalities, loading = false }: LabInsightCardProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Section header */}
      <div className="flex items-center gap-2">
        <FlaskConical className="w-5 h-5 text-indigo-600 shrink-0" />
        <h3 className="text-sm font-semibold text-gray-700">健檢異常指標分析</h3>
        {abnormalities.length > 0 && (
          <span className="text-xs font-medium px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200">
            {abnormalities.length} 項
          </span>
        )}
      </div>

      {/* Empty state */}
      {abnormalities.length === 0 && (
        <div className="rounded-xl border border-gray-100 bg-gray-50 p-6 text-center">
          <FlaskConical className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">目前無異常健檢指標</p>
          <p className="text-xs text-gray-400 mt-1">上傳健康報告後將自動分析</p>
        </div>
      )}

      {/* Abnormality cards */}
      {abnormalities.map((abn) => (
        <AbnormalityCard key={abn.rule_id} abn={abn} />
      ))}

      {/* Medical disclaimer */}
      {abnormalities.length > 0 && (
        <div className="flex items-start gap-1.5 rounded-lg bg-gray-50 border border-gray-100 p-3">
          <AlertTriangle className="w-3.5 h-3.5 text-gray-400 shrink-0 mt-0.5" />
          <p className="text-xs text-gray-400 leading-snug">
            以上分析由 AI 自動產生，僅供健康追蹤參考，不構成醫療診斷建議。
            如有健康疑慮，請諮詢醫療專業人員。
          </p>
        </div>
      )}
    </div>
  );
}
