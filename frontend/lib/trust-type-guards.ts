/**
 * trust-type-guards.ts — Task 4: Structural smoke / type validation
 *
 * These functions use TypeScript type narrowing to validate that runtime objects
 * from the API match the expected type shapes. Being in .ts (not .test.ts) means
 * `npx tsc --noEmit` alone will catch any shape regressions without needing a
 * test runner in the frontend.
 *
 * Usage: imported and called in components to narrow API responses.
 *        TypeScript compile step enforces structural correctness at build time.
 */

import type { RecommendationTrust } from './api'
import type { DailyHealthSummary } from './api'
import type { OutcomeFeedback } from './api'

// ── RecommendationTrust ───────────────────────────────────────────────────────

export function isRecommendationTrust(value: unknown): value is RecommendationTrust {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return (
    typeof v.confidence === 'number' &&
    typeof v.level === 'string' &&
    Array.isArray(v.reasons) &&
    Array.isArray(v.limitations) &&
    typeof v.verifiedByOutcome === 'boolean' &&
    typeof v.nextCheckInSuggestion === 'string'
  )
}

/** Validate a trust object and return it (throws if invalid). */
export function assertRecommendationTrust(value: unknown): RecommendationTrust {
  if (!isRecommendationTrust(value)) {
    throw new TypeError('assertRecommendationTrust: received invalid RecommendationTrust shape')
  }
  return value
}

// ── DailyHealthSummary ────────────────────────────────────────────────────────

export function isDailyHealthSummary(value: unknown): value is DailyHealthSummary {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return (
    typeof v.person_id === 'string' &&
    typeof v.generated_at === 'string' &&
    typeof v.topRisk === 'string' &&
    typeof v.biggestChange === 'string' &&
    typeof v.todayAction === 'string' &&
    typeof v.whyNow === 'string' &&
    typeof v.confidence === 'number'
    // missingData and encouragement are optional — not validated
  )
}

// ── OutcomeFeedback ───────────────────────────────────────────────────────────

export function isOutcomeFeedback(value: unknown): value is OutcomeFeedback {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  // OutcomeFeedback shape: { summary: { total_count, improved_count, ... }, items?: [] }
  if (typeof v.summary !== 'object' || v.summary === null) return false
  const s = v.summary as Record<string, unknown>
  return (
    typeof s.total_count === 'number' &&
    typeof s.improved_count === 'number' &&
    typeof s.unchanged_count === 'number' &&
    typeof s.deteriorated_count === 'number' &&
    typeof s.tracking_count === 'number'
  )
}

// ── Compile-time shape check (catches regressions at tsc step) ────────────────
// These lines are intentionally never called at runtime.
// They exist purely so that `tsc --noEmit` will error if the type shapes diverge.

function _compileTimeShapeChecks() {
  // Verify we can assign all required trust fields
  const trust: RecommendationTrust = {
    confidence: 0.8,
    level: 'high',
    reasons: ['data present'],
    limitations: [],
    verifiedByOutcome: false,
    nextCheckInSuggestion: 'Check in tomorrow',
  }

  // Verify DailyHealthSummary fields
  const summary: DailyHealthSummary = {
    person_id: 'p1',
    generated_at: new Date().toISOString(),
    topRisk: '',
    biggestChange: '',
    todayAction: '',
    whyNow: '',
    confidence: 0.75,
  }

  // Suppress unused variable warnings
  void trust
  void summary
}

// Prevent tree-shaking from dropping the function (it's called nowhere)
export const _enableCompileChecks = _compileTimeShapeChecks
