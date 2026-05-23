.PHONY: up down logs backend-test backend-smoke backend-auth-audit frontend-tsc security-smoke frontend-auth-smoke local-db-up local-db-down local-db-reset local-seed local-seed-reset local-seed-reseed

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

# Full P13-P20 auth/security regression (no DB required — in-memory SQLite)
# Covers: API auth, real JWT, person_id audit, report owner hardening
backend-auth-audit:
	cd backend && PYTHONPATH=. .venv/bin/python -m pytest -v \
		tests/test_auth_negative_smoke.py \
		tests/test_real_token_auth_negative.py \
		tests/test_person_id_authorization_audit.py \
		tests/test_report_authorization_hardening.py

# TypeScript typecheck only — no backend required
frontend-tsc:
	cd frontend && npx tsc --noEmit

# backend-auth-audit + frontend tsc — no running server required
security-smoke:
	$(MAKE) backend-auth-audit
	$(MAKE) frontend-tsc

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
