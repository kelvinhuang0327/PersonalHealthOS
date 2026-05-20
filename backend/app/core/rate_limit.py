import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests: int, window_seconds: int):
        super().__init__(app)
        self.requests = requests
        self.window = window_seconds
        self.store = defaultdict(deque)
        self.lock = Lock()

    async def dispatch(self, request, call_next):
        if request.url.path.startswith('/health'):
            return await call_next(request)

        client_ip = request.client.host if request.client else 'unknown'
        key = f'{client_ip}:{request.url.path}'
        now = time.time()

        with self.lock:
            bucket = self.store[key]
            while bucket and now - bucket[0] > self.window:
                bucket.popleft()
            if len(bucket) >= self.requests:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={'detail': 'Rate limit exceeded'},
                )
            bucket.append(now)

        return await call_next(request)
