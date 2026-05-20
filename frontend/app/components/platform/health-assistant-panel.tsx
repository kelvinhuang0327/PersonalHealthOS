'use client';

import Link from 'next/link';
import { AlertCircle, ArrowRight, CheckCircle2, Clock, FileText, Activity, Pill } from 'lucide-react';
import type { EvidenceSource, RecommendationTrust, DeviceSignal, EscalationDecision, SymptomPattern, LabAbnormality } from '../../../lib/api';
import { RecommendationTrustBlock } from './recommendation-trust-block';
import DeviceSignalCard from './device-signal-card';
import SymptomInsightCard from './symptom-insight-card';
import LabInsightCard from './lab-insight-card';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Recommendation {
  title: string;
  why_now: string;
  priority: 'high' | 'medium' | 'low';
  source_type: string;
  source_id?: string;
  expected_health_impact: string;
  evidence_sources: EvidenceSource[];
  next_action: string;
  is_tracking: boolean;
  tracking_action_id?: string;
  suppression_reason?: string;
  trust?: RecommendationTrust;
}

export interface HealthAssistantData {
  person_id: string;
  generated_at: string;
  recommendations: Recommendation[];
  missing_data: string[];
  device_signals?: DeviceSignal[];
  device_escalation?: EscalationDecision;
  symptom_patterns?: SymptomPattern[];
  lab_abnormalities?: LabAbnormality[];
  evidence_bundle_summary?: {
    symptom_count: number;
    metric_count: number;
    alert_count: number;
    insight_count: number;
    abnormal_lab_count: number;
    missing_data_count: number;
  };
}

interface HealthAssistantPanelProps {
  data: HealthAssistantData | null;
  loading?: boolean;
  onActionClick?: (rec: Recommendation) => void;
}

// ---------------------------------------------------------------------------
// Priority helpers
// ---------------------------------------------------------------------------

const PRIORITY_STYLE: Record<string, string> = {
  high: 'bg-red-50 text-red-700 border border-red-200',
  medium: 'bg-amber-50 text-amber-700 border border-amber-200',
  low: 'bg-blue-50 text-blue-700 border border-blue-200',
};

const PRIORITY_LABEL: Record<string, string> = {
  high: '高優先',
  medium: '中優先',
  low: '低優先',
};

// ---------------------------------------------------------------------------
// Missing data guidance
// ---------------------------------------------------------------------------

const MISSING_DATA_LINKS: Record<string, { href: string; label: string }> = {
  '症狀記錄': { href: '/platform/symptoms', label: '記錄症狀' },
  '健康指標（血壓、血糖、體重等）': { href: '/platform/quick-check-in', label: '填入健康指標' },
  '健檢報告（或無異常項目）': { href: '/platform/documents', label: '上傳健檢報告' },
  '個人健康檔案（性別、年齡等）': { href: '/platform/profile', label: '完善健康檔案' },
};

