import json
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, Text, JSON, String

from app.infrastructure.database import Base


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="Workflow 名称")
    description = Column(Text, nullable=True)
    definition = Column(JSON, nullable=False, comment="nodes + edges")
    status = Column(String(20), default="active", comment="active / archived")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
