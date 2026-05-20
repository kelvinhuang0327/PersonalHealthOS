'use client';

import { Activity, AlertTriangle, CheckCircle, Clock, Info, TrendingUp, Zap } from 'lucide-react';
import type { DeviceSignal, EscalationDecision } from '../../../lib/api';

// ---------------------------------------------------------------------------
// Severity helpers
// ---------------------------------------------------------------------------

const SEVERITY_STYLE: Record<string, string> = {
  high:   'bg-red-50 text-red-700 border border-red-200',
  medium: 'bg-amber-50 text-amber-700 border border-amber-200',
  low:    'bg-blue-50 text-blue-700 border border-blue-200',
};

const SEVERITY_LABEL: Record<string, string> = {
  high:   '高風險',
  medium: '需注意',
  low:    '低風險',
};

const SEVERITY_ICON: Record<string, React.ReactNode> = {
  high:   <AlertTriangle className="h-3.5 w-3.5" />,
  medium: <Zap          className="h-3.5 w-3.5" />,
  low:    <CheckCircle  className="h-3.5 w-3.5" />,
};

const SIGNAL_LABEL: Record<string, string> = {
  elevated_resting_heart_rate: '靜息心率偏高',
  abnormal_pulse_trend:        '心率趨勢異常',
  low_sleep_duration:          '睡眠時間不足',
  reduced_activity:            '活動量不足',
  unstable_spo2:               '血氧不穩定',
};

const METRIC_UNIT: Record<string, string> = {
  heart_rate:  ' bpm',
  sleep_hours: ' 小時',
  steps:       ' 步',
  spo2:        '%',
};

// ---------------------------------------------------------------------------
// Escalation helpers
// ---------------------------------------------------------------------------

const ESC_BANNER_STYLE: Record<string, string> = {
  urgent:  'bg-red-50 border border-red-200 text-red-800',
  warning: 'bg-amber-50 border border-amber-200 text-amber-800',
  watch:   'bg-blue-50 border border-blue-200 text-blue-800',
  none:    '',
};

const ESC_LABEL: Record<string, string> = {
  urgent:  '緊急警示',
  warning: '健康警示',
  watch:   '持續觀察',
  none:    '',
};

const ESC_ICON: Record<string, React.ReactNode> = {
  urgent:  <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />,
  warning: <TrendingUp    className="h-3.5 w-3.5 flex-shrink-0" />,
  watch:   <Info          className="h-3.5 w-3.5 flex-shrink-0" />,
  none:    null,
};

function freshnessLabel(freshness: string): string {
  if (freshness === 'fresh') return '最新數據';
  if (freshness === 'stale') return '數據略舊';
  return '未知時效';
}

// ---------------------------------------------------------------------------
// Escalation banner
// ---------------------------------------------------------------------------

