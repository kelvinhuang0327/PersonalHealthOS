export type QuickCheckInType = 'ok' | 'not_ok' | 'symptom' | 'action'

export type QuickCheckInRecord = {
  id: string
  person_id: string
  type: QuickCheckInType
  label: string
  created_at: string
}

function getStorageKey(personId: string) {
  return `quick_checkins_${personId || 'default'}`
}

function isToday(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return false
  const now = new Date()
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  )
}

export function readQuickCheckIns(personId: string): QuickCheckInRecord[] {
  if (typeof window === 'undefined') return []
  const raw = localStorage.getItem(getStorageKey(personId))
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as QuickCheckInRecord[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function appendQuickCheckIn(personId: string, record: Omit<QuickCheckInRecord, 'person_id'>) {
  if (typeof window === 'undefined') return []
  const next = [
    {
      ...record,
      person_id: personId,
    },
    ...readQuickCheckIns(personId),
  ].slice(0, 100)
  localStorage.setItem(getStorageKey(personId), JSON.stringify(next))
  return next
}

export function getTodayQuickCheckInCount(personId: string) {
  return readQuickCheckIns(personId).filter((record) => isToday(record.created_at)).length
}
