import { useCallback, useEffect, useState } from 'react';
import { Layout } from '../components/Layout';
import { api } from '../lib/api';

export default function ExternalMetricsPage() {
  const [history, setHistory] = useState<any[]>([]);
  const [trend, setTrend] = useState<any>(null);
  const [metric, setMetric] = useState('steps');

  const refresh = useCallback(async () => {
    setHistory(await api.listExternalMetrics());
    setTrend(await api.getExternalMetricTrends(metric));
  }, [metric]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <Layout>
      <div className="card">
        <h1>外部 API 身體指數紀錄</h1>
        <button
          onClick={async () => {
            await api.syncExternalMetrics();
            await refresh();
          }}
        >
          手動同步
        </button>
        <select value={metric} onChange={(e) => setMetric(e.target.value)}>
          <option value="steps">步數</option>
          <option value="heart_rate">心率</option>
          <option value="blood_glucose">血糖</option>
          <option value="sleep_hours">睡眠</option>
        </select>
      </div>
      <div className="card">
        <h3>歷史紀錄</h3>
        <pre>{JSON.stringify(history, null, 2)}</pre>
      </div>
      <div className="card">
        <h3>趨勢顯示</h3>
        <pre>{JSON.stringify(trend, null, 2)}</pre>
      </div>
    </Layout>
  );
}
