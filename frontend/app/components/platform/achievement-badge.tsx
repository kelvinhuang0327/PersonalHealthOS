import { Badge } from '../ui/badge'

export function AchievementBadge({ achieved, label }: { achieved: boolean; label: string }) {
  if (!achieved) return null
  return <Badge className="bg-purple-100 text-purple-700">🏆 {label}</Badge>
}
