type TrendPoint = { recorded_at: string; value: number };

export function TrendCharts({ trends }: { trends?: Record<string, TrendPoint[]> }) {
  return (
    <div className="card">
      <h3>Trend Charts</h3>
      <pre>{JSON.stringify(trends || {}, null, 2)}</pre>
    </div>
  );
}
