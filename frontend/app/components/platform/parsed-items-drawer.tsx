'use client'

import { useEffect, useState } from 'react'
import { Check, ChevronDown, ChevronUp, Loader2, Pencil, X } from 'lucide-react'
import { Button } from '../ui/button'
import { api } from '../../../lib/api'

interface ParsedItem {
  id: string
  item_name: string
  value_num: number | null
  value_text: string | null
  unit: string | null
  ref_range: string | null
  abnormal_flag: string | null
  parser_confidence: number | null
  is_abnormal: boolean
}

interface Props {
  documentId: string
  documentName: string
  onClose: () => void
  onConfirmed: () => void
}

export function ParsedItemsDrawer({ documentId, documentName, onClose, onConfirmed }: Props) {
  const [items, setItems] = useState<ParsedItem[]>([])
  const [loading, setLoading] = useState(true)
  const [confirming, setConfirming] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<{ value: string; unit: string; reference_range: string }>({
    value: '',
    unit: '',
    reference_range: '',
  })
  const [saving, setSaving] = useState(false)
  const [comparePreview, setComparePreview] = useState<string>('')

  useEffect(() => {
    setLoading(true)
    api
      .getDocumentParsedItems(documentId)
      .then((data: unknown) => setItems(data as ParsedItem[]))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [documentId])

  useEffect(() => {
    if (items.length === 0) return
    const markers = items.slice(0, 5).map((item) => item.item_name).filter(Boolean)
    Promise.all(markers.map((metric) => api.getLabHistory(metric, 2).catch(() => [])))
      .then((histories) => {
        const parts: string[] = []
        for (let i = 0; i < histories.length; i += 1) {
          const rows = histories[i] as Array<any>
          if (!rows || rows.length < 2) continue
          const latest = Number(rows[0]?.value)
          const prev = Number(rows[1]?.value)
          if (!Number.isFinite(latest) || !Number.isFinite(prev) || prev === 0) continue
          const deltaPct = ((latest - prev) / prev) * 100
          parts.push(`${markers[i]} ${deltaPct >= 0 ? '↑' : '↓'}${Math.abs(deltaPct).toFixed(0)}%`)
          if (parts.length >= 2) break
        }
        setComparePreview(parts.join('，'))
      })
      .catch(() => setComparePreview(''))
  }, [items])

  const startEdit = (item: ParsedItem) => {
    setEditingId(item.id)
    setEditDraft({
      value: item.value_num !== null ? String(item.value_num) : (item.value_text ?? ''),
      unit: item.unit ?? '',
      reference_range: item.ref_range ?? '',
    })
  }

  const saveEdit = async (itemId: string) => {
    setSaving(true)
    try {
      const updated = (await api.updateParsedItem(documentId, itemId, {
        value: editDraft.value || undefined,
        unit: editDraft.unit || undefined,
        reference_range: editDraft.reference_range || undefined,
      })) as ParsedItem
      setItems((prev) => prev.map((it) => (it.id === itemId ? updated : it)))
      setEditingId(null)
    } catch {
      // keep editing on failure
    } finally {
      setSaving(false)
    }
  }

  const handleConfirm = async () => {
    setConfirming(true)
    try {
      await api.confirmDocumentPost(documentId)
      onConfirmed()
    } finally {
      setConfirming(false)
    }
  }

  const abnormalCount = items.filter((i) => i.is_abnormal).length

  return (
    /* full-screen backdrop */
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Sheet */}
      <div className="relative flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-t-2xl bg-white shadow-2xl sm:rounded-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold">審閱解析結果</h2>
            <p className="text-sm text-slate-500 truncate max-w-xs">{documentName}</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 hover:bg-slate-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Stats bar */}
        {!loading && (
          <div className="flex gap-4 border-b bg-slate-50 px-6 py-2 text-sm">
            <span className="text-slate-600">共 <strong>{items.length}</strong> 項指標</span>
            {abnormalCount > 0 && (
              <span className="font-medium text-rose-600">
                ⚠ {abnormalCount} 項異常
              </span>
            )}
          </div>
        )}

        {comparePreview ? (
          <div className="border-b bg-sky-50 px-6 py-2 text-xs text-sky-700">
            與上份報告相比：{comparePreview}
          </div>
        ) : null}

        {/* Table */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
              <span className="ml-2 text-sm text-slate-500">載入中…</span>
            </div>
          ) : items.length === 0 ? (
            <div className="py-16 text-center text-sm text-slate-400">沒有解析到指標，請先解析文件</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white text-xs text-slate-500">
                <tr className="border-b">
                  <th className="px-4 py-2 text-left">指標名稱</th>
                  <th className="px-4 py-2 text-right">數值</th>
                  <th className="hidden px-4 py-2 text-left sm:table-cell">單位</th>
                  <th className="hidden px-4 py-2 text-left sm:table-cell">參考範圍</th>
                  <th className="px-4 py-2 text-center">狀態</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const isEditing = editingId === item.id
                  const rowBg = item.is_abnormal ? 'bg-rose-50' : ''
                  return (
                    <tr key={item.id} className={`border-b ${rowBg} hover:bg-slate-50`}>
                      <td className="px-4 py-2 font-medium">{item.item_name}</td>

                      {/* Value cell */}
                      <td className="px-4 py-2 text-right">
                        {isEditing ? (
                          <input
                            className="w-20 rounded border px-1 py-0.5 text-right text-sm"
                            value={editDraft.value}
                            onChange={(e) => setEditDraft((d) => ({ ...d, value: e.target.value }))}
                            autoFocus
                          />
                        ) : (
                          <span className={item.is_abnormal ? 'font-semibold text-rose-600' : ''}>
                            {item.value_num !== null ? item.value_num : (item.value_text ?? '—')}
                          </span>
                        )}
                      </td>

                      {/* Unit */}
                      <td className="hidden px-4 py-2 text-slate-500 sm:table-cell">
                        {isEditing ? (
                          <input
                            className="w-16 rounded border px-1 py-0.5 text-sm"
                            value={editDraft.unit}
                            onChange={(e) => setEditDraft((d) => ({ ...d, unit: e.target.value }))}
                          />
                        ) : (
                          item.unit ?? '—'
                        )}
                      </td>

                      {/* Reference range */}
                      <td className="hidden px-4 py-2 text-slate-500 sm:table-cell">
                        {isEditing ? (
                          <input
                            className="w-24 rounded border px-1 py-0.5 text-sm"
                            value={editDraft.reference_range}
                            onChange={(e) => setEditDraft((d) => ({ ...d, reference_range: e.target.value }))}
                          />
                        ) : (
                          item.ref_range ?? '—'
                        )}
                      </td>

                      {/* Status badge */}
                      <td className="px-4 py-2 text-center">
                        {item.is_abnormal ? (
                          <span className="inline-flex items-center rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">
                            {item.abnormal_flag === 'H' ? '偏高' : item.abnormal_flag === 'L' ? '偏低' : '異常'}
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                            正常
                          </span>
                        )}
                      </td>

                      {/* Edit controls */}
                      <td className="px-4 py-2 text-right">
                        {isEditing ? (
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => void saveEdit(item.id)}
                              disabled={saving}
                              className="rounded p-1 text-emerald-600 hover:bg-emerald-50"
                            >
                              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="rounded p-1 text-slate-400 hover:bg-slate-100"
                            >
                              <X className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => startEdit(item)}
                            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t bg-white px-6 py-4">
          <p className="text-xs text-slate-400">
            {item_confidence_note(items)}
          </p>
          <div className="flex gap-3">
            <Button variant="ghost" onClick={onClose}>
              稍後確認
            </Button>
            <Button
              onClick={() => void handleConfirm()}
              disabled={confirming || loading || items.length === 0}
            >
              {confirming ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
              確認並分析
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

function item_confidence_note(items: ParsedItem[]): string {
  const low = items.filter((i) => i.parser_confidence !== null && (i.parser_confidence ?? 1) < 0.7)
  if (low.length === 0) return '解析信心度高，建議仍人工核對異常值'
  return `${low.length} 項解析信心度較低，建議優先核對`
}
