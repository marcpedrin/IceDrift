"""Redis + disk-based cache service with TTL support."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Optional

from loguru import logger

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheService:
    """Unified cache: Redis primary, disk fallback."""

    def __init__(self, redis_url: str = "redis://localhost:6379", disk_cache_dir: str = "./cache"):
        self.redis_url = redis_url
        self.disk_cache_dir = Path(disk_cache_dir)
        self.disk_cache_dir.mkdir(parents=True, exist_ok=True)
        self._redis: Optional[Any] = None
        self._redis_ok = False

    async def connect(self) -> None:
        if not REDIS_AVAILABLE:
            logger.warning("redis not installed – using disk cache only")
            return
        try:
            self._redis = aioredis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=2)
            await self._redis.ping()
            self._redis_ok = True
            logger.info("Redis cache connected at {}", self.redis_url)
        except Exception as exc:
            logger.warning("Redis unavailable ({}), falling back to disk cache", exc)
            self._redis_ok = False

    async def disconnect(self) -> None:
        if self._redis and self._redis_ok:
            await self._redis.aclose()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value. Returns None on miss."""
        if self._redis_ok:
            try:
                raw = await self._redis.get(key)
                if raw is not None:
                    return json.loads(raw)
            except Exception as exc:
                logger.debug("Redis GET failed: {}", exc)
        return self._disk_get(key)

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Store value with TTL in seconds."""
        serialized = json.dumps(value, default=str)
        if self._redis_ok:
            try:
                await self._redis.setex(key, ttl, serialized)
                return
            except Exception as exc:
                logger.debug("Redis SET failed: {}", exc)
        self._disk_set(key, serialized, ttl)

    async def delete(self, key: str) -> None:
        if self._redis_ok:
            try:
                await self._redis.delete(key)
            except Exception:
                pass
        self._disk_delete(key)

    async def exists(self, key: str) -> bool:
        val = await self.get(key)
        return val is not None

    @staticmethod
    def make_key(*parts: str) -> str:
        """Build a deterministic cache key from parts."""
        raw = ":".join(str(p) for p in parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    # ── Disk helpers ───────────────────────────────────────────────────────────

    def _disk_path(self, key: str) -> Path:
        return self.disk_cache_dir / f"{key}.json"

    def _disk_get(self, key: str) -> Optional[Any]:
        path = self._disk_path(key)
        if not path.exists():
            return None
        try:
            with path.open() as f:
                envelope = json.load(f)
            if envelope["expires_at"] < time.time():
                path.unlink(missing_ok=True)
                return None
            return envelope["value"]
        except Exception:
            return None

    def _disk_set(self, key: str, serialized: str, ttl: int) -> None:
        path = self._disk_path(key)
        try:
            envelope = {"expires_at": time.time() + ttl, "value": json.loads(serialized)}
            with path.open("w") as f:
                json.dump(envelope, f)
        except Exception as exc:
            logger.debug("Disk cache write failed: {}", exc)

    def _disk_delete(self, key: str) -> None:
        self._disk_path(key).unlink(missing_ok=True)


# Singleton
_cache_instance: Optional[CacheService] = None


def get_cache() -> CacheService:
    global _cache_instance
    if _cache_instance is None:
        from config import get_settings
        s = get_settings()
        _cache_instance = CacheService(redis_url=s.redis_url, disk_cache_dir=f"{s.data_dir}/cache")
    return _cache_instance
