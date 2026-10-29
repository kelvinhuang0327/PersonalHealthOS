import { apiRequest, jsonBody } from './http-client'

export type PersonRecord = {
  id: string
  display_name: string
  relationship?: string
  relationship_type?: string
  birth_date?: string | null
  gender?: string | null
  is_default?: boolean
  [key: string]: unknown
}

export const personsApi = {
  listPersons: () => apiRequest<PersonRecord[]>('/persons'),
  createPerson: (payload: Record<string, unknown>) => apiRequest<PersonRecord>('/persons', { method: 'POST', body: jsonBody(payload) }),
  updatePerson: (id: string, payload: Record<string, unknown>) => apiRequest<PersonRecord>(`/persons/${encodeURIComponent(id)}`, { method: 'PUT', body: jsonBody(payload) }),
  deletePerson: (id: string) => apiRequest<void>(`/persons/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}
