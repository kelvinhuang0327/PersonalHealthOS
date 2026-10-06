'use client';

import React, { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import type {
  AdaptivePolicy,
  BacklogItem,
  BacklogLevel,
  CtoProviders,
  CtoReviewRun,
  CtoRunDetail,
  CtoSummary,
  ExecutionPolicy,
  OrcRun,
  PolicyMode,
  PrioritizedBacklog,
  RunIntent,
  TaskReview,
} from '../../../../lib/orchestrator-api';
import { ctoApi } from '../../../../lib/orchestrator-api';

type HealthBarProps = Readonly<{ score: number }>;
type CtoRunDetailViewProps = Readonly<{
  detail: CtoRunDetail;
  addedBatchSet: Set<string>;
  addedSingleSet: Set<string>;
  onBack: () => void;
  onAddSingle: (r: TaskReview) => void;
  onAddBatch: (runId: string) => void;
  onRescore: () => void;
}>;
type BacklogItemRowProps = Readonly<{ item: BacklogItem }>;
type PrioritizedBacklogPanelProps = Readonly<{ backlog: PrioritizedBacklog; onRescore: () => void; onApplyAging: () => void }>;
type AdaptivePolicyPanelProps = Readonly<{ policy: AdaptivePolicy; onRefresh: () => void }>;
type ExecutionPolicyPanelProps = Readonly<{ policy: ExecutionPolicy; onSetMode: (mode: PolicyMode) => void; onApplyAging: () => void }>;

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtTs(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-TW', { hour12: false });
  } catch {
    return iso;
  }
}

function fmtDur(s: number | null | undefined): string {
  if (s == null) return '—';
  if (s < 1) return '< 1s';
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

function countdown(isoTarget: string | null | undefined): string {
  if (!isoTarget) return '—';
  try {
    const diff = Math.round((new Date(isoTarget).getTime() - Date.now()) / 1000);
    if (diff <= 0) return '即將執行';
    const m = Math.floor(diff / 60);
    const s = diff % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  } catch {
    return '—';
  }
}

function severityColor(sev: string): string {
  return { CRITICAL: '#f85149', HIGH: '#d29922', MEDIUM: '#3fb950', LOW: '#8b949e' }[sev] ?? '#8b949e';
}

function verdictBadge(v: string | null | undefined) {
  if (!v) return null;
  const colors: Record<string, string> = {
    GO: 'bg-green-700 text-green-100',
    CAUTION: 'bg-yellow-700 text-yellow-100',
    STOP: 'bg-red-700 text-red-100',
  };
  const icons: Record<string, string> = { GO: '✅', CAUTION: '⚠️', STOP: '🛑' };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold ${colors[v] ?? 'bg-zinc-700'}`}>
      {icons[v] ?? ''} {v}
    </span>
  );
}

function decisionBadge(d: string) {
  const cls: Record<string, string> = {
    PASS: 'bg-green-900 text-green-300',
    NEEDS_REPLAN: 'bg-red-900 text-red-300',
    DEFERRED: 'bg-yellow-900 text-yellow-300',
    CLOSED: 'bg-zinc-700 text-zinc-400',
  };
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-mono ${cls[d] ?? 'bg-zinc-700 text-zinc-300'}`}>
      {d}
    </span>
  );
}

function backlogLevelBadge(lvl: BacklogLevel) {
  const cls: Record<string, string> = {
    P0: 'bg-red-800 text-red-200 font-bold',
    P1: 'bg-orange-800 text-orange-200 font-bold',
    P2: 'bg-yellow-800 text-yellow-200',
    P3: 'bg-zinc-700 text-zinc-300',
  };
  return <span className={`px-1.5 py-0.5 rounded text-xs ${cls[lvl] ?? 'bg-zinc-700'}`}>{lvl}</span>;
}

function outcomeCls(o: string): string {
  if (!o) return '';
  const lo = o.toLowerCase();
  if (lo.includes('error') || lo.includes('fail')) return 'text-red-400';
  if (lo.includes('skip') || lo.includes('rate') || lo.includes('timeout')) return 'text-yellow-400';
  if (lo.includes('complet') || lo === 'pass' || lo === 'completed') return 'text-green-400';
  return 'text-zinc-400';
}

