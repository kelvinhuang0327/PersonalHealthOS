from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

_cache: dict[str, tuple[Any, datetime]] = {}


def cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if not entry:
        return None
    value, expires_at = entry
    if datetime.utcnow() < expires_at:
        return value
    del _cache[key]
    return None


def cache_set(key: str, value: Any, ttl_seconds: int = 300):
    _cache[key] = (value, datetime.utcnow() + timedelta(seconds=ttl_seconds))


def cache_invalidate(prefix: str):
    normalized_prefix = prefix.rstrip('*')
    keys_to_delete = [key for key in _cache if key.startswith(normalized_prefix)]
    for key in keys_to_delete:
        del _cache[key]
