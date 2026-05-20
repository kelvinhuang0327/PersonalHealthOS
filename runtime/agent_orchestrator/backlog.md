# Agent Orchestrator Backlog

## North Star

Continuously improve the Personal Health OS platform — making the product more valuable to users,
reducing friction in the core journey, and maturing the behavior-change engine — so users return
daily, trust the AI insights, and complete the actions that improve their health.

## Success Criteria

1. Every task produces `prompt + contract + completed + result + meta` artifacts.
2. Any `INVALID_DELIVERY` is converted to `REPLAN_REQUIRED` and never misclassified as complete.
3. Protected paths are not modified; the gate blocks non-compliant deliveries.
4. Planner/Worker iterate continuously under the fixed schedule without getting stuck in `RUNNING`.

## Priorities

### Priority 1: Core Reliability

- [ ] 8-hour audit and hardening: Clinical Rule Engine coverage and false-positive reduction
Objective: Audit the clinical rule engine, anomaly detection, and confidence engine for coverage gaps, hObjective: Audit the clinical rule engine, anomaly detection, and confidence engine for coverage gaps, hObhon scripts/validate_rules.py` and record all validation output. List every rule with low coverage or known false-positive patterns. Confirm the Objective: Audit the clinical rule engine, anomaly detection, and confidely engine, confidence engine). Document all hardcoded numeric thresholds that should be conObjective: Audit the clinical rule engine, anomaly detection, and confiderage or false-positive issues found. Add or update tests in tests/test_anomaly_engine.py and tests/test_clinical_score_engine.py.
Phase 4: Run `make backend-test` and confirm rule-engPhase 4: Run `make backend-test` and confirm rule-engPhase 4: Run `make backend-.
Scope: backend/app/core/, backend/scripts/, backend/tests/
FilesFilesFilesFilesFilesFilesFilesFilesFilesFilesFilesFilesFilesFilesFiles.py, backend/tests/test_anomaly_engine.py, backend/tests/test_clinical_score_engine.py
Recommended commands: make backend-test, python scripts/validate_rules.py
Acceptance Criteria: make backend-test passes with 0 failures; validate_rules.py exits 0; at least 3 rule improvements or new test cases added with documented rationale.
focus_keys: rule_engine, anomaly_detection, clinical_scoring, coverage, false_positive
expected_duration_minutes: 480

