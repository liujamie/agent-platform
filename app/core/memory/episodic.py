"""
Episodic Memory — 情景记忆。

职责：
  每轮对话结束后，从用户输入 + LLM 回复中提取关键信息
  （事实、偏好、决策），存入 MySQL。
  下次对话时自动检索相关记忆，注入到 LLM 上下文中。
"""

import json
from datetime import datetime
from typing import Any


async def extract_and_save(
    agent_id: int,
    session_id: str,
    user_input: str,
    llm_output: str,
    model_client,
) -> None:
    """Call LLM to extract key information, then save to DB."""
    if model_client is None:
        return

    facts = await _extract_facts(user_input, llm_output, model_client)
    if not facts:
        return

    for fact in facts:
        content = fact.get("content", "")
        fact_type = fact.get("type", "fact")
        importance = fact.get("importance", 1)
        # Save to episodic memory (structured retrieval)
        await _save_episode(
            agent_id=agent_id,
            session_id=session_id,
            content=content,
            fact_type=fact_type,
            importance=importance,
        )
        # Save to semantic memory (vector retrieval) — non-blocking
        try:
            from app.core.memory.semantic import save_memory
            await save_memory(
                agent_id=agent_id,
                session_id=session_id,
                content=content,
                fact_type=fact_type,
                importance=importance,
            )
        except Exception:
            pass


async def retrieve(agent_id: int, limit: int = 5) -> list[dict[str, Any]]:
    """Retrieve important episodes for an agent, highest importance first."""
    from app.main import get_db_session
    from sqlalchemy import select

    db = get_db_session()
    if db is None:
        return []

    try:
        from app.infrastructure.models.memory_episode import MemoryEpisode
        result = await db.execute(
            select(MemoryEpisode)
            .where(MemoryEpisode.agent_id == agent_id)
            .order_by(MemoryEpisode.importance.desc(), MemoryEpisode.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "content": e.content,
                "type": e.type,
                "importance": e.importance,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in result.scalars().all()
        ]
    except Exception:
        return []


async def _extract_facts(
    user_input: str, llm_output: str, model_client,
) -> list[dict] | None:
    """Use LLM to extract structured facts from a conversation turn."""
    # Truncate input to avoid excessive token usage on extraction itself
    user_excerpt = user_input[:800]
    output_excerpt = llm_output[:1500]

    prompt = (
        "从以下对话中提取**跨会话有价值**的信息。\n\n"
        "### 提取（每一项控制在 20 字以内）\n"
        "- fact: 用户的背景、技术栈、项目信息等事实\n"
        "- preference: 用户明确表达的偏好或习惯\n"
        "- decision: 用户做出的技术或业务决策\n\n"
        "### 跳过\n"
        "- 打招呼、感谢、客套话\n"
        "- 当前问题的中间推理过程\n"
        "- 通用知识或常识\n"
        "- 一次性问题（不需要记住的信息）\n\n"
        "按 JSON 数组返回：[{\"content\":\"...\",\"type\":\"fact\",\"importance\":3}]\n"
        "importance 1-5，5 为最重要。无有价值信息返回 []。\n\n"
        f"用户：{user_excerpt}\n\n"
        f"助手：{output_excerpt}"
    )

    try:
        response = await model_client.invoke(
            messages=[{"role": "user", "content": prompt}],
            model=None,
            tools=None,
        )
        text = (response.content or "").strip()
        return _parse_facts(text)
    except Exception:
        return None


def _parse_facts(text: str) -> list[dict]:
    """Parse LLM response to extract fact list."""
    # Try to extract JSON array from the response
    try:
        # Find first [ and last ]
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            data = json.loads(text[start:end+1])
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict) and d.get("content")]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


async def _save_episode(
    agent_id: int,
    session_id: str,
    content: str,
    fact_type: str = "fact",
    importance: int = 1,
) -> None:
    """Save a single episode to MySQL.
    Dedup: if similar content exists for the same agent, boost importance instead of inserting.
    """
    from app.main import get_db_session
    from sqlalchemy import select

    db = get_db_session()
    if db is None:
        return

    try:
        from app.infrastructure.models.memory_episode import MemoryEpisode

        content = content.strip()
        if not content:
            return

        # ── Dedup: check for similar existing episodes ──
        result = await db.execute(
            select(MemoryEpisode)
            .where(MemoryEpisode.agent_id == agent_id)
            .order_by(MemoryEpisode.created_at.desc())
            .limit(20)
        )
        existing = result.scalars().all()

        for ep in existing:
            similarity = _text_similarity(content, ep.content)
            if similarity >= 0.5:
                # Boost existing importance (capped at 5)
                new_importance = min(ep.importance + 1, 5)
                ep.importance = new_importance
                ep.type = fact_type  # Update type to latest
                await db.commit()
                return  # Don't insert duplicate

        # ── No duplicate found, insert new ──
        episode = MemoryEpisode(
            agent_id=agent_id,
            session_id=session_id,
            content=content,
            type=fact_type,
            importance=min(max(importance, 1), 5),
            created_at=datetime.now(),
        )
        db.add(episode)
        await db.commit()
    except Exception:
        await db.rollback()


def _text_similarity(a: str, b: str) -> float:
    """Simple character-level overlap similarity (0.0 - 1.0).
    No vector DB needed - works well for short fact-like text (~30 chars).
    """
    if not a or not b:
        return 0.0
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) < 3:
        return 0.0
    matches = sum(1 for c in shorter if c in longer)
    return matches / len(shorter)