function HealthBar({ score }: HealthBarProps) {
  const filled = Math.round((score / 100) * 10);
  return (
    <span className="font-mono text-sm">
      <span className="text-green-400">{'█'.repeat(filled)}</span>
      <span className="text-zinc-600">{'░'.repeat(10 - filled)}</span>
      <span className="ml-2 text-zinc-300">{score}/100</span>
    </span>
  );
}

async function waitForOutcome(
  poller: (reqId: string) => Promise<{ status: string; run: OrcRun | null; final: boolean }>,
  requestId: string,
  onUpdate: (status: string, msg: string) => void,
  timeoutMs = 70000,
  intervalMs = 3000,
) {
  const deadline = Date.now() + timeoutMs;
  const poll = async (): Promise<void> => {
    try {
      const data = await poller(requestId);
      const outcome = data.run?.outcome ?? data.status ?? '…';
      const msg = data.run?.message ?? '等待中…';
      onUpdate(outcome, msg);
      if (data.final) return;
      if (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, intervalMs));
        return poll();
      } else {
        onUpdate('TIMEOUT', '超時未收到結果，請手動刷新');
      }
    } catch {
      onUpdate('ERROR', '輪詢失敗');
    }
  };
  await poll();
}

// ── CTO Run Detail View ───────────────────────────────────────────────────────

