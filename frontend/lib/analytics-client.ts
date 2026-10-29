import { apiRequest } from './http-client'

export const analyticsApi = {
  getTrendAnalysis: (days = 90) => apiRequest<any>(`/analytics/trends?days=${days}`, {}, { personScoped: true }),
  getHealthAnalysis: () => apiRequest<any>('/analytics/health-analysis', {}, { personScoped: true }),
}
