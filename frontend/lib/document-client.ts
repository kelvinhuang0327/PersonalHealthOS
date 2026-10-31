import { apiRequest, jsonBody, queryPath } from './http-client'

export type LabAbnormality = {
  abnormalityType: string
  severity: 'high' | 'medium' | 'low'
  labItemName: string
  currentValue: number | string | null
  referenceRange?: string | null
  recurrenceCount: number
  confidence: number
  suggestedAction: string
  whyDetected: string
  evidenceSources: Array<{ type: string; summary?: string; recency?: string | null; id?: string | null }>
}

export type DocumentRecord = {
  id: string
  category: string
  original_filename: string
  parse_status: string
  [key: string]: unknown
}

export type LabHistoryRow = {
  metric: string
  report_date: string | null
  document_id: string
  document_name: string
  value_num?: number | null
  value_text?: string | null
  unit?: string | null
  [key: string]: unknown
}

export const documentsApi = {
  listDocuments: () => apiRequest<DocumentRecord[]>('/documents', {}, { personScoped: true }),
  getDocumentParsedItems: (id: string) => apiRequest<any[]>(`/documents/${encodeURIComponent(id)}/parsed-items`, {}, { personScoped: true }),
  parseDocument: (id: string) => apiRequest<any>(`/documents/${encodeURIComponent(id)}/parse`, { method: 'POST' }, { personScoped: true }),
  confirmDocument: (id: string, payload: Record<string, unknown>) =>
    apiRequest<DocumentRecord>(`/documents/${encodeURIComponent(id)}/confirm`, { method: 'PUT', body: jsonBody(payload) }, { personScoped: true }),
  updateParsedItem: (documentId: string, itemId: string, payload: Record<string, unknown>) =>
    apiRequest<any>(`/documents/${encodeURIComponent(documentId)}/parsed-items/${encodeURIComponent(itemId)}`, { method: 'PATCH', body: jsonBody(payload) }, { personScoped: true }),
  getLabHistory: (metric?: string, limit = 5) =>
    apiRequest<LabHistoryRow[]>(queryPath('/documents/lab-history', { metric, limit }), {}, { personScoped: true }),
}

export function uploadDocument(category: string, file: File) {
  const form = new FormData()
  form.set('category', category)
  form.set('file', file)
  return apiRequest<DocumentRecord>('/documents/upload', { method: 'POST', body: form }, { personScoped: true })
}
