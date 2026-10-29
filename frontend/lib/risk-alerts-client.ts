import { apiRequest } from './http-client'

export const riskAlertsApi = {
  listRiskAlerts: () => apiRequest<any[]>('/risk-alerts', {}, { personScoped: true }),
  getRiskAlertUnreadCount: () => apiRequest<{ count: number }>('/risk-alerts/unread-count', {}, { personScoped: true }),
  dismissRiskAlert: (id: string) => apiRequest<any>(`/risk-alerts/${encodeURIComponent(id)}/dismiss`, { method: 'POST' }),
}
