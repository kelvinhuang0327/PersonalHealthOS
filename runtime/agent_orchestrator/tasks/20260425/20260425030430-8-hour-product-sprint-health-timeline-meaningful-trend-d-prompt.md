# Planner Task Prompt

## Objective
8-hour product sprint: Health Timeline meaningful trend detection and Narrative v3 support

## Task Draft
8-hour product sprint: Health Timeline meaningful trend detection and Narrative v3 support

User Value: A health timeline that just shows raw data points is a spreadsheet. A timeline that highlights "Your sleep improved 15% after starting magnesium" is a story the user will share. This task adds trend detection to make the timeline a compelling evidence layer.

Product Maturity Impact: The timeline is the long-term value proposition (the longer you use it, the more valuable it gets). Trend detection turns raw history into motivation to continue.

Expected Change: The timeline becomes a story of change, not a log of events. Users can see "my sleep improved 15% after starting magnesium" because trend arrows show it. This data feeds directly into Narrative v3 causal chains, making the AI smarter.

Objective: Add trend detection to the timeline API and surface it in the UI. Ensure timeline data is rich enough to support Narrative v3 causal chains.

Phase 1: Audit the current timeline API endpoint. What data does it return? Is it raw events or aggregated? Is there any trend comparison (this week vs last week)? What time-series data is missing that would improve the Narrative v3 causal chain?
Phase 2: Design a simple trend detection schema: for each metric tracked, compute direction (up/down/stable) and magnitude (% change) over the last 7 and 30 days. Return as a trends[] array alongside the raw timeline.
Phase 3: Implement the trend computation in backend/app/services/ or backend/app/api/. Update the timeline API response to include trends[]. Verify the trends data feeds into the health narrative pipeline.
Phase 4: Run `make backend-test`. Add a test for trend direction computation (if metric goes up 20%, direction is "up", magnitude is "20%"). Update the UI timeline component to show trend arrows.

Scope: backend/app/api/, backend/app/services/, backend/app/models/, frontend/app/platform/, ai/prompts/
Files to inspect: backend/app/api/ (timeline endpoints), backend/app/services/ (trend computation)
Acceptance Criteria: Timeline API includes trends[] with direction and magnitude; trend direction test passes; UI shows trend indicators; make backend-test passes.
focus_keys: timeline, trend_detection, history_value, narrative_support, insights
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
| 信心度 | 1.00 |
| Pass Rate | 100% |
| 失敗率 | 0% |
| 近期任務數 | 20 |

> 100% gate pass rate across last 20 tasks.

## Focus Keys
timeline, trend_detection, history_value, narrative_support, insights

## Expected Duration
480 minutes (8.0h)

## Previous Context
Latest task #221 status=QUEUED objective=8-hour product sprint: Report upload to Insight value delivery audit
