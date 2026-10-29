const API_BASE_URL = (() => {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1'
  const normalized = raw.replace(/\/$/, '')
  return normalized.endsWith('/api/v1') ? normalized : `${normalized}/api/v1`
})()

export type ApiRequestOptions = {
  personScoped?: boolean
  personId?: string | null
}

function selectedPersonId() {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('person_id')
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  options: ApiRequestOptions = {},
): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`)
  if (options.personScoped) {
    const personId = options.personId ?? selectedPersonId()
    if (personId && !url.searchParams.has('person_id')) url.searchParams.set('person_id', personId)
  }

  const headers = new Headers(init.headers)
  const isFormData = typeof FormData !== 'undefined' && init.body instanceof FormData
  if (!isFormData && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token')
    if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(url.toString(), { ...init, headers })
  if (response.status === 401 && typeof window !== 'undefined') {
    localStorage.removeItem('token')
    window.location.href = '/platform/login'
    throw new Error('Unauthenticated')
  }
  if (!response.ok) {
    const message = await response.text().catch(() => response.statusText)
    throw Object.assign(new Error(message || response.statusText), { status: response.status })
  }
  if (response.status === 204) return undefined as T
  const body = await response.text()
  return body ? (JSON.parse(body) as T) : (undefined as T)
}

export function jsonBody(value: unknown): string {
  return JSON.stringify(value)
}

export function queryPath(path: string, values: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined) query.set(key, String(value))
  }
  const suffix = query.toString()
  return suffix ? `${path}?${suffix}` : path
}
