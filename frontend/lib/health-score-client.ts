import { apiRequest, jsonBody } from './http-client'

export const healthScoreApi = {
  getLatestHealthScore: () => apiRequest<any>('/health-score/latest', {}, { personScoped: true }),
  getHealthScoreHistory: (limit = 20) => apiRequest<any[]>(`/health-score/history?limit=${limit}`, {}, { personScoped: true }),
  calculateHealthScore: (days: number) =>
    apiRequest<any>('/health-score/calculate', { method: 'POST', body: jsonBody({ days }) }, { personScoped: true }),
}