function EscalationBanner({ escalation }: { escalation: EscalationDecision }) {
  const level = escalation.escalationLevel;
  if (level === 'none') return null;

  const bannerStyle = ESC_BANNER_STYLE[level] ?? ESC_BANNER_STYLE.watch;
  const label       = ESC_LABEL[level] ?? level;
  const icon        = ESC_ICON[level];
  const topReason   = escalation.reasons[0] ?? null;

  return (
    <div className={`rounded-lg px-3 py-2 mb-3 text-xs ${bannerStyle}`}>
      <div className="flex items-center gap-1.5 font-semibold mb-0.5">
        {icon}
        {label}
        {escalation.confidence < 0.65 && (
          <span className="ml-auto text-[10px] font-normal opacity-70">
            可信度 {Math.round(escalation.confidence * 100)}%（偏低）
          </span>
        )}
      </div>
      {topReason && (
        <p className="leading-relaxed opacity-90">{topReason}</p>
      )}
      {escalation.requiresFollowUp && (
        <p className="mt-1 font-medium">
          建議：{escalation.recommendedAction ?? '請諮詢醫師評估'}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Single signal row
// ---------------------------------------------------------------------------

function SignalRow({ signal }: { signal: DeviceSignal }) {
  const sev = signal.severity ?? 'low';
  const label = SIGNAL_LABEL[signal.signal_type] ?? signal.signal_type.replace(/_/g, ' ');
  const unit  = METRIC_UNIT[signal.metric_type] ?? '';
  const displayValue =
    signal.current_value != null
      ? `${signal.current_value.toLocaleString()}${unit}`
      : null;

  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-neutral-100 last:border-0">
      {/* Severity badge */}
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium flex-shrink-0 mt-0.5 ${SEVERITY_STYLE[sev] ?? SEVERITY_STYLE.low}`}
      >
        {SEVERITY_ICON[sev]}
        {SEVERITY_LABEL[sev] ?? sev}
      </span>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-neutral-800">{label}</span>
          {displayValue && (
            <span className="text-xs text-neutral-500 font-mono flex-shrink-0">
              {displayValue}
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-neutral-500 leading-relaxed line-clamp-2">
          {signal.why_detected}
        </p>
        {signal.suggested_action && (
          <p className="mt-1 text-xs text-emerald-700 font-medium">
            建議：{signal.suggested_action}
          </p>
        )}
        {/* Freshness + confidence footer */}
        <div className="mt-1.5 flex items-center gap-3 text-[10px] text-neutral-400">
          <span className="flex items-center gap-0.5">
            <Clock className="h-2.5 w-2.5" />
            {freshnessLabel(signal.freshness)}
          </span>
          <span>可信度 {Math.round(signal.confidence * 100)}%</span>
          {signal.freshness === 'stale' && (
            <span className="text-amber-500">資料略舊，分析精度受限</span>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state (no device data)
// ---------------------------------------------------------------------------

function NoDeviceData() {
  return (
    <div className="py-3 text-center">
      <p className="text-xs text-neutral-400">
        尚無裝置健康訊號。連結穿戴裝置後將自動顯示。
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Medical disclaimer
// ---------------------------------------------------------------------------

function MedicalDisclaimer() {
  return (
    <p className="mt-3 pt-2.5 border-t border-neutral-100 text-[10px] text-neutral-400 leading-relaxed">
      本系統提供健康資料參考，不構成醫療診斷或醫療建議。如有疑慮，請諮詢專業醫師。
    </p>
  );
}

// ---------------------------------------------------------------------------
// Public component
// ---------------------------------------------------------------------------

interface DeviceSignalCardProps {
  signals: DeviceSignal[];
  escalation?: EscalationDecision;
  loading?: boolean;
}

export default function DeviceSignalCard({
  signals,
  escalation,
  loading = false,
}: DeviceSignalCardProps) {
  const highCount = signals.filter((s) => s.severity === 'high').length;
  const hasEscalation =
    escalation && escalation.escalationLevel !== 'none';

  return (
    <section className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-indigo-600" />
          <h3 className="text-sm font-semibold text-neutral-800">裝置健康訊號</h3>
          {signals.length > 0 && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-100">
              {signals.length}
            </span>
          )}
        </div>
        {highCount > 0 && !hasEscalation && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-red-50 text-red-700 border border-red-200">
            <AlertTriangle className="h-3 w-3" />
            {highCount} 項高風險
          </span>
        )}
      </div>

      {/* Escalation banner */}
      {!loading && hasEscalation && escalation && (
        <EscalationBanner escalation={escalation} />
      )}

      {/* Body */}
      {loading ? (
        <div className="space-y-2 animate-pulse">
          <div className="h-10 bg-neutral-100 rounded" />
          <div className="h-10 bg-neutral-100 rounded" />
        </div>
      ) : signals.length === 0 ? (
        <NoDeviceData />
      ) : (
        <div>
          {signals.map((sig, i) => (
            <SignalRow key={`${sig.signal_type}-${i}`} signal={sig} />
          ))}
        </div>
      )}

      {/* Medical disclaimer (shown when there is anything to show) */}
      {!loading && (signals.length > 0 || hasEscalation) && <MedicalDisclaimer />}
    </section>
  );
}

