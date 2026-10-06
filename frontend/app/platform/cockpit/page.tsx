'use client';

import Link from 'next/link';
import QualityGatePanel from '../../components/platform/quality-gate-panel';

export default function CockpitHubPage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200 px-4 py-12">
      <div className="max-w-3xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold">🚀 AI 駕駛艙</h1>
          <p className="text-zinc-500 mt-2">選擇要進入的模組</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link href="/platform/cockpit/orchestration" className="block group">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-3 hover:border-blue-600 transition-colors">
              <div className="text-3xl">🤖</div>
              <h2 className="text-xl font-semibold group-hover:text-blue-400 transition-colors">任務排程</h2>
              <p className="text-sm text-zinc-500">
                Planner / Worker 排程控制、任務列表、執行記錄、Provider 設定
              </p>
              <div className="text-blue-500 text-sm mt-2">前往 →</div>
            </div>
          </Link>

          <Link href="/platform/cockpit/cto-review" className="block group">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-3 hover:border-purple-600 transition-colors">
              <div className="text-3xl">🧠</div>
              <h2 className="text-xl font-semibold group-hover:text-purple-400 transition-colors">CTO 審核</h2>
              <p className="text-sm text-zinc-500">
                任務品質審核、決策分析、優先 Backlog 管理、Adaptive Policy
              </p>
              <div className="text-purple-500 text-sm mt-2">前往 →</div>
            </div>
          </Link>
        </div>

        {/* ── P0 Sprint Quality Gate ──────────────────────────────────────── */}
        <QualityGatePanel />
      </div>
    </div>
  );
}