function getMissingDataLink(item: string) {
  return MISSING_DATA_LINKS[item] ?? { href: '/platform/profile', label: '補充資料' };
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function PriorityBadge({ priority }: { priority: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${PRIORITY_STYLE[priority] ?? PRIORITY_STYLE.low}`}>
      {PRIORITY_LABEL[priority] ?? priority}
    </span>
  );
}

function TrackingBadge() {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700 border border-green-200">
      <CheckCircle2 className="h-3 w-3" />
      追蹤中
    </span>
  );
}

function RecommendationCard({
  rec,
  index,
  onActionClick,
}: {
  rec: Recommendation;
  index: number;
  onActionClick?: (rec: Recommendation) => void;
}) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
            {index + 1}
          </span>
          <h4 className="text-sm font-semibold text-neutral-800 truncate">{rec.title}</h4>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {rec.is_tracking && <TrackingBadge />}
          <PriorityBadge priority={rec.priority} />
        </div>
      </div>

      {/* Why now */}
      <p className="mt-2 text-xs text-neutral-600 leading-relaxed">{rec.why_now}</p>

      {/* Expected impact */}
      {rec.expected_health_impact && (
        <p className="mt-1.5 text-xs text-emerald-700 font-medium">
          預期效果：{rec.expected_health_impact}
        </p>
      )}

      {/* Evidence sources */}
      {rec.evidence_sources.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {rec.evidence_sources.slice(0, 3).map((src, i) => (
            <span key={i} className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-neutral-100 rounded text-[11px] text-neutral-500">
              <FileText className="h-2.5 w-2.5" />
              {src.summary}
            </span>
          ))}
        </div>
      )}

      {/* Trust section */}
      {rec.trust && <RecommendationTrustBlock trust={rec.trust} />}

      {/* Action button */}
      <div className="mt-3 flex items-center justify-between">
        <span className="text-xs text-neutral-500">{rec.next_action}</span>
        {!rec.is_tracking && onActionClick && (
          <button
            onClick={() => onActionClick(rec)}
            className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-md transition-colors"
          >
            建立行動
            <ArrowRight className="h-3 w-3" />
          </button>
        )}
        {rec.is_tracking && (
          <Link
            href="/platform/actions"
            className="inline-flex items-center gap-1 px-3 py-1.5 bg-neutral-100 hover:bg-neutral-200 text-neutral-700 text-xs font-medium rounded-md transition-colors"
          >
            查看行動
            <ArrowRight className="h-3 w-3" />
          </Link>
        )}
      </div>
    </div>
  );
}

function EmptyState({ missingData }: { missingData: string[] }) {
  return (
    <div className="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 p-5">
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-neutral-700">需要更多資料才能提供個人化建議</p>
          <p className="mt-1 text-xs text-neutral-500">
            補充以下健康資料後，助理將為你生成針對性的健康建議：
          </p>
          <ul className="mt-3 space-y-2">
            {missingData.map((item) => {
              const link = getMissingDataLink(item);
              return (
                <li key={item} className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                  <span className="text-xs text-neutral-600">{item}</span>
                  <Link
                    href={link.href}
                    className="ml-auto text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-0.5"
                  >
                    {link.label}
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 animate-pulse">
      <div className="flex items-center gap-2">
        <div className="w-5 h-5 rounded-full bg-neutral-200" />
        <div className="h-4 w-48 bg-neutral-200 rounded" />
        <div className="ml-auto h-4 w-16 bg-neutral-200 rounded" />
      </div>
      <div className="mt-2 space-y-1.5">
        <div className="h-3 w-full bg-neutral-100 rounded" />
        <div className="h-3 w-3/4 bg-neutral-100 rounded" />
      </div>
      <div className="mt-3 flex justify-end">
        <div className="h-7 w-20 bg-neutral-200 rounded-md" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export default function HealthAssistantPanel({
  data,
  loading = false,
  onActionClick,
}: HealthAssistantPanelProps) {
  const hasRecs = data && data.recommendations.length > 0;
  const hasMissing = data && data.missing_data.length > 0 && !hasRecs;

  return (
    <section className="rounded-xl border border-blue-100 bg-gradient-to-b from-blue-50 to-white p-5 shadow-sm">
      {/* Panel header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-blue-600" />
          <h3 className="text-base font-semibold text-neutral-800">今日健康小助手</h3>
        </div>
        {data?.generated_at && (
          <div className="flex items-center gap-1 text-[11px] text-neutral-400">
            <Clock className="h-3 w-3" />
            {new Date(data.generated_at).toLocaleTimeString('zh-TW', {
              hour: '2-digit',
              minute: '2-digit',
            })} 更新
          </div>
        )}
      </div>

      {/* Loading skeletons */}
      {loading && (
        <div className="space-y-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {/* Recommendations */}
      {!loading && hasRecs && (
        <div className="space-y-3">
          {data.recommendations.map((rec, i) => (
            <RecommendationCard
              key={rec.source_id ?? `rec-${i}`}
              rec={rec}
              index={i}
              onActionClick={onActionClick}
            />
          ))}
        </div>
      )}

      {/* Device signal section */}
      {!loading && data && (
        <div className="mt-4">
          <DeviceSignalCard signals={data.device_signals ?? []} escalation={data.device_escalation} />
        </div>
      )}

      {/* Symptom intelligence section */}
      {!loading && data && (
        <div className="mt-4">
          <SymptomInsightCard patterns={data.symptom_patterns ?? []} />
        </div>
      )}

      {/* Lab insight section (P4 Report-to-Action Bridge) */}
      {!loading && data && (
        <div className="mt-4">
          <LabInsightCard abnormalities={data.lab_abnormalities ?? []} />
        </div>
      )}

      {/* Missing data empty state */}
      {!loading && !hasRecs && hasMissing && (
        <EmptyState missingData={data.missing_data} />
      )}

      {/* No data at all */}
      {!loading && !data && (
        <div className="flex items-center gap-2 text-sm text-neutral-500 py-4 justify-center">
          <Pill className="h-4 w-4" />
          <span>無法載入健康建議，請稍後再試</span>
        </div>
      )}

      {/* Footer links */}
      {!loading && (
        <div className="mt-4 pt-3 border-t border-neutral-100 flex flex-wrap gap-3">
          <Link href="/platform/actions" className="text-xs text-blue-600 hover:text-blue-700 font-medium">
            全部行動 →
          </Link>
          <Link href="/platform/symptoms" className="text-xs text-neutral-500 hover:text-neutral-700">
            記錄症狀
          </Link>
          <Link href="/platform/documents" className="text-xs text-neutral-500 hover:text-neutral-700">
            上傳報告
          </Link>
          <Link href="/platform/quick-check-in" className="text-xs text-neutral-500 hover:text-neutral-700">
            填入健康指標
          </Link>
        </div>
      )}
    </section>
  );
}
