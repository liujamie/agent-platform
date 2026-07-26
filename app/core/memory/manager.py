"""
MemoryManager — Agent 工作上下文管理。

职责：
  从 ConversationService 拿到完整历史后，在 token 预算内
  组装出最优的 LLM 上下文：
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


async def build_context(
    history: list[dict[str, Any]],
    max_tokens: int = 4096,
    model_client=None,
) -> list[dict[str, Any]]:
    """
    Build an optimized context from full conversation history.

    1. If history fits within max_tokens → return as-is.
    2. If not → keep recent messages, compress the rest into a summary
       and prepend it as a system message.
    3. If no model_client available for summarization → just keep
       the last N messages that fit.
    """
    if not history:
        return []

    total = _messages_token_count(history)
    if total <= max_tokens:
        return list(history)

    # Strategy: working backwards, keep as many recent messages as fit
    kept: list[dict] = []
    kept_tokens = 0
    compress_candidates: list[dict] = []

    for msg in reversed(history):
        tokens = _estimate_tokens(msg.get("content", "") or "")
        if kept_tokens + tokens <= max_tokens:
            kept.insert(0, msg)
            kept_tokens += tokens
        else:
            compress_candidates.insert(0, msg)

    # If all messages fit after trimming (shouldn't happen but safety)
    if not compress_candidates:
        return kept

    # Try to summarize the trimmed portion
    summary = await _summarize(compress_candidates, model_client)
    if summary:
        kept.insert(0, {"role": "system", "content": f"## 历史摘要\n\n{summary}"})
        # Re-check if still under limit after adding summary
        total_now = _messages_token_count(kept)
        if total_now > max_tokens:
            # Drop the earliest kept messages until under limit
            while len(kept) > 1 and _messages_token_count(kept) > max_tokens:
                kept.pop(1)  # Skip index 0 (the summary)
        return kept

    # No summary available → just return what fits
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
            model=None,  # Use current model
            tools=None,
        )
        summary = (response.content or "").strip()
        return summary[:500] if len(summary) > 500 else summary
    except Exception:
        return None
