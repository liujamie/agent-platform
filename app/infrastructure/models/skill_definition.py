from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text, JSON, String

from app.infrastructure.database import Base


class SkillDefinition(Base):
    __tablename__ = "skill_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="技能名称（=目录名）")
    description = Column(Text, nullable=True, comment="简要描述")
    tags = Column(JSON, nullable=True, comment="标签列表")
    path = Column(String(255), nullable=False, comment="skills/{name} 相对路径")
    version = Column(String(20), default="1.0.0", comment="语义版本号")
    git_commit_hash = Column(String(40), nullable=True, comment="最近一次同步的 Git commit")
    status = Column(String(20), default="active", comment="active / archived")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
