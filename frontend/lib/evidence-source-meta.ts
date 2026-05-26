/**
 * Shared evidence source metadata for frontend evidence badge + source-page links.
 *
 * Consumed by:
 *   - components/platform/decision-recommendation-layer.tsx (Actions page — P89)
 *   - components/platform/daily-assistant-entry.tsx (Daily Assistant — P91)
 *
 * Rules (safe, page-level only):
 *   - Entries with `href` render a source-page navigation link.
 *   - Entries without `href` render no link (label reserved for future use).
 *   - Generic source types (e.g. 'recommendation') have no entry → no link.
 *   - Do NOT add deep-links to specific records — page-level only.
 */

export type EvidenceSourceMeta = {
  label: string
  href?: string
}

export const EVIDENCE_SOURCE_META: Record<string, EvidenceSourceMeta> = {
  lab_report_item:   { label: '查看健檢報告', href: '/platform/documents' },
  lab_abnormality:   { label: '查看健檢報告', href: '/platform/documents' },
  symptom:           { label: '查看症狀紀錄', href: '/platform/symptoms' },
  long_term_symptom: { label: '查看症狀紀錄', href: '/platform/symptoms' },
  risk_alert:        { label: '查看風險提醒' },  // no href — no /risk-alerts page yet
  // P94: 3-grid card ref source types (label-only — no dedicated navigation page)
  health_metric:     { label: '健康指標數據' },
  outcome:           { label: '健康成效紀錄' },
  recommendation:    { label: '行動建議來源' },
}

/** P97: compute the evidence navigation href, upgrading to a deep-link when
 * `document_id` is available for lab-sourced evidence.
 *
 * Falls back to the page-level href from EVIDENCE_SOURCE_META when no
 * document_id is present, and returns undefined when the source type has
 * no navigation target at all.
 */
export function getEvidenceHref(
  sourceType: string,
  ref?: { document_id?: string | null },
): string | undefined {
  const meta = EVIDENCE_SOURCE_META[sourceType]
  if (!meta?.href) return undefined
  if (
    (sourceType === 'lab_report_item' || sourceType === 'lab_abnormality') &&
    ref?.document_id
  ) {
    return `/platform/documents?document_id=${ref.document_id}`
  }
  return meta.href
}
