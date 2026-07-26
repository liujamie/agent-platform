from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text, BLOB, String

from app.infrastructure.database import Base


class SemanticMemory(Base):
    __tablename__ = "semantic_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, nullable=False, comment="所属 Agent")
    session_id = Column(String(100), nullable=True, comment="来源会话")
    content = Column(Text, nullable=False, comment="原始文本")
    embedding = Column(BLOB, nullable=True, comment="向量（float32）")
    type = Column(String(20), default="fact", comment="fact / preference / decision")
    importance = Column(Integer, default=1, comment="重要性 1-5")
    created_at = Column(DateTime, default=datetime.now)
