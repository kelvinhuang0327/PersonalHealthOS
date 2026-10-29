import { apiRequest, jsonBody } from './http-client'

export const reportsApi = {
  generateReport: (payload: { person_id: string; include_sections: string[] }) =>
    apiRequest<{ report_id: string }>('/reports/generate', { method: 'POST', body: jsonBody(payload) }),
  getReportStatus: (id: string) => apiRequest<{ status: string; download_url?: string }>(`/reports/${encodeURIComponent(id)}`),
}
