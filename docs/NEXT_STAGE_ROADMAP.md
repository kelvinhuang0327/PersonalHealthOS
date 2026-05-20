# PersonalHealthOS Next Stage Roadmap

Updated: 2026-05-19

## CTO Decision

The next stage should optimize for one product promise:

> A personal health assistant that continuously uses symptoms, history, reports, daily metrics, and future device signals to recommend what the user should notice, track, and do next.

The previous P0 closure plan was directionally right, but too internally focused on the Orchestrator. The roadmap is now adjusted so Orchestrator visibility supports the user-facing health assistant loop instead of becoming the main product surface.

Do not create a new repository. All work must stay inside the existing `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS` workspace.

## Current System State

Observed from the current repository and runtime state:

- MVP health platform foundation exists: profile, metrics, symptoms, documents, reports, risk alerts, AI summaries, dashboard.
- Health intelligence exists: risk engine, rule engine, insight engine, health score, narrative engine, decision engine service.
- Actions system exists with action creation, completion, outcome computation, reminders, and frontend execution center.
- Orchestrator exists with Planner, Worker, scheduler, task pool, result quality gate, CTO review surfaces, and Dashboard summary panel.
- `detect_product_issues()` exists, but currently detects mostly orchestrator/process issues from task history, not real product usage issues.
- Planner currently tries backlog first, then problem signals, then task pool. This is not yet true product-signal-first planning.
- Dashboard already renders an Orchestration summary panel, but it does not yet expose full User Value / Product Maturity / Expected Change / Quality Gate evidence.
- Actions Page has a Decision Recommendation layer, but backend `/actions/prioritized` still primarily sorts by reminder/status/priority, and completed recommendations can still re-enter via decision items.
- External device data path exists only as mock external metrics sync. It is not yet a real wearable ingestion layer or a first-class assistant evidence source.
- Runtime Orchestrator DB shows 390 completed tasks, 3 `REPLAN_REQUIRED`, and 2 `FAILED_RATE_LIMIT`, but scheduler is currently disabled and latest task activity is stale.
- Runtime backlog appears corrupted/repeated in places and should not be treated as the next source of truth.

## Roadmap Alignment Check

### Aligned

- STEP1 product plan already targets profile, health records, symptoms, documents, risk alerts, AI summary, and dashboard.
- AI module design already includes symptom analysis, health report interpretation, and risk prediction.
- Stage 2 already adds health scores, timeline, trend analysis, and report parsing.
- Current dashboard and actions work support the direction of a health assistant.

### Misaligned

- STEP1 explicitly excludes wearable real-time streaming; the new product target requires a future device data path. This should be moved from "out of scope" to staged roadmap P2/P5.
- Orchestrator tasks are not yet driven by product behavior metrics such as completion rate, snooze rate, ignored notification rate, or insight-to-action conversion.
- The previous P0 plan over-emphasized "AI is optimizing the product" visibility. Users primarily need "AI is watching my health context and helping me act today."
- Actions Page is partially Decision Engine aligned, but not fully closed because status-based grouping and existing action state still dominate parts of the experience.
- Quality Gate exists in backend, but user-facing and CTO-facing evidence remains too shallow.

## Key Blockers

1. Product issue signal is incomplete.
   `detect_product_issues()` must use real product/user behavior metrics, not only orchestrator task history.

2. Health assistant evidence is fragmented.
   Symptoms, history, report items, metrics, actions, outcomes, and external metrics need a single evidence bundle used by Decision Engine and UI.

3. Planner priority order is wrong for closure.
   Product signals should come before backlog/task-pool rotation once actionable signals exist.

4. Actions are not fully decision-closed.
   Completed actions and already-tracked decision items must not return as top system recommendations unless there is a clear recurrence/resurface reason.

5. Orchestrator runtime is stale.
   Scheduler is disabled, latest tasks are old, and repeated `problem_signal` tasks suggest signal-loop overfitting.

6. Runtime backlog is not trustworthy.
   The backlog file contains repeated/corrupted text. The next sprint prompt should be used directly instead of relying on that backlog.

7. Device data is mock-only.
   Wearable data can be planned now, but real connector work should wait until the assistant evidence contract is stable.

## Reordered Roadmap

### P0 - Personal Health Assistant Core Closure

Goal: Make the product feel like a daily health assistant, not a collection of health pages.

Required outcomes:

