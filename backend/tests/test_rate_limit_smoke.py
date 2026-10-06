"""P26 — Rate-limit middleware smoke tests.

Tests the InMemoryRateLimitMiddleware in isolation using a minimal FastAPI
test application.  No DB, no auth, no running server required.

Design notes
------------
- Each test calls _make_limited_app() which creates a *fresh* middleware
  instance with a fresh in-memory store, so tests are fully independent.
- A low threshold (requests=2 or 3) is used to trigger 429 quickly.
- TestClient sends requests from host='testclient'; the middleware uses
  (client_ip, path) as the bucket key, which works correctly.
- The production app (app.main) is intentionally NOT imported here so
  these tests remain decoupled from database / settings wiring.

Coverage map
------------
TestRateLimitMiddleware
  test_health_get_exempt_when_enabled      → /health never returns 429
  test_health_live_exempt_when_enabled     → /health/live never returns 429
  test_health_ready_exempt_when_enabled    → /health/ready never returns 429
  test_non_health_route_limited            → threshold exceeded → 429
  test_429_body_is_safe                    → detail key present, no internals
  test_disabled_mode_no_interference       → no middleware → never 429
  test_different_paths_tracked_separately  → per-path buckets are independent
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import InMemoryRateLimitMiddleware


def _make_limited_app(requests: int = 3, window: int = 60) -> FastAPI:
    """Return a fresh minimal FastAPI app with rate limiting enabled."""
    mini = FastAPI()
    mini.add_middleware(
        InMemoryRateLimitMiddleware,
        requests=requests,
        window_seconds=window,
    )

    @mini.get('/health')
    def health():
        return {'status': 'ok'}

    @mini.get('/health/live')
    def health_live():
        return {'status': 'alive'}

    @mini.get('/health/ready')
    def health_ready():
        return {'status': 'ready'}

    @mini.get('/api/v1/resource')
    def resource():
        return {'data': 'value'}

    @mini.get('/api/v1/other')
    def other():
        return {'data': 'other'}

    return mini


class TestRateLimitMiddleware:
    def test_health_get_exempt_when_enabled(self):
        """/health must never be rate-limited even when middleware is active."""
        client = TestClient(_make_limited_app(requests=2))
        for _ in range(5):
            r = client.get('/health')
            assert r.status_code == 200, f"Expected 200 for /health, got {r.status_code}"

    def test_health_live_exempt_when_enabled(self):
        """/health/live must never be rate-limited."""
        client = TestClient(_make_limited_app(requests=2))
        for _ in range(5):
            r = client.get('/health/live')
            assert r.status_code == 200

    def test_health_ready_exempt_when_enabled(self):
        """/health/ready must never be rate-limited."""
        client = TestClient(_make_limited_app(requests=2))
        for _ in range(5):
            r = client.get('/health/ready')
            assert r.status_code == 200

    def test_non_health_route_limited(self):
        """Non-health route returns 429 once the per-IP-per-path threshold is hit."""
        client = TestClient(_make_limited_app(requests=3))
        # First 3 requests must succeed
        for i in range(3):
            r = client.get('/api/v1/resource')
            assert r.status_code == 200, f"Request {i + 1} should be allowed, got {r.status_code}"
        # 4th request must be throttled
        r = client.get('/api/v1/resource')
        assert r.status_code == 429, f"Expected 429 after threshold, got {r.status_code}"

    def test_429_body_is_safe(self):
        """429 response body must have 'detail' and must not leak internals."""
        client = TestClient(_make_limited_app(requests=1))
        client.get('/api/v1/resource')  # exhaust the 1-request allowance
        r = client.get('/api/v1/resource')
        assert r.status_code == 429
        body = r.json()
        assert 'detail' in body, f"'detail' key missing from 429 body: {body}"
        assert 'Rate limit exceeded' in body['detail']
        # Must not leak stack trace or internal keys
        assert 'traceback' not in body
        assert 'error' not in body
        assert 'store' not in body

    def test_disabled_mode_no_interference(self):
        """Without the middleware, no request is ever rate-limited."""
        mini = FastAPI()

        @mini.get('/api/v1/resource')
        def resource():
            return {'data': 'value'}

        client = TestClient(mini)
        for _ in range(10):
            r = client.get('/api/v1/resource')
            assert r.status_code == 200

    def test_different_paths_tracked_separately(self):
        """Exhausting one path's bucket must not affect a different path's bucket."""
        client = TestClient(_make_limited_app(requests=2))
        # Exhaust /api/v1/resource
        client.get('/api/v1/resource')
        client.get('/api/v1/resource')
        r_limited = client.get('/api/v1/resource')
        assert r_limited.status_code == 429

        # /api/v1/other must still be accessible (separate bucket)
        r_other = client.get('/api/v1/other')
        assert r_other.status_code == 200, (
            f"/api/v1/other should not be affected by /api/v1/resource bucket, got {r_other.status_code}"
        )
