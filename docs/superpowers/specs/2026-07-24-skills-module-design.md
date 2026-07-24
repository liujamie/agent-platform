# Skills 模块设计

## 概述

为 Agent Platform 增加 Skills 模块，允许用户创建和管理可复用的 Markdown 指令片段，绑定到 Agent 后自动注入 system prompt，增强 Agent 的专业能力。

## 数据模型

### SkillDefinition

**文件**: `app/infrastructure/models/skill_definition.py`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| name | String(100) UNIQUE | Skill 唯一标识 |
| description | Text | 简述，在 Agent 页面选择时显示 |
| content | Text | Markdown 指令正文 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### AgentDefinition 扩展

新增 `skills` JSON 字段，存 skill name 列表：

```
skills = Column(JSON, nullable=True, comment="绑定的 Skill 名称列表")
```

AgentConfig 同步增加 `skills: list[str] = Field(default_factory=list)`。

## 架构

```
Skill 管理页面 ─→ Admin API ─→ SkillDefinition (DB)
    (CRUD)                      skills 表

Agent 编辑页面 ─→ 勾选 Skill ─→ AgentDefinition.skills (DB)
    (复选)                       skills: ["xxx", "yyy"]

Agent 运行时:
  Role (system prompt)
  + [Skill: xxx] 的内容
  + [Skill: yyy] 的内容
  + 工具列表 (tools + MCP connections)
  → 最终 system prompt
```

## 模块详情

### 1. ORM 模型

新建 `app/infrastructure/models/skill_definition.py`，在 `__init__.py` 导出。

### 2. Admin API

新建 `app/api/admin_skill_routes.py`，标准 CRUD：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/admin/skills` | 列表 |
| POST | `/api/v1/admin/skills` | 创建 |
| PUT | `/api/v1/admin/skills/{id}` | 编辑 |
| DELETE | `/api/v1/admin/skills/{id}` | 删除 |

### 3. Agent 绑定

- `AgentConfig` 增加 `skills: list[str]`
- `AgentDefinition` ORM 增加 `skills` JSON 列
- `admin_routes.py` Agent CRUD 处理 skills 字段
- `_agent_to_dict` 返回 skills

### 4. System Prompt 拼接

`ReActAgent._build_system_message()` 在 role 后追加已绑定 skill 的内容：

```python
async def _load_skills(self) -> str:
    """Load skill contents and append to system prompt."""
    if not self.config.skills:
        return ""
    try:
        from app.main import get_db_session
        session = get_db_session()
        if not session:
            return ""
        from sqlalchemy import select
        from app.infrastructure.models import SkillDefinition
        result = await session.execute(
            select(SkillDefinition).where(SkillDefinition.name.in_(self.config.skills))
        )
        parts = []
        for skill in result.scalars().all():
            parts.append(f"[Skill: {skill.name}]\n{skill.content}")
        return "\n\n" + "\n\n".join(parts)
    except Exception:
        return ""
```

### 5. 前端页面

**Skills 管理页** (`/skills`):
- 表格：名称 | 描述 | 创建时间 | 操作
- Modal 表单：名称 + 描述 + Markdown 文本域（textarea）
- 同 Tools/Models 风格

**Agent 编辑页** — 在 MCP 连接之后新增 Skill 多选框：

```
┌─ Skills（可复用的能力指令）─────────────────────────┐
│                                                     │
│  ☑ code-review   代码审查，自动检查代码质量          │
│  ☐ git-workflow  团队 Git 工作流规范                 │
│  ☐ security      安全审计 checklist                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 文件变更清单

**新增:**
1. `app/infrastructure/models/skill_definition.py`
2. `app/api/admin_skill_routes.py`
3. `frontend/src/pages/Skills.vue`

**修改:**
1. `app/infrastructure/models/__init__.py`
2. `app/main.py` — 注册路由 + 自动迁移
3. `app/models/agent.py` — AgentConfig 加 skills
4. `app/infrastructure/models/agent_definition.py` — 加 skills 列
5. `app/core/agent/react.py` — 拼接 skill 内容到 system prompt
6. `app/api/admin_routes.py` — Agent CRUD 处理 skills
7. `app/api/agent_routes.py` — 传入 skills
8. `frontend/src/main.js` — 添加路由
9. `frontend/src/App.vue` — 侧边栏
10. `frontend/src/pages/AgentForm.vue` — 加 skill 多选框