- Add a unified Health Assistant Evidence Bundle service/API that joins symptoms, profile/history, reports/lab items, risk alerts, health metrics, external metrics, actions, and outcomes.
- Add `get_action_recommendations()` as the single recommendation layer fed by `decision_items` and evidence bundle.
- Ensure completed actions do not appear in system recommendations unless recurrence/resurface rules explicitly allow it.
- Dashboard shows "今日健康小助手" with top risk, why now, recommended action, evidence sources, missing data, and next check-in.
- Dashboard still shows Orchestrator visibility, but framed as product trust: what the system improved, what passed the gate, and what is blocked.
- Quality Gate UI shows User Value, Product Maturity, Expected Change, and verdict in a real connected state.
- Planner uses detected product issues before backlog/task-pool rotation.

Closure gates:

- `HEALTH_ASSISTANT_EVIDENCE_PASS`
- `ACTION_DECISION_CLOSURE_PASS`
- `ORCHESTRATOR_VISIBLE_PASS`
- `PROBLEM_DRIVEN_TASK_PASS`
- `QUALITY_GATE_UI_PASS`

### P1 - Daily Behavior Loop and Outcome Feedback

Goal: Make recommendations become actions, and actions become learning signals.

- Improve Action -> Outcome -> Feedback loop.
- Add structured check-ins after action completion.
- Feed outcomes back into Decision Engine scoring.
- Show whether an action helped over 7/14/30 days.
- Track action completion rate, snooze rate, and resurfaced recommendation conversion.

### P2 - Device Data Readiness

Goal: Prepare wearable/device data as a first-class evidence source without overbuilding connectors too early.

- Replace mock external metrics with a provider-neutral ingestion contract.
- Normalize heart rate, sleep, steps, blood pressure, glucose, and device source metadata.
- Add freshness and reliability scoring per data source.
- Surface "device data missing/stale" in the Health Assistant Evidence Bundle.

### P3 - Symptom Intelligence Upgrade

Goal: Make symptom tracking useful for daily decisions and longitudinal risk context.

- Improve symptom severity/duration parsing.
- Detect repeated symptom patterns.
- Connect symptom timelines to report anomalies and metrics.
- Add escalation language with medical disclaimer, not diagnosis.

### P4 - Report-to-Action Closure

Goal: Turn health reports into actions users can understand and follow.

- Map abnormal lab items to decision items.
- Add report evidence citations to recommendations.
- Show "what changed since last report".
- Add document-to-action conversion metric.

### P5 - Notification and Reminder Intelligence

Goal: Make reminders timely, not noisy.

- Use Decision Engine priority for notification timing.
- Track ignored, snoozed, resurfaced, completed.
- Add notification optimization tasks from product signals.
- Avoid daily summaries until P0/P1 loops are closed.

### P6 - Personalization and Learning

Goal: Make the assistant adapt to the user's actual response patterns.

- Learn from completion history, outcome changes, snooze reasons, and preferred check-in times.
- Personalize recommendation cadence.
- Deprioritize actions the user repeatedly ignores unless risk rises.

### P7 - Narrative Memory

Goal: Make the assistant remember the user's health story over time.

- Persist narrative history.
- Compare current state to previous narratives.
- Add "what changed", "what stayed unresolved", and "what to watch next".

### P8 - Family / Multi-Person Health Assistant

Goal: Support family profiles without confusing whose health context is being used.

- Strengthen person-scoped evidence bundles.
- Make dashboard/action/recommendation context explicit.
- Add permission and role guardrails before broader sharing.

### P9 - Product Analytics to Orchestrator

Goal: Let the Orchestrator improve the product based on real user behavior.

- Persist product events server-side.
- Feed completion rate, snooze count, ignored notifications, insight-action conversion, narrative expand rate, document-action conversion, and assistant check-in completion into `detect_product_issues()`.
- Add anti-loop safeguards so the same problem signal cannot generate repeated shallow tasks.

### P10 - Production Trust, Compliance, and Ecosystem

Goal: Harden the assistant for real-world health usage.

- Strengthen audit logs and privacy boundaries.
- Add provider governance for device integrations.
- Expand safety guardrails for health recommendations.
- Prepare compliance documentation and production monitoring.

## Most Valuable Next Optimization

The most valuable next optimization is:

> Build the Health Assistant Evidence Bundle and use it to close Dashboard + Actions + Orchestrator visibility around one daily recommendation loop.

This should happen before expanding notifications, wearable connectors, or advanced personalization. Without the evidence bundle, new features will keep increasing surface area without improving trust.

## Latest Execution Task Prompt

