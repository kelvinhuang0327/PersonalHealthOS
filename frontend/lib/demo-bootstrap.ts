import type { HealthAction } from './actions'
import type { AnalyticsEvent } from './analytics'

type PersonLite = { id: string; display_name: string }

const ACTION_PREFIX = 'health_actions_'
const ANALYTICS_KEY = 'health_platform_analytics_events_v1'
const SESSION_KEY = 'health_platform_session_id_v1'

function isoDaysAgo(days: number) {
  return new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString()
}

function buildActions(persons: PersonLite[]): HealthAction[] {
  const byName = new Map(persons.map((p) => [p.display_name, p.id]))
  const selfId = byName.get('本人') || persons[0]?.id || 'person-self'
  const childId = byName.get('小孩') || persons[1]?.id || selfId
  const parentId = byName.get('父母') || persons[2]?.id || selfId
  return [
    {
      id: 'act-self-1',
      person_id: selfId,
      source_type: 'insight',
      source_id: 'insight-self-trend',
      title: '每日晚餐後步行 30 分鐘',
      description: '配合血壓與尿酸改善，維持中等強度步行。',
      action_type: 'habit',
      priority: 'high',
      status: 'in_progress',
      frequency: 'daily',
      streak: 5,
      last_completed_at: isoDaysAgo(1),
      impact_status: 'improved',
      reminder_status: 'none',
      confidence: 0.84,
      evidence_level: 'A',
      guideline_source: 'ACC/AHA 2017',
      rule_id: 'trend_bp_sleep_link',
      category: 'cardio',
      created_at: isoDaysAgo(12),
    },
    {
      id: 'act-self-2',
      person_id: selfId,
      source_type: 'alert',
      source_id: 'alert-self-bp',
      title: '每週三次固定時段量血壓',
      description: '早晚各一次，連續兩週回看趨勢。',
      action_type: 'monitor',
      priority: 'high',
      status: 'todo',
      frequency: 'weekly',
      streak: 1,
      impact_status: 'no_change',
      reminder_status: 'overdue',
      confidence: 0.8,
      evidence_level: 'B',
      guideline_source: 'Rule Library',
      rule_id: 'bp_high_3times',
      category: 'risk',
      created_at: isoDaysAgo(8),
    },
    {
      id: 'act-self-3',
      person_id: selfId,
      source_type: 'recommendation',
      source_id: 'rec-self-low-purine',
      title: '低普林飲食紀錄',
      description: '追蹤一週飲食並減少高普林食物攝取。',
      action_type: 'lifestyle',
      priority: 'medium',
      status: 'done',
      frequency: 'daily',
      streak: 7,
      completed_at: isoDaysAgo(0),
      last_completed_at: isoDaysAgo(0),
      impact_status: 'improved',
      reminder_status: 'none',
      confidence: 0.79,
      evidence_level: 'B',
      guideline_source: 'EULAR Gout Guideline',
      rule_id: 'hyperuricemia_followup',
      category: 'metabolic',
      created_at: isoDaysAgo(15),
    },
    {
      id: 'act-child-1',
      person_id: childId,
      source_type: 'recommendation',
      source_id: 'rec-child-sleep',
      title: '睡前 30 分鐘不看螢幕',
      description: '建立規律作息，降低鼻塞不適感。',
      action_type: 'habit',
      priority: 'low',
      status: 'snoozed',
      frequency: 'daily',
      streak: 2,
      impact_status: 'no_change',
      reminder_status: 'no_data',
      confidence: 0.68,
      evidence_level: 'C',
      guideline_source: 'Pediatric Sleep Hygiene',
      rule_id: 'child_sleep_consistency',
      category: 'lifestyle',
      created_at: isoDaysAgo(6),
    },
    {
      id: 'act-parent-1',
      person_id: parentId,
      source_type: 'alert',
      source_id: 'alert-parent-metabolic',
      title: '父母代謝風險追蹤清單',
      description: '每週記錄血壓、體重與空腹血糖。',
      action_type: 'follow_up',
      priority: 'high',
      status: 'todo',
      frequency: 'weekly',
      streak: 0,
      impact_status: 'worse',
      reminder_status: 'risk_up',
      confidence: 0.88,
      evidence_level: 'A',
      guideline_source: 'ADA + ESC Guidelines',
      rule_id: 'parent_metabolic_cluster',
      category: 'clinical',
      created_at: isoDaysAgo(10),
    },
  ]
}

function buildAnalyticsEvents(persons: PersonLite[]): AnalyticsEvent[] {
  const byName = new Map(persons.map((p) => [p.display_name, p.id]))
  const selfId = byName.get('本人') || persons[0]?.id
  const parentId = byName.get('父母') || persons[0]?.id
  const userId = 'demo-user-local'
  const session = 'demo-session-seeded'
  const steps = [
    ['user_open_app', 18, '/platform/dashboard'],
    ['view_dashboard', 18, '/platform/dashboard'],
    ['view_insights', 14, '/platform/insights'],
    ['create_action', 9, '/platform/insights'],
    ['checkin_action', 7, '/platform/actions'],
    ['complete_action', 5, '/platform/actions'],
    ['view_weekly_report', 8, '/platform/weekly-report'],
    ['switch_person', 6, '/platform/dashboard'],
  ] as const
  const events: AnalyticsEvent[] = []
  let idx = 0
  for (const [name, count, page] of steps) {
    for (let i = 0; i < count; i += 1) {
      const personId = name === 'switch_person' && i % 2 === 0 ? parentId : selfId
      events.push({
        id: `demo_evt_${idx++}`,
        event_name: name,
        user_id: userId,
        person_id: personId,
        session_id: session,
        page,
        timestamp: isoDaysAgo((count - i) % 15),
        metadata:
          name === 'switch_person'
            ? { from: selfId, to: parentId }
            : name.includes('action')
            ? { action_id: `act-${i % 3}` }
            : undefined,
      })
    }
  }
  return events.sort((a, b) => (a.timestamp > b.timestamp ? 1 : -1))
}

export function seedDemoClientData(persons: PersonLite[]) {
  if (typeof window === 'undefined') return
  const actions = buildActions(persons)
  for (const p of persons) {
    const rows = actions.filter((a) => a.person_id === p.id)
    localStorage.setItem(`${ACTION_PREFIX}${p.id}`, JSON.stringify(rows))
  }
  localStorage.setItem(ANALYTICS_KEY, JSON.stringify(buildAnalyticsEvents(persons)))
  localStorage.setItem(SESSION_KEY, 'demo-session-seeded')
}

export function resetDemoClientData(persons: PersonLite[]) {
  if (typeof window === 'undefined') return
  for (const p of persons) {
    localStorage.removeItem(`${ACTION_PREFIX}${p.id}`)
  }
  localStorage.removeItem(ANALYTICS_KEY)
  localStorage.removeItem(SESSION_KEY)
}
