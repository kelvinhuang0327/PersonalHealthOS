"""P25 — Backend Runtime Health Endpoint Smoke Tests

Verifies that all three health endpoints return the correct contract:
  GET /health       → 200 always (no DB dependency)
  GET /health/live  → 200 always (no DB dependency)
  GET /health/ready → 200 (DB reachable) or 503 (DB not reachable)
                      Must NOT return 500 regardless of DB state.

These tests use in-process TestClient — no running server required.
The /health/ready test accepts both 200 and 503 so the suite passes in
CI environments where PostgreSQL may not be running.

Coverage map
------------
TestHealthEndpoints
  test_health_returns_ok                → 200 + {status: ok, service: ...}
  test_health_live_returns_alive        → 200 + {status: alive, service: ...}
  test_health_ready_contract            → 200 or 503 (not 500) + {status: ...}
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    def test_health_returns_ok(self):
        """GET /health must return 200 with status=ok (no DB dependency)."""
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "service" in body

    def test_health_live_returns_alive(self):
        """GET /health/live must return 200 with status=alive (no DB dependency)."""
        r = client.get("/health/live")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "alive"
        assert "service" in body

    def test_health_ready_contract(self):
        """GET /health/ready must return 200 (DB up) or 503 (DB down) — never 500.

        The response body must always have a 'status' key:
          200: {'status': 'ready',     'service': ...}
          503: {'status': 'not_ready', 'detail': ...}
        """
        r = client.get("/health/ready")
        assert r.status_code in {200, 503}, (
            f"Expected 200 or 503, got {r.status_code}: {r.text}"
        )
        body = r.json()
        assert "status" in body, f"Missing 'status' key in response: {body}"
        if r.status_code == 200:
            assert body["status"] == "ready"
            assert "service" in body
        else:
            assert body["status"] == "not_ready"
            assert "detail" in body
