import { apiRequest } from './http-client'

export const timelineApi = {
  getTimeline: (days = 180, limit = 200) => apiRequest<{ items: any[] }>(`/timeline?days=${days}&limit=${limit}`, {}, { personScoped: true }),
}
