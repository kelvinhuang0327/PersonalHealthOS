type Lab = {
  id: string;
  report_date?: string;
  report_type: string;
  created_at: string;
  abnormal_items: number;
};

export function RecentLabs({ items = [] }: { items?: Lab[] }) {
  return (
    <div className="card">
      <h3>近期檢驗</h3>
      {items.map((l) => (
        <div key={l.id}>
          <p>
            {l.report_type} / {l.report_date || '-'}
          </p>
          <p>
            異常項目: {l.abnormal_items} / {new Date(l.created_at).toLocaleString()}
          </p>
        </div>
      ))}
    </div>
  );
}
