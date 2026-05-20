"""task_pool.py — Programmatic 8-hour task pool for Personal Health OS.

The pool drives continuous product improvement across 12 categories ordered by
user-impact priority:

  Tier 1 — Behavior & UX (highest user value)
    behavior_loop_optimization
    ux_flow_redesign
    action_system_enhancement

  Tier 2 — Intelligence & Narrative
    decision_engine_improvement
    health_narrative_deepening
    user_journey_analysis

  Tier 3 — Engagement & Growth
    retention_habit_loop
    notifications_lifecycle
    reports_product_value

  Tier 4 — Data & Consistency
    timeline_history_value
    growth_analytics
    cross_page_consistency

When the markdown backlog is exhausted or blocked by the Duplicate Gate, the
planner draws from this pool in priority order, ensuring continuous forward
progress on real product value — never just engineering busywork.

Rotation rules:
  • Planner never picks the same category consecutively.
  • Tier 1 categories are weighted 3×, Tier 2 2×, Tier 3/4 1× in frequency.
  • Engineering-only tasks (no user value statement) are blocked by the gate.
"""
from __future__ import annotations

import re
from typing import Any

from app.orchestrator.task_quality_gate import TaskDraft

# ── Category priority tiers ───────────────────────────────────────────────────
# Planner picks from TIER_1 first, then TIER_2, then TIER_3_4.
# Within each tier, least-recently-used wins.

_TIER_1 = [
    'behavior_loop_optimization',
    'ux_flow_redesign',
    'action_system_enhancement',
]
_TIER_2 = [
    'decision_engine_improvement',
    'health_narrative_deepening',
    'user_journey_analysis',
]
_TIER_3_4 = [
    'retention_habit_loop',
    'notifications_lifecycle',
    'reports_product_value',
    'timeline_history_value',
    'growth_analytics',
    'cross_page_consistency',
]

# Weighted rotation order exposed to the planner (Tier 1 × 3, Tier 2 × 2, Tier 3/4 × 1)
CATEGORIES: list[str] = _TIER_1 + _TIER_2 + _TIER_3_4

# ── Task templates (one per category) ────────────────────────────────────────
# Each template must pass evaluate_task_draft:
#   • ≥200 chars
#   • ≥3 content lines (phases / scope / acceptance)
#   • Acceptance criteria present
#   • No banned tokens
#
# PRIORITY ORDER: Tier 1 (Behavior/UX) > Tier 2 (Intelligence) > Tier 3/4 (Engagement/Data)
# Each template explicitly states User Value and Product Maturity Impact.

