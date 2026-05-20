# Cache Strategy

## Backend Cache
- Redis Cluster
- Write-through for read models where needed
- Cache-aside for expensive analytics endpoints

## Targets
- Dashboard overview: 60s TTL
- Timeline: 120s TTL
- Trend analysis: 300s TTL
- Health score latest: 300s TTL
- AI module result: 900s TTL

## Invalidation Events
- `health.metric.recorded`
- `health.symptom.logged`
- `health.lab_report.parsed`

## Key Naming
- `dashboard:{user_id}:{days}`
- `timeline:{user_id}:{days}:{cursor}`
- `trend:{user_id}:{metric}:{days}`
- `health_score:{user_id}:latest`
- `ai_result:{module}:{input_hash}`

## Safety
- Never cache raw JWT
- PII cache payload minimized
- Encrypt in transit for Redis connection
