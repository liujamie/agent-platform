from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text, JSON, String

from app.infrastructure.database import Base


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, nullable=False, comment="关联 workflow_definitions.id")
    trace_id = Column(String(36), nullable=False, unique=True)
    status = Column(String(20), default="running", comment="running / success / failed / paused")
    trigger_type = Column(String(20), default="manual", comment="manual / schedule / webhook / agent")
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    variables = Column(JSON, nullable=True, comment="上下文变量快照")
    started_at = Column(DateTime, default=datetime.now)
    ended_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)


class WorkflowNodeExecution(Base):
    __tablename__ = "workflow_node_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, nullable=False)
    node_id = Column(String(100), nullable=False)
    node_type = Column(String(20), nullable=False)
    node_name = Column(String(100), default="")
    status = Column(String(20), default="pending", comment="pending / running / success / failed / skipped")
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)


class WorkflowApproval(Base):
    __tablename__ = "workflow_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, nullable=False)
    node_exec_id = Column(Integer, nullable=False)
    node_id = Column(String(100), nullable=False)
    status = Column(String(20), default="pending", comment="pending / approved / rejected")
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    assignee = Column(String(100), default="admin")
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    handled_at = Column(DateTime, nullable=True)
