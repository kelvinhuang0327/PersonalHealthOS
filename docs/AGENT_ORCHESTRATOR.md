# Dual-Agent Orchestrator

本專案已落地 dual-agent orchestrator（Planner / Worker / Gate / Scheduler）。

## Profile 與 Runtime

- Project profile: `runtime/agent_orchestrator/project_profile.json`
- Schema: `runtime/agent_orchestrator/project_profile.schema.json`
- Backlog: `runtime/agent_orchestrator/backlog.md`
- Runtime DB: `runtime/agent_orchestrator/orchestrator.db`（啟動後自動建立）
- Task artifacts: `runtime/agent_orchestrator/tasks/YYYYMMDD/`

## API

Base path: `/api/v1/orchestrator`

- `GET /summary`
- `GET /tasks`
- `GET /tasks/{task_id}`
- `GET /runs`
- `POST /run-now` (`role=planner|worker`)
- `POST /scheduler` (enable/disable + interval)
- `POST /providers` (planner/worker provider switch)
- `POST /scheduler/run-at-once` (把下一次 planner/worker 排程設為立即)

## 手動 Smoke Path

1. `POST /api/v1/orchestrator/run-now` with `{"role":"planner"}`
2. `POST /api/v1/orchestrator/run-now` with `{"role":"worker"}`
3. `GET /api/v1/orchestrator/tasks/{task_id}` 檢查 contract/result/log tail
4. `POST /api/v1/orchestrator/run-now` with `{"role":"worker","simulate_invalid_delivery":true}` 驗證 invalid delivery -> `REPLAN_REQUIRED`

## Scheduler

- 由 `backend/app/orchestrator/scheduler.py` 提供背景 loop。
- FastAPI startup 僅在 `ORCHESTRATOR_SCHEDULER_AUTOSTART=true` 時自動啟動（預設值為 `false`）。
- 預設間隔由 project profile `default_schedule_minutes` 決定，可經 API 更新。
