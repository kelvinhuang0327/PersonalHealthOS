# Personal Health Platform - Production System Upgrade

## 1. 系統架構升級

### 1.1 架構目標
- 將單體 API 升級為可水平擴展的事件驅動微服務架構。
- 支援新增能力：家庭健康管理、穿戴裝置整合、健康提醒、醫療文件管理、健康報告 PDF。
- 提升可用性、安全性、可觀測性與運維效率。

### 1.2 目標拓撲
- `API Gateway`：統一入口、JWT 驗證、Rate Limit、WAF。
- `Core Services`：
  - Identity Service
  - User Profile Service
  - Health Data Service
  - Family Management Service
  - Device Integration Service
  - Notification Service
  - Document Service
  - Report Service (PDF)
  - AI Orchestrator Service
- `Data Layer`：PostgreSQL（分庫或 logical schema）、Redis、Object Storage (S3-compatible)
- `Async Layer`：RabbitMQ/Kafka（建議 RabbitMQ 起步）
- `Observability`：OpenTelemetry + Prometheus + Grafana + ELK

### 1.3 新能力映射
- 家庭健康管理：`Family Management Service`
- 穿戴裝置整合：`Device Integration Service`
- 健康提醒：`Notification Service` + Scheduler Worker
- 醫療文件管理：`Document Service`
- 健康報告 PDF：`Report Service`

### 1.4 部署模型
- K8s (prod) + HPA
- Multi-AZ PostgreSQL, Redis Sentinel/Cluster
- Object Storage 版本控管 + lifecycle policy

---

## 2. Microservice 設計

### 2.1 Service Boundary
1. `identity-service`
- 註冊/登入/JWT refresh/RBAC
- DB: `identity_db`

2. `profile-service`
- 個人資料、健康背景、偏好設定
- DB: `profile_db`

3. `health-data-service`
- 健康指標、症狀、健檢結構化資料
- DB: `health_db`

4. `family-service`
- 家庭成員、關係、授權委託（viewer/editor)
- DB: `family_db`

5. `device-ingestion-service`
- Apple Health/Fitbit/Garmin connector
- Webhook ingestion + normalization + dedup
- DB: `device_db`

6. `notification-service`
- 規則提醒、排程提醒、推播/email/SMS
- MQ consumer + retry + DLQ

7. `document-service`
- 檔案上傳、版本管理、分類、權限、病毒掃描流程
- DB: `document_db` + S3 bucket

8. `report-service`
- 報告聚合、PDF 生成、歷史版本
- DB: `report_db`

9. `ai-orchestrator-service`
- 健檢解讀 AI、症狀分析 AI、風險預測 AI
- prompt orchestration + guardrail + evaluation
- DB: `ai_db` (optional for audit logs)

### 2.2 API Style
- External: REST (Gateway)
- Internal: REST/gRPC（建議 service-to-service 走 gRPC）
- Async domain events: MQ

### 2.3 關鍵資料模型（新增）
- `family_accounts`, `family_members`, `family_permissions`
- `device_connections`, `device_sync_jobs`, `device_raw_events`
- `reminder_rules`, `reminder_jobs`, `notification_logs`
- `document_versions`, `document_access_logs`
- `health_reports`, `health_report_exports`

---

## 3. Message Queue 設計

### 3.1 Event Types
- `health.metric.recorded`
- `symptom.logged`
- `lab.report.parsed`
- `risk.alert.created`
- `family.member.invited`
- `device.data.ingested`
- `reminder.triggered`
- `report.pdf.requested`
- `report.pdf.generated`

### 3.2 Exchange/Queue（RabbitMQ）
- Exchanges:
  - `health.events` (topic)
  - `notification.events` (topic)
  - `report.events` (topic)
- Queues:
  - `ai-risk-prediction.q`
  - `notification.dispatch.q`
  - `timeline.rebuild.q`
  - `report.pdf.q`
  - `device.normalization.q`
  - `*.dlq`

### 3.3 Retry / DLQ
- 重試策略：exponential backoff（1m, 5m, 15m）
- `x-death` 超過閾值轉入 DLQ
- DLQ 由 Ops pipeline 告警 + replay endpoint 處理

---

## 4. Caching 設計

### 4.1 Redis 使用場景
- Session/token blacklist
- Dashboard read model（短 TTL）
- Timeline snapshot cache
- Trend analysis result cache
- AI response cache (idempotent window)
- Rate limiting counters

### 4.2 Key Design
- `dashboard:{user_id}:{days}` TTL 60s
- `timeline:{user_id}:{days}:{page}` TTL 120s
- `trend:{user_id}:{metric}:{days}` TTL 300s
- `health_score:{user_id}:latest` TTL 300s
- `ai_module:{module}:{hash(input)}` TTL 900s

### 4.3 Invalidation
- 事件驅動失效：`health.metric.recorded`, `symptom.logged`, `lab.report.parsed`
- 主動清除受影響 user key space

---

## 5. Security 設計

### 5.1 身分與授權
- OAuth2 + JWT access token + refresh token rotation
- RBAC + ABAC（家庭成員授權）
- Service-to-service mTLS + service account

### 5.2 敏感資料保護
- 傳輸加密：TLS 1.2+
- 靜態加密：PostgreSQL TDE / volume encryption, S3 SSE
- 欄位加密：PII（姓名、生日、聯絡資訊）
- 秘密管理：Vault / KMS

### 5.3 安全控制
- WAF + API rate limit + bot protection
- Upload 安全：MIME 白名單 + anti-virus scan + file sandbox
- Audit log（不可變更）
- SIEM 告警（異常登入、越權、批量下載）

### 5.4 合規與醫療邊界
- 永遠附帶醫療免責聲明
- AI 僅提供風險整理與追蹤建議，不可診斷/處方
- 資料最小化與刪除機制（DSR）

---

## 參考實作檔案
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/infra/docker-compose.production.yml`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/infra/message-queue-topology.md`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/infra/cache-strategy.md`
- `/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/infra/security-architecture.md`
