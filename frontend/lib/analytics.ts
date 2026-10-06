export type AnalyticsEvent = {
  id: string;
  event_name: string;
  user_id?: string;
  person_id?: string;
  session_id?: string;
  timestamp: string;
  page?: string;
  metadata?: Record<string, any>;
};

const EVENTS_KEY = 'health_platform_analytics_events_v1';
const SESSION_KEY = 'health_platform_session_id_v1';
const analyticsEnabled = process.env.NEXT_PUBLIC_ENABLE_ANALYTICS !== 'false';

function safeRead(): AnalyticsEvent[] {
  if (typeof window === 'undefined') return [];
  const raw = localStorage.getItem(EVENTS_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as AnalyticsEvent[];
  } catch {
    return [];
  }
}

function safeWrite(events: AnalyticsEvent[]) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(EVENTS_KEY, JSON.stringify(events.slice(-5000)));
}

function getSessionId() {
  if (typeof window === 'undefined') return '';
  const existing = localStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const created = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  localStorage.setItem(SESSION_KEY, created);
  return created;
}

function getUserId() {
  if (typeof window === 'undefined') return undefined;
  return localStorage.getItem('user_id') || undefined;
}

function getPersonId() {
  if (typeof window === 'undefined') return undefined;
  return localStorage.getItem('person_id') || undefined;
}

export function trackEvent(eventName: string, payload?: { page?: string; metadata?: Record<string, any> }) {
  if (!analyticsEnabled) return null;
  const events = safeRead();
  const event: AnalyticsEvent = {
    id: `evt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    event_name: eventName,
    user_id: getUserId(),
    person_id: getPersonId(),
    session_id: getSessionId(),
    timestamp: new Date().toISOString(),
    page: payload?.page,
    metadata: payload?.metadata,
  };
  events.push(event);
  safeWrite(events);
  return event;
}

export function getEvents() {
  return safeRead();
}

export function clearEvents() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(EVENTS_KEY);
}

export function exportEvents() {
  return JSON.stringify(safeRead(), null, 2);
}

export function flushEvents() {
  return safeRead();
}

type FunnelStep = { step: string; event: string };

const FUNNEL_STEPS: FunnelStep[] = [
  { step: 'App Open', event: 'user_open_app' },
  { step: 'View Dashboard', event: 'view_dashboard' },
  { step: 'View Insight', event: 'view_insights' },
  { step: 'Create Action', event: 'create_action' },
  { step: 'Check-in Action', event: 'checkin_action' },
  { step: 'Complete Action', event: 'complete_action' },
];

function dateKey(iso: string) {
  return iso.slice(0, 10);
}

function visitorId(e: AnalyticsEvent) {
  return e.user_id || e.person_id || e.session_id || 'anon';
}

export function getAnalyticsSummary() {
  const events = safeRead();
  const now = new Date();
  const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

  const visitorsByDate = new Map<string, Set<string>>();
  const firstSeen = new Map<string, string>();
  const allVisitors = new Set<string>();
  const topEventsMap = new Map<string, number>();

  for (const e of events) {
    const vId = visitorId(e);
    allVisitors.add(vId);
    const d = dateKey(e.timestamp);
    if (!visitorsByDate.has(d)) visitorsByDate.set(d, new Set());
    visitorsByDate.get(d)!.add(vId);
    if (!firstSeen.has(vId) || e.timestamp < firstSeen.get(vId)!) firstSeen.set(vId, e.timestamp);
    topEventsMap.set(e.event_name, (topEventsMap.get(e.event_name) || 0) + 1);
  }

  const dauVisitors = new Set(events.filter((e) => new Date(e.timestamp) >= dayAgo).map(visitorId));
  const wauVisitors = new Set(events.filter((e) => new Date(e.timestamp) >= weekAgo).map(visitorId));
  const mauVisitors = new Set(events.filter((e) => new Date(e.timestamp) >= monthAgo).map(visitorId));
  const dau = dauVisitors.size;
  const wau = wauVisitors.size;
  const mau = mauVisitors.size;
  const stickiness = mau > 0 ? dau / mau : 0;

  const funnel = FUNNEL_STEPS.map((s) => {
    const set = new Set(events.filter((e) => e.event_name === s.event).map(visitorId));
    return { step: s.step, count: set.size };
  });
  const funnelBase = funnel[0]?.count || 0;
  const funnelWithRate = funnel.map((f) => ({
    ...f,
    rate: funnelBase > 0 ? f.count / funnelBase : 0,
  }));

  const retained = (days: number) => {
    if (firstSeen.size < 3) return null;
    let eligible = 0;
    let kept = 0;
    for (const [vId, first] of firstSeen.entries()) {
      const firstDate = new Date(first);
      const target = new Date(firstDate.getTime() + days * 24 * 60 * 60 * 1000);
      if (target <= now) {
        eligible += 1;
        const hasReturn = events.some((e) => visitorId(e) === vId && new Date(e.timestamp) >= target);
        if (hasReturn) kept += 1;
      }
    }
    if (!eligible) return null;
    return kept / eligible;
  };

  const topEvents = [...topEventsMap.entries()]
    .map(([event_name, count]) => ({ event_name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  const recentEvents = [...events].sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1)).slice(0, 20);

  return {
    kpi: { dau, wau, mau, stickiness },
    retention: { day1: retained(1), day7: retained(7), day30: retained(30) },
    funnel: funnelWithRate,
    topEvents,
    recentEvents,
  };
}
