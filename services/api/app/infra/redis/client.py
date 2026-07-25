"""Redis client helpers."""

from __future__ import annotations

from redis.asyncio import Redis


async def ping_redis(redis_url: str) -> bool:
    client = Redis.from_url(redis_url, decode_responses=True)
    try:
        result = await client.ping()
        return bool(result)
    finally:
        await client.aclose()
