'use client';

import React, { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import type {
  LlmControlState,
  OrcDashboardSummary,
  OrcRun,
  OrcSummary,
  OrcTask,
  ProvidersResponse,
} from '../../../../lib/orchestrator-api';
import { orcApi } from '../../../../lib/orchestrator-api';

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtTs(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-TW', { hour12: false });
  } catch {
    return iso;
  }
}

function fmtDur(started: string | null | undefined, finished: string | null | undefined): string {
  if (!started || !finished) return '—';
  try {
    const diff = Math.round((new Date(finished).getTime() - new Date(started).getTime()) / 1000);
    if (diff < 1) return '< 1s';
    if (diff < 60) return `${diff}s`;
    return `${Math.floor(diff / 60)}m ${diff % 60}s`;
  } catch {
    return '—';
  }
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

function outcomeCls(o: string): string {
  if (!o) return '';
  const lo = o.toLowerCase();
  if (lo.includes('error') || lo.includes('fail')) return 'text-red-400';
  if (lo.includes('skip') || lo.includes('rate') || lo.includes('timeout')) return 'text-yellow-400';
  if (lo.includes('complet') || lo === 'pass' || lo === 'completed') return 'text-green-400';
  return 'text-zinc-400';
}

const STATUS_LABELS: Record<string, string> = {
  QUEUED: '等待中',
  RUNNING: '執行中',
  COMPLETED: '已完成',
  FAILED: '失敗',
  FAILED_RATE_LIMIT: '額度限制',
  REPLAN_REQUIRED: '需重新規劃',
  CANCELLED: '已取消',
  PENDING_REVIEW: '待審核',
};

function taskStatusBadge(s: string) {
  const cls: Record<string, string> = {
    QUEUED: 'bg-zinc-700 text-zinc-300',
    RUNNING: 'bg-blue-900 text-blue-300 animate-pulse',
    COMPLETED: 'bg-green-900 text-green-300',
    FAILED: 'bg-red-900 text-red-300',
    FAILED_RATE_LIMIT: 'bg-amber-900 text-amber-200',
    REPLAN_REQUIRED: 'bg-yellow-900 text-yellow-300',
    CANCELLED: 'bg-zinc-700 text-zinc-500',
    PENDING_REVIEW: 'bg-purple-900 text-purple-300',
  };
  return <span className={`px-1.5 py-0.5 rounded text-xs font-mono ${cls[s] ?? 'bg-zinc-700'}`}>{STATUS_LABELS[s] ?? s}</span>;
}

function schedulerStatusLabel(summary: OrcSummary | null, schedulerEnabled: boolean): string {
  if (summary == null) return '…';
  return schedulerEnabled ? '⏺ 啟用中' : '⏸ 已暫停';
}

function buildProviderHint(reason: string | undefined, model: string, prefix: string): string {
  const daemonText = reason ? ` Copilot Daemon：${reason}` : '';
  const modelText = ` Copilot Model：${model || '預設'}`;
  return `${prefix}${daemonText}${modelText}`.trim();
}

function llmModeLabel(mode: LlmControlState['mode'] | undefined): string {
  if (mode === 'hard-off') return 'Hard Off';
  return 'Safe Run';
}

// ── Category label map ────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
  behavior_loop_optimization: '行為改變循環',
  ux_flow_redesign: 'UX 流程優化',
  action_system_enhancement: '行動建議系統',
  decision_engine_improvement: '決策引擎',
  health_narrative_deepening: '健康敘事',
  user_journey_analysis: '用戶旅程',
  retention_habit_loop: '習慣留存',
  notifications_lifecycle: '通知生命週期',
  reports_product_value: '報告價值',
  timeline_history_value: '歷史時間軸',
  growth_analytics: '成長分析',
  cross_page_consistency: '跨頁一致性',
};

const IMPACT_TIERS: { label: string; color: string; categories: string[] }[] = [
  {
    label: '行為 & 體驗',
    color: 'border-blue-700 bg-blue-950/40',
    categories: ['behavior_loop_optimization', 'ux_flow_redesign', 'action_system_enhancement', 'user_journey_analysis'],
  },
  {
    label: '決策 & 洞察',
    color: 'border-purple-700 bg-purple-950/40',
    categories: ['decision_engine_improvement', 'health_narrative_deepening', 'growth_analytics'],
  },
  {
    label: '留存 & 一致性',
    color: 'border-teal-700 bg-teal-950/40',
    categories: ['retention_habit_loop', 'notifications_lifecycle', 'reports_product_value', 'timeline_history_value', 'cross_page_consistency'],
  },
];

// ── Product View panel ────────────────────────────────────────────────────────

