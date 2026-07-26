"""
MemoryManager — Agent 工作上下文管理。

职责：
  从 ConversationService 拿到完整历史后，在 token 预算内
  组装出最优的 LLM 上下文：
    - 单条超长消息自动截断（保留首尾）
    - 完整保留最近 N 条消息
    - 超出预算时将最早的消息压缩为摘要
    - 摘要本身也作为一条 system 消息参与上下文
"""

from typing import Any

# Rough token estimation: 1 token ≈ 2 chars for CJK
_CHARS_PER_TOKEN = 2


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _messages_token_count(messages: list[dict]) -> int:
    return sum(_estimate_tokens(m.get("content", "") or "") for m in messages)


def _truncate_content(content: str, max_tokens: int) -> str:
    """
    Truncate a single message's content if it exceeds max_tokens.
    Strategy: keep head (20%) and tail (80%) with a truncation notice.
    This preserves both the beginning (context) and end (conclusion).
    """
    tokens = _estimate_tokens(content)
    if tokens <= max_tokens:
        return content

    chars = len(content)
    max_chars = max_tokens * _CHARS_PER_TOKEN

    # Keep first ~20% and last ~80% within the budget
    head_ratio = 0.2
    head_chars = int(max_chars * head_ratio)
    tail_chars = max_chars - head_chars - 50  # 50 chars for the notice

    if tail_chars < 50:  # Too small, just take the head
        return content[:max_chars] + f"\n\n...（内容过长，已截断，共 {tokens} tokens）"

    head = content[:head_chars]
    tail = content[-tail_chars:]
    return f"{head}\n\n...（中间内容已截断，共 {tokens} tokens）\n\n{tail}"


async def build_context(
    history: list[dict[str, Any]],
    max_tokens: int = 4096,
    model_client=None,
    agent_id: int | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    """
    Build an optimized context from full conversation history.

    0. Retrieve episodic memories + semantic search → inject as sys msg.
    1. Truncate any single message exceeding max_tokens * 0.5.
    2. If all messages fit → return as-is.
    3. If not → keep recent messages, compress the rest into a summary
       and prepend it as a system message.
    4. If no model_client available for summarization → just keep
       the last N messages that fit.
    """
    # ── Level 0: memory injection (always retrieve, even without history) ──
    memory_lines = []

    if agent_id is not None:
        # 0a: Episodic — recent important facts
        from app.core.memory.episodic import retrieve as retrieve_episodes
        episodes = await retrieve_episodes(agent_id, limit=3)
        for e in episodes:
            memory_lines.append(f"- [{e['type']}] {e['content']}")

        # 0b: Semantic — query-relevant facts (if user provided a query)
        if query:
            try:
                from app.core.memory.semantic import search_memories
                semantic_hits = await search_memories(agent_id, query, top_k=3, min_score=0.7)
                for hit in semantic_hits:
                    memory_lines.append(f"- 🔍 {hit['content']}")
            except Exception:
                pass

    episode_msg = None
    if memory_lines:
        episode_msg = {
            "role": "system",
            "content": "## 关于用户的历史记忆\n\n" + "\n".join(memory_lines),
        }

    if not history:
        return [episode_msg] if episode_msg else []

    # ── Level 1: message-level truncation ──
    max_msg_tokens = max_tokens // 2
    truncated_history = []
    for msg in history:
        content = msg.get("content", "") or ""
        truncated = _truncate_content(content, max_msg_tokens)
        if truncated != content:
            truncated_history.append({**msg, "content": truncated})
        else:
            truncated_history.append(msg)

    # Add episodes if we have any
    if episode_msg:
        truncated_history.insert(0, episode_msg)

    total = _messages_token_count(truncated_history)
    if total <= max_tokens:
        return truncated_history

    # ── Level 2: context-level sliding window + summary ──
    kept: list[dict] = []
    kept_tokens = 0
    compress_candidates: list[dict] = []

    for msg in reversed(truncated_history):
        tokens = _estimate_tokens(msg.get("content", "") or "")
        if kept_tokens + tokens <= max_tokens:
            kept.insert(0, msg)
            kept_tokens += tokens
        else:
            compress_candidates.insert(0, msg)

    if not compress_candidates:
        return kept

    summary = await _summarize(compress_candidates, model_client)
    if summary:
        kept.insert(0, {"role": "system", "content": f"## 历史摘要\n\n{summary}"})
        total_now = _messages_token_count(kept)
        if total_now > max_tokens:
            while len(kept) > 1 and _messages_token_count(kept) > max_tokens:
                kept.pop(1)
        return kept

    return kept


async def _summarize(messages: list[dict], model_client) -> str | None:
    """Call LLM to compress a list of messages into a short summary."""
    if model_client is None:
        return None

    text_parts = []
    for m in messages:
        role = m.get("role", "unknown")
        content = (m.get("content", "") or "").strip()
        if content:
            text_parts.append(f"{role}: {content[:200]}")

    if not text_parts:
        return None

    prompt = f"""请将以下对话内容压缩为一段简洁的中文摘要（50-100字），保留关键事实、决定和结论，不保留客套话：

{"---".join(text_parts[-5:])}"""

    try:
        response = await model_client.invoke(
            messages=[{"role": "user", "content": prompt}],
            model=None,
            tools=None,
        )
        summary = (response.content or "").strip()
        return summary[:500] if len(summary) > 500 else summary
    except Exception:
        return None
