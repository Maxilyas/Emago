"""
app/core/redis_client.py
Pool Redis async partagé. Initialisé dans le lifespan FastAPI.
"""
from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()

_redis_pool: aioredis.Redis | None = None


async def init_redis() -> None:
    """Appelé dans le lifespan FastAPI au démarrage."""
    global _redis_pool
    _redis_pool = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
    )
    await _redis_pool.ping()


async def close_redis() -> None:
    """Appelé dans le lifespan FastAPI au shutdown."""
    if _redis_pool:
        await _redis_pool.aclose()


def get_redis() -> aioredis.Redis:
    if _redis_pool is None:
        raise RuntimeError("Redis non initialisé — appelé avant le lifespan.")
    return _redis_pool


async def publish_event(channel: str, event: dict) -> None:
    """
    Publie un événement JSON sur un canal Redis pub/sub.
    Convention : emago:events:{channel}
    Le WebSocket handler souscrit sur ces canaux.
    """
    r = get_redis()
    await r.publish(f"emago:events:{channel}", json.dumps(event))
