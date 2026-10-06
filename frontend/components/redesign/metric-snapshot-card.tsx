import { Card } from '../../app/components/ui/card';
import { cn } from '../../app/components/ui/utils';

type Point = { value: number };

function buildSparkline(points: Point[]) {
  if (!points.length) return '';
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return points
    .map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * 100;
      const y = 100 - ((point.value - min) / range) * 100;
      return `${x},${y}`;
    })
    .join(' ');
}

export function MetricSnapshotCard({
  title,
  value,
  helper,
  status = 'neutral',
  points = [],
}: {
  title: string;
  value: string;
  helper: string;
  status?: 'neutral' | 'good' | 'warning' | 'danger';
  points?: Point[];
}) {
  const strokeClass =
    status === 'good'
      ? 'stroke-emerald-500'
      : status === 'warning'
      ? 'stroke-amber-500'
      : status === 'danger'
      ? 'stroke-rose-500'
      : 'stroke-cyan-600';
  const badgeClass =
    status === 'good'
      ? 'chip chip-success'
      : status === 'warning'
      ? 'chip chip-warning'
      : status === 'danger'
      ? 'chip chip-danger'
      : 'chip chip-primary';

  return (
    <Card className="rounded-[24px] p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-500">{title}</p>
          <p className="metric-value mt-2 text-slate-950">{value}</p>
        </div>
        <span className={badgeClass}>{status === 'good' ? '穩定' : status === 'warning' ? '留意' : status === 'danger' ? '異常' : '摘要'}</span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-600">{helper}</p>
      <div className="mt-4 rounded-2xl bg-slate-50 p-3">
        {points.length > 1 ? (
          <svg viewBox="0 0 100 100" className="h-14 w-full">
            <polyline
              fill="none"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={buildSparkline(points)}
              className={cn('fill-none', strokeClass)}
            />
          </svg>
        ) : (
          <div className="flex h-14 items-center text-sm text-slate-400">資料不足，尚未形成趨勢。</div>
        )}
      </div>
    </Card>
  );
}