```md
# PersonalHealthOS - P0 Personal Health Assistant Closure Sprint

## Goal

This sprint must make the product core feel like a personal health assistant:

1. It understands the user's current health context from symptoms, history, reports, metrics, actions, outcomes, and external/device-like metrics.
2. It recommends what to pay attention to and what to do next.
3. It explains why now, with evidence.
4. It prevents completed/already-tracked actions from reappearing as top recommendations.
5. It shows the Orchestrator and Quality Gate only where they help trust and product closure.

Do not create a new repo. Work only inside the existing PersonalHealthOS repo.

## Task 1 - Health Assistant Evidence Bundle

Create a backend service and API response contract for a unified evidence bundle.

Required evidence sources:

- user profile and history
- recent symptoms and long-term symptoms
- recent health metrics
- external metrics currently stored from `/external-metrics`
- lab report items and abnormal report summaries
- active risk alerts
- insights
- current actions
- completed actions and outcomes

Acceptance Criteria:

- Evidence bundle is person-scoped.
- Missing data is explicit, not silent.
- Each evidence item includes source type, source id, recency, confidence/evidence level when available, and a short user-readable summary.
- Unit tests cover symptoms-only, reports-only, metrics-only, and mixed-data cases.

## Task 2 - Decision-backed Action Recommendations

Implement `get_action_recommendations()` as the single recommendation layer for Actions Page and Dashboard.

Inputs:

- `decision_items`
- Health Assistant Evidence Bundle
- active/completed/snoozed actions
- action outcomes

Output top 3 system recommendations with:

- title
- whyNow
- priority
- related decision item
- expected health impact
- evidence sources
- recommended next action
- suppression reason if hidden

Acceptance Criteria:

- Top 3 come from backend decision/evidence layer.
- Completed actions do not appear unless a recurrence/resurface rule explicitly applies.
- Already active actions are marked as already tracking, not duplicated.
- User-created actions remain visible separately.
- Actions Page no longer uses status sort as the primary recommendation source.

## Task 3 - Dashboard Daily Health Assistant Surface

Add or update Dashboard section:

「今日健康小助手」

It must show:

- top health focus
- why now
- primary recommended action
- evidence sources used
- missing data that would improve accuracy
- next check-in suggestion

Acceptance Criteria:

- Works with real backend/local data, not mock-only data.
- Empty state explains what data is missing.
- Uses same recommendation result as Actions Page.
- Links to symptoms, documents, metrics, or actions based on the missing/next step.

## Task 4 - Product-driven Orchestrator Planning

Upgrade `detect_product_issues()` so it reads real product behavior metrics, not only task history.

Minimum signals:

- action completion rate
- snooze count
- notification ignored rate
- insight-to-action conversion
- narrative expand rate
- document-to-action conversion
- assistant recommendation accepted rate

Planner order must become:

1. REPLAN_REQUIRED recovery
2. high-severity product issue
3. stale/corrupted backlog safety item
4. task pool fallback

Acceptance Criteria:

- high snooze -> notification optimization task
- low action completion -> action UX/feedback task
- low insight-action conversion -> decision/action bridge task
- low assistant recommendation accepted rate -> recommendation clarity task
- no product issue -> task pool fallback
- task payload preserves issue evidence
- repeated identical problem_signal tasks are blocked by cooldown

## Task 5 - Orchestrator + Quality Gate UI Trust Layer

Update Dashboard Orchestrator panel and/or Cockpit Orchestration UI to show:

- Orchestrator status: running / idle / blocked
- recent 3 tasks
- User Value Delivered: PASS / FAIL / UNKNOWN
- Product Maturity Impact: PASS / FAIL / UNKNOWN
- Expected Change Evidence: PASS / FAIL / UNKNOWN
- Gate verdict: PASS / RESULT_SHALLOW / REPLAN_REQUIRED / RATE_LIMIT
- next optimization direction

Acceptance Criteria:

- `RESULT_SHALLOW` displays warning copy.
- `REPLAN_REQUIRED` displays replan-needed state.
- `PASS` displays effective optimization state.
- UI reads real task contract/result data.
- Dashboard has useful empty/offline states.

## Final Validation

Run the most relevant available checks and report:

1. Modified files
2. New or changed APIs/services
3. Tests executed and results
4. P0 closure gates:
   - HEALTH_ASSISTANT_EVIDENCE_PASS / FAIL
   - ACTION_DECISION_CLOSURE_PASS / FAIL
   - ORCHESTRATOR_VISIBLE_PASS / FAIL
   - PROBLEM_DRIVEN_TASK_PASS / FAIL
   - QUALITY_GATE_UI_PASS / FAIL

Final expected classification:

P0_PERSONAL_HEALTH_ASSISTANT_CLOSURE_READY
```
