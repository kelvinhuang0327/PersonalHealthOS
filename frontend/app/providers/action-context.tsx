'use client'

import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { buildActionFromSource, HealthAction } from '../../lib/actions'
import type { UnifiedDecisionItem } from '../../lib/decision-support'
import { api } from '../../lib/api'
import { usePerson } from './person-context'
import { trackEvent } from '../../lib/analytics'

// ─── localStorage cache helpers ──────────────────────────────────────────────
function cacheKey(personId: string) {
  return `health_actions_cache_${personId}`
}
function readCache(personId: string): HealthAction[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(cacheKey(personId))
    return raw ? (JSON.parse(raw) as HealthAction[]) : []
  } catch {
    return []
  }
}
function writeCache(personId: string, actions: HealthAction[]) {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(cacheKey(personId), JSON.stringify(actions))
  } catch {}
}

type ActionContextValue = {
  actions: HealthAction[]
  isLoading: boolean
  createFromSource: (sourceType: HealthAction['source_type'], source: Record<string, unknown>, status?: HealthAction['status']) => Promise<void>
  /** Create an Action from a backend UnifiedDecisionItem, deduplicating by source_id/title. */
  createFromDecisionItem: (item: UnifiedDecisionItem) => Promise<{ existed: boolean }>
  updateStatus: (id: string, status: HealthAction['status']) => Promise<void>
  deleteAction: (id: string) => Promise<void>
  refreshActions: () => Promise<void>
}

const ActionContext = createContext<ActionContextValue>({
  actions: [],
  isLoading: false,
  createFromSource: async () => {},
  createFromDecisionItem: async () => ({ existed: false }),
  updateStatus: async () => {},
  deleteAction: async () => {},
  refreshActions: async () => {},
})

