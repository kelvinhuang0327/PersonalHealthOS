'use client'

import { useEffect, useState } from 'react'
import { api, type FamilyHealthContext, type FamilyRecommendation, type FamilyRelationshipRecord } from '../../../lib/api'
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
      setContext(ctxRes.context)
      setRelationships(relRes.relationships)
      setRecommendations(recRes.recommendations)
    } catch (e) {
      setError('無法載入家庭健康資料')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const hasFamily = relationships.length > 0

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
            count={relationships.length}
          >
            <ul className="divide-y divide-slate-50">
              {relationships.map(rel => (
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
              <ul className="space-y-1">
                {context.childAttentionItems.map((item, i) => (
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
              <ul className="space-y-1">
                {context.caregiverAlerts.map((alert, i) => (
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
                {context.sharedRisks.map((risk, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                    <Shield className="w-3.5 h-3.5 text-red-400 mt-0.5 shrink-0" />
                    {risk}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <Section
              title="家庭健康建議"
              icon={<Lightbulb className="w-4 h-4 text-yellow-400" />}
              count={recommendations.length}
              defaultOpen={false}
            >
              <ul className="space-y-2">
                {recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <UrgencyBadge urgency={rec.urgency} />
                    <span className="text-sm text-slate-700 leading-snug">{rec.text}</span>
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
            <div className="text-xs text-slate-400 space-y-0.5">
              {context.limitations.map((lim, i) => (
                <p key={i}>• {lim}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
