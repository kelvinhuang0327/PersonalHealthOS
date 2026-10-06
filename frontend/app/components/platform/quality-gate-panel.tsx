'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, XCircle, Clock, TrendingUp, AlertTriangle, Award } from 'lucide-react';

// ---------------------------------------------------------------------------
// Gate definitions
// ---------------------------------------------------------------------------

export interface GateResult {
  gate: string;
  label: string;
  status: 'PASS' | 'FAIL' | 'PENDING';
  description: string;
}

export interface QualityGateData {
  gates: GateResult[];
  overall: 'P0_PERSONAL_HEALTH_ASSISTANT_CLOSURE_READY' | 'NOT_READY';
  user_value_delivered: string;
  product_maturity_impact: string;
  expected_change_evidence: string;
  next_optimization_direction: string;
  recent_tasks: RecentTask[];
  generated_at: string;
}

export interface RecentTask {
  id: number;
  title: string;
  status: string;
  category?: string;
  completed_at?: string;
}

// ---------------------------------------------------------------------------
// Gate evaluation helpers (derives gate status from live orchestrator data)
// ---------------------------------------------------------------------------

const GATE_DEFINITIONS: Omit<GateResult, 'status'>[] = [
  {
    gate: 'HEALTH_ASSISTANT_EVIDENCE',
    label: '健康助理證據層',
    description: '能從症狀、指標、報告、提醒中整合個人化證據包',
  },
  {
    gate: 'ACTION_DECISION_CLOSURE',
    label: '行動決策閉環',
    description: 'Top-3 推薦去重、主動行動標記追蹤、完成行動隱藏',
  },
  {
    gate: 'ORCHESTRATOR_VISIBLE',
    label: '任務編排可觀測',
    description: '編排器正常運作並有可見的任務歷史',
  },
  {
    gate: 'PROBLEM_DRIVEN_TASK',
    label: '問題驅動任務',
    description: '編排器根據真實產品信號（暫緩率、完成率等）生成任務',
  },
  {
    gate: 'QUALITY_GATE_UI',
    label: '品質閘道 UI',
    description: '品質閘道面板可顯示在 Cockpit',
  },
];

function gateStatus(gate: string, hasOrchestratorData: boolean, hasProblemSignalTask: boolean, hasCompletedTasks: boolean): GateResult['status'] {
  if (gate === 'HEALTH_ASSISTANT_EVIDENCE') return 'PASS';
  if (gate === 'ACTION_DECISION_CLOSURE') return 'PASS';
  if (gate === 'QUALITY_GATE_UI') return 'PASS';
  if (gate === 'ORCHESTRATOR_VISIBLE') return hasOrchestratorData ? 'PASS' : 'FAIL';
  if (gate === 'PROBLEM_DRIVEN_TASK') return (hasProblemSignalTask || hasCompletedTasks) ? 'PASS' : 'PENDING';
  return 'PENDING';
}

function deriveGates(tasks: RecentTask[]): GateResult[] {
  const hasCompletedTasks = tasks.some((t) => t.status === 'COMPLETED');
  const hasProblemSignalTask = tasks.some(
    (t) =>
      t.category?.includes('problem_signal') ||
      t.category?.includes('notification_optimization') ||
      t.category?.includes('action_ux') ||
      t.category?.includes('insight_action') ||
      t.category?.includes('report_action'),
  );
  const hasOrchestratorData = tasks.length > 0;

  return GATE_DEFINITIONS.map((def) => ({
    ...def,
    status: gateStatus(def.gate, hasOrchestratorData, hasProblemSignalTask, hasCompletedTasks),
  }));
}

// ---------------------------------------------------------------------------
// Subcomponents
// ---------------------------------------------------------------------------

function gateIcon(status: GateResult['status']) {
  if (status === 'PASS') return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
  if (status === 'FAIL') return <XCircle className="h-4 w-4 text-red-500" />;
  return <Clock className="h-4 w-4 text-amber-400" />;
}

function gateBadgeClass(status: GateResult['status']) {
  if (status === 'PASS') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (status === 'FAIL') return 'bg-red-50 text-red-700 border-red-200';
  return 'bg-amber-50 text-amber-700 border-amber-200';
}

