import { Badge } from '../ui/badge'

export function StreakBadge({ streak }: { streak: number }) {
  if (!streak) return <Badge className="bg-slate-200 text-slate-700">streak 0</Badge>
  const cls = streak >= 7 ? 'bg-emerald-100 text-emerald-700' : 'bg-sky-100 text-sky-700'
  return <Badge className={cls}>{streak} day streak</Badge>
}
