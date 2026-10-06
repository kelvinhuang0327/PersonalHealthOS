import { Card } from '../ui/card'
import type { AnalyticsEvent } from '../../../lib/analytics'

export function RecentEventsList({ events }: { events: AnalyticsEvent[] }) {
  return (
    <Card>
      <h3 className="mb-2 font-semibold">Recent Events</h3>
      <div className="max-h-80 space-y-1 overflow-auto text-xs">
        {events.length === 0 ? <p className="text-slate-500">No events yet.</p> : null}
        {events.map((e) => (
          <div key={e.id} className="rounded-md border border-slate-100 p-2">
            <div className="flex items-center justify-between">
              <span className="font-medium">{e.event_name}</span>
              <span className="text-slate-500">{new Date(e.timestamp).toLocaleString()}</span>
            </div>
            <div className="text-slate-500">
              person: {e.person_id || '-'} {e.page ? `· page: ${e.page}` : ''}
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
