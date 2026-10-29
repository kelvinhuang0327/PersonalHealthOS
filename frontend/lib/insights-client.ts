import { apiRequest } from './http-client'

export const insightsApi = {
  listInsights: () => apiRequest<any[]>('/insights', {}, { personScoped: true }),
  generateInsights: () => apiRequest<any[]>('/insights/generate', { method: 'POST' }, { personScoped: true }),
  dismissInsight: (id: string) => apiRequest<any>(`/insights/${encodeURIComponent(id)}/dismiss`, { method: 'POST' }, { personScoped: true }),
}
