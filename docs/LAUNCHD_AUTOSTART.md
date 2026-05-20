# macOS 開機登入自動啟動（launchd / LaunchAgent）

本專案提供完整 LaunchAgent 方案，符合：

- 主服務登入自啟（backend + frontend）
- planner / worker 每 10 分鐘 tick
- 可選 worker daemon 常駐
- 固定 log 路徑與可觀察性
- 啟動 health/smoke check
- 主服務異常退出由 launchd 自動重啟

## 檔案結構

- 主啟動與控制腳本：`scripts/launchd/`
- LaunchAgent template：`launchd/templates/`
- 產生後 plist：`launchd/generated/`
- runtime logs/pids：`runtime/launchd/logs/`、`runtime/launchd/pids/`

## LaunchAgent 用途

- `com.personalhealthos.main`
  - 登入即啟動主服務（`start_all.sh --foreground`）
  - `RunAtLoad=true`
  - `KeepAlive=true`
- `com.personalhealthos.planner.tick`
  - planner tick，每 600 秒（10 分鐘）
  - `StartInterval=600`
- `com.personalhealthos.worker.tick`
  - worker tick，每 600 秒（10 分鐘）
  - `StartInterval=600`
- `com.personalhealthos.worker.daemon`（可選）
  - worker daemon 常駐模式
  - `RunAtLoad=true`, `KeepAlive=true`

## 安裝

先生成 plist（帶實際專案路徑）並安裝載入：

```bash
cd /Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS
./scripts/launchd/install_launchagents.sh
```

若要同時安裝 daemon worker：

```bash
./scripts/launchd/install_launchagents.sh --with-daemon
```

## 重載（修改後）

```bash
./scripts/launchd/reload_launchagents.sh
```

含 daemon：

```bash
./scripts/launchd/reload_launchagents.sh --with-daemon
```

## 卸載 / 停止自啟

```bash
./scripts/launchd/uninstall_launchagents.sh
```

含 daemon：

```bash
./scripts/launchd/uninstall_launchagents.sh --with-daemon
```

## 手動啟停主服務

```bash
./scripts/launchd/start_all.sh --foreground
./scripts/launchd/stop_all.sh
```

補充：

- `start_all.sh` 會預設帶 `APP_AUTO_CREATE_TABLES=false`，避免 DB 不可用時直接在 startup crash；若你要啟用 create_all，可先 `export APP_AUTO_CREATE_TABLES=true`。
- 若要調整 worker daemon 迴圈頻率，可設定 `WORKER_DAEMON_INTERVAL_SECONDS`。

## 驗證登入後自動啟動

1. `install_launchagents.sh` 成功
2. 登出再登入 macOS
3. 檢查：
   - `launchctl list | grep com.personalhealthos`
   - `lsof -nP -iTCP:8000 -sTCP:LISTEN`
   - `lsof -nP -iTCP:3100 -sTCP:LISTEN`
4. 驗證 API：
   - `curl -fsS http://127.0.0.1:8000/health`
   - `curl -fsS http://127.0.0.1:8000/api/v1/orchestrator/summary`

預設前端埠：

- launchd 方案預設使用 `3100`（可用環境變數 `FRONTEND_PORT` 覆寫）。

## 觀測與 log

- 主 launch agent stdout/stderr：
  - `runtime/launchd/logs/main.stdout.log`
  - `runtime/launchd/logs/main.stderr.log`
- backend/frontend service log：
  - `runtime/launchd/logs/backend.service.log`
  - `runtime/launchd/logs/frontend.service.log`
- planner/worker/daemon tick log：
  - `runtime/launchd/logs/planner.tick.stdout.log`
  - `runtime/launchd/logs/planner.tick.stderr.log`
  - `runtime/launchd/logs/worker.tick.stdout.log`
  - `runtime/launchd/logs/worker.tick.stderr.log`
  - `runtime/launchd/logs/worker.daemon.stdout.log`
  - `runtime/launchd/logs/worker.daemon.stderr.log`

快速狀態檢查：

```bash
./scripts/launchd/status_launchagents.sh
```
