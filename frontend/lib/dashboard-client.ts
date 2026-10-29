import { apiRequest } from './http-client'

export const dashboardApi = {
  getDashboard: () => apiRequest<any>('/dashboard', {}, { personScoped: true }),
  dashboardTrends: (days = 30) => apiRequest<any>(`/dashboard/trends?days=${days}`, {}, { personScoped: true }),
}
