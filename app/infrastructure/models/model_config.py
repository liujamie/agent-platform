from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, Text, String

from app.infrastructure.database import Base


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="模型标识名")
    provider = Column(String(20), nullable=False, default="openai", comment="openai / dashscope")
    api_key_encrypted = Column(Text, nullable=True, comment="加密后的 API Key")
    base_url = Column(String(255), nullable=True, comment="API 地址（仅 openai 类型）")
    model = Column(String(100), nullable=False, comment="模型名，如 deepseek-v4-flash")
    is_current = Column(Boolean, default=False, comment="是否为当前使用的模型")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
