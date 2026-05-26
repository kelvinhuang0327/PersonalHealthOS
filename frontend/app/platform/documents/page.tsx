'use client'

import { FormEvent, useEffect, useState } from 'react'
import { CheckCircle2, AlertTriangle, Eye, Loader2 } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { ErrorBoundary } from '../../components/ui/error-boundary'
import { Skeleton } from '../../components/ui/skeleton'
import { ParsedItemsDrawer } from '../../components/platform/parsed-items-drawer'
import { LabComparisonTable } from '../../components/platform/lab-comparison-table'
import { api, uploadDocument } from '../../../lib/api'
import { trackEvent } from '../../../lib/analytics'

interface Doc {
  id: string
  original_filename: string
  parse_status: string
  confirmed_at: string | null
  uploaded_at: string
  category: string
  confirmed_data?: { extracted_items?: number; abnormal_items?: number } | null
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('health_check')
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [parsingId, setParsingId] = useState<string | null>(null)
  const [reviewDoc, setReviewDoc] = useState<Doc | null>(null)
  const [tab, setTab] = useState<'documents' | 'history'>('documents')

  const refresh = () => api.listDocuments().then((d: unknown) => setDocs(d as Doc[])).catch(() => setDocs([])).finally(() => setLoading(false))

  useEffect(() => {
    trackEvent('view_documents', { page: '/platform/documents' })
    refresh()
  }, [])

  const onUpload = async (e: FormEvent) => {
    e.preventDefault()
    if (!file) return
    setUploading(true)
    try {
      await uploadDocument(category, file)
      trackEvent('upload_document', { page: '/platform/documents', metadata: { category, file_type: file.type || 'unknown' } })
      setFile(null)
      refresh()
    } finally {
      setUploading(false)
    }
  }

  const parseDoc = async (id: string) => {
    setParsingId(id)
    try {
      await api.parseDocument(id)
      refresh()
    } finally {
      setParsingId(null)
    }
  }

  const statusLabel = (doc: Doc) => {
    if (doc.parse_status === 'confirmed') return null
    if (doc.parse_status === 'parsed' || doc.parse_status === 'completed') {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
          <AlertTriangle className="h-3 w-3" />
          待確認 — 解析結果未審閱
        </span>
      )
    }
    return (
      <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
        {doc.parse_status}
      </span>
    )
  }

  const canReview = (doc: Doc) =>
    ['parsed', 'completed', 'confirmed'].includes(doc.parse_status)

  return (
    <div className="space-y-4" data-testid="documents-page">
      {/* Upload form */}
      <Card data-testid="documents-upload-section">
        <h2 className="text-2xl font-semibold">健檢報告</h2>
        <form className="mt-2 grid gap-2 md:grid-cols-4" onSubmit={(e) => void onUpload(e)}>
          <select
            className="rounded-xl border px-3 py-2"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="health_check">健檢報告</option>
            <option value="lab">檢驗結果</option>
            <option value="imaging">影像檢查</option>
          </select>
          <input
            className="rounded-xl border px-3 py-2 md:col-span-2"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <Button type="submit" disabled={!file || uploading}>
            {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            上傳
          </Button>
        </form>
      </Card>

      {/* Document list */}
      <Card>
        <div className="mb-3 flex gap-2">
          <button
            type="button"
            onClick={() => setTab('documents')}
            className={`rounded-full px-3 py-1.5 text-sm ${tab === 'documents' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600'}`}
          >
            文件列表
          </button>
          <button
            type="button"
            onClick={() => setTab('history')}
            className={`rounded-full px-3 py-1.5 text-sm ${tab === 'history' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600'}`}
          >
            歷史比較
          </button>
        </div>
      </Card>

      {tab === 'documents' ? (
      <ErrorBoundary><Card data-testid="documents-list-section">
        <h3 className="font-semibold">文件列表</h3>
        <div className="mt-2 space-y-2">
          {loading ? (
            <div data-testid="documents-loading">
              <Skeleton variant="card" className="h-20" />
              <Skeleton variant="card" className="h-20" />
              <Skeleton variant="card" className="h-20" />
            </div>
          ) : null}
          {docs.length === 0 && (
            <p className="py-8 text-center text-sm text-slate-400">尚未上傳任何文件</p>
          )}
          {docs.map((d) => (
            <div
              key={d.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-medium truncate">{d.original_filename}</p>
                  {d.parse_status === 'confirmed' ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                      <CheckCircle2 className="h-3 w-3" />
                      已確認
                    </span>
                  ) : (
                    statusLabel(d)
                  )}
                </div>
                <p className="mt-0.5 text-xs text-slate-400">
                  {new Date(d.uploaded_at).toLocaleDateString('zh-TW')} · {d.category}
                </p>
                {d.parse_status === 'confirmed' && typeof d.confirmed_data?.extracted_items === 'number' ? (
                  <p data-testid="documents-confirmed-summary" className="mt-0.5 text-xs text-slate-500">
                    {d.confirmed_data.extracted_items} 項指標
                    {typeof d.confirmed_data.abnormal_items === 'number' && d.confirmed_data.abnormal_items > 0
                      ? ` · ${d.confirmed_data.abnormal_items} 項異常`
                      : null}
                  </p>
                ) : null}
              </div>

              <div className="flex gap-2">
                {d.parse_status === 'pending' && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void parseDoc(d.id)}
                    disabled={parsingId === d.id}
                  >
                    {parsingId === d.id ? (
                      <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                    ) : null}
                    解析
                  </Button>
                )}
                {canReview(d) && (
                  <Button
                    size="sm"
                    variant={d.parse_status === 'confirmed' ? 'ghost' : 'default'}
                    onClick={() => setReviewDoc(d)}
                  >
                    <Eye className="mr-1 h-3 w-3" />
                    審閱解析結果
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card></ErrorBoundary>
      ) : null}

      {tab === 'history' ? (
        <ErrorBoundary>
          <Card>
            <h3 className="mb-2 font-semibold">健檢報告歷史比較</h3>
            <LabComparisonTable />
          </Card>
        </ErrorBoundary>
      ) : null}

      {/* Parsed items review drawer */}
      {reviewDoc && (
        <ParsedItemsDrawer
          documentId={reviewDoc.id}
          documentName={reviewDoc.original_filename}
          onClose={() => setReviewDoc(null)}
          onConfirmed={() => {
            setReviewDoc(null)
            refresh()
          }}
        />
      )}
    </div>
  )
}
