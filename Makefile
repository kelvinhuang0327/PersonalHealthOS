.PHONY: up down logs backend-test backend-smoke backend-auth-audit frontend-tsc security-smoke config-smoke validation-smoke outcome-smoke frontend-auth-smoke frontend-e2e-local local-db-up local-db-down local-db-reset local-seed local-seed-reset local-seed-reseed

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

backend-test:
	cd backend && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt && PYTHONPATH=. .venv/bin/python -m pytest -q

# Quick auth negative smoke only (no DB required — uses in-memory SQLite)
backend-smoke:
	cd backend && PYTHONPATH=. .venv/bin/python -m pytest -v tests/test_auth_negative_smoke.py tests/test_real_token_auth_negative.py

# Full P13-P20 + P44/P45 auth/security regression (no DB required — in-memory SQLite)
# Covers: API auth, real JWT, person_id audit, report owner hardening, download token policy
backend-auth-audit:
	cd backend && PYTHONPATH=. .venv/bin/python -m pytest -v \
		tests/test_auth_negative_smoke.py \
		tests/test_real_token_auth_negative.py \
		tests/test_person_id_authorization_audit.py \
		tests/test_report_authorization_hardening.py \
		tests/test_report_download_token_policy.py

# TypeScript typecheck only — no backend required
frontend-tsc:
	cd frontend && npx tsc --noEmit

# backend-auth-audit + frontend tsc — no running server required
security-smoke:
	$(MAKE) backend-auth-audit
	$(MAKE) frontend-tsc

# Config guard smoke — verifies production JWT secret guard and startup integration
# No DB required. Runs P28 unit tests, P29 env/startup integration tests, and P43 startup warning tests.
config-smoke:
	cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q \
		tests/test_config_security_guard.py \
		tests/test_runtime_config_startup_guard.py

# P23–P30 input validation, boundary, injection, and schema boundary regression
# No DB required. All tests use in-memory SQLite.
validation-smoke:
	cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q \
		tests/test_input_validation_hardening.py \
		tests/test_input_validation_boundary.py \
		tests/test_injection_smoke.py \
		tests/test_schema_validation_p30.py

# P58/P59 outcome feedback service + API route smoke — no DB required (in-memory SQLite)
# Covers safe copy, confidence=0.0, actual_metric_change=null, window_days validation,
# not_useful / not_applicable / snoozed presence and summary counts.
outcome-smoke:
	cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q \
		tests/test_outcome_feedback_service.py \
		tests/test_api_outcome_feedback_p59.py

# Health endpoint contract smoke + full security regression — no running server required
# /health and /health/live are DB-independent (always 200).
# /health/ready accepts 200 (DB up) or 503 (DB down); never 500.
runtime-smoke:
	cd backend && PYTHONPATH=. .venv/bin/python -m pytest -v tests/test_runtime_smoke.py
	$(MAKE) security-smoke
	$(MAKE) config-smoke
	$(MAKE) validation-smoke
	$(MAKE) outcome-smoke

# Targeted Playwright auth E2E tests
# Requires:
#   1. Backend running:  cd backend && uvicorn app.main:app --port 8000
#   2. Frontend built:   cd frontend && npm run build
# Playwright webServer auto-starts next start --port 3010
frontend-auth-smoke:
	cd frontend && npx playwright test \
		tests/e2e/auth-negative.spec.ts \
		tests/e2e/auth-ui-negative.spec.ts \
		tests/e2e/auth-ui-multi.spec.ts \
		--reporter=line

# Full Playwright e2e suite (all 6 specs)
# Requires:
#   1. Backend running:  cd backend && uvicorn app.main:app --port 8000
#   2. Frontend built:   cd frontend && npm run build
# CI uses npm run e2e:ci (mocked-only subset) instead of this target
frontend-e2e-local:
	cd frontend && npm run e2e

local-db-up:
	docker compose -f docker-compose.local.yml up -d

local-db-down:
	docker compose -f docker-compose.local.yml down

local-db-reset:
	docker compose -f docker-compose.local.yml down -v
	docker compose -f docker-compose.local.yml up -d

local-seed:
	cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_demo_data.py --seed-only

local-seed-reset:
	cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_demo_data.py --reset-only

local-seed-reseed:
	cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_demo_data.py

validate-rules:
	cd backend && PYTHONPATH=. .venv/bin/python scripts/validate_rules.py
