import type { HealthAction } from './actions'
import { apiRequest, jsonBody, queryPath } from './http-client'

export const actionsApi = {
  getActions: (personId?: string, dueWithinDays?: number) =>
    apiRequest<HealthAction[]>(queryPath('/actions', { due_within_days: dueWithinDays }), {}, { personScoped: true, personId }),
  createAction: (payload: Partial<HealthAction> & Record<string, unknown>) =>
    apiRequest<HealthAction>('/actions', { method: 'POST', body: jsonBody(payload) }, { personScoped: true }),
  getActionOutcomes: (id: string) => apiRequest<any[]>(`/actions/${encodeURIComponent(id)}/outcomes`),
  updateAction: (id: string, payload: Partial<HealthAction> & Record<string, unknown>) =>
    apiRequest<HealthAction>(`/actions/${encodeURIComponent(id)}`, { method: 'PATCH', body: jsonBody(payload) }),
  deleteAction: (id: string) => apiRequest<void>(`/actions/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}
