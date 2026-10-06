import { useEffect, useState } from 'react';

import { FlowBanner } from '../app/components/platform/flow-banner';
import { StateCard } from '../app/components/platform/state-card';
import { Layout } from '../components/Layout';
import { api } from '../lib/api';

export default function HealthInsightsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [status, setStatus] = useState<{ tone: 'loading' | 'success' | 'error' | 'info'; title: string; message: string } | null>(null);

  const refresh = () =>
    api
      .listInsights()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setInitialLoading(false));

  useEffect(() => {
    refresh();
  }, []);

  return (
    <Layout>
      <div className="card">
        <h1>健康洞察</h1>
        <p className="mt-2 text-sm text-slate-500">先產生洞察，再把它轉成可執行的行動。</p>
        <button
          onClick={async () => {
            setBusy(true);
            setStatus({ tone: 'loading', title: '正在產生洞察', message: '系統正在整理最近的資料與趨勢，請稍候。' });
            try {
              await api.generateInsights();
              await refresh();
              setStatus({ tone: 'success', title: '洞察已更新', message: '新的洞察已完成整理，現在可以直接加入行動或忽略。' });
            } catch (error) {
              setStatus({ tone: 'error', title: '產生失敗', message: '請稍後再試，或確認資料來源是否可用。' });
            } finally {
              setBusy(false);
            }
          }}
          disabled={busy}
        >
          {busy ? '產生中...' : '產生洞察'}
        </button>
        <div className="mt-4 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
          <p className="font-semibold text-slate-900">使用方式</p>
          <p className="mt-1">按下產生後，頁面會先顯示處理中，再更新成新洞察。沒有資料時，會明確告知你目前還沒有可分析內容。</p>
        </div>
        {status ? (
          <div className="mt-4">
            <FlowBanner tone={status.tone} title={status.title} message={status.message} />
          </div>
        ) : null}
      </div>

      <div className="card">
        {initialLoading ? (
          <StateCard
            tone="loading"
            title="正在載入健康洞察"
            description="系統正在整理最新資料與既有洞察，請稍候。"
            badgeText="頁面載入中"
          />
        ) : items.length === 0 ? (
          <StateCard
            tone="info"
            title="目前沒有可顯示的洞察"
            description="按上方「產生洞察」後，系統會整理最新健康資料、趨勢與提醒，產出可行的下一步建議。"
            actionLabel={busy ? '洞察產生中' : '產生洞察'}
            onAction={async () => {
              if (busy) return;
              setBusy(true);
              setStatus({ tone: 'loading', title: '正在產生洞察', message: '系統正在整理最近的資料與趨勢，請稍候。' });
              try {
                await api.generateInsights();
                await refresh();
                setStatus({ tone: 'success', title: '洞察已更新', message: '新的洞察已完成整理，現在可以直接加入行動或忽略。' });
              } catch (error) {
                setStatus({ tone: 'error', title: '產生失敗', message: '請稍後再試，或確認資料來源是否可用。' });
              } finally {
                setBusy(false);
              }
            }}
            badgeText="空狀態"
          />
        ) : (
          items.map((row) => (
            <div key={row.id} className="alert">
              <strong>{row.title}</strong>
              <p>{row.summary}</p>
              <p>類型：{row.insight_type}</p>
              <p>建議：{row.recommendation || '-'}</p>
              <button
                className="secondary"
                onClick={async () => {
                  await api.dismissInsight(row.id);
                  refresh();
                }}
              >
                忽略
              </button>
            </div>
          ))
        )}
      </div>
    </Layout>
  );
}
