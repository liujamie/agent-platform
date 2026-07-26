import json
import time
import uuid
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
    """Get all messages for a session from the Redis list."""
    if redis_client is None:
        return []
    raw = await redis_client.lrange(f"session:{session_id}:msgs", 0, -1)
    return [json.loads(m) for m in raw if m]


async def session_add_message(session_id: str, message: dict, ttl: int = 3600):
    """Append a message to the session's message list.
    Keeps at most 20 messages (sliding window).
    Sets TTL on the message list for auto-expiry.
    """
    if redis_client is None:
        return
    key = f"session:{session_id}:msgs"
    await redis_client.rpush(key, json.dumps(message, ensure_ascii=False))
    # Trim to last 20
    await redis_client.ltrim(key, -20, -1)
    # Reset TTL
    await redis_client.expire(key, ttl)


async def session_clear(session_id: str):
    """Clear all messages for a session (keeps metadata)."""
    if redis_client is None:
        return
    await redis_client.delete(f"session:{session_id}:msgs")


# ── Multi-session management ────────────────────────

def _new_session_id() -> str:
    return f"sess_{uuid.uuid4().hex[:12]}"


async def session_create(agent_id: int) -> str:
    """Create a new session for an agent. Returns the session_id."""
    session_id = _new_session_id()
    now = time.time()

    if redis_client is None:
        return session_id

    # Store session metadata
    await redis_client.hset(
        f"session:{session_id}:meta",
        mapping={
            "name": "新对话",
            "agent_id": str(agent_id),
            "created_at": str(now),
        },
    )
    # Add to agent's session index (ZSET sorted by creation time)
    await redis_client.zadd(f"agent:sessions:{agent_id}", {session_id: now})
    return session_id


async def session_rename(session_id: str, name: str) -> None:
    if redis_client is None:
        return
    await redis_client.hset(f"session:{session_id}:meta", "name", name)


async def session_list(agent_id: int) -> list[dict[str, Any]]:
    """List all sessions for an agent, newest first."""
    if redis_client is None:
        return []

    # Get session IDs from the sorted set, descending (newest first)
    session_ids = await redis_client.zrevrange(f"agent:sessions:{agent_id}", 0, -1)
    results = []
    for sid in session_ids:
        meta = await redis_client.hgetall(f"session:{sid}:meta")
        if not meta:
            continue
        # Count messages
        msg_count = await redis_client.llen(f"session:{sid}:msgs") if redis_client else 0
        results.append({
            "session_id": sid,
            "name": meta.get("name", "新对话"),
            "agent_id": int(meta.get("agent_id", 0)),
            "created_at": float(meta.get("created_at", 0)),
            "message_count": msg_count,
        })
    return results


async def session_delete(session_id: str) -> None:
    """Delete a session and all its data."""
    if redis_client is None:
        return
    # Get agent_id from meta first
    agent_id = await redis_client.hget(f"session:{session_id}:meta", "agent_id")
    # Remove from agent's session index
    if agent_id:
        await redis_client.zrem(f"agent:sessions:{agent_id}", session_id)
    # Delete all session keys
    await redis_client.delete(f"session:{session_id}:meta")
    await redis_client.delete(f"session:{session_id}:msgs")


async def session_get_first_message(session_id: str) -> str | None:
    """Get the first user message text (for auto-naming)."""
    if redis_client is None:
        return None
    msgs = await redis_client.lrange(f"session:{session_id}:msgs", 0, 0)
    if msgs:
        try:
            msg = json.loads(msgs[0])
            if msg.get("role") == "user":
                return msg.get("content", "")
        except Exception:
            pass
    return None
