from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text, String, Index

from app.infrastructure.database import Base


class RunLog(Base):
    __tablename__ = "run_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(36), nullable=False, index=True)
    agent_id = Column(Integer, nullable=True)
    workflow_id = Column(Integer, nullable=True)
    input = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    status = Column(String(20), default="success", comment="success / error")
    tokens = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_run_logs_created", "created_at"),
    )
