"""
Semantic Memory — 语义记忆。

通过向量嵌入 + 余弦相似度实现语义级检索，
不依赖关键词匹配，能从大量记忆中精准找到相关内容。
"""

import struct
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select

from app.config.settings import get_settings
from app.infrastructure.models import SemanticMemory as SemanticMemoryModel


# ── Embedding API ────────────────────────────────────

def _get_client() -> AsyncOpenAI | None:
    """Create an OpenAI-compatible client for SiliconFlow embedding API."""
    settings = get_settings()
    if not settings.siliconflow_api_key:
        return None
    return AsyncOpenAI(
        api_key=settings.siliconflow_api_key,
        base_url="https://api.siliconflow.cn/v1",
    )


async def embed_text(text: str) -> list[float] | None:
    """Convert text to vector embedding via SiliconFlow API."""
    client = _get_client()
    if client is None:
        return None
    try:
        settings = get_settings()
        response = await client.embeddings.create(
            input=text,
            model=settings.embedding_model,
        )
        return response.data[0].embedding
    except Exception:
        return None


# ── Vector helpers ───────────────────────────────────

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Higher = more similar."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def vec_to_bytes(vec: list[float]) -> bytes:
    """Serialize float32 list to bytes (for BLOB storage)."""
    return struct.pack(f"{len(vec)}f", *vec)


def vec_from_bytes(data: bytes) -> list[float]:
    """Deserialize bytes to float32 list."""
    n = len(data) // 4
    return list(struct.unpack(f"{n}f", data))


# ── CRUD ─────────────────────────────────────────────

async def save_memory(
    agent_id: int,
    session_id: str,
    content: str,
    fact_type: str = "fact",
    importance: int = 1,
) -> None:
    """Save a piece of info + its vector embedding to semantic_memories table."""
    from app.main import get_db_session

    db = get_db_session()
    if db is None:
        return

    vector = await embed_text(content)
    if vector is None:
        return

    try:
        memory = SemanticMemoryModel(
            agent_id=agent_id,
            session_id=session_id,
            content=content,
            embedding=vec_to_bytes(vector),
            type=fact_type,
            importance=min(max(importance, 1), 5),
        )
        db.add(memory)
        await db.commit()
    except Exception:
        await db.rollback()


async def search_memories(
    agent_id: int,
    query: str,
    top_k: int = 3,
    min_score: float = 0.7,
) -> list[dict[str, Any]]:
    """Search memories by semantic similarity to the query text."""
    query_vec = await embed_text(query)
    if query_vec is None:
        return []

    from app.main import get_db_session

    db = get_db_session()
    if db is None:
        return []

    try:
        result = await db.execute(
            select(SemanticMemoryModel)
            .where(SemanticMemoryModel.agent_id == agent_id)
            .order_by(SemanticMemoryModel.created_at.desc())
        )
        memories = result.scalars().all()

        scored = []
        for m in memories:
            if not m.embedding:
                continue
            vec = vec_from_bytes(m.embedding)
            score = cosine_similarity(query_vec, vec)
            if score >= min_score:
                scored.append((score, m))

        scored.sort(key=lambda x: -x[0])
        return [
            {
                "content": m.content,
                "type": m.type,
                "score": round(score, 4),
            }
            for score, m in scored[:top_k]
        ]
    except Exception:
        return []


async def delete_by_agent(agent_id: int) -> None:
    """Delete all semantic memories for an agent."""
    from app.main import get_db_session

    db = get_db_session()
    if db is None:
        return
    try:
        from sqlalchemy import delete
        await db.execute(
            delete(SemanticMemoryModel).where(SemanticMemoryModel.agent_id == agent_id)
        )
        await db.commit()
    except Exception:
        await db.rollback()