export function ActionProvider({ children }: { children: ReactNode }) {
  const { personId } = usePerson()
  const [actions, setActions] = useState<HealthAction[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const inflightRef = useRef(false)

  // Normalise a raw API response row → HealthAction shape
  function normalise(raw: Record<string, unknown>): HealthAction {
    return {
      id: String(raw.id ?? ''),
      person_id: String(raw.person_id ?? personId ?? ''),
      source_type: (raw.source_type as HealthAction['source_type']) ?? 'manual',
      source_id: String(raw.source_id ?? ''),
      title: String(raw.title ?? ''),
      description: String(raw.description ?? ''),
      action_type: (raw.action_type as HealthAction['action_type']) ?? 'lifestyle',
      priority: (raw.priority as HealthAction['priority']) ?? 'medium',
      status: (raw.status as HealthAction['status']) ?? 'todo',
      due_date: raw.due_date ? String(raw.due_date) : undefined,
      frequency: (raw.frequency as HealthAction['frequency']) ?? 'daily',
      streak: typeof raw.streak_count === 'number' ? raw.streak_count : (typeof raw.streak === 'number' ? raw.streak : 0),
      last_completed_at: raw.last_completed_at ? String(raw.last_completed_at) : undefined,
      completed_at: raw.completed_at ? String(raw.completed_at) : undefined,
      impact_status: (raw.impact_status as HealthAction['impact_status']) ?? 'no_change',
      reminder_status: (raw.reminder_status as HealthAction['reminder_status']) ?? 'none',
      snoozed_until: raw.snoozed_until ? String(raw.snoozed_until) : undefined,
      snoozed_at: raw.snoozed_at ? String(raw.snoozed_at) : undefined,
      snooze_reason: raw.snooze_reason ? String(raw.snooze_reason) : undefined,
      resurface_count: typeof raw.resurface_count === 'number' ? raw.resurface_count : 0,
      confidence: typeof raw.confidence === 'number' ? raw.confidence : undefined,
      evidence_level: raw.evidence_level ? (raw.evidence_level as 'A' | 'B' | 'C') : undefined,
      guideline_source: raw.guideline_source ? String(raw.guideline_source) : undefined,
      rule_id: raw.rule_id ? String(raw.rule_id) : undefined,
      category: raw.category ? String(raw.category) : undefined,
      created_at: raw.created_at ? String(raw.created_at) : new Date().toISOString(),
    }
  }

  const refreshActions = useCallback(async () => {
    if (!personId || inflightRef.current) return
    inflightRef.current = true
    setIsLoading(true)
    try {
      const rows = await api.getActions(personId)
      const normalised = (Array.isArray(rows) ? rows : []).map((r: Record<string, unknown>) => normalise(r))
      setActions(normalised)
      writeCache(personId, normalised)
    } catch {
      // On network error, fall back to cache
      const cached = readCache(personId)
      if (cached.length) setActions(cached)
    } finally {
      setIsLoading(false)
      inflightRef.current = false
    }
  }, [personId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!personId) { setActions([]); return }
    // Seed from cache immediately so UI has data while fetching
    const cached = readCache(personId)
    if (cached.length) setActions(cached)
    refreshActions()
  }, [personId, refreshActions])

  const value = useMemo(
    () => ({
      actions,
      isLoading,
      refreshActions,

      createFromSource: async (
        sourceType: HealthAction['source_type'],
        source: Record<string, unknown>,
        status: HealthAction['status'] = 'todo'
      ) => {
        if (!personId) return
        const payload = buildActionFromSource(personId, sourceType, source, status)
        // Optimistic insert
        setActions((prev) => {
          const updated = [payload, ...prev]
          writeCache(personId, updated)
          return updated
        })
        try {
          const created = await api.createAction({
            source_type: payload.source_type,
            source_id: payload.source_id,
            title: payload.title,
            description: payload.description,
            category: payload.category,
            action_type: payload.action_type,
            priority: payload.priority,
            frequency: payload.frequency,
            status: payload.status,
            due_date: payload.due_date,
            confidence: payload.confidence,
            evidence_level: payload.evidence_level,
            guideline_source: payload.guideline_source,
            rule_id: payload.rule_id,
          })
          trackEvent('create_action', { page: '/platform/actions', metadata: { action_id: created?.id, source_type: sourceType, status } })
          // Replace optimistic with server response
          await refreshActions()
        } catch {
          // Rollback optimistic on failure
          await refreshActions()
        }
      },

      /**
       * Create an action from a backend UnifiedDecisionItem, preserving all
       * decision metadata (source_type, source_id, why_now, priority,
       * evidence_level, guideline_source).
       *
       * Deduplication: if an action with the same source_id (or a fuzzy-title
       * match with ≥80% overlap) already exists and is NOT done/snoozed, we
       * skip creation and return { existed: true } so the UI can navigate to
       * the existing action instead.
       */
      createFromDecisionItem: async (item: UnifiedDecisionItem): Promise<{ existed: boolean }> => {
        if (!personId) return { existed: false }

        // ── Deduplication check ─────────────────────────────────────────────
        const normalize = (s: string) => s.trim().toLowerCase().replace(/\s+/g, ' ')
        const itemTitle = normalize(item.title)
        const existing = actions.find((a) => {
          // Exact source_id match (same origin from decision engine)
          if (a.source_id && a.source_id === item.source_id) return true
          // Fuzzy title match — avoid creating duplicate with different wording
          const aTitle = normalize(a.title)
          if (aTitle.length > 0 && itemTitle.length > 0) {
            const longer = Math.max(aTitle.length, itemTitle.length)
            // Simple Dice coefficient on shared bigrams
            let shared = 0
            for (let i = 0; i < itemTitle.length - 1; i++) {
              const bigram = itemTitle.slice(i, i + 2)
              if (aTitle.includes(bigram)) shared++
            }
            const similarity = (2 * shared) / (aTitle.length + itemTitle.length - 2)
            if (similarity >= 0.75) return true
          }
          return false
        })
        // If found and still active, skip creation
        if (existing && existing.status !== 'done' && existing.status !== 'snoozed') {
          return { existed: true }
        }

        // ── Build payload preserving all decision metadata ──────────────────
        const now = new Date()
        const priority = item.priority as HealthAction['priority']
        const payload: HealthAction = {
          id: `act_${now.getTime()}_${Math.random().toString(36).slice(2, 8)}`,
          person_id: personId,
          source_type: (item.source_type as HealthAction['source_type']) ?? 'recommendation',
          source_id: item.source_id,
          title: item.title,
          description: item.description || item.why_now[0] || '',
          action_type: item.source_type === 'alert' ? 'monitor' : 'lifestyle',
          priority,
          status: 'todo',
          due_date: item.due_date ?? new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString(),
          frequency: 'daily',
          streak: 0,
          impact_status: 'no_change',
          reminder_status: 'none',
          confidence: item.confidence,
          evidence_level: item.evidence_level as 'A' | 'B' | 'C' | undefined,
          guideline_source: item.guideline_source ?? undefined,
          rule_id: item.source_id,
          category: item.category,
          created_at: now.toISOString(),
        }

        // Optimistic insert
        setActions((prev) => {
          const updated = [payload, ...prev]
          writeCache(personId, updated)
          return updated
        })
        try {
          await api.createAction({
            source_type: payload.source_type,
            source_id: payload.source_id,
            title: payload.title,
            description: payload.description,
            category: payload.category,
            action_type: payload.action_type,
            priority: payload.priority,
            frequency: payload.frequency,
            status: payload.status,
            due_date: payload.due_date,
            confidence: payload.confidence,
            evidence_level: payload.evidence_level,
            guideline_source: payload.guideline_source,
            rule_id: payload.rule_id,
          })
          trackEvent('create_action_from_decision', {
            page: '/platform/actions',
            metadata: { source_id: item.source_id, source_type: item.source_type, priority: item.priority },
          })
          await refreshActions()
        } catch {
          await refreshActions()
        }
        return { existed: false }
      },

      updateStatus: async (id: string, status: HealthAction['status']) => {
        if (!personId) return
        // Optimistic update
        setActions((prev) => {
          const updated = prev.map((a) =>
            a.id !== id ? a : { ...a, status, completed_at: status === 'done' ? new Date().toISOString() : a.completed_at }
          )
          writeCache(personId, updated)
          return updated
        })
        try {
          await api.updateAction(id, { status })
          if (status === 'done') {
            trackEvent('complete_action', { page: '/platform/actions', metadata: { action_id: id } })
          } else if (status === 'in_progress') {
            trackEvent('checkin_action', { page: '/platform/actions', metadata: { action_id: id } })
          }
          await refreshActions()
        } catch {
          await refreshActions()
        }
      },

      deleteAction: async (id: string) => {
        if (!personId) return
        setActions((prev) => {
          const updated = prev.filter((a) => a.id !== id)
          writeCache(personId, updated)
          return updated
        })
        try {
          await api.deleteAction(id)
          await refreshActions()
        } catch {
          await refreshActions()
        }
      },
    }),
    [actions, isLoading, personId, refreshActions]
  )

  return <ActionContext.Provider value={value}>{children}</ActionContext.Provider>
}

export function useActions() {
  return useContext(ActionContext)
}