- [ ] 8-hour hardening: Action backend idempotency and outcome-tracking reliability
Objective: Eliminate data-loss edge cases and race conditions in the action creation, completion, and outcome-tracking pipeline.
Phase 1: Audit backend/app/api/ endpoints related to actions and styles/Phase 1: Audit backend/app/api/ endpoints related to actions and styles/Phase 1: Audit backend/app/api/ endpoints related to actions and stels/ and backend/app/services/ for action-related business logPhase 1: Audit backend/app/api/ endpoints related to actions and styles/Phase 1: Audit backend/app/api/ endpoints related to actions and styles/Phase 1: Audit backend/aonstraint enforcement, and idempotency guards. Run `pytest tests/test_action_streak.py` after each fix.
Phase 4: Add or update integration tests to cover the action creation to outcome-tracking pipeline. Ensure `make backend-test` passes with 0 failures.
Scope: backend/app/api/, backend/app/models/, backend/app/services/, backend/tests/
Files to inspect: backend/app/api/ (action-related endpoints), backend/app/services/ (action services), backend/tests/test_action_streak.py
Recommended commands: make backend-test, pytest tests/test_action_streak.py
Acceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-tesAcceptance Criteria: make backend-ardrails.
Phase 1: Review ai/prompts/ (health_summary_system_prompt.md, health_risk_prediction_prompt.md, symptom_analysis_prompt.md). Identify gaps in components/Phase 1: Review ai/prompts/ (health_summary_system_prompt.md, health_rase 2: InspectPhase 1: Review ai/prompts/ (health_summary_system_prompt.md, health_risk_prediction_prompt.md, symptom_analysis_prompt.md). Identify gapsumPhase 1: Review ai/prompts/ (health_summary_system_prompt.md, h.
Phase 3: Revise prompt templates to strengthen evidence requirements and reduce hallucination risk. Add or improve guardrail checks in backend/app/services/ai_guardrail_service.py.
Phase 4: Run `make backend-test` and `pytest tests/test_ai_service.py tests/test_ai_guardrail_service.py`. Verify all existing assertions pass. Add at least 2 new regression tests for edge-case guardrail behaviour.
Scope: ai/prompts/, backend/app/services/, backend/tests/
Files to inspect: ai/prompts/health_summary_system_prompt.md, ai/prompts/hallucination_guardrail_policy.md, backend/app/services/aFiles to inspect: ai/prompts/health_summary_system_prompt.md, ai/prompts/hallucination_guardrail_policy.md, backend/app/services/aFiles to inspect: ai/prompts/health_summary_system_prompt.md, ai/prompts/hallucination_guardrail_policy.md, backend/app/services/aFiles to inspect: ai/prompts/health_summary_system_prompt.md, ai/prompts/hallucination_guardrail_policy.md, backend/app/services/aFiles to inspect: ai/prompts/health_r Confidence

- [ ] 8-hour stabilisation: Build pipeline and test suite flaky-test elimination
Objective: Identify and resolve flaky tests, slow build steps, and recurring CI issues that reduce developer confidence in the test suite, and document build times before/after.
Phase 1: Run `make backend-test` and `npm run build` in sequence. Record all warnings, tests taking longer than 1 second, and any intermittent failures. List the top-5 stability risks.
PhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhPhmpose*.yml, Makefile
Files to inspect: backend/pytest.ini, backend/Dockerfile, frontend/Dockerfile, Makefile, docker-compose.yml
Recommended commands: make backend-test, npm run build, npm run lint
Acceptance Criteria: make backend-test passes at least 2 consecuAcceptance Criteria: make backend-test passes at least 2 consecuAcceptance Criteria: make backend-test passes at least 2 consecuAcceptance Criteria: make backend-test passes aolation
Acceptance Criteria: make backend-test passes at least 2 consecuAcceptance Criteria: make backend-test passes at least 2 consecuAcceptance Criteria: make backend-test passes at least 2 consecuAcceptance Criteria: make backend-test passes aolation
s across clean environments.
Phase 1: Run `python scripts/seed_demo_data.py` twice in a clean Docker environment (docker-compose.local.yml). Record any errors, non-idempotent behaviour, or missing data categories.
Phase 2: Inspect backend/scripts/ (seed_demo_data.py, self_heal_db.py, ensure_indexes.py). Document all hardcoded paths, missinPhase 2: Inspect backend/scripts/ (seed_demo_data.py, self_heal_db.py, ensure_indexes.py). Document ald add Phase 2: Inspect backend/scripts/ (seed_demo_data.py, self_heal_db. styles/Phase 2: Inspect backend/scripts/ (seed_demo_data.py, self_heal_db.py, ensure_indexes.py). Document all hardcoded paths, missinPhase 2: Inspect backend/scripts/ (seed_demo_data.py, self_heal_db.py, ensure_indexes.py). Document ald add Phase mpose.local.yml, setup.sh
Files to inspect: backend/scripts/seed_demo_data.py, backend/scripts/self_heal_db.py, backend/scripts/ensure_indexes.py, setup.sh
Recommended commands: python scripts/seed_demo_data.py, make backend-test
Acceptance Criteria: seed_demo_data.py runs idempotentAcceptance Criteria: seed_demo_data.py runs idempotentAcceptance Criteria: seed_demo_data.py runs idempotentAcceptance Criteria: seed_demo_data.py runs idempotentAcceptance Criterie
expected_duration_minutes: 480
