import { apiRequest, jsonBody } from './http-client'

export const symptomsApi = {
  listSymptoms: () => apiRequest<any[]>('/symptoms', {}, { personScoped: true }),
  createSymptom: (payload: Record<string, unknown>) =>
    apiRequest<any>('/symptoms', { method: 'POST', body: jsonBody(payload) }, { personScoped: true }),
}
