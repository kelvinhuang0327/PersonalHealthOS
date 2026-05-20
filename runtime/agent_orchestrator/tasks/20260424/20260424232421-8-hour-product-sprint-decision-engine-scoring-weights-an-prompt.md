# Planner Task Prompt

## Objective
8-hour product sprint: Decision Engine scoring weights and explainability

## Task Draft
8-hour product sprint: Decision Engine scoring weights and explainability

User Value: Users see health scores and decisions but cannot understand why. "Your cardiovascular score is 62" is meaningless without a cause-and-effect explanation. This task makes every decision legible and trustworthy.

Product Maturity Impact: Decision explainability is the #1 factor in clinical trust. A platform that explains its reasoning converts passive viewers into active participants.

Expected Change: Users who previously saw a score and gave up now read the explanation and understand what to change. The top_factors field turns every score into a coaching moment, converting passive data viewers into active health participants.

Objective: Audit scoring weight logic and add explainability to the top-3 decision outputs.

Phase 1: Inspect backend/app/core/ (confidence engine, clinical score engine). Document every hardcoded weight and threshold. Which inputs have the most influence? Are weights validated against any evidence base?
Phase 2: Audit the decision output format. Does the API response include a human-readable explanation of why the score is what it is? If not, design the explanation schema: top_factors (list of {factor, contribution, direction}) alongside the score.
Phase 3: Implement explanation generation for the top-3 decision types (risk score, action priority, narrative summary). Update ai/prompts/ to include factor attribution in output.
Phase 4: Run `make backend-test`. Add a test that asserts the decision response includes top_factors with at least 2 entries. Verify no regression in existing clinical score tests.

Scope: backend/app/core/, backend/app/services/, ai/prompts/, backend/tests/
Files to inspect: backend/app/core/ (confidence_engine, clinical_score_engine), ai/prompts/health_risk_prediction_prompt.md
Acceptance Criteria: make backend-test passes; decision API response includes top_factors explanation field; at least 2 explanation-assertion tests added; scoring weights documented with rationale.
focus_keys: decision_engine, explainability, scoring_weights, confidence, clinical_trust
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
decision_engine, explainability, scoring_weights, confidence, clinical_trust

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #199 status=QUEUED objective=8-hour product sprint: Action recommendation precision and deduplication
