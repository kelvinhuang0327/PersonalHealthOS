type Insight = {
  id: string;
  insight_type: string;
  severity: string;
  title: string;
  summary: string;
  recommendation?: string;
  generated_at: string;
  rule_id?: string;
  guideline_source?: string;
  confidence?: number;
  evidence_level?: string;
};

export function InsightsPanel({ insights = [] }: { insights?: Insight[] }) {
  return (
    <div className="card">
      <h3>健康洞察</h3>
      {insights.length === 0 && <p>目前無洞察結果</p>}
      {insights.map((insight) => (
        <div key={insight.id} className="alert">
          <strong>{insight.title}</strong>
          <p>{insight.summary}</p>
          <p>類型: {insight.insight_type}</p>
          <p>建議: {insight.recommendation || '-'}</p>
          <p>
            Rule: {insight.rule_id || '-'} / Guide: {insight.guideline_source || '-'} / Conf: {insight.confidence ?? '-'} /
            Evidence: {insight.evidence_level || '-'}
          </p>
        </div>
      ))}
    </div>
  );
}