_TASK_TEMPLATES: dict[str, dict[str, Any]] = {

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 1 — Behavior & UX  (highest user value, picked first)
    # ══════════════════════════════════════════════════════════════════════════

    'behavior_loop_optimization': {
        'title': '8-hour product sprint: Action → Outcome → Feedback closed-loop optimization',
        'draft_markdown': (
            '8-hour product sprint: Action → Outcome → Feedback closed-loop optimization\n\n'
            'User Value: Users who complete a health action today get no meaningful feedback on whether '
            'it worked. This task closes that loop — making every action feel worth doing again.\n\n'
            'Product Maturity Impact: Transforms the platform from a task-tracker into a genuine '
            'behavior-change engine. Completion rate and 7-day retention are the north-star metrics.\n\n'
            'Expected Change: Action completion rate rises as users see that their actions produce '
            'measurable outcomes. AI recommendation quality improves progressively as outcome data '
            'accumulates — the engine becomes self-improving.\n\n'
            'Objective: Design and implement the full behavior loop: Action completion triggers an '
            'Outcome check-in prompt; the check-in result feeds back into the AI narrative and the '
            'next Action recommendation. Track completion rate before and after.\n\n'
            'Phase 1: Map the current behavior loop gap. Find where action completion data exists '
            'in the backend (backend/app/api/, backend/app/models/) and where it does NOT feed back '
            'into insights or the next recommendation cycle. Document the exact missing links.\n'
            'Phase 2: Design the Outcome check-in model. Sketch the data schema (action_id, '
            'outcome_rating, outcome_note, checked_at). Implement the API endpoint POST /actions/{id}/outcome '
            'with proper validation and idempotency.\n'
            'Phase 3: Wire the outcome into the AI recommendation pipeline. When generating the next '
            'prioritized_actions list, weight actions whose previous outcomes were positive higher. '
            'Update ai/prompts/health_summary_system_prompt.md to reference recent outcomes.\n'
            'Phase 4: Add the outcome check-in UI prompt to the frontend action completion flow. '
            'Show a simple 1-5 star or thumbs-up/down after marking an action done. '
            'Run `npm run lint` and `make backend-test` to confirm no regressions.\n\n'
            'Scope: backend/app/api/, backend/app/models/, backend/app/services/, '
            'ai/prompts/, frontend/app/platform/, frontend/components/\n'
            'Acceptance Criteria: POST /actions/{id}/outcome endpoint exists and returns 200; '
            'outcome data influences the next AI recommendation cycle; '
            'frontend shows outcome prompt after action completion; '
            'make backend-test passes; npm run lint passes.\n'
            'focus_keys: behavior_loop, outcome_tracking, feedback, action_completion, retention\n'
            'expected_duration_minutes: 480'
        ),
        'focus_keys': ('behavior_loop', 'outcome_tracking', 'feedback', 'action_completion', 'retention'),
        'duplicate_signature': 'behavior_loop_optimization_v1',
        'category': 'behavior_loop_optimization',
    },

    'ux_flow_redesign': {
        'title': '8-hour product sprint: Dashboard → Insights → Action flow friction reduction',
        'draft_markdown': (
            '8-hour product sprint: Dashboard → Insights → Action flow friction reduction\n\n'
            'User Value: New users arrive at the Dashboard and do not know what to do next. '
            'This task audits and removes every step of unnecessary friction so the '
            '"Dashboard → read an Insight → take an Action" journey takes under 60 seconds.\n\n'
            'Product Maturity Impact: A frictionless core flow is the single biggest lever '
            'for first-week retention. Removing 3 friction points can double D7 retention.\n\n'
            'Expected Change: Time-to-first-action drops from 3+ clicks to under 60 seconds. '
            'Empty states become guided onboarding moments instead of dead ends. '
            'D7 retention improves as fewer users abandon before taking their first action.\n\n'
            'Objective: Audit the core user flow from Dashboard to Insights to Action completion. '
            'Identify the top 5 friction points. Fix at least 3 of them.\n\n'
            'Phase 1: Walk through the full flow as a first-time user. Document every click, load, '
            'blank state, confusing label, and missing CTA. Use frontend/app/platform/ as your map. '
            'Rate each step: Does it move the user forward or create hesitation?\n'
            'Phase 2: Inspect the Dashboard page (app/platform/dashboard/page.tsx). '
            'Is the most important health signal visible above the fold? '
            'Is there a clear next-action CTA? Are empty states helpful or discouraging?\n'
            'Phase 3: Fix the top-3 friction points. Concrete examples: add a "Start here" CTA '
            'to empty Dashboard; improve Insight card CTAs to link directly to the relevant Action; '
            'reduce loading states with skeleton placeholders; clarify confusing copy.\n'
            'Phase 4: Run `npm run lint` to confirm no regressions. '
            'Write a brief before/after friction audit report (what changed and why).\n\n'
            'Scope: frontend/app/platform/dashboard/, frontend/app/platform/insights/, '
            'frontend/app/platform/actions/, frontend/components/\n'
            'Files to inspect: app/platform/dashboard/page.tsx, app/platform/insights/, '
            'app/platform/actions/, components/shared/\n'
            'Acceptance Criteria: At least 3 friction points fixed with evidence; '
            'Dashboard has a visible primary CTA in empty state; '
            'npm run lint passes; before/after audit documented.\n'
            'focus_keys: ux_flow, dashboard, insights, friction, cta, onboarding\n'
            'expected_duration_minutes: 480'
        ),
        'focus_keys': ('ux_flow', 'dashboard', 'insights', 'friction', 'cta', 'onboarding'),
        'duplicate_signature': 'ux_flow_redesign_v1',
        'category': 'ux_flow_redesign',
    },

    'action_system_enhancement': {
        'title': '8-hour product sprint: Action recommendation precision and deduplication',
        'draft_markdown': (
            '8-hour product sprint: Action recommendation precision and deduplication\n\n'
            'User Value: Users currently see duplicated or irrelevant action recommendations, '
            'which erodes trust and reduces completion rates. This task makes every recommended '
            'action feel personally relevant and achievable.\n\n'
            'Product Maturity Impact: Precision of action recommendations is a core differentiator. '
            'A recommendation engine that learns from outcomes creates a moat that generic apps cannot copy.\n\n'
            'Expected Change: Users receive a deduplicated, personalized action list every session. '
            'Actions with positive past outcomes rise to the top. '
            'Over 4 weeks the recommendation engine becomes measurably self-improving.\n\n'
            'Objective: Audit the action recommendation pipeline. Remove duplicates. '
            'Improve relevance scoring. Correlate recommended action priority with actual completion rate.\n\n'
            'Phase 1: Audit the current action recommendation logic in backend/app/services/. '
            'Find where duplicates arise (same action recommended multiple times, same category repeatedly). '
            'Document the deduplication gap.\n'
            'Phase 2: Inspect how prioritized_actions are scored. What signals feed into the priority? '
            'Is there any personalization based on past completions or outcomes? '
            'Document missing signals.\n'
            'Phase 3: Implement deduplication: within a single recommendation batch, '
            'no action title or category should appear more than once. '
            'Add at least one personalization signal (e.g. past completion rate for that action type).\n'
            'Phase 4: Run `make backend-test`. Add tests that assert: '
            '(a) no duplicate action titles in a recommendation batch; '
            '(b) actions with higher past completion rates score higher. '
            'Document priority vs completion correlation before/after.\n\n'
            'Scope: backend/app/services/, backend/app/api/, backend/tests/\n'
            'Files to inspect: backend/app/services/ (action recommendation services), '
            'backend/app/api/ (action endpoints)\n'
            'Acceptance Criteria: make backend-test passes; '
            'no duplicate actions in a recommendation batch (asserted by test); '
            'at least one personalization signal implemented; '
            'priority vs completion correlation documented.\n'
            'focus_keys: action_recommendation, deduplication, personalization, completion_rate, precision\n'
            'expected_duration_minutes: 480'
        ),
        'focus_keys': ('action_recommendation', 'deduplication', 'personalization', 'completion_rate', 'precision'),
        'duplicate_signature': 'action_system_enhancement_v1',
        'category': 'action_system_enhancement',
    },

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 2 — Intelligence & Narrative
    # ══════════════════════════════════════════════════════════════════════════

    'decision_engine_improvement': {
        'title': '8-hour product sprint: Decision Engine scoring weights and explainability',
        'draft_markdown': (
            '8-hour product sprint: Decision Engine scoring weights and explainability\n\n'
            'User Value: Users see health scores and decisions but cannot understand why. '
            '"Your cardiovascular score is 62" is meaningless without a cause-and-effect explanation. '
            'This task makes every decision legible and trustworthy.\n\n'
            'Product Maturity Impact: Decision explainability is the #1 factor in clinical trust. '
            'A platform that explains its reasoning converts passive viewers into active participants.\n\n'
            'Expected Change: Users who previously saw a score and gave up now read the explanation '
            'and understand what to change. The top_factors field turns every score into a coaching '
            'moment, converting passive data viewers into active health participants.\n\n'
            'Objective: Audit scoring weight logic and add explainability to the top-3 decision outputs.\n\n'
            'Phase 1: Inspect backend/app/core/ (confidence engine, clinical score engine). '
            'Document every hardcoded weight and threshold. Which inputs have the most influence? '
            'Are weights validated against any evidence base?\n'
            'Phase 2: Audit the decision output format. Does the API response include a human-readable '
            'explanation of why the score is what it is? If not, design the explanation schema: '
            'top_factors (list of {factor, contribution, direction}) alongside the score.\n'
            'Phase 3: Implement explanation generation for the top-3 decision types '
            '(risk score, action priority, narrative summary). '
            'Update ai/prompts/ to include factor attribution in output.\n'
            'Phase 4: Run `make backend-test`. Add a test that asserts the decision response '
            'includes top_factors with at least 2 entries. '
            'Verify no regression in existing clinical score tests.\n\n'
            'Scope: backend/app/core/, backend/app/services/, ai/prompts/, backend/tests/\n'
            'Files to inspect: backend/app/core/ (confidence_engine, clinical_score_engine), '
            'ai/prompts/health_risk_prediction_prompt.md\n'
            'Acceptance Criteria: make backend-test passes; '
            'decision API response includes top_factors explanation field; '
            'at least 2 explanation-assertion tests added; '
            'scoring weights documented with rationale.\n'
            'focus_keys: decision_engine, explainability, scoring_weights, confidence, clinical_trust\n'
            'expected_duration_minutes: 480'
        ),
        'focus_keys': ('decision_engine', 'explainability', 'scoring_weights', 'confidence', 'clinical_trust'),
        'duplicate_signature': 'decision_engine_improvement_v1',
        'category': 'decision_engine_improvement',
    },

    'health_narrative_deepening': {
        'title': '8-hour product sprint: Health Narrative v3 causal chain and human-readable rewrite',
        'draft_markdown': (
            '8-hour product sprint: Health Narrative v3 causal chain and human-readable rewrite\n\n'
            'User Value: Current health narratives read like clinical notes — dense, passive, and '
            'jargon-heavy. Users do not read them. This task rewrites the narrative pipeline to '
            'produce stories that users actually finish reading and act on.\n\n'
            'Product Maturity Impact: The health narrative is the product\'s voice. '
            'If it is compelling, users share it, return to it, and trust it. '
            'If it is clinical and boring, the product becomes a report viewer, not a health partner.\n\n'
            'Expected Change: Narrative read-through rate increases as outputs become causal and plain-language. '
            'Users start sharing narratives because they are personally relevant and legible. '
            'Hallucination incidents drop as guardrails block absolute-risk language without evidence.\n\n'
            'Objective: Upgrade the health narrative to include causal chains '
            '(X caused Y because Z), plain-language rewrites, and reduced misleading risk language.\n\n'
            'Phase 1: Read the last 5 narrative outputs from the system (or generate examples). '
            'Score each on: readability (Flesch-Kincaid), causal clarity (does it explain why?), '
            'actionability (does it lead to a next step?). Document the top 3 weaknesses.\n'
            'Phase 2: Rewrite ai/prompts/health_summary_system_prompt.md to require: '
            '(a) one causal sentence per insight (Because X, your Y is Z); '
            '(b) no passive voice in the first paragraph; '
            '(c) a concrete next-step sentence at the end of each insight block.\n'
            'Phase 3: Update ai/prompts/hallucination_guardrail_policy.md to block narratives '
            'that use absolute risk language without evidence citations '
            '(e.g. "you will develop..." must be rejected).\n'
            'Phase 4: Run `make backend-test` and `pytest tests/test_ai_service.py`. '
            'Add 2 new tests: one that checks causal sentence format, '
            'one that blocks absolute-risk language. Verify all existing tests pass.\n\n'
            'Scope: ai/prompts/, backend/app/services/, backend/tests/\n'
            'Files to inspect: ai/prompts/health_summary_system_prompt.md, '
            'ai/prompts/hallucination_guardrail_policy.md, backend/app/services/ai_service.py\n'
            'Acceptance Criteria: Updated prompt requires causal sentences and plain language; '
            'guardrail blocks absolute-risk language; '
            'make backend-test passes; at least 2 new narrative quality tests added.\n'
            'focus_keys: health_narrative, causal_chain, readability, guardrail, human_readable\n'
            'expected_duration_minutes: 480'
        ),
        'focus_keys': ('health_narrative', 'causal_chain', 'readability', 'guardrail', 'human_readable'),
        'duplicate_signature': 'health_narrative_deepening_v1',
        'category': 'health_narrative_deepening',
    },

    'user_journey_analysis': {
        'title': '8-hour product sprint: Full user journey friction audit — Report upload to Action complete',
        'draft_markdown': (
            '8-hour product sprint: Full user journey friction audit — Report upload to Action complete\n\n'
            'User Value: A new user who uploads a health report should be able to '
            'read an AI insight and complete their first recommended action in under 5 minutes. '
            'This task maps and fixes the biggest blockers in that journey.\n\n'
            'Product Maturity Impact: The "time to first meaningful outcome" metric defines '
            'whether a user becomes a retained user or churns. '
            'Shortening TTFMO from 30 minutes to 5 minutes is a step-change in product maturity.\n\n'
            'Expected Change: TTFMO drops visibly after fixing the top-3 friction points. '
            'Fewer users abandon between report upload and first action. '
            'The friction audit becomes a repeatable quarterly product-quality process.\n\n'
            'Objective: End-to-end audit of the journey from Report Upload → AI Insight → Action '
            'completion. Find and fix the top-3 friction points.\n\n'
            'Phase 1: Trace the full journey in the codebase and UI. '
            'Report Upload: what happens after the file is accepted? '
            'How long before an Insight appears? What if parsing fails? '
            'Insight: is the connection from insight to action explicit? '
            'Action: how many taps to mark complete? Document each step with file references.\n'
            'Phase 2: Score each step on: latency (does the user wait?), '
            'clarity (does the user know what to do?), confidence (does the user trust the result?). '
            'Identify the 3 steps with the lowest scores.\n'
            'Phase 3: Fix the top-3 friction steps. Examples: '
            'add a progress indicator during report parsing; '
            'add an explicit "This insight suggests → [Action]" link; '
            'reduce action completion to a single tap from the Insight card.\n'
            'Phase 4: Run `npm run lint` and `make backend-test`. '
            'Document the before/after step count and estimated TTFMO improvement.\n\n'
            'Scope: frontend/app/platform/, backend/app/api/, backend/app/services/\n'
            'Files to inspect: app/platform/reports/, app/platform/insights/, '
            'app/platform/actions/, backend/app/api/ (report endpoints)\n'
            'Acceptance Criteria: At least 3 friction steps fixed with evidence; '
            'before/after journey step count documented; '
            'npm run lint and make backend-test pass.\n'
            'focus_keys: user_journey, friction_audit, ttfmo, onboarding, report_to_action\n'
            'expected_duration_minutes: 480'
        ),
        'focus_keys': ('user_journey', 'friction_audit', 'ttfmo', 'onboarding', 'report_to_action'),
        'duplicate_signature': 'user_journey_analysis_v1',
        'category': 'user_journey_analysis',
    },

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 3 — Engagement & Growth
    # ══════════════════════════════════════════════════════════════════════════

    'retention_habit_loop': {
        'title': '8-hour product sprint: Daily habit loop design and streak feedback optimization',
        'draft_markdown': (
            '8-hour product sprint: Daily habit loop design and streak feedback optimization\n\n'
            'User Value: Users who do not return daily forget the product exists. '
            'This task designs a daily hook that makes returning to the platform a habit, '
            'not a chore — using streaks, feedback loops, and return triggers.\n\n'
            'Product Maturity Impact: D30 retention is the vanity-free measure of product-market fit. '
            'A well-designed habit loop (cue → routine → reward) is the primary driver of D30 retention.\n\n'
            'Expected Change: D7 and D30 retention improve as streak milestones create emotional investment. '
            'Users who reach day-7 streak are 3× more likely to reach day 30. '
            'Milestone celebrations make progress visible and reinforce the daily return habit.\n\n'
            'Objective: Design and implement a daily habit loop: '
            'daily check-in cue, streak tracking, and completion reward signal.\n\n'
            'Phase 1: Audit the current streak implementation in backend/app/services/ and '
            'backend/tests/test_action_streak.py. Does the streak reset correctly at midnight? '
            'Is it surfaced prominently in the UI? Is there any reward signal when a streak milestone is hit?\n'
            'Phase 2: Design the daily cue: what triggers a user to open the app each day? '
            'Sketch: a daily summary notification (Today\'s health snapshot), '
            'a streak reminder (Day 4 streak — don\'t break it!), '
            'or a fresh action recommendation (Your #1 action for today is...).\n'
            'Phase 3: Implement the streak milestone reward signal in the frontend. '
            'When a user hits day 3, 7, 14, or 30, show a celebratory moment '
            '(a banner, animation, or summary card). Update the backend streak endpoint '
            'to return milestone_reached: bool alongside the count.\n'
            'Phase 4: Run `make backend-test` and `npm run lint`. '
            'Add a test for streak milestone detection. '
            'Document the habit loop design with the cue/routine/reward labels.\n\n'
            'Scope: backend/app/services/, backend/app/api/, frontend/app/platform/, frontend/components/\n'
            'Files to inspect: backend/tests/test_action_streak.py, '
            'backend/app/services/ (streak-related), frontend/app/platform/\n'
            'Acceptance Criteria: Streak milestone field returned by API; '
            'frontend shows milestone celebration at day 3/7/14/30; '
            'make backend-test passes; habit loop documented.\n'
            'focus_keys: retention, habit_loop, streak, daily_hook, milestone, d30\n'
            'expected_duration_minutes: 480'
        ),
        'focus_keys': ('retention', 'habit_loop', 'streak', 'daily_hook', 'milestone', 'd30'),
        'duplicate_signature': 'retention_habit_loop_v1',
        'category': 'retention_habit_loop',
    },

    'notifications_lifecycle': {
        'title': '8-hour product sprint: Notification urgency accuracy and fatigue prevention',
        'draft_markdown': (
            '8-hour product sprint: Notification urgency accuracy and fatigue prevention\n\n'
            'User Value: Overnotified users disable notifications entirely. '
            'Undernotified users miss important health signals. '
            'This task makes every notification feel timely, relevant, and worth reading.\n\n'
            'Product Maturity Impact: Notification open rate is a direct proxy for '
            'how much users trust the platform\'s judgment. A high open rate means the product '
            'has earned the right to speak. Notification fatigue kills engagement silently.\n\n'
            'Expected Change: Notification open rate rises as urgency accuracy improves. '
            'Users stop disabling notifications because each one feels relevant and timely. '
            'The daily cap prevents fatigue; snooze resurfacing prevents important signals from vanishing.\n\n'
            'Objective: Audit notification urgency accuracy, snooze/resurfacing behavior, '
            'and implement basic fatigue prevention.\n\n'
            'Phase 1: Audit the notification pipeline end-to-end. '
            'What triggers a notification? Is urgency (LOW/MEDIUM/HIGH) assigned correctly? '
            'Is there a daily notification cap? What happens when a user snoozes — '
            'does the notification resurface or disappear forever?\n'
            'Phase 2: Audit the snooze → resurfacing flow. '
            'Implement: a snoozed notification must resurface within 24 hours '
            'unless the underlying health event is resolved. '
            'Add a resurfaced_at timestamp to the notification model.\n'
            'Phase 3: Implement a daily notification cap (max 3 notifications per day per user). '
            'Prioritize HIGH urgency notifications when the cap is reached. '
            'Add the cap enforcement in backend/app/services/.\n'
            'Phase 4: Run `make backend-test`. Add tests for: '
            '(a) daily cap enforcement; (b) snooze resurfacing within 24h. '
            'Verify notification-related tests pass.\n\n'
            'Scope: backend/app/services/, backend/app/api/, backend/app/models/, backend/tests/\n'
            'Files to inspect: backend/app/services/ (notification services), '
            'backend/app/api/ (notification endpoints)\n'
            'Acceptance Criteria: Daily notification cap enforced; '
            'snooze resurfacing implemented; make backend-test passes; '
            'urgency assignment documented.\n'
            'focus_keys: notifications, urgency, fatigue_prevention, snooze, resurfacing, cap\n'
            'expected_duration_minutes: 480'
        ),
        'focus_keys': ('notifications', 'urgency', 'fatigue_prevention', 'snooze', 'resurfacing', 'cap'),
        'duplicate_signature': 'notifications_lifecycle_v1',
        'category': 'notifications_lifecycle',
    },

    'reports_product_value': {
        'title': '8-hour product sprint: Report upload to Insight value delivery audit',
        'draft_markdown': (
            '8-hour product sprint: Report upload to Insight value delivery audit\n\n'
            'User Value: A user who uploads a blood test report expects to understand '
            'what it means for their health within minutes, not days. '
            'This task audits whether that value is actually delivered and fixes the gaps.\n\n'
            'Product Maturity Impact: The report upload flow is the moment of highest intent. '
            'If the user gets a clear, actionable insight immediately, '
            'they become a power user. If the result is generic or delayed, they churn.\n\n'
            'Expected Change: Users who upload a report immediately see a specific insight referencing '
            'their own values, not a generic health summary. The CTA from report to first action '
            'reduces post-upload abandonment. Report upload becomes the product\'s highest-value moment.\n\n'
            'Objective: Audit the report upload → parsing → insight → action pipeline '
            'for value leakage. Fix the top-3 value-delivery failures.\n\n'
            'Phase 1: Upload a sample report (or trace the code with a mocked file). '
            'Record: How long does parsing take? Does the user see a progress indicator? '
            'Is the resulting insight specific to the report content or generic? '
            'Does the insight lead directly to a recommended action?\n'
            'Phase 2: Inspect backend/app/services/ for report parsing logic. '
            'What data is extracted? What is discarded? '
            'Is there a validation step that tells the user "your report was parsed successfully, '
            'here is what we found"?\n'
            'Phase 3: Fix the top-3 value gaps. Examples: '
            'add a parsing success confirmation with key extracted values; '
            'ensure insights reference specific report values (e.g. "Your LDL of 145 mg/dL..."); '
            'add a "Report processed — here is your #1 action" CTA.\n'
            'Phase 4: Run `make backend-test`. Add a test that asserts '
            'the insight generated from a report references at least one extracted metric value. '
            'Document value delivery before/after.\n\n'
            'Scope: backend/app/services/, backend/app/api/, frontend/app/platform/reports/, '
            'uploads/, ai/prompts/\n'
            'Files to inspect: backend/app/services/ (parsing services), '
            'ai/prompts/health_check_interpreter_prompt.md, frontend/app/platform/reports/\n'
            'Acceptance Criteria: Insight references specific report metric; '
            'parsing success confirmation shown to user; '
            'CTA from report to first action exists; make backend-test passes.\n'
            'focus_keys: reports, parsing, insight_value, cta, report_to_action, specific_metrics\n'
            'expected_duration_minutes: 480'
        ),
        'focus_keys': ('reports', 'parsing', 'insight_value', 'cta', 'report_to_action', 'specific_metrics'),
        'duplicate_signature': 'reports_product_value_v1',
        'category': 'reports_product_value',
    },

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 4 — Data & Consistency
    # ══════════════════════════════════════════════════════════════════════════

    'timeline_history_value': {
        'title': '8-hour product sprint: Health Timeline meaningful trend detection and Narrative v3 support',
        'draft_markdown': (
            '8-hour product sprint: Health Timeline meaningful trend detection and Narrative v3 support\n\n'
            'User Value: A health timeline that just shows raw data points is a spreadsheet. '
            'A timeline that highlights "Your sleep improved 15% after starting magnesium" '
            'is a story the user will share. This task adds trend detection to make '
            'the timeline a compelling evidence layer.\n\n'
            'Product Maturity Impact: The timeline is the long-term value proposition '
            '(the longer you use it, the more valuable it gets). '
            'Trend detection turns raw history into motivation to continue.\n\n'
            'Expected Change: The timeline becomes a story of change, not a log of events. '
            'Users can see "my sleep improved 15% after starting magnesium" because trend arrows show it. '
            'This data feeds directly into Narrative v3 causal chains, making the AI smarter.\n\n'
            'Objective: Add trend detection to the timeline API and surface it in the UI. '
            'Ensure timeline data is rich enough to support Narrative v3 causal chains.\n\n'
            'Phase 1: Audit the current timeline API endpoint. '
            'What data does it return? Is it raw events or aggregated? '
            'Is there any trend comparison (this week vs last week)? '
            'What time-series data is missing that would improve the Narrative v3 causal chain?\n'
            'Phase 2: Design a simple trend detection schema: '
            'for each metric tracked, compute direction (up/down/stable) '
            'and magnitude (% change) over the last 7 and 30 days. '
            'Return as a trends[] array alongside the raw timeline.\n'
            'Phase 3: Implement the trend computation in backend/app/services/ or '
            'backend/app/api/. Update the timeline API response to include trends[]. '
            'Verify the trends data feeds into the health narrative pipeline.\n'
            'Phase 4: Run `make backend-test`. Add a test for trend direction computation '
            '(if metric goes up 20%, direction is "up", magnitude is "20%"). '
            'Update the UI timeline component to show trend arrows.\n\n'
            'Scope: backend/app/api/, backend/app/services/, backend/app/models/, '
            'frontend/app/platform/, ai/prompts/\n'
            'Files to inspect: backend/app/api/ (timeline endpoints), '
            'backend/app/services/ (trend computation)\n'
            'Acceptance Criteria: Timeline API includes trends[] with direction and magnitude; '
            'trend direction test passes; UI shows trend indicators; '
            'make backend-test passes.\n'
            'focus_keys: timeline, trend_detection, history_value, narrative_support, insights\n'
            'expected_duration_minutes: 480'
        ),
        'focus_keys': ('timeline', 'trend_detection', 'history_value', 'narrative_support', 'insights'),
        'duplicate_signature': 'timeline_history_value_v1',
        'category': 'timeline_history_value',
    },

    'growth_analytics': {
        'title': '8-hour product sprint: Feature usage funnel and retention drop-off analysis',
        'draft_markdown': (
            '8-hour product sprint: Feature usage funnel and retention drop-off analysis\n\n'
            'User Value: Users who do not use certain features are losing value they paid for. '
            'This task finds which features are not being used and why, '
            'so we can either fix them or retire them.\n\n'
            'Product Maturity Impact: Knowing the usage funnel (how many users reach each step) '
            'is the foundation of product-led growth. Without it, every design decision is a guess.\n\n'
            'Expected Change: The team can see exactly where users drop off. Features with <20% usage '
            'are surfaced for redesign or removal. Product decisions shift from intuition to data. '
            'The funnel endpoint becomes the primary weekly health metric for the product.\n\n'
            'Objective: Build a usage funnel analysis across the core product surfaces '
            'and identify the highest-drop-off steps.\n\n'
            'Phase 1: Define the funnel steps for the core journey: '
            '(1) Login, (2) View Dashboard, (3) View an Insight, '
            '(4) Click an Action, (5) Complete an Action, (6) Return next day. '
            'Determine which backend events currently exist to measure each step.\n'
            'Phase 2: Inspect the backend for existing event logging or analytics hooks. '
            'What user events are recorded in the database? '
            'Is there a concept of "session" or "daily active user"? '
            'Document what exists and what is missing.\n'
            'Phase 3: Implement at least 3 missing funnel event logs. '
            'Examples: log when a user views an insight (GET /insights/:id → append to insight_views); '
            'log when an action is clicked but not completed; '
            'log when a user opens the app on consecutive days.\n'
            'Phase 4: Build a simple admin API endpoint GET /analytics/funnel that returns '
            'per-step counts for the last 7 days. Run `make backend-test`. '
            'Document the current funnel drop-off percentages.\n\n'
            'Scope: backend/app/api/, backend/app/models/, backend/app/services/\n'
            'Files to inspect: backend/app/api/ (analytics/admin endpoints), '
            'backend/app/models/ (event models)\n'
            'Acceptance Criteria: 3 funnel event logs implemented; '
            'GET /analytics/funnel endpoint returns per-step counts; '
            'make backend-test passes; drop-off percentages documented.\n'
            'focus_keys: analytics, funnel, retention, dau, feature_usage, drop_off\n'
            'expected_duration_minutes: 480'
        ),
        'focus_keys': ('analytics', 'funnel', 'retention', 'dau', 'feature_usage', 'drop_off'),
        'duplicate_signature': 'growth_analytics_v1',
        'category': 'growth_analytics',
    },

    'cross_page_consistency': {
        'title': '8-hour product sprint: Cross-page consistency audit — conflicting decisions and broken signals',
        'draft_markdown': (
            '8-hour product sprint: Cross-page consistency audit — conflicting decisions and broken signals\n\n'
            'User Value: A user who sees a "High Risk" label on the Dashboard but "All Good" '
            'on the Insights page loses trust immediately. '
            'This task hunts and fixes every inconsistency in how health signals are displayed.\n\n'
            'Product Maturity Impact: Consistency is the bedrock of clinical trust. '
            'A single contradictory data point can destroy months of earned credibility. '
            'Consistent, coherent signals are the mark of a mature health product.\n\n'
            'Expected Change: A user can navigate from Dashboard to Insights to Actions and see the '
            'same risk score and action count everywhere. Trust in the platform\'s data integrity '
            'increases. Conflicting decisions — the #1 source of user confusion — are eliminated.\n\n'
            'Objective: Audit all four core surfaces (Dashboard, Insights, Actions, Notifications) '
            'for data inconsistencies, conflicting recommendations, and missing context.\n\n'
            'Phase 1: Open each surface and record every piece of health data shown: '
            'risk score, action count, notification count, insight summary. '
            'Check: do the same numbers appear consistently on every surface? '
            'Is the same action recommended on both Insights and Actions pages? '
            'Document every discrepancy found.\n'
            'Phase 2: Trace each discrepancy to its source in the backend. '
            'Is it a stale cache? A different API endpoint that uses different logic? '
            'A UI component that applies different filtering? Identify the root cause.\n'
            'Phase 3: Fix the top-3 consistency issues. '
            'Prioritize: risk score inconsistency > action count mismatch > notification badge mismatch. '
            'For each fix, document which file was changed and what the correct source of truth is.\n'
            'Phase 4: Run `npm run lint` and `make backend-test`. '
            'Add a frontend test (or API contract test) that asserts '
            'the same risk score is returned from both the Dashboard API and the Insights API.\n\n'
            'Scope: frontend/app/platform/, backend/app/api/, backend/app/services/\n'
            'Files to inspect: app/platform/dashboard/page.tsx, app/platform/insights/, '
            'app/platform/actions/, app/platform/notifications/\n'
            'Acceptance Criteria: At least 3 consistency issues fixed; '
            'source of truth documented per data type; '
            'npm run lint and make backend-test pass.\n'
            'focus_keys: consistency, cross_page, conflicting_decisions, trust, data_integrity\n'
            'expected_duration_minutes: 480'
        ),
        'focus_keys': ('consistency', 'cross_page', 'conflicting_decisions', 'trust', 'data_integrity'),
        'duplicate_signature': 'cross_page_consistency_v1',
        'category': 'cross_page_consistency',
    },
}


