"""Redis infrastructure package."""

from app.infra.redis.client import ping_redis

__all__ = ["ping_redis"]
