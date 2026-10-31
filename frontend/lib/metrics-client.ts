import { apiRequest, jsonBody } from './http-client'

export const metricsApi = {
  listMetrics: (limit = 50) => apiRequest<any[]>(`/metrics?limit=${limit}`, {}, { personScoped: true }),
  getLatestMetric: () => apiRequest<any>('/metrics/latest', {}, { personScoped: true }),
  createMetric: (payload: Record<string, unknown>) =>
    apiRequest<any>('/metrics', { method: 'POST', body: jsonBody(payload) }, { personScoped: true }),
}

export function getLatestMetricByPerson(personId: string) {
  return apiRequest<any>('/metrics/latest', {}, { personScoped: true, personId })
}
