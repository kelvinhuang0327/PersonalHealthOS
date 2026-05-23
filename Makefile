.PHONY: up down logs backend-test backend-smoke local-db-up local-db-down local-db-reset local-seed local-seed-reset local-seed-reseed

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
