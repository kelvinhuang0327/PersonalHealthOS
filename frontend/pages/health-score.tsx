import { FormEvent, useEffect, useState } from 'react';

import { Layout } from '../components/Layout';
import { api } from '../lib/api';

export default function HealthScorePage() {
  const [days, setDays] = useState(30);
  const [latest, setLatest] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);

  const refresh = async () => {
    const [latestScore, scoreHistory] = await Promise.all([api.getLatestHealthScore(), api.getHealthScoreHistory(20)]);
    setLatest(latestScore);
    setHistory(scoreHistory || []);
  };

  useEffect(() => {
    refresh();
  }, []);

  const onCalculate = async (e: FormEvent) => {
    e.preventDefault();
    await api.calculateHealthScore(days);
    await refresh();
  };

  return (
    <Layout>
      <div className="card">
        <h1>健康分數</h1>
        <form onSubmit={onCalculate}>
          <input type="number" value={days} onChange={(e) => setDays(Number(e.target.value))} min={7} max={365} />
          <button type="submit">重新計算分數</button>
        </form>
      </div>

      {latest && (
        <div className="card">
          <h2>最新分數：{latest.overall_score}</h2>
          <div className="grid">
            <div className="card">心血管：{latest.cardiovascular_score}</div>
            <div className="card">代謝：{latest.metabolic_score}</div>
            <div className="card">體重：{latest.weight_score}</div>
            <div className="card">睡眠：{latest.sleep_score}</div>
          </div>
          <pre>{JSON.stringify(latest.score_detail, null, 2)}</pre>
        </div>
      )}

      <div className="card">
        <h3>分數歷史</h3>
        <pre>{JSON.stringify(history, null, 2)}</pre>
      </div>
    </Layout>
  );
}
