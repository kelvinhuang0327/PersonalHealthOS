/**
 * P108 — Unit Alias Normalization
 *
 * Normalizes clinically equivalent unit spellings for comparison only.
 * Raw unit strings must be displayed exactly as reported.
 *
 * Aliases handled:
 *   IU/L  → U/L   (international units, same magnitude as U/L for common enzymes)
 *   iu/l  → u/l   (lowercase variant)
 *   μmol  → umol  (Unicode Greek mu → ASCII u)
 *   µmol  → umol  (Unicode micro sign → ASCII u)
 *
 * NOT handled (real conversion required — must remain suppressed):
 *   mg/dL ↔ mmol/L
 */
export function normalizeUnitForCompare(unit?: string | null): string {
  return (unit ?? '')
    .trim()
    .toLowerCase()
    .replace(/^µ/, 'u')
    .replace(/^μ/, 'u')
    .replace(/^iu\//, 'u/')
}
