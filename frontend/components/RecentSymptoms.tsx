type Symptom = {
  id: string;
  symptom: string;
  occurred_at: string;
  note?: string;
  estimated_start_date?: string;
  estimated_duration_days?: number;
};

export function RecentSymptoms({ items = [] }: { items?: Symptom[] }) {
  return (
    <div className="card">
      <h3>近期症狀</h3>
      {items.map((s) => (
        <div key={s.id}>
          <strong>{s.note || s.symptom}</strong>
          <p>{new Date(s.occurred_at).toLocaleString()}</p>
          <p>
            推算：{s.estimated_start_date || '-'} / {s.estimated_duration_days ?? '-'} 天
          </p>
        </div>
      ))}
    </div>
  );
}
