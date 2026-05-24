'use client'

import { useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { Button } from '../ui/button'
import { api } from '../../../lib/api'
import { usePerson } from '../../providers/person-context'

const ALL_SECTIONS = [
  { key: 'score', label: '健康評分' },
  { key: 'metrics', label: '近期指標' },
  { key: 'labs', label: '實驗室報告摘要' },
  { key: 'insights', label: 'AI 洞察摘要' },
  { key: 'actions', label: '行動追蹤' },
] as const

export function ReportExportModal() {
  const { personId } = usePerson()
  const [open, setOpen] = useState(false)
  const [sections, setSections] = useState<string[]>(ALL_SECTIONS.map((s) => s.key))
  const [status, setStatus] = useState<'idle' | 'generating' | 'ready' | 'failed'>('idle')
  const [downloadUrl, setDownloadUrl] = useState('')

  const generate = async () => {
    setStatus('generating')
    try {
      const started = (await api.generateReport({ person_id: personId, include_sections: sections })) as { report_id: string }
      const reportId = started.report_id
      const timer = window.setInterval(async () => {
        const res = (await api.getReportStatus(reportId).catch(() => ({ status: 'failed' }))) as { status: string; download_url?: string }
        if (res.status === 'ready') {
          window.clearInterval(timer)
          setStatus('ready')
          setDownloadUrl(res.download_url || '')
        } else if (res.status === 'failed') {
          window.clearInterval(timer)
          setStatus('failed')
        }
      }, 3000)
    } catch {
      setStatus('failed')
    }
  }

  const handleDownload = async () => {
    if (!downloadUrl) return
    const jwtToken = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    // Construct absolute URL: downloadUrl is /api/v1/... ; strip /api/v1 from base
    const apiBase = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/api\/v1\/?$/, '')
    const fullUrl = downloadUrl.startsWith('http') ? downloadUrl : `${apiBase}${downloadUrl}`

    // Extract report token from URL and strip it before fetch to prevent token
    // appearing in server-side access logs (P45 hardening).
    let fetchUrl = fullUrl
    let reportToken: string | null = null
    try {
      const parsed = new URL(fullUrl)
      reportToken = parsed.searchParams.get('token')
      parsed.searchParams.delete('token')
      fetchUrl = parsed.toString()
    } catch {
      // URL parsing failed; fall back to original URL
    }

    const headers: Record<string, string> = {}
    if (jwtToken) headers['Authorization'] = `Bearer ${jwtToken}`
    if (reportToken) headers['X-Report-Download-Token'] = reportToken

    try {
      const res = await fetch(fetchUrl, { headers })
      if (!res.ok) {
        setStatus('failed')
        return
      }
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = 'health_report.pdf'
      a.click()
      URL.revokeObjectURL(objectUrl)
    } catch {
      setStatus('failed')
    }
  }

  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}>匯出報告</Button>
      {open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <div className="relative w-full max-w-md rounded-2xl bg-white p-5 shadow-2xl">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold">匯出健康報告</h3>
              <button type="button" className="rounded p-1 hover:bg-slate-100" onClick={() => setOpen(false)}>
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-2">
              {ALL_SECTIONS.map((section) => (
                <label key={section.key} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={sections.includes(section.key)}
                    onChange={(e) => {
                      if (e.target.checked) setSections((prev) => [...prev, section.key])
                      else setSections((prev) => prev.filter((key) => key !== section.key))
                    }}
                  />
                  {section.label}
                </label>
              ))}
            </div>

            <div className="mt-4">
              {status === 'ready' && downloadUrl ? (
                <button
                  type="button"
                  onClick={() => void handleDownload()}
                  className="inline-flex rounded-xl bg-emerald-600 px-3 py-2 text-sm font-medium text-white"
                >
                  下載報告
                </button>
              ) : (
                <Button onClick={() => void generate()} disabled={status === 'generating' || sections.length === 0}>
                  {status === 'generating' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  生成報告
                </Button>
              )}
              {status === 'failed' ? <p className="mt-2 text-xs text-rose-600">生成失敗，請稍後重試</p> : null}
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}

