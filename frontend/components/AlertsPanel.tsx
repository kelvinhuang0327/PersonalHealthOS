type Props = {
  alerts?: Array<{
    id: string;
    severity: string;
    title: string;
    description: string;
    created_at: string;
    rule_id?: string;
    guideline_source?: string;
    confidence?: number;
    evidence_level?: string;
  }>;
};

export function AlertsPanel({ alerts = [] }: Props) {
  return (
    <div className="card">
      <h3>健康提醒</h3>
      {alerts.length === 0 && <p>目前無警示</p>}
      {alerts.map((a) => (
        <div key={a.id} className="alert">
          <strong>{a.title}</strong>
          <p>{a.description}</p>
          <p>
            {a.severity} / {new Date(a.created_at).toLocaleString()}
          </p>
          <p>
            規則：{a.rule_id || '-'} / 指引：{a.guideline_source || '-'} / 可信度：{a.confidence ?? '-'} / 證據等級：{' '}
            {a.evidence_level || '-'}
          </p>
        </div>
      ))}
    </div>
  );
}
