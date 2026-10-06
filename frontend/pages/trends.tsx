import { FormEvent, useEffect, useState } from 'react';

import { Layout } from '../components/Layout';
import { api } from '../lib/api';

export default function TrendsPage() {
  const [days, setDays] = useState(90);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const run = async () => {
      const res = await api.getTrendAnalysis(days);
      setData(res);
    };
    void run();
  }, [days]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const res = await api.getTrendAnalysis(days);
    setData(res);
  };

  return (
    <Layout>
      <div className="card">
        <h1>健康趨勢分析</h1>
        <form onSubmit={onSubmit}>
          <input type="number" value={days} onChange={(e) => setDays(Number(e.target.value))} min={7} max={365} />
          <button type="submit">分析趨勢</button>
        </form>
      </div>

      <div className="grid">
        {(data?.summaries || []).map((s: any) => (
          <div key={s.metric} className="card">
            <h3>{s.metric}</h3>
            <p>方向：{s.direction}</p>
            <p>資料點數：{s.points}</p>
            <p>起始值：{s.first_value ?? 'N/A'}</p>
            <p>最新值：{s.last_value ?? 'N/A'}</p>
            <p>變化百分比：{s.change_percent ?? 'N/A'}</p>
            <p>每日斜率：{s.slope_per_day ?? 'N/A'}</p>
          </div>
        ))}
      </div>
    </Layout>
  );
}
