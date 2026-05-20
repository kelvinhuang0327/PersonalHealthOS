export type NotificationSnoozeRecord = {
  key: string
  title: string
  source_type: string
  source_id: string
  snoozed_until?: string
  snoozed_at?: string
  snooze_reason?: string
  resurface_count?: number
  resurfaced_at?: string
}

export const DEFAULT_NOTIFICATION_SNOOZE_HOURS = 24

function getStorageKey(personId: string) {
  return `notifications_center_lifecycle_${personId || 'default'}`
}

function parseDate(value?: string) {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function getNotificationStorageKey(personId: string) {
  return getStorageKey(personId)
}

export function readNotificationSnoozeRecords(personId: string): NotificationSnoozeRecord[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(getStorageKey(personId))
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as NotificationSnoozeRecord[]) : []
  } catch {
    return []
  }
}

export function writeNotificationSnoozeRecords(personId: string, records: NotificationSnoozeRecord[]) {
  if (typeof window === 'undefined') return
  localStorage.setItem(getStorageKey(personId), JSON.stringify(records))
}

export function hydrateNotificationSnoozeRecords(personId: string, now = new Date()) {
  const records = readNotificationSnoozeRecords(personId)
  let changed = false

  const next = records.map((record) => {
    const until = parseDate(record.snoozed_until)
    if (!until || until.getTime() > now.getTime()) return record

    changed = true
    return {
      ...record,
      resurface_count: (record.resurface_count || 0) + 1,
      resurfaced_at: now.toISOString(),
      snoozed_until: undefined,
      snoozed_at: undefined,
      snooze_reason: undefined,
    }
  })

  if (changed) {
    writeNotificationSnoozeRecords(personId, next)
  }

  return next
}

export function saveNotificationSnooze(
  personId: string,
  record: Pick<NotificationSnoozeRecord, 'key' | 'title' | 'source_type' | 'source_id'> & {
    snoozeReason?: string
    snoozeHours?: number
  }
) {
  const now = new Date()
  const hours = record.snoozeHours || DEFAULT_NOTIFICATION_SNOOZE_HOURS
  const until = new Date(now.getTime() + hours * 60 * 60 * 1000).toISOString()
  const rows = hydrateNotificationSnoozeRecords(personId, now)
  const existing = rows.find((row) => row.key === record.key)
  const next = rows.filter((row) => row.key !== record.key)

  next.push({
    key: record.key,
    title: record.title,
    source_type: record.source_type,
    source_id: record.source_id,
    snoozed_until: until,
    snoozed_at: now.toISOString(),
    snooze_reason: record.snoozeReason,
    resurface_count: existing?.resurface_count || 0,
    resurfaced_at: existing?.resurfaced_at,
  })

  writeNotificationSnoozeRecords(personId, next)
  return next
}

export function clearNotificationSnooze(personId: string, key: string) {
  const rows = hydrateNotificationSnoozeRecords(personId)
  const next = rows.filter((row) => row.key !== key)
  writeNotificationSnoozeRecords(personId, next)
  return next
}

export function isSnoozeActive(record?: NotificationSnoozeRecord | null, now = new Date()) {
  const until = parseDate(record?.snoozed_until)
  return Boolean(until && until.getTime() > now.getTime())
}

export function isResurfacedToday(record?: NotificationSnoozeRecord | null, now = new Date()) {
  const resurfacedAt = parseDate(record?.resurfaced_at)
  if (!resurfacedAt) return false
  return resurfacedAt.toDateString() === now.toDateString()
}
