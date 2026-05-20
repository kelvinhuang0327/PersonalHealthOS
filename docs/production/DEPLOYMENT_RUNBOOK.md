# Health Insights Platform Production Runbook

## 1) Target Architecture (Minimal Stable)
- Frontend: Next.js container (or Vercel) with `NEXT_PUBLIC_API_BASE_URL`.
- Backend: FastAPI container with env-driven DB/S3/AI config.
- Database: Managed PostgreSQL (staging/prod separated).
- Object Storage: S3-compatible bucket (MinIO for local fallback).

## 2) Required Environment Variables
Use root `.env.example` as template.

### Frontend
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_ENABLE_ANALYTICS`
- `NEXT_PUBLIC_ERROR_TRACKING_DSN`

### Backend
- `APP_ENV`, `APP_HOST`, `APP_PORT`, `APP_DEBUG`, `APP_AUTO_CREATE_TABLES`, `LOG_LEVEL`
- `DATABASE_URL`
- `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `S3_REGION`
- `MAX_UPLOAD_MB`, `ALLOWED_MIME_TYPES`, `ALLOWED_FILE_EXTENSIONS`, `MAX_UPLOAD_FILENAME_LENGTH`
- `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS`, `CORS_ALLOW_CREDENTIALS`
- `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`
- `SENTRY_DSN`, `SENTRY_ENVIRONMENT`

## 3) Deploy with Docker Compose (Production-like)
```bash
cp .env.example .env
# edit secrets in .env
docker compose -f docker-compose.prod.yml up -d --build
```

Health checks:
- Backend liveness: `GET /health/live`
- Backend readiness: `GET /health/ready`
- Legacy health: `GET /health`
- Frontend root: `GET /`

## 4) CI/CD
Workflow: `.github/workflows/ci-cd.yml`
- Frontend: lint, build, e2e
- Backend: pytest
- Deploy job: placeholder for cloud CLI/API

## 5) Rollback
1. Keep previous container image tag.
2. Redeploy previous tag for frontend/backend.
3. Re-run health checks.
4. Validate `/platform/dashboard` and core `/api/v1/*` endpoints.

## 6) Troubleshooting
- `503 /health/ready`: verify `DATABASE_URL` reachability and DB credentials.
- Upload 400 errors: check MIME/extension/size env config.
- CORS errors: verify `CORS_ALLOW_ORIGINS` includes frontend domain.
- 429 responses: tune `RATE_LIMIT_*` or disable in emergency.

## 7) Security Checklist Before Release
- Replace all default secrets (`JWT_SECRET_KEY`, S3 keys).
- `APP_DEBUG=false`
- Restrict `CORS_ALLOW_ORIGINS` and `TRUSTED_HOSTS` to real domains.
- Keep `APP_AUTO_CREATE_TABLES=false` in production.

## 8) Local reproducible setup (self-healing)
```bash
./setup.sh
```
The script performs dependency checks/install attempts (mac/linux), env preparation, postgres start, backend/frontend start, demo reseed, and endpoint verification.

Manual fallback:
```bash
make local-db-up
make local-seed-reseed
```
