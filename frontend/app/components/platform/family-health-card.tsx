'use client'

import { useEffect, useState } from 'react'
import { api, type FamilyContextItem, type FamilyHealthContext, type FamilyRecommendation, type FamilyRelationshipRecord } from '../../../lib/api'
import {
  Users,
  AlertTriangle,
  Baby,
  Heart,
  Lightbulb,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Shield,
  UserPlus,
  Info,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  let color = 'bg-amber-100 text-amber-700'
  if (pct >= 70) color = 'bg-green-100 text-green-700'
  else if (pct < 40) color = 'bg-slate-100 text-slate-600'
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${color}`}>
      可信度 {pct}%
    </span>
  )
}

function UrgencyBadge({ urgency }: { urgency: FamilyRecommendation['urgency'] }) {
  const map: Record<string, string> = {
    high: 'bg-red-100 text-red-700',
    medium: 'bg-amber-100 text-amber-700',
    low: 'bg-blue-100 text-blue-700',
  }
  const labels: Record<string, string> = { high: '高', medium: '中', low: '低' }
  return (
    <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${map[urgency] ?? 'bg-slate-100 text-slate-600'}`}>
      {labels[urgency] ?? urgency}
    </span>
  )
}

function EvidenceSourceBadge({ sourceType }: { sourceType: string }) {
  const cfg: Record<string, { label: string; className: string }> = {
    child_health:     { label: '兒童健康', className: 'bg-pink-50 text-pink-600 border border-pink-200' },
    caregiver_health: { label: '照護提醒', className: 'bg-amber-50 text-amber-600 border border-amber-200' },
    shared_risk:      { label: '共同風險', className: 'bg-red-50 text-red-600 border border-red-200' },
    action:           { label: '行動建議', className: 'bg-blue-50 text-blue-600 border border-blue-200' },
  }
  const { label, className } = cfg[sourceType] ?? { label: sourceType, className: 'bg-slate-100 text-slate-500' }
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium shrink-0 ${className}`}>
      {label}
    </span>
  )
}

function SourcePoolBadge({ pool }: { pool: string }) {
  const cfg: Record<string, { label: string; className: string }> = {
    lab:          { label: '檢驗', className: 'bg-purple-50 text-purple-600 border border-purple-200' },
    symptom:      { label: '症狀', className: 'bg-orange-50 text-orange-600 border border-orange-200' },
    device:       { label: '裝置', className: 'bg-teal-50 text-teal-600 border border-teal-200' },
    narrative:    { label: '記錄', className: 'bg-sky-50 text-sky-600 border border-sky-200' },
    action:       { label: '行動', className: 'bg-blue-50 text-blue-600 border border-blue-200' },
    relationship: { label: '關係', className: 'bg-indigo-50 text-indigo-600 border border-indigo-200' },
  }
  const { label, className } = cfg[pool] ?? { label: pool, className: 'bg-slate-100 text-slate-500' }
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium shrink-0 ${className}`}>
      {label}
    </span>
  )
}

function AudienceBadge({ audience }: { audience: FamilyRecommendation['audience'] }) {
  const labels: Record<string, string> = {
    caregiver: '照護者',
    member: '成員',
    family: '全家',
  }
  return (
    <span className="text-xs text-slate-400 shrink-0">
      → {labels[audience] ?? audience}
    </span>
  )
}

