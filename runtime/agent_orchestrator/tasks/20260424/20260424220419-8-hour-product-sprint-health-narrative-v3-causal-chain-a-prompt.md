# Planner Task Prompt

## Objective
8-hour product sprint: Health Narrative v3 causal chain and human-readable rewrite

## Task Draft
8-hour product sprint: Health Narrative v3 causal chain and human-readable rewrite

User Value: Current health narratives read like clinical notes — dense, passive, and jargon-heavy. Users do not read them. This task rewrites the narrative pipeline to produce stories that users actually finish reading and act on.

Product Maturity Impact: The health narrative is the product's voice. If it is compelling, users share it, return to it, and trust it. If it is clinical and boring, the product becomes a report viewer, not a health partner.

Expected Change: Narrative read-through rate increases as outputs become causal and plain-language. Users start sharing narratives because they are personally relevant and legible. Hallucination incidents drop as guardrails block absolute-risk language without evidence.

Objective: Upgrade the health narrative to include causal chains (X caused Y because Z), plain-language rewrites, and reduced misleading risk language.

Phase 1: Read the last 5 narrative outputs from the system (or generate examples). Score each on: readability (Flesch-Kincaid), causal clarity (does it explain why?), actionability (does it lead to a next step?). Document the top 3 weaknesses.
Phase 2: Rewrite ai/prompts/health_summary_system_prompt.md to require: (a) one causal sentence per insight (Because X, your Y is Z); (b) no passive voice in the first paragraph; (c) a concrete next-step sentence at the end of each insight block.
Phase 3: Update ai/prompts/hallucination_guardrail_policy.md to block narratives that use absolute risk language without evidence citations (e.g. "you will develop..." must be rejected).
Phase 4: Run `make backend-test` and `pytest tests/test_ai_service.py`. Add 2 new tests: one that checks causal sentence format, one that blocks absolute-risk language. Verify all existing tests pass.

Scope: ai/prompts/, backend/app/services/, backend/tests/
Files to inspect: ai/prompts/health_summary_system_prompt.md, ai/prompts/hallucination_guardrail_policy.md, backend/app/services/ai_service.py
Acceptance Criteria: Updated prompt requires causal sentences and plain language; guardrail blocks absolute-risk language; make backend-test passes; at least 2 new narrative quality tests added.
focus_keys: health_narrative, causal_chain, readability, guardrail, human_readable
expected_duration_minutes: 480

## Scope
- Read backlog and project references listed in project profile.
- Implement only what is required to satisfy this task objective.
- Produce both human-readable and machine-readable delivery artifacts.

## Constraints
- Do not modify protected paths from project profile.
- Do not leave the task in RUNNING when blocked by runtime/permission issues.
- Keep changes focused and production-safe.

## Acceptance Criteria
- Pass required check: make backend-test
- Pass required check: backend:pytest
- Pass required check: frontend:npm run build
- No forbidden path modifications.

## Handoff Notes
- Record changed files in task_result.json.
- Attach evidence for each acceptance check.
- Keep next_action clear for the next planner tick.

## System State
| 項目 | 値 |
|------|----|
| Regime | `ACTIVE` |
| 信心度 | 0.85 |
| Pass Rate | 85% |
| 失敗率 | 15% |
| 近期任務數 | 20 |

> 85% gate pass rate across last 20 tasks.

## Focus Keys
health_narrative, causal_chain, readability, guardrail, human_readable

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #189 status=QUEUED objective=8-hour product sprint: Action → Outcome → Feedback closed-loop optimization
