# Active Task — P101 Report + Symptom → Recommendation Integration Contract

**Last updated:** 2026-05-26 (P101)
**Status:** Replaces stale P64 content (authorized at P101 start, per P100 roadmap checkpoint)

---

## Task Name

`P101_REPORT_SYMPTOM_RECOMMENDATION_CONTRACT`

## Goal

Close the P1 product core gap: prove via a single mocked Playwright integration
contract that lab report evidence AND symptom evidence both surface in Daily Assistant
/ recommendation surfaces with correct source-specific hrefs and document_id deep links.

## Completed

All 5 tests created and passing under `make report-symptom-recommendation-contract`:

| # | Test | Testid / assert |
|---|------|----------------|
| T1 | Daily Assistant topRiskRef lab evidence → `?document_id=` href | `p94-top-risk-ref-link` |
| T2 | Daily Assistant todayActionRef symptom evidence → `/platform/symptoms` (no fake deeplink) | `p94-today| T2 | Daily Assistant todayActionRef symptom evidence → `/platform/symptoms` (no fake deeplink) | `p94rc| T2 | Daily Assistant todayActionRef symptom evidence → `/platform/symptomsep | T2 | Daily Assistant todayActionDo| T2 | Daily Assistant todayActionRef symptom evidence → `/platform/symptoms` (no fake deep di| og |

## Commits
## Commits
y Assistant todayActionRef symptommendation iy Assistant todayActionRef symptommendation iy Assistant todayActionRef symptoaty Assistant todayActionRef symptommendation iy Assistant todayActionRef symptommendatvin/Kelvin-WorkSpace/PersonalHealthOS`
- Canonical branch: `main`
- Do NOT: create branch / worktree / checkout other branch / detached HEAD / push / amend / force push

## Pre-flight

```
git rev-parse --show-toplevel
git branch --show-current
git status --short
git log --oneline -8
```

STOP if:
- repo ≠ PersonalHealthOS
- branch ≠ main
- missing P101 commit

## Guard Inventory (9 guards after P101)

| Guard | Tests | Phase |
|-------|-------|-------|
| `runtime-smoke` | 56 | P65+ |
| `daily-assistant-contract` | 5 | P76–P77 |
| `actions-page-contract` | 4 | P82–P83 |
| `documents-page-contract` | 4 | P85 |
| `symptoms-page-contract` | 4 | P86 |
| `documents-confirmed-data-contract` | 4 | P87 |
| `daily-summary-evidence-contract` | 4 | P92–P95 |
| `documents-evidence-deeplink-contract` | 4 | P97 |
| `report-symptom-recommendation-contract` | 5 | P101 |

**Total: 90 tests (29 Playwright + 56 backend + 5 new P101)**

## Next Recommended Lane

**P102 — Lab Trend Visualization Discovery**

Goal: Cross-report comparison table showing lab value trends across 3–5 health check
documents. Discovery/design phase only — no implementation.

Or alternatively:

**P102 — First-Run Report Upload Onboarding Discovery**

Goal: Design the first-run flow for a new user uploading their first health report.

Decision deferred to P102 CEO review.
