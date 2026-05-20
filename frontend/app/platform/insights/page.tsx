'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useMemo, useState } from 'react'
import { BookOpenText, ChevronDown, History, Microscope } from 'lucide-react'
import { CategoryMiniTrend } from '../../components/platform/category-mini-trend'
import { ErrorBoundary } from '../../components/ui/error-boundary'
import { Skeleton } from '../../components/ui/skeleton'
import { Badge } from '../../components/ui/badge'
import { Card } from '../../components/ui/card'
import { usePerson } from '../../providers/person-context'
import { api } from '../../../lib/api'
import { trackEvent } from '../../../lib/analytics'

const CATEGORY_TABS = [
  { key: 'cardiovascular', label: '心血管' },
  { key: 'metabolic', label: '代謝' },
  { key: 'activity', label: '活動' },
  { key: 'sleep', label: '睡眠' },
  { key: 'overall', label: '整體' },
] as const

const CATEGORY_METRICS: Record<string, { key: string; label: string; color: string }> = {
  cardiovascular: { key: 'systolic_bp', label: '血壓趨勢', color: '#ef4444' },
  metabolic: { key: 'blood_glucose', label: '血糖趨勢', color: '#f59e0b' },
  activity: { key: 'steps', label: '活動量趨勢', color: '#3b82f6' },
  sleep: { key: 'sleep_hours', label: '睡眠趨勢', color: '#8b5cf6' },
  overall: { key: 'weight_kg', label: '整體趨勢', color: '#06b6d4' },
}

function inferCategory(insight: any): string {
  const evidenceCategory = String(insight?.evidence_json?.category || '').toLowerCase()
  if (evidenceCategory) return evidenceCategory
  const text = `${insight?.title || ''} ${insight?.summary || ''} ${insight?.recommendation || ''}`.toLowerCase()
  if (/(blood pressure|bp|心血管|血壓|cardio)/.test(text)) return 'cardiovascular'
  if (/(glucose|metabolic|代謝|血糖|bmi|尿酸)/.test(text)) return 'metabolic'
  if (/(sleep|睡眠)/.test(text)) return 'sleep'
  if (/(steps|walk|exercise|活動|運動)/.test(text)) return 'activity'
  return 'overall'
}

function evidenceLevel(insight: any): string {
  return String(insight?.evidence_json?.evidence_level || insight?.evidence_level || 'C').toUpperCase()
}

