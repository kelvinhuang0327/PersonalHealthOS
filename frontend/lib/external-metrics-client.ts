import { apiRequest } from './http-client'

export const externalMetricsApi = {
  listExternalMetrics: (days = 30) => apiRequest<any[]>(`/external-metrics/history?days=${days}`, {}, { personScoped: true }),
  getExternalMetricTrends: (metric = 'steps', days = 30) =>
    apiRequest<any>(`/external-metrics/trends?metric=${encodeURIComponent(metric)}&days=${days}`, {}, { personScoped: true }),
  syncExternalMetrics: () => apiRequest<any>('/external-metrics/sync', { method: 'POST' }, { personScoped: true }),
}
