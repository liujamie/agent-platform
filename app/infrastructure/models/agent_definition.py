import json
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, Text, JSON, String
from sqlalchemy.orm import Mapped

from app.infrastructure.database import Base


class AgentDefinition(Base):
    __tablename__ = "agent_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="Agent 名称")
    role = Column(Text, nullable=False, comment="System prompt")
    model_name = Column(String(50), nullable=False, comment="模型名")
    tools = Column(JSON, nullable=True, comment="绑定的工具列表")
    memory_enabled = Column(Boolean, default=True)
    temperature = Column(Integer, default=70)  # 0-100 scaled
    status = Column(String(20), default="active", comment="active / archived")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
