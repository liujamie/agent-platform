"""
ConversationService — 完整会话记录管理。

职责：
  保存和读取完整的原始对话消息（一条不丢），存储在 MySQL。
  不关心 token 窗口，不压缩，不摘要。
"""

import uuid
from datetime import datetime
from typing import Any

from app.infrastructure.models.conversation import Conversation, ConversationMessage


def _new_session_id() -> str:
    return f"sess_{uuid.uuid4().hex[:12]}"


async def create_conversation(agent_id: int, session_id: str | None = None, name: str = "新对话") -> dict[str, Any]:
    """Create a new conversation record in MySQL. Returns the session_id."""
    from app.main import get_db_session
    session = get_db_session()
    if session is None:
        return {"session_id": session_id or _new_session_id(), "name": name}

    if session_id is None:
        session_id = _new_session_id()

    try:
        conv = Conversation(
            session_id=session_id,
            agent_id=agent_id,
            name=name,
            message_count=0,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
    except Exception:
        await session.rollback()
    return {"session_id": session_id, "name": name}


async def add_message(session_id: str, role: str, content: str, tokens: int = 0) -> None:
    """Append a message to a conversation."""
    from app.main import get_db_session
    from sqlalchemy import select, func

    db = get_db_session()
    if db is None:
        return

    conv_id = await _get_conversation_id(db, session_id)
    if conv_id is None:
        return

    try:
        # Get next msg_index
        result = await db.execute(
            select(func.coalesce(func.max(ConversationMessage.msg_index), -1) + 1)
            .where(ConversationMessage.conversation_id == conv_id)
        )
        next_index = result.scalar() or 0

        msg = ConversationMessage(
            conversation_id=conv_id,
            role=role,
            content=content,
            tokens=tokens,
            msg_index=next_index,
            created_at=datetime.now(),
        )
        db.add(msg)
        # Update count
        await db.execute(
            Conversation.__table__.update()
            .where(Conversation.id == conv_id)
            .values(message_count=Conversation.message_count + 1, updated_at=datetime.now())
        )
        await db.commit()
    except Exception:
        await db.rollback()


async def get_messages(session_id: str) -> list[dict[str, Any]]:
    """Get ALL messages for a conversation, ordered by msg_index."""
    from app.main import get_db_session
    from sqlalchemy import select

    db = get_db_session()
    if db is None:
        return []

    conv_id = await _get_conversation_id(db, session_id)
    if conv_id is None:
        return []

    try:
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conv_id)
            .order_by(ConversationMessage.msg_index)
        )
        return [
            {"role": m.role, "content": m.content, "tokens": m.tokens}
            for m in result.scalars().all()
        ]
    except Exception:
        return []


async def list_by_agent(agent_id: int) -> list[dict[str, Any]]:
    """List all conversations for an agent, newest first."""
    from app.main import get_db_session
    from sqlalchemy import select

    db = get_db_session()
    if db is None:
        return []

    try:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.agent_id == agent_id, Conversation.status == "active")
            .order_by(Conversation.updated_at.desc())
        )
        return [
            {
                "session_id": c.session_id,
                "name": c.name,
                "message_count": c.message_count,
                "created_at": c.created_at.timestamp() if c.created_at else 0,
            }
            for c in result.scalars().all()
        ]
    except Exception:
        return []


async def rename(session_id: str, name: str) -> None:
    """Rename a conversation."""
    from app.main import get_db_session
    from sqlalchemy import select

    db = get_db_session()
    if db is None:
        return
    try:
        result = await db.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            conv.name = name
            conv.updated_at = datetime.now()
            await db.commit()
    except Exception:
        await db.rollback()


async def delete_conversation(session_id: str) -> None:
    """Soft-delete a conversation (mark archived)."""
    from app.main import get_db_session
    from sqlalchemy import select

    db = get_db_session()
    if db is None:
        return
    try:
        result = await db.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            conv.status = "archived"
            conv.updated_at = datetime.now()
            # Also delete messages
            from sqlalchemy import delete
            await db.execute(
                delete(ConversationMessage).where(ConversationMessage.conversation_id == conv.id)
            )
            await db.commit()
    except Exception:
        await db.rollback()


async def get_message_count(session_id: str) -> int:
    """Get message count for auto-naming."""
    from app.main import get_db_session
    from sqlalchemy import select, func

    db = get_db_session()
    if db is None:
        return 0
    conv_id = await _get_conversation_id(db, session_id)
    if conv_id is None:
        return 0
    try:
        result = await db.execute(
            select(func.count(ConversationMessage.id))
            .where(ConversationMessage.conversation_id == conv_id)
        )
        return result.scalar() or 0
    except Exception:
        return 0


async def _get_conversation_id(db, session_id: str) -> int | None:
    """Look up conversation internal ID by session_id."""
    from sqlalchemy import select
    try:
        result = await db.execute(
            select(Conversation.id).where(Conversation.session_id == session_id)
        )
        return result.scalar_one_or_none()
    except Exception:
        return None
