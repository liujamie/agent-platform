from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, Text, JSON, String

from app.infrastructure.database import Base


class MCPConnection(Base):
    __tablename__ = "mcp_connections"
    __table_args__ = (
        Index("idx_mcp_connections_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="连接名称")
    connection_type = Column(String(20), nullable=False, default="stdio", comment="stdio / sse")
    command = Column(String(255), nullable=True, comment="stdio 模式：启动命令")
    args = Column(JSON, nullable=True, comment="stdio 模式：命令参数列表")
    url = Column(String(255), nullable=True, comment="SSE 模式：服务器 URL")
    env_vars = Column(JSON, nullable=True, comment="环境变量键值对")
    status = Column(String(20), default="disconnected", comment="disconnected / connected / error")
    error_message = Column(Text, nullable=True, comment="连接失败时的错误信息")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
