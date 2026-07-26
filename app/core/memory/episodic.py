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
        await _save_episode(
            agent_id=agent_id,
            session_id=session_id,
            content=fact.get("content", ""),
            fact_type=fact.get("type", "fact"),
            importance=fact.get("importance", 1),
        )


async def retrieve(agent_id: int, limit: int = 5) -> list[dict[str, Any]]:
    """Retrieve recent important episodes for an agent."""
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
        "从以下对话中提取重要信息，包括：\n"
        "1. 用户透露的事实或背景信息（type: fact）\n"
        "2. 用户的偏好或习惯（type: preference）\n"
        "3. 做出的决策或结论（type: decision）\n\n"
        "只提取明确、有价值的信息，忽略客套话和通用问候。\n"
        "每条信息控制在 30 字以内。\n"
        "按 JSON 数组返回：[{\"content\": \"...\", \"type\": \"fact\", \"importance\": 3}]\n"
        "importance 1-5，5 为最重要。\n"
        "如果没有值得记录的信息，返回 []。\n\n"
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
    """Save a single episode to MySQL."""
    from app.main import get_db_session

    db = get_db_session()
    if db is None:
        return

    try:
        from app.infrastructure.models.memory_episode import MemoryEpisode
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
