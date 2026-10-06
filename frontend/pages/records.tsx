import { FormEvent, useEffect, useState } from 'react';
import { Layout } from '../components/Layout';
import { api } from '../lib/api';

export default function RecordsPage() {
  const [records, setRecords] = useState<any[]>([]);
  const [form, setForm] = useState<any>({ recorded_at: new Date().toISOString() });

  const refresh = () => api.listMetrics().then(setRecords).catch(() => setRecords([]));

  useEffect(() => {
    refresh();
  }, []);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await api.createMetric(form);
    setForm({ recorded_at: new Date().toISOString() });
    refresh();
  };

  return (
      <Layout>
      <div className="card">
        <h1>健康紀錄</h1>
        <form onSubmit={onSubmit}>
          <input type="datetime-local" onChange={(e) => setForm({ ...form, recorded_at: new Date(e.target.value).toISOString() })} />
          <input placeholder="收縮壓" type="number" onChange={(e) => setForm({ ...form, systolic_bp: Number(e.target.value) })} />
          <input placeholder="舒張壓" type="number" onChange={(e) => setForm({ ...form, diastolic_bp: Number(e.target.value) })} />
          <input placeholder="心率" type="number" onChange={(e) => setForm({ ...form, heart_rate: Number(e.target.value) })} />
          <input placeholder="血糖" type="number" onChange={(e) => setForm({ ...form, blood_glucose: Number(e.target.value) })} />
          <input placeholder="體重 (kg)" type="number" onChange={(e) => setForm({ ...form, weight_kg: Number(e.target.value) })} />
          <input placeholder="睡眠時數" type="number" onChange={(e) => setForm({ ...form, sleep_hours: Number(e.target.value) })} />
          <textarea placeholder="備註" onChange={(e) => setForm({ ...form, note: e.target.value })} />
          <button type="submit">新增紀錄</button>
        </form>
      </div>

      <div className="card">
        <h3>近期紀錄</h3>
        <pre>{JSON.stringify(records, null, 2)}</pre>
      </div>
    </Layout>
  );
}
