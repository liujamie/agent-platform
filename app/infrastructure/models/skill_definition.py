from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text, String

from app.infrastructure.database import Base


class SkillDefinition(Base):
    __tablename__ = "skill_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="Skill 名称")
    description = Column(Text, nullable=True, comment="简要描述")
    content = Column(Text, nullable=False, comment="Markdown 指令正文")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