function RelationshipTypeLabel({ type }: { type: string }) {
  const labels: Record<string, string> = {
    self: '本人',
    child: '子女',
    parent: '父母',
    spouse: '配偶',
    caregiver: '照護者',
  }
  return <span className="text-xs text-slate-500">{labels[type] ?? type}</span>
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center gap-2">
      <UserPlus className="w-8 h-8 text-slate-300" />
      <p className="text-sm font-medium text-slate-500">尚未設定家庭成員</p>
      <p className="text-xs text-slate-400">
        新增家庭成員後即可查看家庭健康概覽
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section collapse wrapper
// ---------------------------------------------------------------------------

function Section({
  title,
  icon,
  count,
  children,
  defaultOpen = true,
}: {
  title: string
  icon: React.ReactNode
  count?: number
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-slate-100 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-50 hover:bg-slate-100 transition-colors"
      >
        <span className="flex items-center gap-2 text-sm font-medium text-slate-700">
          {icon}
          {title}
          {count !== undefined && (
            <span className="text-xs bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded-full">
              {count}
            </span>
          )}
        </span>
        {open ? (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        )}
      </button>
      {open && <div className="px-3 py-2">{children}</div>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function FamilyHealthCard() {
  const [context, setContext] = useState<FamilyHealthContext | null>(null)
  const [relationships, setRelationships] = useState<FamilyRelationshipRecord[]>([])
  const [recommendations, setRecommendations] = useState<FamilyRecommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const [ctxRes, relRes, recRes] = await Promise.all([
        api.getFamilyHealthContext(),
        api.getFamilyRelationships(),
        api.getFamilyRecommendations(),
      ])
      setContext(ctxRes?.context || null)
      setRelationships(Array.isArray(relRes?.relationships) ? relRes.relationships : [])
      setRecommendations(Array.isArray(recRes?.recommendations) ? recRes.recommendations : [])
    } catch (e) {
      setError('無法載入家庭健康資料')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const hasFamily = Array.isArray(relationships) && relationships.length > 0

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-indigo-500" />
          <h2 className="text-base font-semibold text-slate-800">家庭健康總覽</h2>
        </div>
        <div className="flex items-center gap-2">
          {context && <ConfidenceBadge value={context.confidence} />}
          <button
            onClick={load}
            disabled={loading}
            className="p-1 rounded hover:bg-slate-100 transition-colors disabled:opacity-50"
            title="重新載入"
          >
            <RefreshCw className={`w-4 h-4 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && !error && (
        <div className="text-sm text-slate-400 text-center py-4 animate-pulse">
          載入中…
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && !hasFamily && <EmptyState />}

      {/* Content */}
      {!loading && !error && hasFamily && context && (
        <div className="flex flex-col gap-3">
          {/* Family members */}
          <Section
            title="家庭成員"
            icon={<Users className="w-4 h-4 text-indigo-400" />}
            count={Array.isArray(relationships) ? relationships.length : 0}
          >
            <ul className="divide-y divide-slate-50">
              {(Array.isArray(relationships) ? relationships : []).map(rel => (
                <li key={rel.id} className="flex items-center justify-between py-1.5">
                  <span className="text-sm text-slate-700">
                    {rel.related_display_name || '成員'}
                  </span>
                  <RelationshipTypeLabel type={rel.relationship_type} />
                </li>
              ))}
            </ul>
          </Section>

          {/* Child attention items */}
          {context.childAttentionItems.length > 0 && (
            <Section
              title="兒童注意事項"
              icon={<Baby className="w-4 h-4 text-pink-400" />}
              count={context.childAttentionItems.length}
              defaultOpen
            >
              <p className="text-xs text-slate-400 mb-1.5 flex items-center gap-1">
                <Info className="w-3 h-3" /> 來源：健康觀察資料（檢驗 / 症狀 / 裝置）
              </p>
              <ul className="space-y-1">
                {context.childAttentionDetails && context.childAttentionDetails.length > 0
                  ? context.childAttentionDetails.map((item: FamilyContextItem, i: number) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                        <Baby className="w-3.5 h-3.5 text-pink-400 mt-0.5 shrink-0" />
                        <span className="flex-1">{item.text}</span>
                        <SourcePoolBadge pool={item.source_pool} />
                      </li>
                    ))
                  : context.childAttentionItems.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                        <Baby className="w-3.5 h-3.5 text-pink-400 mt-0.5 shrink-0" />
                        {item}
                      </li>
                    ))}
              </ul>
            </Section>
          )}

          {/* Caregiver alerts */}
          {context.caregiverAlerts.length > 0 && (
            <Section
              title="照護者提醒"
              icon={<AlertTriangle className="w-4 h-4 text-amber-500" />}
              count={context.caregiverAlerts.length}
              defaultOpen
            >
              <p className="text-xs text-slate-400 mb-1.5 flex items-center gap-1">
                <Info className="w-3 h-3" /> 來源：健康觀察資料（檢驗 / 症狀 / 裝置）
              </p>
              <ul className="space-y-1">
                {context.caregiverAlertDetails && context.caregiverAlertDetails.length > 0
                  ? context.caregiverAlertDetails.map((item: FamilyContextItem, i: number) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                        <span className="flex-1">{item.text}</span>
                        <SourcePoolBadge pool={item.source_pool} />
                      </li>
                    ))
                  : context.caregiverAlerts.map((alert, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                        {alert}
                      </li>
                    ))}
              </ul>
            </Section>
          )}

          {/* Shared risks */}
          {context.sharedRisks.length > 0 && (
            <Section
              title="家庭共同風險"
              icon={<Shield className="w-4 h-4 text-red-400" />}
              count={context.sharedRisks.length}
              defaultOpen={false}
            >
              <ul className="space-y-1">
                {context.sharedRiskDetails && context.sharedRiskDetails.length > 0
                  ? context.sharedRiskDetails.map((item: FamilyContextItem, i: number) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                        <Shield className="w-3.5 h-3.5 text-red-400 mt-0.5 shrink-0" />
                        <span className="flex-1">{item.text}</span>
                        <SourcePoolBadge pool={item.source_pool} />
                      </li>
                    ))
                  : context.sharedRisks.map((risk, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                        <Shield className="w-3.5 h-3.5 text-red-400 mt-0.5 shrink-0" />
                        {risk}
                      </li>
                    ))}
              </ul>
            </Section>
          )}

          {/* Recommendations */}
          {Array.isArray(recommendations) && recommendations.length > 0 && (
            <Section
              title="家庭健康建議"
              icon={<Lightbulb className="w-4 h-4 text-yellow-400" />}
              count={Array.isArray(recommendations) ? recommendations.length : 0}
              defaultOpen={false}
            >
              <ul className="space-y-2.5">
                {(Array.isArray(recommendations) ? recommendations : []).map((rec, i) => (
                  <li key={i} className="flex flex-col gap-1">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <UrgencyBadge urgency={rec.urgency} />
                      <EvidenceSourceBadge sourceType={rec.source_type} />
                      <AudienceBadge audience={rec.audience} />
                    </div>
                    <span className="text-sm text-slate-700 leading-snug pl-0.5">{rec.text}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {/* Family action suggestions */}
          {context.familyActionSuggestions.length > 0 && (
            <Section
              title="家庭行動建議"
              icon={<Heart className="w-4 h-4 text-rose-400" />}
              count={context.familyActionSuggestions.length}
              defaultOpen={false}
            >
              <ul className="space-y-1">
                {context.familyActionSuggestions.map((sug, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                    <Heart className="w-3.5 h-3.5 text-rose-400 mt-0.5 shrink-0" />
                    {sug}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {/* Limitations */}
          {context.limitations.length > 0 && (
            <div className="bg-slate-50 rounded-lg px-3 py-2 text-xs text-slate-500 space-y-0.5">
              {context.limitations.map((lim, i) => (
                <p key={i} className="flex items-start gap-1.5">
                  <Info className="w-3 h-3 mt-0.5 shrink-0 text-slate-400" />{lim}
                </p>
              ))}
            </div>
          )}

          {/* No-diagnosis disclaimer */}
          <p className="text-xs text-slate-400 text-center">
            以上內容為觀察性摘要，非醫療診斷，請依個人狀況諮詢專業醫療人員。
          </p>
        </div>
      )}
    </div>
  )
}