function CtoRunDetailView({
  detail,
  addedBatchSet,
  addedSingleSet,
  onBack,
  onAddSingle,
  onAddBatch,
  onRescore,
}: CtoRunDetailViewProps) {
  const { run, reviews, intelligence } = detail;
  const [showReport, setShowReport] = useState(false);
  const [showTimeline, setShowTimeline] = useState(false);
  const batchAdded = addedBatchSet.has(run.run_id);
  const passCount = reviews.filter((r) => r.decision === 'PASS').length;
  const replanCount = reviews.filter((r) => r.decision === 'NEEDS_REPLAN').length;
  const deferredCount = reviews.filter((r) => r.decision === 'DEFERRED').length;

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-5">
      <div className="flex items-center justify-between">
        <button onClick={onBack} className="text-xs text-blue-400 hover:underline">← 返回列表</button>
        <span className="text-xs text-zinc-500 font-mono">{run.run_id}</span>
      </div>

      {/* Run metadata */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
        <div><span className="text-zinc-500">開始：</span>{fmtTs(run.started_at)}</div>
        <div><span className="text-zinc-500">完成：</span>{fmtTs(run.completed_at)}</div>
        <div><span className="text-zinc-500">耗時：</span>{fmtDur(run.duration_seconds)}</div>
        <div>
          <span className="text-zinc-500">頻率：</span>{run.frequency_mode}
          {run.run_intent && <span className="ml-2 text-purple-400">[{run.run_intent}]</span>}
        </div>
        <div><span className="text-zinc-500">強制：</span>{run.is_force_run ? '是' : '否'}</div>
        <div><span className="text-zinc-500">手動：</span>{run.is_manual ? '是' : '否'}</div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 text-xs text-center">
        {[
          { label: '候選', value: run.candidate_count, cls: '' },
          { label: '通過', value: passCount, cls: 'text-green-400' },
          { label: '需重規', value: replanCount, cls: 'text-red-400' },
          { label: '延後', value: deferredCount, cls: 'text-yellow-400' },
        ].map((s) => (
          <div key={s.label} className="bg-zinc-800 rounded p-3">
            <div className="text-zinc-500 mb-1">{s.label}</div>
            <div className={`text-xl font-bold ${s.cls}`}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Intelligence Panel */}
      {intelligence.health_score != null && (
        <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-4 space-y-3">
          <div className="font-semibold text-sm">🧠 CTO 智慧分析</div>
          <div className="flex items-center gap-4">
            {verdictBadge(intelligence.verdict)}
            <HealthBar score={intelligence.health_score} />
          </div>
          {intelligence.top_risks && intelligence.top_risks.length > 0 && (
            <div>
              <div className="text-xs text-zinc-500 mb-2">⚠️ 主要風險</div>
              {intelligence.top_risks.map((risk) => (
                <div key={`${risk.task_id}-${risk.severity}`} className="text-xs mb-1.5">
                  <span style={{ color: severityColor(risk.severity) }} className="font-bold">[{risk.severity}]</span>
                  {' '}Task #{risk.task_id} — {risk.description}
                  <span className="ml-2 text-zinc-500">impact: {risk.impact}/100, urgency: {risk.urgency}</span>
                </div>
              ))}
            </div>
          )}
          {intelligence.top_actions && intelligence.top_actions.length > 0 && (
            <div>
              <div className="text-xs text-zinc-500 mb-2">🎯 主要行動</div>
              {intelligence.top_actions.map((action) => (
                <div key={`${action.priority}-${action.action}`} className="text-xs mb-1.5">
                  <span className={`font-bold ${action.priority === 'P0' ? 'text-red-400' : 'text-yellow-400'}`}>[{action.priority}]</span>
                  {' '}{action.action}
                  {action.create_task && <span className="ml-2 text-blue-400 text-[10px]">[create_task]</span>}
                  <div className="text-zinc-500 pl-4">{action.expected_benefit}</div>
                </div>
              ))}
            </div>
          )}
          {intelligence.roadmap && intelligence.roadmap.length > 0 && (
            <div>
              <div className="text-xs text-zinc-500 mb-1">📍 路線圖</div>
              {intelligence.roadmap.map((item) => (
                <div key={item} className="text-xs text-zinc-400 pl-2">• {item}</div>
              ))}
            </div>
          )}
          <div className="flex gap-3 pt-2">
            {batchAdded ? (
              <span className="text-xs text-green-400">✓ 已全部入 backlog</span>
            ) : (
              <button
                onClick={() => onAddBatch(run.run_id)}
                className="text-xs bg-blue-800 hover:bg-blue-700 text-white px-3 py-1 rounded"
              >
                加入全部高優先 backlog
              </button>
            )}
            <button onClick={onRescore} className="text-xs bg-zinc-700 hover:bg-zinc-600 px-3 py-1 rounded">
              重新計分
            </button>
          </div>
        </div>
      )}

      {/* Decision Timeline */}
      <div>
        <button onClick={() => setShowTimeline(!showTimeline)} className="text-sm text-blue-400 hover:underline">
          {showTimeline ? '▾' : '▸'} 決策時間軸（{reviews.length} 筆）
        </button>
        {showTimeline && (
          <div className="mt-3 space-y-2">
            {reviews.map((rev) => {
              const singleAdded = addedSingleSet.has(String(rev.id));
              return (
                <div key={rev.id} className="bg-zinc-800 rounded p-3 text-xs space-y-1.5">
                  <div className="flex items-center gap-3 flex-wrap">
                    {decisionBadge(rev.decision)}
                    <span style={{ color: severityColor(rev.severity) }} className="font-bold text-[10px]">{rev.severity}</span>
                    <span className="text-zinc-500">Task #{rev.task_id}</span>
                    <span className="text-zinc-500">— {rev.category}</span>
                    <span className="text-zinc-500">impact: {rev.impact_score}/100</span>
                  </div>
                  <div className="text-zinc-300">{rev.reason}</div>
                  <div className="text-zinc-500">建議：{rev.suggested_action}</div>
                  {rev.decision !== 'PASS' && (
                    singleAdded ? (
                      <span className="text-green-400 text-[10px]">✓ 已入 backlog</span>
                    ) : (
                      <button
                        onClick={() => onAddSingle(rev)}
                        className="text-[10px] bg-blue-900 hover:bg-blue-800 text-blue-300 px-2 py-0.5 rounded"
                      >
                        ＋ 加入 backlog
                      </button>
                    )
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Report JSON */}
      <button onClick={() => setShowReport(!showReport)} className="text-sm text-blue-400 hover:underline">
        {showReport ? '▾' : '▸'} 報告 JSON
      </button>
      {showReport && (
        <pre className="bg-zinc-800 rounded p-3 text-xs font-mono overflow-auto max-h-96">
          {JSON.stringify(intelligence, null, 2)}
        </pre>
      )}
    </div>
  );
}

// ── Backlog Components ────────────────────────────────────────────────────────

function BacklogItemRow({ item }: BacklogItemRowProps) {
  const pct = Math.round(Math.min(100, item.priority_score));
  return (
    <div className="bg-zinc-800 rounded p-2.5 text-xs">
      <div className="flex items-center gap-2 mb-1">
        {backlogLevelBadge(item.priority_level)}
        <span style={{ color: severityColor(item.severity) }} className="text-[10px] font-bold">{item.severity}</span>
        <span className="text-zinc-400 truncate">{item.suggested_action}</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1 bg-zinc-700 rounded-full h-1">
          <div className="bg-blue-500 h-1 rounded-full" style={{ width: `${pct}%` }} />
        </div>
        <span className="text-zinc-500 font-mono w-12 text-right">{item.priority_score.toFixed(0)}</span>
        <span className="text-zinc-600">⟳{item.selection_count}</span>
      </div>
    </div>
  );
}

function PrioritizedBacklogPanel({
  backlog, onRescore, onApplyAging,
}: PrioritizedBacklogPanelProps) {
  const [showP2P3, setShowP2P3] = useState(false);
  const highPriority = [...(backlog.by_level.P0 ?? []), ...(backlog.by_level.P1 ?? [])];
  const lowPriority = [...(backlog.by_level.P2 ?? []), ...(backlog.by_level.P3 ?? [])];

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-lg">📋 優先 Backlog</h2>
        <div className="flex gap-2">
          <button onClick={onRescore} className="text-xs bg-zinc-700 hover:bg-zinc-600 px-3 py-1 rounded">重新計分</button>
          <button onClick={onApplyAging} className="text-xs bg-zinc-700 hover:bg-zinc-600 px-3 py-1 rounded">Aging 觸發</button>
        </div>
      </div>
      <div className="flex gap-3 text-xs">
        {(['P0', 'P1', 'P2', 'P3'] as BacklogLevel[]).map((lvl) => (
          <span key={lvl}>{backlogLevelBadge(lvl)} {backlog.counts[lvl] ?? 0}</span>
        ))}
        <span className="text-zinc-500">/ 共 {backlog.total}</span>
      </div>
      {highPriority.length > 0 && (
        <div className="space-y-2">
          {highPriority.map((item) => <BacklogItemRow key={item.id} item={item} />)}
        </div>
      )}
      {lowPriority.length > 0 && (
        <>
          <button onClick={() => setShowP2P3(!showP2P3)} className="text-xs text-blue-400 hover:underline">
            {showP2P3 ? '▾' : '▸'} P2/P3 ({lowPriority.length} 筆)
          </button>
          {showP2P3 && (
            <div className="space-y-2">
              {lowPriority.map((item) => <BacklogItemRow key={item.id} item={item} />)}
            </div>
          )}
        </>
      )}
      {backlog.total === 0 && <div className="text-xs text-zinc-600 text-center py-4">Backlog 為空</div>}
    </div>
  );
}

function AdaptivePolicyPanel({ policy, onRefresh }: AdaptivePolicyPanelProps) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-lg">🔀 Adaptive Policy</h2>
        <button onClick={onRefresh} className="text-xs bg-zinc-700 hover:bg-zinc-600 px-3 py-1 rounded">刷新</button>
      </div>
      <div className="space-y-2">
        {Object.entries(policy.intent_merge_rates).map(([intent, rate]) => (
          <div key={intent} className="flex items-center gap-3 text-xs">
            <span className="w-20 text-zinc-400">{intent}</span>
            <div className="flex-1 bg-zinc-700 rounded-full h-2">
              <div className="bg-purple-500 h-2 rounded-full" style={{ width: `${Math.round(rate * 100)}%` }} />
            </div>
            <span className="text-zinc-400 font-mono w-12 text-right">{Math.round(rate * 100)}%</span>
          </div>
        ))}
      </div>
      <div className="text-xs text-zinc-500">
        retry coverage limit: {policy.policy_adjustments.retry_coverage_limit}
      </div>
    </div>
  );
}

function ExecutionPolicyPanel({
  policy, onSetMode, onApplyAging,
}: ExecutionPolicyPanelProps) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-3">
      <h2 className="font-semibold text-lg">⚖️ 執行政策</h2>
      <div className="flex items-center gap-4 flex-wrap">
        <div className="text-xs text-zinc-500">模式：</div>
        {(['balanced', 'strict_priority', 'fairness'] as PolicyMode[]).map((m) => (
          <button
            key={m}
            onClick={() => onSetMode(m)}
            className={`px-3 py-1 rounded text-xs ${
              policy.mode === m ? 'bg-blue-700 text-white' : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
            }`}
          >
            {m}
          </button>
        ))}
        <button onClick={onApplyAging} className="px-3 py-1 rounded text-xs bg-zinc-700 hover:bg-zinc-600">
          Aging 觸發
        </button>
      </div>
      <div className="text-xs text-zinc-500">
        consecutive_high: {policy.consecutive_high}
        {policy.consecutive_category && (
          <span className="ml-4">consecutive_category: {policy.consecutive_category} ({policy.consecutive_category_count})</span>
        )}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CtoReviewPage() {
  const [ctoSummary, setCtoSummary] = useState<CtoSummary | null>(null);
  const [ctoRuns, setCtoRuns] = useState<CtoReviewRun[]>([]);
  const [ctoRunDetail, setCtoRunDetail] = useState<CtoRunDetail | null>(null);
  const [ctoSelectedRun, setCtoSelectedRun] = useState<string | null>(null);
  const [ctoTrace, setCtoTrace] = useState<{ requestId: string; outcome: string; note: string } | null>(null);
  const [ctoForce, setCtoForce] = useState(false);
  const [ctoIntent, setCtoIntent] = useState<RunIntent>('retry');
  const [adaptivePolicy, setAdaptivePolicy] = useState<AdaptivePolicy | null>(null);
  const [execPolicy, setExecPolicy] = useState<ExecutionPolicy | null>(null);
  const [ctoProviders, setCtoProviders] = useState<CtoProviders | null>(null);
  const [ctoPlannerProvider, setCtoPlannerProvider] = useState('codex');
  const [ctoPlannerModel, setCtoPlannerModel] = useState('');
  const [ctoProviderHint, setCtoProviderHint] = useState('');
  const [prioritizedBacklog, setPrioritizedBacklog] = useState<PrioritizedBacklog | null>(null);
  const [addedBatchSet, setAddedBatchSet] = useState<Set<string>>(new Set());
  const [addedSingleSet, setAddedSingleSet] = useState<Set<string>>(new Set());
  const [schedulerSaving, setSchedulerSaving] = useState<'enable' | 'disable' | null>(null);
  const [tick, setTick] = useState(0);
  // tick is used to force re-render for countdown

  // 1-second countdown tick
  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const loadAll = useCallback(async () => {
    try {
      const [sum, runsResp, provResp, adaptResp, execResp, prioResp] = await Promise.all([
        ctoApi.getSummary(),
        ctoApi.getRuns({ limit: 20 }),
        ctoApi.getProviders(),
        ctoApi.getAdaptivePolicy(),
        ctoApi.getBacklogPolicy(),
        ctoApi.getPrioritizedBacklog(),
      ]);
      setCtoSummary(sum);
      setCtoRuns(runsResp.items ?? []);
      setCtoProviders(provResp);
      setCtoPlannerProvider(provResp.planner_provider);
      setCtoPlannerModel(provResp.planner_model ?? '');
      setAdaptivePolicy(adaptResp);
      setExecPolicy(execResp);
      setPrioritizedBacklog(prioResp);
      setCtoProviderHint(`目前：${provResp.planner_provider_label}`);
    } catch { /* ignore */ }
  }, []);

  const loadRunDetail = useCallback(async (runId: string) => {
    try {
      const data = await ctoApi.getRunDetail(runId);
      setCtoRunDetail(data);
      setCtoSelectedRun(runId);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  // Auto-refresh every 30s
  useEffect(() => {
    const t = setInterval(() => ctoApi.getSummary().then(setCtoSummary).catch(() => {}), 30_000);
    return () => clearInterval(t);
  }, []);

  // ── Actions ───────────────────────────────────────────────────────────────

  const handleEnable = async () => {
    setSchedulerSaving('enable');
    try {
      await ctoApi.setScheduler(true);
      await loadAll();
    } catch (e: unknown) {
      alert(`啟用失敗：${(e as Error).message}`);
    } finally {
      setSchedulerSaving(null);
    }
  };

  const handleDisable = async () => {
    setSchedulerSaving('disable');
    try {
      await ctoApi.setScheduler(false);
      await loadAll();
    } catch (e: unknown) {
      alert(`停止失敗：${(e as Error).message}`);
    } finally {
      setSchedulerSaving(null);
    }
  };

  const handleCtoRunNow = async () => {
    try {
      const data = await ctoApi.runNow({
        force: ctoForce,
        run_intent: ctoForce ? ctoIntent : undefined,
      });
      setCtoTrace({ requestId: data.request_id, outcome: '等待中…', note: '已觸發 CTO Planner…' });
      await waitForOutcome(
        (rid) => ctoApi.getRunStatus(rid),
        data.request_id,
        (outcome, note) => setCtoTrace({ requestId: data.request_id, outcome, note }),
        70000,
        3000,
      );
      setCtoForce(false);
      await loadAll();
    } catch (e: unknown) {
      const err = e as { status?: number; message?: string };
      const msg = err.status === 429 ? `Rate limit：${err.message}` : `觸發失敗：${err.message}`;
      setCtoTrace({ requestId: '—', outcome: err.status === 429 ? 'RATE_LIMITED' : 'ERROR', note: msg });
    }
  };

  const handleSaveProviders = async () => {
    try {
      const data = await ctoApi.setProviders({
        planner_provider: ctoPlannerProvider,
        planner_model: ctoPlannerModel || undefined,
      });
      setCtoProviderHint(`已套用：${data.planner_provider_label}`);
      setTimeout(() => loadAll(), 200);
    } catch (e: unknown) {
      setCtoProviderHint(`儲存失敗：${(e as Error).message}`);
    }
  };

  const handleAddBacklogSingle = async (review: TaskReview) => {
    try {
      await ctoApi.addBacklogItem({
        cto_run_id: review.cto_run_id,
        task_id: review.task_id,
        category: review.category,
        severity: review.severity,
        impact_score: review.impact_score,
        urgency: review.urgency,
        suggested_action: review.suggested_action,
      });
      setAddedSingleSet((s) => new Set([...s, String(review.id)]));
      ctoApi.getPrioritizedBacklog().then(setPrioritizedBacklog);
    } catch { /* ignore */ }
  };

  const handleAddBatchBacklog = async (runId: string) => {
    try {
      await ctoApi.batchAddBacklog({ cto_run_id: runId, min_severity: 'HIGH', min_impact: 60 });
      setAddedBatchSet((s) => new Set([...s, runId]));
      ctoApi.getPrioritizedBacklog().then(setPrioritizedBacklog);
    } catch { /* ignore */ }
  };

  const handleRescore = async () => {
    await ctoApi.rescoreBacklog();
    ctoApi.getPrioritizedBacklog().then(setPrioritizedBacklog);
  };

  const handleSetPolicyMode = async (mode: PolicyMode) => {
    const data = await ctoApi.setBacklogPolicy(mode);
    setExecPolicy(data);
  };

  // ── CTO scheduler state — NOTE: shares enabled flag with main scheduler ──
  // A CTO-specific scheduled_at may come from ctoSummary.next_run_at
  const schedulerActive = ctoSummary?.next_run_at != null;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200 px-4 py-6">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">🧠 CTO 審核系統</h1>
            <p className="text-xs text-zinc-500 mt-1">任務品質審核、決策分析、Backlog 管理</p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/platform/cockpit/orchestration"
              className="px-3 py-1.5 rounded text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors"
            >
              🤖 任務排程 →
            </Link>
            <Link
              href="/platform/cockpit"
              className="px-3 py-1.5 rounded text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-500 transition-colors"
            >
              ← 駕駛艙
            </Link>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: '待處理', value: ctoSummary?.pending_count ?? '…' },
            { label: '通過', value: ctoSummary?.approved_count ?? '…' },
            { label: '延後', value: ctoSummary?.deferred_count ?? '…' },
            {
              label: 'Health Score',
              value: ctoSummary?.health_score == null
                ? '—'
                : <span className="text-green-400">{ctoSummary.health_score}/100</span>,
            },
          ].map((s) => (
            <div key={s.label} className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
              <div className="text-xs text-zinc-500 mb-1">{s.label}</div>
              <div className="text-2xl font-bold">{s.value}</div>
            </div>
          ))}
        </div>

        {/* ── CTO Scheduler Control ──────────────────────────────────────── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-4">
          <h2 className="font-semibold text-lg">🗓 CTO 排程控制</h2>

          {/* Status + Enable / Stop buttons */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
              schedulerActive
                ? 'bg-green-900/50 text-green-300 border border-green-700'
                : 'bg-yellow-900/40 text-yellow-300 border border-yellow-700'
            }`}>
              <span className={`w-2 h-2 rounded-full ${schedulerActive ? 'bg-green-400 animate-pulse' : 'bg-yellow-400'}`} />
              {schedulerActive ? 'CTO 排程啟用中' : 'CTO 排程已暫停'}
            </div>

            <button
              onClick={handleEnable}
              disabled={schedulerSaving !== null || schedulerActive}
              className="px-4 py-1.5 rounded text-sm font-medium bg-green-700 hover:bg-green-600 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {schedulerSaving === 'enable' ? '啟用中…' : '▶ 啟用排程'}
            </button>

            <button
              onClick={handleDisable}
              disabled={schedulerSaving !== null || !schedulerActive}
              className="px-4 py-1.5 rounded text-sm font-medium bg-red-800 hover:bg-red-700 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {schedulerSaving === 'disable' ? '停止中…' : '⏹ 停止排程'}
            </button>
          </div>

          {/* Timing info */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="text-xs text-zinc-500 mb-1">頻率模式</div>
              <div className="font-medium text-zinc-300">{ctoSummary?.frequency_mode ?? '—'}</div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="text-xs text-zinc-500 mb-1">下次 CTO 執行</div>
              <div className="font-mono text-lg font-bold text-purple-300">
                {tick > -1 && schedulerActive ? countdown(ctoSummary?.next_run_at) : '—'}
              </div>
              <div className="text-xs text-zinc-500 mt-1">{fmtTs(ctoSummary?.next_run_at)}</div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="text-xs text-zinc-500 mb-1">上次執行</div>
              <div className="text-zinc-300 text-sm">{fmtTs(ctoSummary?.latest_run_at)}</div>
            </div>
          </div>

          {/* Summary + Verdict */}
          {ctoSummary?.verdict && (
            <div className="flex items-center gap-4 flex-wrap pt-1">
              {verdictBadge(ctoSummary.verdict)}
              {ctoSummary.health_score != null && <HealthBar score={ctoSummary.health_score} />}
              {ctoSummary.summary && (
                <div className="text-xs text-zinc-400 max-w-lg">{ctoSummary.summary}</div>
              )}
            </div>
          )}
        </div>

        {/* ── CTO Provider Config ───────────────────────────────────────── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-3">
          <h2 className="font-semibold text-lg">⚙️ CTO Provider 設定</h2>
          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <label htmlFor="cto-planner-select" className="block text-xs text-zinc-500 mb-1">CTO Planner</label>
              <select
                id="cto-planner-select"
                value={ctoPlannerProvider}
                onChange={(e) => setCtoPlannerProvider(e.target.value)}
                className="bg-zinc-800 text-zinc-200 rounded px-3 py-1.5 text-sm"
              >
                {(ctoProviders?.planner_options ?? []).map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="cto-model-input" className="block text-xs text-zinc-500 mb-1">Model（可選）</label>
              <input
                id="cto-model-input"
                list="cto-model-presets"
                value={ctoPlannerModel}
                onChange={(e) => setCtoPlannerModel(e.target.value)}
                placeholder="e.g. claude-sonnet-4-5"
                className="bg-zinc-800 text-zinc-200 rounded px-3 py-1.5 text-sm w-48"
              />
              <datalist id="cto-model-presets">
                {(ctoProviders?.planner_model_presets ?? []).map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
            </div>
            <button
              onClick={handleSaveProviders}
              className="bg-blue-700 hover:bg-blue-600 text-white px-4 py-1.5 rounded text-sm"
            >
              儲存
            </button>
          </div>
          <div className="text-xs text-zinc-500">{ctoProviderHint}</div>
        </div>

        {/* ── CTO Run Now ───────────────────────────────────────────────── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-3">
          <h2 className="font-semibold text-lg">▶ CTO 立即執行</h2>
          <div className="flex items-center gap-4 flex-wrap">
            <button
              onClick={handleCtoRunNow}
              className="bg-purple-700 hover:bg-purple-600 text-white px-5 py-2 rounded text-sm font-medium transition-colors"
            >
              🧠 CTO 立即審核
            </button>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={ctoForce}
                onChange={(e) => setCtoForce(e.target.checked)}
                className="rounded"
              />
              <span>強制重跑</span>
            </label>
            {ctoForce && (
              <>
                <div className="text-xs text-yellow-400">⚠️ 強制重跑將忽略去重限制</div>
                <select
                  value={ctoIntent}
                  onChange={(e) => setCtoIntent(e.target.value as RunIntent)}
                  className="bg-zinc-800 text-zinc-200 rounded px-2 py-1 text-xs"
                >
                  <option value="retry">retry</option>
                  <option value="compare">compare</option>
                  <option value="override">override</option>
                </select>
              </>
            )}
          </div>

          {/* Trace */}
          {ctoTrace && (
            <div className="bg-zinc-800 rounded-lg p-3 text-xs font-mono space-y-1 border border-zinc-700">
              <div className="text-zinc-500 text-[10px] uppercase tracking-wider mb-1">執行追蹤</div>
              <div><span className="text-zinc-500">request_id: </span><span className="text-zinc-300">{ctoTrace.requestId}</span></div>
              <div>
                <span className="text-zinc-500">outcome: </span>
                <span className={outcomeCls(ctoTrace.outcome)}>{ctoTrace.outcome}</span>
              </div>
              <div><span className="text-zinc-500">note: </span><span className="text-zinc-400">{ctoTrace.note}</span></div>
            </div>
          )}
        </div>

        {/* ── CTO Runs List / Detail ────────────────────────────────────── */}
        {ctoSelectedRun && ctoRunDetail ? (
          <CtoRunDetailView
            detail={ctoRunDetail}
            addedBatchSet={addedBatchSet}
            addedSingleSet={addedSingleSet}
            onBack={() => { setCtoSelectedRun(null); setCtoRunDetail(null); }}
            onAddSingle={handleAddBacklogSingle}
            onAddBatch={handleAddBatchBacklog}
            onRescore={handleRescore}
          />
        ) : (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-3">
            <h2 className="font-semibold text-lg">📊 CTO 審核記錄</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-zinc-500 border-b border-zinc-800">
                    <th className="text-left py-2 pr-4">開始時間</th>
                    <th className="text-left py-2 pr-4">完成時間</th>
                    <th className="text-left py-2 pr-4">頻率</th>
                    <th className="text-left py-2 pr-4">候選</th>
                    <th className="text-left py-2 pr-4">通過</th>
                    <th className="text-left py-2 pr-4">需重規</th>
                    <th className="text-left py-2 pr-4">決議</th>
                    <th className="text-left py-2">摘要</th>
                  </tr>
                </thead>
                <tbody>
                  {ctoRuns.map((r) => (
                    <tr
                      key={r.run_id}
                      onClick={() => loadRunDetail(r.run_id)}
                      className="border-b border-zinc-800/50 hover:bg-zinc-800 cursor-pointer transition-colors"
                    >
                      <td className="py-2 pr-4 whitespace-nowrap font-mono">{fmtTs(r.started_at)}</td>
                      <td className="py-2 pr-4 whitespace-nowrap font-mono">{fmtTs(r.completed_at)}</td>
                      <td className="py-2 pr-4">
                        {r.frequency_mode}
                        {r.is_manual && <span className="ml-1 text-blue-400">[manual]</span>}
                        {r.is_force_run && <span className="ml-1 text-yellow-400">[force]</span>}
                        {r.run_intent && <span className="ml-1 text-purple-400">[{r.run_intent}]</span>}
                      </td>
                      <td className="py-2 pr-4">{r.candidate_count}</td>
                      <td className="py-2 pr-4 text-green-400">{r.pass_count}</td>
                      <td className="py-2 pr-4 text-red-400">{r.replan_count}</td>
                      <td className="py-2 pr-4">{verdictBadge(r.verdict)}</td>
                      <td className="py-2 text-zinc-400 max-w-xs truncate">{r.summary}</td>
                    </tr>
                  ))}
                  {ctoRuns.length === 0 && (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-zinc-600">尚無審核記錄</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Prioritized Backlog ───────────────────────────────────────── */}
        {prioritizedBacklog && (
          <PrioritizedBacklogPanel
            backlog={prioritizedBacklog}
            onRescore={handleRescore}
            onApplyAging={() => ctoApi.applyAging().then(() => ctoApi.getPrioritizedBacklog().then(setPrioritizedBacklog))}
          />
        )}

        {/* ── Adaptive Policy ───────────────────────────────────────────── */}
        {adaptivePolicy && (
          <AdaptivePolicyPanel
            policy={adaptivePolicy}
            onRefresh={() => ctoApi.refreshAdaptivePolicy().then(setAdaptivePolicy)}
          />
        )}

        {/* ── Execution Policy ──────────────────────────────────────────── */}
        {execPolicy && (
          <ExecutionPolicyPanel
            policy={execPolicy}
            onSetMode={handleSetPolicyMode}
            onApplyAging={() => ctoApi.applyAging().then(() => ctoApi.getPrioritizedBacklog().then(setPrioritizedBacklog))}
          />
        )}

      </div>
    </div>
  );
}