# ── Tier priority mapping for weighted selection ──────────────────────────────

_TIER_PRIORITY: dict[str, int] = {
    cat: 1 for cat in _TIER_1  # weight 3 in practice (sampled 3× into candidate pool)
}
_TIER_PRIORITY.update({cat: 2 for cat in _TIER_2})  # weight 2
_TIER_PRIORITY.update({cat: 3 for cat in _TIER_3_4})  # weight 1

# Engineering-only guard: task categories that provide zero direct user value
# are blocked from being selected when product-facing alternatives exist.
_ENGINEERING_ONLY: frozenset[str] = frozenset()  # All 12 categories now have user value


# ── Public API ────────────────────────────────────────────────────────────────

def get_task_pool_info() -> list[dict[str, Any]]:
    """Return metadata for all pool categories (for API / UI display)."""
    return [
        {
            'category': cat,
            'title': _TASK_TEMPLATES[cat]['title'],
            'duplicate_signature': _TASK_TEMPLATES[cat]['duplicate_signature'],
            'focus_keys': list(_TASK_TEMPLATES[cat]['focus_keys']),
        }
        for cat in CATEGORIES
    ]


def pick_next_category(
    recent_tasks: list[dict[str, Any]],
    last_used_category: str | None = None,
    cooldown_days: int = 1,
) -> str:
    """Select the category least recently used that is not already ACTIVE or on cooldown.

    Strategy:
    1. Build the set of signatures currently ACTIVE (QUEUED/RUNNING/REPLAN_REQUIRED).
    2. Build the set of signatures completed within ``cooldown_days`` — these are
       deprioritised so the planner rotates through different templates each day.
    3. Skip the ``last_used_category`` if there are other options.
    4. Prefer the category with the fewest recent appearances (excluding ACTIVE tasks).
    5. When all categories are on cooldown, pick the one whose sig was completed earliest
       (oldest finished_at) so we always make forward progress rather than deadlocking.
    """
    from datetime import datetime, timedelta, timezone
    _ACTIVE_STATUSES = {'QUEUED', 'RUNNING', 'REPLAN_REQUIRED'}
    cooldown_cutoff = datetime.now(timezone.utc) - timedelta(days=cooldown_days)

    active_sigs: set[str] = set()
    cooldown_sigs: set[str] = set()
    category_counts: dict[str, int] = {cat: 0 for cat in CATEGORIES}
    # Track when each pool sig was last completed for tiebreaking when all on cooldown
    sig_last_finished: dict[str, datetime] = {}

    for task in recent_tasks:
        sig = str(task.get('duplicate_signature') or '')
        status = str(task.get('status') or '')
        if status in _ACTIVE_STATUSES and sig:
            active_sigs.add(sig)
        elif status == 'COMPLETED' and sig:
            # Check finished_at to determine cooldown membership
            finished_raw = task.get('finished_at') or task.get('updated_at')
            if finished_raw:
                try:
                    finished = datetime.fromisoformat(str(finished_raw).replace('Z', '+00:00'))
                    if finished > cooldown_cutoff:
                        cooldown_sigs.add(sig)
                    # Track the most-recent completion for each pool sig
                    if sig in sig_last_finished:
                        sig_last_finished[sig] = max(sig_last_finished[sig], finished)
                    else:
                        sig_last_finished[sig] = finished
                except (ValueError, AttributeError):
                    pass
        # Count all non-active appearances per category
        for cat, tmpl in _TASK_TEMPLATES.items():
            if tmpl['duplicate_signature'] == sig and status not in _ACTIVE_STATUSES:
                category_counts[cat] = category_counts.get(cat, 0) + 1

    # Preferred candidates: not ACTIVE and not in the cooldown window
    preferred = [
        cat for cat in CATEGORIES
        if _TASK_TEMPLATES[cat]['duplicate_signature'] not in active_sigs
        and _TASK_TEMPLATES[cat]['duplicate_signature'] not in cooldown_sigs
    ]

    if preferred:
        candidates = preferred
    else:
        # All categories on cooldown — pick the one completed earliest (oldest) so we
        # always make forward progress rather than blocking completely.
        non_active = [
            cat for cat in CATEGORIES
            if _TASK_TEMPLATES[cat]['duplicate_signature'] not in active_sigs
        ]
        candidates = non_active if non_active else list(CATEGORIES)
        # Sort by last finished time ascending (oldest completed first = highest priority)
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        candidates = sorted(
            candidates,
            key=lambda c: sig_last_finished.get(_TASK_TEMPLATES[c]['duplicate_signature'], epoch),
        )

    # Deprioritise the last used category if other options exist
    if last_used_category and last_used_category in candidates and len(candidates) > 1:
        candidates = [c for c in candidates if c != last_used_category] or candidates

    # Pick the candidate with the fewest previous completions (within preferred set)
    if preferred:
        return min(candidates, key=lambda c: category_counts.get(c, 0))
    # All on cooldown — candidates already sorted by oldest-first, just return first
    return candidates[0]


def build_task_draft(category: str) -> TaskDraft:
    """Build a TaskDraft from the pool template for the given category."""
    if category not in _TASK_TEMPLATES:
        raise ValueError(f'Unknown task pool category: {category!r}')
    tmpl = _TASK_TEMPLATES[category]
    return TaskDraft(
        title=tmpl['title'],
        draft_markdown=tmpl['draft_markdown'],
        focus_keys=tuple(tmpl['focus_keys']),
        expected_duration_minutes=480,  # 8 hours
        category=category,
        duplicate_signature=tmpl['duplicate_signature'],
    )