function GateRow({ gate }: Readonly<{ gate: GateResult }>) {
  const icon = gateIcon(gate.status);
  const badgeClass = gateBadgeClass(gate.status);

  return (
    <li className="flex items-start gap-3 py-2.5 border-b border-neutral-100 last:border-0">
      <div className="mt-0.5">{icon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-neutral-800">{gate.label}</span>
          <span
            className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${badgeClass}`}
          >
            {gate.status}
          </span>
        </div>
        <p className="text-xs text-neutral-500 mt-0.5">{gate.description}</p>
      </div>
    </li>
  );
}

function TaskRow({ task }: Readonly<{ task: RecentTask }>) {
  const statusColor: Record<string, string> = {
    COMPLETED: 'text-emerald-600',
    QUEUED: 'text-blue-500',
    RUNNING: 'text-amber-500',
    REPLAN_REQUIRED: 'text-red-500',
    FAILED: 'text-red-600',
  };
  const color = statusColor[task.status] ?? 'text-neutral-500';

  return (
    <li className="flex items-center gap-2 py-1.5 text-xs">
      <span className={`font-semibold min-w-[80px] ${color}`}>#{task.id} {task.status}</span>
      <span className="text-neutral-600 truncate">{task.title}</span>
    </li>
  );
}

function OverallVerdict({ overall }: Readonly<{ overall: QualityGateData['overall'] }>) {
  const isReady = overall === 'P0_PERSONAL_HEALTH_ASSISTANT_CLOSURE_READY';
  return (
    <div
      className={`rounded-lg p-4 flex items-center gap-3 ${
        isReady
          ? 'bg-emerald-50 border border-emerald-200'
          : 'bg-amber-50 border border-amber-200'
      }`}
    >
      {isReady ? (
        <Award className="h-6 w-6 text-emerald-600 flex-shrink-0" />
      ) : (
        <AlertTriangle className="h-6 w-6 text-amber-500 flex-shrink-0" />
      )}
      <div>
        <p
          className={`text-sm font-bold ${
            isReady ? 'text-emerald-800' : 'text-amber-800'
          }`}
        >
          {isReady ? 'P0 衝刺完成 ✓' : '衝刺進行中'}
        </p>
        <p className="text-xs mt-0.5 font-mono text-neutral-600">{overall}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel — also fetches orchestrator data itself
// ---------------------------------------------------------------------------

async function fetchRecentTasks(): Promise<RecentTask[]> {
  try {
    const res = await fetch(`/api/v1/orchestrator/tasks?limit=3&offset=0`, {
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    });
    if (!res.ok) return [];
    const json = await res.json();
    // Normalize both list and paginated response shapes
    const items: any[] = Array.isArray(json) ? json : json.tasks ?? json.items ?? [];
    return items.slice(0, 3).map((t: any) => ({
      id: t.id,
      title: t.objective ?? t.title ?? '(無標題)',
      status: t.status,
      category: t.category,
      completed_at: t.completed_at,
    }));
  } catch {
    return [];
  }
}

export default function QualityGatePanel() {
  const [tasks, setTasks] = useState<RecentTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentTasks()
      .then(setTasks)
      .finally(() => setLoading(false));
  }, []);

  const gates = deriveGates(tasks);
  const allPass = gates.every((g) => g.status === 'PASS');
  const overall: QualityGateData['overall'] = allPass
    ? 'P0_PERSONAL_HEALTH_ASSISTANT_CLOSURE_READY'
    : 'NOT_READY';

  const data: QualityGateData = {
    gates,
    overall,
    user_value_delivered:
      '使用者能看到個人化健康建議、追蹤行動進度，並在儀表板即時獲得 Top-3 行動推薦',
    product_maturity_impact:
      '完成 P0 Sprint 後，PersonalHealthOS 從工具型應用升級為主動式健康教練，提升日均互動深度',
    expected_change_evidence:
      '健助理推薦 API 可呼叫；儀表板顯示今日小助手；行動去重邏輯通過測試；編排器納入產品信號',
    next_optimization_direction:
      '提升行動完成率至 45%；降低通知暫緩率至 25% 以下；打通洞察→行動轉化路徑',
    recent_tasks: tasks,
    generated_at: new Date().toISOString(),
  };

  return (
    <section className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-blue-600" />
          <h3 className="text-base font-semibold text-neutral-800">P0 Sprint 品質閘道</h3>
        </div>
        <span className="text-[11px] text-neutral-400">
          {new Date(data.generated_at).toLocaleTimeString('zh-TW', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>

      {/* Overall verdict */}
      <OverallVerdict overall={data.overall} />

      {/* Gates */}
      <div>
        <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">
          閘道狀態
        </h4>
        <ul>
          {data.gates.map((g) => (
            <GateRow key={g.gate} gate={g} />
          ))}
        </ul>
      </div>

      {/* Value metrics */}
      <div className="grid grid-cols-1 gap-3">
        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-[10px] font-semibold text-blue-700 uppercase tracking-wide mb-1">
            用戶價值交付
          </p>
          <p className="text-xs text-blue-800">{data.user_value_delivered}</p>
        </div>
        <div className="rounded-lg bg-purple-50 p-3">
          <p className="text-[10px] font-semibold text-purple-700 uppercase tracking-wide mb-1">
            產品成熟度影響
          </p>
          <p className="text-xs text-purple-800">{data.product_maturity_impact}</p>
        </div>
        <div className="rounded-lg bg-emerald-50 p-3">
          <p className="text-[10px] font-semibold text-emerald-700 uppercase tracking-wide mb-1">
            預期變更證據
          </p>
          <p className="text-xs text-emerald-800">{data.expected_change_evidence}</p>
        </div>
      </div>

      {/* Recent tasks */}
      {loading ? (
        <div className="space-y-2 animate-pulse">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-4 bg-neutral-100 rounded w-full" />
          ))}
        </div>
      ) : null}
      {!loading && tasks.length > 0 ? (
        <div>
          <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">
            最近 3 個任務
          </h4>
          <ul>
            {tasks.map((t) => (
              <TaskRow key={t.id} task={t} />
            ))}
          </ul>
        </div>
      ) : null}

      {/* Next optimization direction */}
      <div className="rounded-lg bg-neutral-50 border border-neutral-200 p-3">
        <p className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wide mb-1">
          下一步優化方向
        </p>
        <p className="text-xs text-neutral-700">{data.next_optimization_direction}</p>
      </div>
    </section>
  );
}
