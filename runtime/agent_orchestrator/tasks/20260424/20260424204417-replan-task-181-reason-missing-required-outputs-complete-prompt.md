# Planner Task Prompt

## Objective
Replan task #181: 產品問題衝刺: 全類別輪替完成 — 選擇下一個最高價值優化領域 (reason: Missing required outputs: completed_markdown)

## Task Draft
Replan task #181: 產品問題衝刺: 全類別輪替完成 — 選擇下一個最高價值優化領域 (reason: Missing required outputs: completed_markdown)

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
| 信心度 | 0.95 |
| Pass Rate | 95% |
| 失敗率 | 5% |
| 近期任務數 | 20 |

> 95% gate pass rate across last 20 tasks.

## Previous Context
Latest task #181 status=REPLAN_REQUIRED objective=產品問題衝刺: 全類別輪替完成 — 選擇下一個最高價值優化領域
Latest gate verdict=INVALID_DELIVERY reason=Missing required outputs: completed_markdown
