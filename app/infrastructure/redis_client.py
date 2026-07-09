import json
from typing import Any, Optional

from redis.asyncio import Redis

from app.config.settings import get_settings

redis_client: Optional[Redis] = None


async def init_redis():
    global redis_client
    settings = get_settings()
    redis_client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        decode_responses=True,
    )
    # Verify connection
    await redis_client.ping()


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.aclose()


async def cache_get(key: str) -> Optional[str]:
    if redis_client is None:
        return None
    return await redis_client.get(key)


async def cache_set(key: str, value: str, ttl: int = 300):
    if redis_client is None:
        return
    await redis_client.setex(key, ttl, value)


async def cache_delete(key: str):
    if redis_client is None:
        return
    await redis_client.delete(key)


# Session memory via Redis
async def session_get_messages(session_id: str) -> list[dict]:
    data = await cache_get(f"session:{session_id}")
    return json.loads(data) if data else []


async def session_add_message(session_id: str, message: dict, ttl: int = 3600):
    messages = await session_get_messages(session_id)
    messages.append(message)
    # Keep last 20 messages
    if len(messages) > 20:
        messages = messages[-20:]
    await cache_set(f"session:{session_id}", json.dumps(messages, ensure_ascii=False), ttl)


async def session_clear(session_id: str):
    await cache_delete(f"session:{session_id}")
