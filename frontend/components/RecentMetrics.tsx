type Metric = {
  id: string;
  recorded_at: string;
  systolic_bp?: number;
  diastolic_bp?: number;
  heart_rate?: number;
  blood_glucose?: number;
  weight_kg?: number;
  sleep_hours?: number;
};

export function RecentMetrics({ items = [] }: { items?: Metric[] }) {
  return (
    <div className="card">
      <h3>近期健康數據</h3>
      {items.map((m) => (
        <div key={m.id}>
          <p>{new Date(m.recorded_at).toLocaleString()}</p>
          <p>
            血壓：{m.systolic_bp ?? '-'} / {m.diastolic_bp ?? '-'} | 心率：{m.heart_rate ?? '-'} | 血糖：{' '}
            {m.blood_glucose ?? '-'}
          </p>
        </div>
      ))}
    </div>
  );
}
