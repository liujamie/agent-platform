from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text, String

from app.infrastructure.database import Base


class MemoryEpisode(Base):
    __tablename__ = "memory_episodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, nullable=False, comment="所属 Agent ID")
    session_id = Column(String(100), nullable=True, comment="来源会话 ID")
    content = Column(Text, nullable=False, comment="关键信息摘要")
    type = Column(String(20), default="fact", comment="fact / preference / decision")
    importance = Column(Integer, default=1, comment="重要性 1-5")
    created_at = Column(DateTime, default=datetime.now)
