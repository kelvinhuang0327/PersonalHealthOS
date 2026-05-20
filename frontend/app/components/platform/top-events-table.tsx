import { Card } from '../ui/card'

export function TopEventsTable({ events }: { events: Array<{ event_name: string; count: number }> }) {
  return (
    <Card>
      <h3 className="mb-2 font-semibold">Top Events</h3>
      <div className="space-y-1 text-sm">
        {events.length === 0 ? <p className="text-slate-500">No events yet.</p> : null}
        {events.map((e) => (
          <div key={e.event_name} className="flex items-center justify-between rounded-md bg-slate-50 px-2 py-1">
            <span>{e.event_name}</span>
            <span className="font-medium">{e.count}</span>
          </div>
        ))}
      </div>
    </Card>
  )
}
