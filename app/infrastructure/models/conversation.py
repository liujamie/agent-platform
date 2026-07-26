from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text, String

from app.infrastructure.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, unique=True, comment="前端传入的会话标识")
    agent_id = Column(Integer, nullable=False, comment="所属 Agent ID")
    name = Column(String(200), default="新对话", comment="会话名称")
    message_count = Column(Integer, default=0, comment="消息总数")
    status = Column(String(20), default="active", comment="active / archived")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, nullable=False, comment="关联 conversations.id")
    role = Column(String(20), nullable=False, comment="user / assistant / tool / system")
    content = Column(Text, nullable=False, comment="消息内容")
    tokens = Column(Integer, default=0, comment="预估 token 数")
    msg_index = Column(Integer, nullable=False, comment="消息序号（从 0 开始）")
    created_at = Column(DateTime, default=datetime.now)