function InsightsContent() {
  const searchParams = useSearchParams()
  const initialCategory = searchParams?.get('category') || 'overall'
  const [activeCategory, setActiveCategory] = useState(initialCategory)
  const { currentPerson } = usePerson()
  const [items, setItems] = useState<any[]>([])
  const [trends, setTrends] = useState<Record<string, Array<{ recorded_at: string; value: number }>>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    trackEvent('view_insights', { page: '/platform/insights', metadata: { category: initialCategory } })
    void Promise.all([
      api.listInsights().catch(() => []),
      api.dashboardTrends(30).catch(() => ({ trends: {} })),
    ])
      .then(([insights, trendData]) => {
        setItems((insights as any[]) || [])
        setTrends(((trendData as any)?.trends || {}) as Record<string, Array<{ recorded_at: string; value: number }>>)
      })
      .finally(() => setLoading(false))
  }, [initialCategory])

  useEffect(() => {
    setActiveCategory(initialCategory)
  }, [initialCategory])

  const filteredItems = useMemo(() => {
    if (activeCategory === 'overall') return items
    return items.filter((item) => inferCategory(item) === activeCategory)
  }, [activeCategory, items])

  const metricMeta = CATEGORY_METRICS[activeCategory] || CATEGORY_METRICS.overall
  const trendPoints = trends[metricMeta.key] || []

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton variant="card" className="h-28" />
        <Skeleton variant="card" className="h-40" />
        <Skeleton variant="card" className="h-40" />
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <Card className="rounded-3xl border border-slate-200/80 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                <Microscope className="h-3.5 w-3.5" />
                Deep Dive Explorer
              </div>
              <h2 className="text-2xl font-semibold">深度分析</h2>
              {currentPerson && currentPerson.relationship !== 'self' ? <p className="mt-1 text-xs text-sky-700">目前查看：{currentPerson.display_name}</p> : null}
              <p className="text-sm text-slate-500">當你看到提醒時，這裡是用來理解為什麼與接下來怎麼做的地方。</p>
            </div>
            <Link href="/platform/dashboard" className="text-sm font-medium text-sky-700 hover:underline">
              回到儀表板
            </Link>
          </div>
        </Card>

        <section className="space-y-4">
          <div className="flex gap-2 overflow-x-auto pb-1">
            {CATEGORY_TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveCategory(tab.key)}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  activeCategory === tab.key
                    ? 'bg-slate-900 text-white'
                    : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
            <Card className="rounded-2xl p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold">{CATEGORY_TABS.find((tab) => tab.key === activeCategory)?.label || '整體'}洞察</h3>
                  <p className="text-sm text-slate-500">聚焦同一類問題，避免和 Dashboard 重複。</p>
                </div>
                <Badge className="bg-sky-100 text-sky-700">{filteredItems.length} 則</Badge>
              </div>
              <div className="mt-4 space-y-3">
                {filteredItems.length === 0 ? (
                  <div className="rounded-2xl bg-slate-50 p-5 text-sm text-slate-400">目前沒有這個分類的洞察。</div>
                ) : (
                  filteredItems.map((item) => (
                    <Card key={item.id} className="rounded-2xl border border-slate-200 p-4 shadow-none">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-slate-950">{item.title}</p>
                        <Badge className="bg-slate-100 text-slate-700">{String(item.severity || 'info')}</Badge>
                        <Badge className="bg-emerald-100 text-emerald-700">證據 {evidenceLevel(item)}</Badge>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-700">{item.summary}</p>
                      {item.recommendation ? (
                        <div className="mt-3 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                          建議：{item.recommendation}
                        </div>
                      ) : null}
                    </Card>
                  ))
                )}
              </div>
            </Card>

            <Card className="rounded-2xl p-5">
              <h3 className="text-lg font-semibold">相關指標趨勢</h3>
              <p className="text-sm text-slate-500">{metricMeta.label}</p>
              <div className="mt-4">
                <CategoryMiniTrend points={trendPoints} color={metricMeta.color} />
              </div>
              <div className="mt-4 space-y-2">
                {filteredItems.slice(0, 2).map((item) => (
                  <div key={item.id} className="rounded-xl border border-slate-200 p-3 text-sm">
                    <p className="font-medium text-slate-900">{item.evidence_json?.guideline_source || 'Rule Library'}</p>
                    <p className="mt-1 text-slate-500">{item.evidence_json?.guideline_reference || item.evidence_json?.condition_summary || '可展開查看規則觸發條件'}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </section>

        <section>
          <Card className="rounded-2xl p-5">
            <div className="flex items-center gap-2">
              <BookOpenText className="h-4 w-4 text-sky-600" />
              <h3 className="text-lg font-semibold">解釋中心</h3>
            </div>
            <p className="mt-1 text-sm text-slate-500">打開每則洞察背後的規則來源、觸發條件與指引依據。</p>
            <div className="mt-4 space-y-3">
              {filteredItems.map((item) => (
                <details key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-950">{item.title}</p>
                      <p className="text-sm text-slate-500">為什麼這很重要</p>
                    </div>
                    <ChevronDown className="h-4 w-4 text-slate-400" />
                  </summary>
                  <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
                    <div className="rounded-xl bg-white p-3">
                      <p className="text-xs uppercase tracking-wide text-slate-400">rule_id</p>
                      <p className="mt-1 font-medium text-slate-900">{item.evidence_json?.rule_id || '未提供'}</p>
                    </div>
                    <div className="rounded-xl bg-white p-3">
                      <p className="text-xs uppercase tracking-wide text-slate-400">condition</p>
                      <p className="mt-1 font-medium text-slate-900">{item.evidence_json?.condition_summary || item.evidence_json?.condition || '未提供'}</p>
                    </div>
                    <div className="rounded-xl bg-white p-3">
                      <p className="text-xs uppercase tracking-wide text-slate-400">guideline</p>
                      <p className="mt-1 font-medium text-slate-900">{item.evidence_json?.guideline_source || 'Rule Library'}</p>
                    </div>
                  </div>
                </details>
              ))}
            </div>
          </Card>
        </section>

        <section>
          <Card className="rounded-2xl p-5">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-slate-500" />
              <h3 className="text-lg font-semibold">歷史洞察</h3>
            </div>
            <div className="mt-4 space-y-3">
              {items
                .slice()
                .sort((a, b) => new Date(b.generated_at).getTime() - new Date(a.generated_at).getTime())
                .map((item) => (
                  <div key={item.id} className="flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-slate-200 p-4">
                    <div>
                      <p className="font-medium text-slate-950">{item.title}</p>
                      <p className="mt-1 text-sm text-slate-500">{item.summary}</p>
                      <p className="mt-2 text-xs text-slate-400">{new Date(item.generated_at).toLocaleString('zh-TW')}</p>
                    </div>
                    <Badge className={item.is_active ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}>
                      {item.is_active ? 'ongoing' : 'resolved'}
                    </Badge>
                  </div>
                ))}
            </div>
          </Card>
        </section>
      </div>
    </ErrorBoundary>
  )
}

export default function InsightsPage() {
  return (
    <Suspense fallback={<div className="space-y-3"><div className="h-28 animate-pulse rounded-3xl bg-slate-100" /><div className="h-40 animate-pulse rounded-2xl bg-slate-100" /></div>}>
      <InsightsContent />
    </Suspense>
  )
}