function ProductView({ dashSummary }: Readonly<{ dashSummary: OrcDashboardSummary | null }>) {
  if (!dashSummary) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 text-zinc-500 text-sm">
        載入產品視圖中…
      </div>
    );
  }

  const completedByCategory = Object.fromEntries(
    dashSummary.top_categories.map((c) => [c.category, c.completed_count]),
  );

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-5">
      <div>
        <h2 className="font-semibold text-lg text-zinc-100">🎯 產品優化視圖</h2>
        <p className="text-xs text-zinc-500 mt-0.5">AI 持續改善的 12 個產品領域，按影響力分組</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: '今日任務', value: dashSummary.today_total, cls: 'text-zinc-100' },
          { label: '已完成', value: dashSummary.today_completed, cls: 'text-green-400' },
          { label: '執行中', value: dashSummary.today_running, cls: 'text-blue-400' },
          { label: '需複查', value: dashSummary.today_replan + dashSummary.today_failed, cls: dashSummary.today_replan + dashSummary.today_failed > 0 ? 'text-amber-400' : 'text-zinc-500' },
        ].map((s) => (
          <div key={s.label} className="bg-zinc-800 rounded-lg p-3 text-center">
            <div className={`text-2xl font-bold ${s.cls}`}>{s.value}</div>
            <div className="text-xs text-zinc-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Impact tier breakdown */}
      <div className="space-y-3">
        {IMPACT_TIERS.map((tier) => (
          <div key={tier.label} className={`rounded-lg border p-4 ${tier.color}`}>
            <p className="text-xs font-semibold text-zinc-300 mb-2 uppercase tracking-wider">{tier.label}</p>
            <div className="flex flex-wrap gap-2">
              {tier.categories.map((cat) => {
                const count = completedByCategory[cat] ?? 0;
                const label = CATEGORY_LABELS[cat] ?? cat;
                return (
                  <span
                    key={cat}
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      count > 0
                        ? 'bg-green-900/60 text-green-300 border border-green-700'
                        : 'bg-zinc-800 text-zinc-500 border border-zinc-700'
                    }`}
                  >
                    {label}{count > 0 ? ` ✓${count}` : ''}
                  </span>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Recent completed tasks */}
      {dashSummary.recent_completed.length > 0 && (
        <div>
          <p className="text-xs text-zinc-500 mb-2 font-semibold uppercase tracking-wider">近期完成</p>
          <div className="space-y-2">
            {dashSummary.recent_completed.map((t) => (
              <div key={t.id} className="flex items-start justify-between gap-3 bg-zinc-800 rounded-lg px-3 py-2">
                <div className="min-w-0">
                  <p className="text-sm text-zinc-200 truncate">{t.title}</p>
                  {t.category_label && (
                    <p className="text-xs text-zinc-500 mt-0.5">{t.category_label}</p>
                  )}
                </div>
                <div className="shrink-0 flex items-center gap-1.5">
                  {(!t.gate_verdict || t.gate_verdict === 'PASS') && (
                    <span className="text-[10px] rounded bg-green-900 text-green-300 px-1.5 py-0.5">PASS</span>
                  )}
                  {t.gate_verdict && t.gate_verdict !== 'PASS' && (
                    <span className="text-[10px] rounded bg-amber-900 text-amber-300 px-1.5 py-0.5">
                      {t.gate_verdict === 'RESULT_SHALLOW' ? '需補強' : t.gate_verdict}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

async function waitForOutcome(
  poller: (reqId: string) => Promise<{ status: string; run: OrcRun | null; final: boolean }>,
  requestId: string,
  onUpdate: (status: string, msg: string) => void,
  timeoutMs = 70000,
  intervalMs = 2000,
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

// ── Task Detail View ──────────────────────────────────────────────────────────

function TaskDetailView({ detail, onBack }: Readonly<{ detail: Record<string, unknown>; onBack: () => void }>) {
  const task = detail.task as OrcTask | undefined;
  const contract = detail.contract_json as Record<string, unknown> | null;
  const result = detail.result_json as Record<string, unknown> | null;
  const log = detail.worker_log_tail as string[] | undefined;
  const failureReason = typeof result?.failure_reason === 'string' ? result.failure_reason : null;
  const finalMessage = typeof result?.final_message === 'string' ? result.final_message : null;
  const resetHint = typeof result?.reset_hint === 'string' ? result.reset_hint : null;
  const [showLog, setShowLog] = useState(false);
  const [showContract, setShowContract] = useState(false);

  return (
    <div className="space-y-4">
      <button onClick={onBack} className="text-xs text-blue-400 hover:underline">← 返回列表</button>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
        <div><span className="text-zinc-500">ID: </span>{task?.id}</div>
        <div><span className="text-zinc-500">UID: </span><span className="font-mono">{task?.task_uid}</span></div>
        <div><span className="text-zinc-500">狀態: </span>{task && taskStatusBadge(task.status)}</div>
        <div><span className="text-zinc-500">Gate: </span><span className="font-mono">{task?.gate_verdict ?? '—'}</span></div>
        <div><span className="text-zinc-500">建立: </span>{fmtTs(task?.created_at)}</div>
        <div><span className="text-zinc-500">完成: </span>{fmtTs(task?.finished_at)}</div>
        <div><span className="text-zinc-500">耗時: </span>{fmtDur(task?.started_at, task?.finished_at)}</div>
        <div><span className="text-zinc-500">Planner: </span>{task?.planner_provider ?? '—'}</div>
        <div><span className="text-zinc-500">Worker: </span>{task?.worker_provider ?? '—'}</div>
      </div>
      <div className="text-sm font-semibold">{task?.title}</div>
      <div className="text-xs text-zinc-400">{task?.objective}</div>
      {task?.gate_reason && (
        <div className="bg-zinc-800 rounded p-3 text-xs text-yellow-300">Gate 原因：{task.gate_reason}</div>
      )}
      {task?.status === 'FAILED_RATE_LIMIT' && (
        <div className="bg-amber-950/60 border border-amber-800 rounded p-3 text-xs text-amber-200 space-y-1">
          <div className="font-semibold">偵測到 provider 額度限制，任務已被終止，不會繼續阻塞 Planner。</div>
          {failureReason ? <div>failure_reason: {failureReason}</div> : null}
          {finalMessage ? <div>{finalMessage}</div> : null}
          {resetHint ? <div className="text-amber-300">{resetHint}</div> : null}
        </div>
      )}
      {task?.latest_progress_summary && (
        <div className="text-xs text-blue-300">{task.latest_progress_summary}</div>
      )}
      {result && (
        <div className="bg-zinc-800 rounded p-3 text-xs">
          <div className="text-zinc-500 mb-2 font-semibold">任務結果</div>
          <div className="font-mono whitespace-pre-wrap">{JSON.stringify(result, null, 2)}</div>
        </div>
      )}
      <button onClick={() => setShowContract(!showContract)} className="text-xs text-blue-400 hover:underline">
        {showContract ? '▾' : '▸'} 合約 JSON
      </button>
      {showContract && contract && (
        <pre className="bg-zinc-800 rounded p-3 text-xs font-mono overflow-auto max-h-64">{JSON.stringify(contract, null, 2)}</pre>
      )}
      <button onClick={() => setShowLog(!showLog)} className="text-xs text-blue-400 hover:underline ml-4">
        {showLog ? '▾' : '▸'} 執行日誌
      </button>
      {showLog && log && (
        <pre className="bg-zinc-800 rounded p-3 text-xs font-mono overflow-auto max-h-48">{log.join('\n')}</pre>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function OrchestrationPage() {
  const [summary, setSummary] = useState<OrcSummary | null>(null);
  const [providers, setProviders] = useState<ProvidersResponse | null>(null);
  const [tasks, setTasks] = useState<OrcTask[]>([]);
  const [taskTotal, setTaskTotal] = useState(0);
  const [taskPage, setTaskPage] = useState(1);
  const [taskStatus, setTaskStatus] = useState('');
  const [taskDate, setTaskDate] = useState('');
  const [runs, setRuns] = useState<OrcRun[]>([]);
  const [selectedTask, setSelectedTask] = useState<number | null>(null);
  const [taskDetail, setTaskDetail] = useState<Record<string, unknown> | null>(null);
  const [trace, setTrace] = useState<{ requestId: string; outcome: string; note: string } | null>(null);
  const [schedulerSaving, setSchedulerSaving] = useState<'enable' | 'disable' | null>(null);
  const [llmSaving, setLlmSaving] = useState<'safe-run' | 'hard-off' | null>(null);
  const [providerSaving, setProviderSaving] = useState(false);
  const [providerHint, setProviderHint] = useState('');
  const [plannerProvider, setPlannerProvider] = useState('codex');
  const [workerProvider, setWorkerProvider] = useState('codex');
  const [workerCopilotModel, setWorkerCopilotModel] = useState('');
  const [tick, setTick] = useState(0);
  const [dashSummary, setDashSummary] = useState<OrcDashboardSummary | null>(null);
  const [activeTab, setActiveTab] = useState<'product' | 'technical'>('product');
  const PAGE_SIZE = 20;

  // Countdown tick
  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const loadSummary = useCallback(async () => {
    try {
      const data = await orcApi.getSummary();
      setSummary(data);
    } catch { /* ignore */ }
  }, []);

  const loadDashSummary = useCallback(async () => {
    try {
      const data = await orcApi.getDashboardSummary();
      setDashSummary(data);
    } catch { /* ignore */ }
  }, []);

  const loadProviders = useCallback(async () => {
    try {
      const data = await orcApi.getProviders();
      setProviders(data);
      setPlannerProvider(data.planner_provider);
      setWorkerProvider(data.worker_provider);
      setWorkerCopilotModel(data.worker_copilot_model ?? '');
      const selectedWorker = data.worker_options.find((option) => option.value === data.worker_provider);
      setProviderHint(buildProviderHint(
        selectedWorker?.reason,
        (data.worker_copilot_model ?? '').trim(),
        '切換後會影響下一次 planner / worker 啟動；不會中斷目前已在執行的任務。',
      ));
    } catch { /* ignore */ }
  }, []);

  const loadTasks = useCallback(async () => {
    try {
      const data = await orcApi.getTasks({
        page: taskPage,
        page_size: PAGE_SIZE,
        status: taskStatus || undefined,
        date: taskDate || undefined,
      });
      setTasks(data.items ?? []);
      setTaskTotal(data.total ?? 0);
    } catch { /* ignore */ }
  }, [taskPage, taskStatus, taskDate]);

  const loadRuns = useCallback(async () => {
    try {
      const data = await orcApi.getRuns({ limit: 10 });
      setRuns(data.runs ?? data.items ?? []);
    } catch { /* ignore */ }
  }, []);

  const loadTaskDetail = useCallback(async (id: number) => {
    try {
      const data = await orcApi.getTaskDetail(id);
      setTaskDetail(data as Record<string, unknown>);
    } catch { /* ignore */ }
  }, []);

  const [taskPool, setTaskPool] = useState<{
    categories: string[];
    pool: { category: string; title: string; duplicate_signature: string; focus_keys: string[]; is_active: boolean }[];
    active_count: number;
    available_count: number;
  } | null>(null);
  const [showTaskPool, setShowTaskPool] = useState(false);

  const loadTaskPool = useCallback(async () => {
    try {
      const data = await orcApi.getTaskPool();
      setTaskPool(data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    loadSummary();
    loadDashSummary();
    loadProviders();
    loadTasks();
    loadRuns();
    loadTaskPool();
  }, [loadSummary, loadDashSummary, loadProviders, loadTasks, loadRuns, loadTaskPool]);

  useEffect(() => { loadTasks(); }, [loadTasks]);

  // Auto-refresh every 30s
  useEffect(() => {
    const t = setInterval(() => loadSummary(), 30_000);
    return () => clearInterval(t);
  }, [loadSummary]);

  // ── Actions ───────────────────────────────────────────────────────────────

  const handleEnable = async () => {
    setSchedulerSaving('enable');
    try {
      await orcApi.setScheduler(true);
      await loadSummary();
    } catch (e: unknown) {
      alert(`啟用失敗：${(e as Error).message}`);
    } finally {
      setSchedulerSaving(null);
    }
  };

  const handleDisable = async () => {
    setSchedulerSaving('disable');
    try {
      await orcApi.setScheduler(false);
      await loadSummary();
    } catch (e: unknown) {
      alert(`停止失敗：${(e as Error).message}`);
    } finally {
      setSchedulerSaving(null);
    }
  };

  const handleSaveProviders = async () => {
    setProviderSaving(true);
    try {
      const data = await orcApi.setProviders({
        planner_provider: plannerProvider,
        worker_provider: workerProvider,
        worker_copilot_model: workerCopilotModel.trim(),
      });
      const selectedWorker = data.worker_options.find((option) => option.value === data.worker_provider);
      setProviderHint(buildProviderHint(selectedWorker?.reason, (data.worker_copilot_model ?? '').trim(), `已套用：${data.combo_label}。`));
      setTimeout(() => loadProviders(), 200);
    } catch (e: unknown) {
      setProviderHint(`儲存失敗：${(e as Error).message}`);
    } finally {
      setProviderSaving(false);
    }
  };

  const handleRunNow = async (role: 'planner' | 'worker') => {
    try {
      const data = await orcApi.runNow(role);
      setTrace({ requestId: data.request_id, outcome: '等待中…', note: `已觸發 ${role}，等待結果…` });
      await waitForOutcome(
        (rid) => orcApi.getRunStatus(rid),
        data.request_id,
        (outcome, note) => setTrace({ requestId: data.request_id, outcome, note }),
      );
      await Promise.all([loadSummary(), loadTasks(), loadRuns()]);
    } catch (e: unknown) {
      setTrace({ requestId: '—', outcome: 'ERROR', note: `觸發失敗：${(e as Error).message}` });
    }
  };

  const schedulerEnabled = summary?.scheduler_enabled ?? false;
  const schedulerSummaryLabel = schedulerStatusLabel(summary, schedulerEnabled);
  const llmControl = summary?.llm_control ?? null;
  const maxPage = Math.max(1, Math.ceil(taskTotal / PAGE_SIZE));
  const start = taskTotal ? (taskPage - 1) * PAGE_SIZE + 1 : 0;
  const end = taskTotal ? Math.min(taskPage * PAGE_SIZE, taskTotal) : 0;

  const handleSetLlmMode = async (mode: 'safe-run' | 'hard-off') => {
    setLlmSaving(mode);
    try {
      await orcApi.setLlmControl(mode);
      await loadSummary();
    } catch (e: unknown) {
      alert(`LLM 控制切換失敗：${(e as Error).message}`);
    } finally {
      setLlmSaving(null);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200 px-4 py-6">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">🤖 AI 優化任務中心</h1>
            <p className="text-xs text-zinc-500 mt-1">AI 持續規劃並執行產品優化任務</p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/platform/cockpit/cto-review"
              className="px-3 py-1.5 rounded text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors"
            >
              🧠 CTO 審核 →
            </Link>
            <Link
              href="/platform/cockpit"
              className="px-3 py-1.5 rounded text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-500 transition-colors"
            >
              ← 駕駛艙
            </Link>
          </div>
        </div>

        {/* Tab switcher */}
        <div className="flex gap-1 bg-zinc-900 border border-zinc-800 rounded-lg p-1 w-fit">
          <button
            onClick={() => setActiveTab('product')}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              activeTab === 'product'
                ? 'bg-zinc-700 text-zinc-100'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            🎯 產品視圖
          </button>
          <button
            onClick={() => setActiveTab('technical')}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              activeTab === 'technical'
                ? 'bg-zinc-700 text-zinc-100'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            ⚙️ 技術控制
          </button>
        </div>

        {/* Product View Tab */}
        {activeTab === 'product' && <ProductView dashSummary={dashSummary} />}

        {/* Technical Tab — existing sections below */}
        {activeTab === 'technical' && (<>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: '今日任務', value: summary?.total_today ?? '…' },
            { label: '執行中', value: summary?.total_running ?? '…' },
            { label: '完成', value: summary?.total_completed ?? '…' },
            {
              label: '排程',
              value: (
                <span className={schedulerEnabled ? 'text-green-400' : 'text-yellow-400'}>
                  {schedulerSummaryLabel}
                </span>
              ),
            },
          ].map((s) => (
            <div key={s.label} className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
              <div className="text-xs text-zinc-500 mb-1">{s.label}</div>
              <div className="text-2xl font-bold">{s.value}</div>
            </div>
          ))}
        </div>

        {/* ── Scheduler Control ─────────────────────────────────────────── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-4">
          <h2 className="font-semibold text-lg">🗓 排程控制</h2>

          {/* Status + Enable / Stop buttons */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
              schedulerEnabled ? 'bg-green-900/50 text-green-300 border border-green-700' : 'bg-yellow-900/40 text-yellow-300 border border-yellow-700'
            }`}>
              <span className={`w-2 h-2 rounded-full ${schedulerEnabled ? 'bg-green-400 animate-pulse' : 'bg-yellow-400'}`} />
              {schedulerEnabled ? '排程啟用中' : '排程已暫停'}
            </div>

            <button
              onClick={handleEnable}
              disabled={schedulerSaving !== null || schedulerEnabled}
              className="px-4 py-1.5 rounded text-sm font-medium bg-green-700 hover:bg-green-600 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {schedulerSaving === 'enable' ? '啟用中…' : '▶ 啟用排程'}
            </button>

            <button
              onClick={handleDisable}
              disabled={schedulerSaving !== null || !schedulerEnabled}
              className="px-4 py-1.5 rounded text-sm font-medium bg-red-800 hover:bg-red-700 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {schedulerSaving === 'disable' ? '停止中…' : '⏹ 停止排程'}
            </button>
          </div>

          {/* Countdown + timing */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="text-xs text-zinc-500 mb-1">Worker 狀態</div>
              <div className={`font-medium ${summary?.worker_busy ? 'text-yellow-400' : 'text-green-400'}`}>
                {summary?.worker_state ?? '—'}
              </div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="text-xs text-zinc-500 mb-1">下次 Planner 執行</div>
              <div className="font-mono text-lg font-bold text-blue-300">
                {tick > -1 && schedulerEnabled ? countdown(summary?.next_planner_tick_estimate) : '—'}
              </div>
              <div className="text-xs text-zinc-500 mt-1">{fmtTs(summary?.next_planner_tick_estimate)}</div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="text-xs text-zinc-500 mb-1">下次 Worker 執行</div>
              <div className="font-mono text-lg font-bold text-teal-300">
                {tick > -1 && schedulerEnabled ? countdown(summary?.next_worker_tick_estimate) : '—'}
              </div>
              <div className="text-xs text-zinc-500 mt-1">{fmtTs(summary?.next_worker_tick_estimate)}</div>
            </div>
          </div>

          {/* Interval config */}
          <div className="text-xs text-zinc-500">
            Planner interval：{summary?.scheduler?.planner_interval_minutes ?? '—'} 分鐘 ／
            Worker interval：{summary?.scheduler?.worker_interval_minutes ?? '—'} 分鐘
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h2 className="font-semibold text-lg">🔐 LLM Execution Policy</h2>
              <p className="text-xs text-zinc-500 mt-1">唯一控制來源。背景執行、API fallback、觀測統一讀這個 state。</p>
            </div>
            <div className={`px-3 py-1.5 rounded-full text-sm font-medium border ${llmControl?.mode === 'hard-off' ? 'bg-red-950/50 text-red-300 border-red-700' : 'bg-blue-950/50 text-blue-300 border-blue-700'}`}>
              {llmModeLabel(llmControl?.mode)}
            </div>
          </div>

          <div className="flex gap-3 flex-wrap">
            <button
              onClick={() => handleSetLlmMode('safe-run')}
              disabled={llmSaving !== null || llmControl?.mode === 'safe-run'}
              className="px-4 py-1.5 rounded text-sm font-medium bg-blue-700 hover:bg-blue-600 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {llmSaving === 'safe-run' ? '切換中…' : 'Safe Run'}
            </button>
            <button
              onClick={() => handleSetLlmMode('hard-off')}
              disabled={llmSaving !== null || llmControl?.mode === 'hard-off'}
              className="px-4 py-1.5 rounded text-sm font-medium bg-red-800 hover:bg-red-700 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {llmSaving === 'hard-off' ? '切換中…' : 'Hard Off'}
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="text-xs text-zinc-500 mb-1">背景執行</div>
              <div className={llmControl?.effective_background_run_allowed ? 'text-green-400 font-medium' : 'text-yellow-400 font-medium'}>
                {llmControl?.effective_background_run_allowed ? '允許' : '阻擋'}
              </div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="text-xs text-zinc-500 mb-1">LLM 實際呼叫次數</div>
              <div className="font-mono text-lg font-bold text-zinc-100">{llmControl?.call_count ?? 0}</div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="text-xs text-zinc-500 mb-1">被阻擋次數</div>
              <div className="font-mono text-lg font-bold text-amber-300">{llmControl?.blocked_count ?? 0}</div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-3">
              <div className="text-xs text-zinc-500 mb-1">最近決策</div>
              <div className={`font-medium ${llmControl?.last_allowed ? 'text-green-400' : 'text-amber-300'}`}>{llmControl?.last_decision_code ?? '—'}</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-zinc-400">
            <div className="bg-zinc-800 rounded-lg p-3 space-y-1">
              <div>最後決策時間：{fmtTs(llmControl?.last_decision_at)}</div>
              <div>最後決策來源：{llmControl?.last_source ?? '—'}</div>
              <div>最後阻擋時間：{fmtTs(llmControl?.last_blocked_at)}</div>
            </div>
            <div className="bg-zinc-800 rounded-lg p-3 space-y-1">
              <div>最後 LLM 呼叫：{fmtTs(llmControl?.last_call_at)}</div>
              <div>最後呼叫來源：{llmControl?.last_call_source ?? '—'}</div>
              <div>Provider / Model：{llmControl?.last_provider ?? '—'} / {llmControl?.last_model ?? '—'}</div>
            </div>
          </div>

          <div className="text-xs text-zinc-500">
            Safe Run：只允許 scheduler-controlled source。Hard Off：所有 LLM 呼叫直接 fallback，並同步關閉 scheduler enabled。
          </div>
        </div>

        {/* ── Provider Config ───────────────────────────────────────────── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-3">
          <h2 className="font-semibold text-lg">⚙️ Provider 設定</h2>
          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <label htmlFor="planner-provider" className="block text-xs text-zinc-500 mb-1">Planner</label>
              <select
                id="planner-provider"
                value={plannerProvider}
                onChange={(e) => setPlannerProvider(e.target.value)}
                className="bg-zinc-800 text-zinc-200 rounded px-3 py-1.5 text-sm"
              >
                {(providers?.planner_options ?? []).map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="worker-provider" className="block text-xs text-zinc-500 mb-1">Worker</label>
              <select
                id="worker-provider"
                value={workerProvider}
                onChange={(e) => setWorkerProvider(e.target.value)}
                className="bg-zinc-800 text-zinc-200 rounded px-3 py-1.5 text-sm"
              >
                {(providers?.worker_options ?? []).map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}{o.available === false ? '（不可用）' : ''}
                  </option>
                ))}
              </select>
            </div>
            {(workerProvider === 'copilot' || workerProvider === 'copilot-daemon') && (
              <div>
                <label htmlFor="worker-copilot-model" className="block text-xs text-zinc-500 mb-1">Copilot Model</label>
                <input
                  id="worker-copilot-model"
                  list="worker-copilot-model-options"
                  value={workerCopilotModel}
                  onChange={(e) => setWorkerCopilotModel(e.target.value)}
                  placeholder="預設 / auto / gpt-5-mini"
                  className="bg-zinc-800 text-zinc-200 rounded px-3 py-1.5 text-sm min-w-[220px]"
                />
                <datalist id="worker-copilot-model-options">
                  {(providers?.worker_copilot_model_presets ?? []).map((preset) => (
                    <option key={preset.value || 'default'} value={preset.value}>
                      {preset.label}
                    </option>
                  ))}
                </datalist>
              </div>
            )}
            <button
              onClick={handleSaveProviders}
              disabled={providerSaving}
              className="bg-blue-700 hover:bg-blue-600 text-white px-4 py-1.5 rounded text-sm disabled:opacity-50"
            >
              {providerSaving ? '儲存中…' : '儲存'}
            </button>
          </div>
          <div className="text-xs text-zinc-500">{providerHint}</div>
        </div>

        {/* ── Run Now ───────────────────────────────────────────────────── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-3">
          <h2 className="font-semibold text-lg">▶ 立即執行</h2>
          <div className="flex gap-3 flex-wrap">
            <button
              onClick={() => handleRunNow('planner')}
              className="bg-indigo-700 hover:bg-indigo-600 text-white px-4 py-2 rounded text-sm font-medium transition-colors"
            >
              🧩 Planner 立即執行
            </button>
            <button
              onClick={() => handleRunNow('worker')}
              className="bg-teal-700 hover:bg-teal-600 text-white px-4 py-2 rounded text-sm font-medium transition-colors"
            >
              ⚙️ Worker 立即執行
            </button>
          </div>

          {/* Trace block */}
          {trace && (
            <div className="bg-zinc-800 rounded-lg p-3 text-xs font-mono space-y-1 border border-zinc-700">
              <div className="text-zinc-500 text-[10px] uppercase tracking-wider mb-1">執行追蹤</div>
              <div><span className="text-zinc-500">request_id: </span><span className="text-zinc-300">{trace.requestId}</span></div>
              <div>
                <span className="text-zinc-500">outcome: </span>
                <span className={outcomeCls(trace.outcome)}>{trace.outcome}</span>
              </div>
              <div><span className="text-zinc-500">note: </span><span className="text-zinc-400">{trace.note}</span></div>
            </div>
          )}
        </div>

        {/* ── Task Pool ─────────────────────────────────────────────────── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-lg">🗂 任務池 — Task Pool</h2>
            <div className="flex items-center gap-3">
              {taskPool && (
                <span className="text-xs text-zinc-400">
                  <span className="text-green-400 font-semibold">{taskPool.available_count}</span>
                  {' '}可用 /
                  <span className="text-yellow-400 font-semibold ml-1">{taskPool.active_count}</span>
                  {' '}執行中
                </span>
              )}
              <button
                onClick={() => { setShowTaskPool(!showTaskPool); if (!showTaskPool) loadTaskPool(); }}
                className="text-xs text-blue-400 hover:underline"
              >
                {showTaskPool ? '▾ 收起' : '▸ 展開'}
              </button>
            </div>
          </div>
          <p className="text-xs text-zinc-500">
            當 backlog 耗盡或被 Duplicate Gate 阻擋時，Planner 會自動從以下 10 個類別中選取下一個任務，實現持續迭代。
          </p>
          {showTaskPool && taskPool && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
              {taskPool.pool.map((item) => (
                <div
                  key={item.category}
                  className={`rounded-lg p-3 border text-xs space-y-1 ${
                    item.is_active
                      ? 'bg-blue-950/40 border-blue-800'
                      : 'bg-zinc-800 border-zinc-700'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-zinc-500">{item.category}</span>
                    {item.is_active ? (
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-900 text-blue-300 font-medium">執行中</span>
                    ) : (
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-700 text-zinc-400">可用</span>
                    )}
                  </div>
                  <div className="text-zinc-300 leading-snug">{item.title}</div>
                  <div className="text-zinc-500">{item.focus_keys.join(' · ')}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Task List ─────────────────────────────────────────────────── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <h2 className="font-semibold text-lg">📋 任務列表</h2>
            <div className="flex gap-2 items-center flex-wrap">
              <select
                value={taskStatus}
                onChange={(e) => { setTaskStatus(e.target.value); setTaskPage(1); }}
                className="bg-zinc-800 text-zinc-300 rounded px-2 py-1 text-xs"
              >
                {[
                  { value: '', label: '全部狀態' },
                  { value: 'QUEUED', label: '等待中 (QUEUED)' },
                  { value: 'RUNNING', label: '執行中 (RUNNING)' },
                  { value: 'COMPLETED', label: '已完成 (COMPLETED)' },
                  { value: 'PENDING_REVIEW', label: '待審核 (PENDING_REVIEW)' },
                  { value: 'FAILED', label: '失敗 (FAILED)' },
                  { value: 'FAILED_RATE_LIMIT', label: '額度限制 (FAILED_RATE_LIMIT)' },
                  { value: 'REPLAN_REQUIRED', label: '需重新規劃 (REPLAN_REQUIRED)' },
                  { value: 'CANCELLED', label: '已取消 (CANCELLED)' },
                ].map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
              <input
                type="date"
                value={taskDate}
                onChange={(e) => { setTaskDate(e.target.value.replaceAll('-', '')); setTaskPage(1); }}
                className="bg-zinc-800 text-zinc-300 rounded px-2 py-1 text-xs"
              />
            </div>
          </div>

          {selectedTask && taskDetail ? (
            <TaskDetailView
              detail={taskDetail}
              onBack={() => { setSelectedTask(null); setTaskDetail(null); }}
            />
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-zinc-500 border-b border-zinc-800">
                      <th className="text-left py-2 pr-4">#</th>
                      <th className="text-left py-2 pr-4">建立時間</th>
                      <th className="text-left py-2 pr-4 max-w-xs">標題</th>
                      <th className="text-left py-2 pr-4">狀態</th>
                      <th className="text-left py-2 pr-4">Gate</th>
                      <th className="text-left py-2 pr-4">耗時</th>
                      <th className="text-left py-2">完成時間</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tasks.map((t) => (
                      <tr
                        key={t.id}
                        className="border-b border-zinc-800/50 hover:bg-zinc-800 cursor-pointer transition-colors"
                        onClick={() => { setSelectedTask(t.id); loadTaskDetail(t.id); }}
                      >
                        <td className="py-2 pr-4 font-mono text-zinc-400">{t.id}</td>
                        <td className="py-2 pr-4 whitespace-nowrap">{fmtTs(t.created_at)}</td>
                        <td className="py-2 pr-4 max-w-xs truncate">
                          {t.title}
                          {t.status === 'RUNNING' && t.latest_progress_summary && (
                            <span className="ml-2 text-blue-400 text-[10px]">{t.latest_progress_summary}</span>
                          )}
                        </td>
                        <td className="py-2 pr-4">{taskStatusBadge(t.status)}</td>
                        <td className="py-2 pr-4 font-mono text-zinc-400 text-[10px]">{t.gate_verdict ?? '—'}</td>
                        <td className="py-2 pr-4 font-mono text-zinc-400">{fmtDur(t.started_at, t.finished_at)}</td>
                        <td className="py-2 whitespace-nowrap">{fmtTs(t.finished_at)}</td>
                      </tr>
                    ))}
                    {tasks.length === 0 && (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-zinc-600">無資料</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between text-xs text-zinc-500">
                <span>
                  {taskTotal
                    ? `${start}-${end} / 共 ${taskTotal} 筆（第 ${taskPage}/${maxPage} 頁）`
                    : '0 筆資料'}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setTaskPage((p) => Math.max(1, p - 1))}
                    disabled={taskPage <= 1}
                    className="px-2 py-1 bg-zinc-800 rounded disabled:opacity-30"
                  >← 上頁</button>
                  <button
                    onClick={() => setTaskPage((p) => Math.min(maxPage, p + 1))}
                    disabled={taskPage >= maxPage}
                    className="px-2 py-1 bg-zinc-800 rounded disabled:opacity-30"
                  >下頁 →</button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* ── Run History ───────────────────────────────────────────────── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-3">
          <h2 className="font-semibold text-lg">📜 執行記錄（最近 10 筆）</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 border-b border-zinc-800">
                  <th className="text-left py-2 pr-4">時間</th>
                  <th className="text-left py-2 pr-4">角色</th>
                  <th className="text-left py-2 pr-4">結果</th>
                  <th className="text-left py-2 pr-4">任務 ID</th>
                  <th className="text-left py-2 pr-4">請求 ID</th>
                  <th className="text-left py-2">備註</th>
                </tr>
              </thead>
              <tbody>
                {runs.slice(0, 10).map((r) => (
                  <tr key={r.id} className="border-b border-zinc-800/50">
                    <td className="py-1.5 pr-4 whitespace-nowrap font-mono">{fmtTs(r.tick_at)}</td>
                    <td className="py-1.5 pr-4">{r.runner}</td>
                    <td className={`py-1.5 pr-4 font-mono ${outcomeCls(r.outcome)}`}>{r.outcome}</td>
                    <td className="py-1.5 pr-4 font-mono text-zinc-400">{r.task_id ?? '—'}</td>
                    <td className="py-1.5 pr-4 font-mono text-zinc-500 text-[10px]">{r.request_id?.slice(0, 8) ?? '—'}</td>
                    <td className="py-1.5 text-zinc-500 max-w-xs truncate">{r.message}</td>
                  </tr>
                ))}
                {runs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-zinc-600">無執行記錄</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        </>)}

      </div>
    </div>
  );
}
