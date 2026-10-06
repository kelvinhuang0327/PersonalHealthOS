type Props = {
  healthScore?: {
    overall_score?: number;
    components?: Record<string, number>;
  };
};

export function HealthScoreCard({ healthScore }: Props) {
  return (
    <div className="card">
      <h3>健康分數</h3>
      <p style={{ fontSize: 28, fontWeight: 700 }}>{healthScore?.overall_score ?? '-'}</p>
      <pre>{JSON.stringify(healthScore?.components || {}, null, 2)}</pre>
    </div>
  );
}
