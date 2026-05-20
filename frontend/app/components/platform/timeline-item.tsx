import { Card } from '../ui/card'

export function TimelineItem({ item }: { item: any }) {
  return (
    <div className="relative pl-6">
      <span className="absolute left-0 top-3 h-2 w-2 rounded-full bg-sky-500" />
      <Card className="mb-3">
        <p className="font-semibold">{item.title || item.label}</p>
        <p className="text-xs text-slate-500">{item.start_date} ~ {item.end_date || item.start_date}</p>
        <p className="text-sm">{item.description || item.type}</p>
      </Card>
    </div>
  )
}
