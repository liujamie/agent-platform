# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Backend (Python 3.11+)
pip install -e ".[dev]"   # Install with dev deps
uvicorn app.main:app --reload  # Dev server on :8000
pytest                    # Run all tests
pytest -v                 # Verbose
pytest tests/test_file.py -k test_name  # Single test
agent-platform            # CLI shortcut to start dev server

# Frontend (Vue 3 + Vite)
cd frontend && npm install
npm run dev               # Dev server on :3000 (proxies /api → :8000)
npm run build             # Production build

# Docker (full stack)
docker-compose up -d      # API + Frontend + MySQL + Redis
```

## Project Architecture

Multi-Agent orchestration platform with a DAG workflow engine. Backend is FastAPI (Python 3.11+), frontend is Vue 3 SPA.

### Layered Structure

```
app/
├── api/                  # FastAPI routers (prefix /api/v1/*)
│   ├── agent_routes.py   #   POST /agent/run (simple), /agent/stream (SSE)
│   ├── tool_routes.py    #   GET  /tool/list, POST /tool/execute
│   ├── model_routes.py   #   GET  /model/list, POST /model/switch
│   ├── workflow_routes.py#   POST /workflow/run, /workflow/stream
│   └── admin_routes.py   #   Full CRUD: /admin/agents, /admin/workflows, /admin/logs, /admin/stats
├── config/               # Pydantic-settings from .env
├── core/
│   ├── agent/            # BaseAgent → ReActAgent + AgentStateMachine (FSM)
│   ├── tool/             # BaseTool → ToolRegistry → @tool decorator
│   └── workflow/         # WorkflowGraph (DAG) → WorkflowExecutor (Kahn's topo sort, parallel layers)
├── infrastructure/
│   ├── database.py       # SQLAlchemy async engine + session (MySQL via aiomysql)
│   ├── redis_client.py   # Redis async client + session memory helpers
│   └── models/           # ORM: AgentDefinition, WorkflowDefinition, RunLog
├── memory/               # BaseMemory → SessionMemory (in-memory sliding window)
├── model/                # ModelClient abstraction → OpenAIClient, DashScopeClient → ModelRouter
├── models/               # Pydantic schemas: agent, workflow, tool, common
├── observability/        # Tracer (span tree per trace) + MetricsCollector
├── tools/                # Built-in tools: current_time, web_search, code_executor, rag_query
└── main.py               # FastAPI app, lifespan (DB/Redis init, model registration)
```

### Key Design Decisions

- **Model Router** (`app/model/router.py`): Multiple LLM providers registered at startup. `swich_to()` selects active provider; `invoke_with_fallback()` chains providers in order. Both OpenAI-compatible (DeepSeek, etc.) and DashScope (Qwen) clients use the same `AsyncOpenAI` SDK under the hood.
- **Tool System** (`app/core/tool/`): Tools are registered via the `@tool(name, description, parameters)` decorator in `app/tools/*.py`. The `ToolRegistry` auto-loads on import via `app/main.py`'s `import app.tools` line. Registry exposes OpenAI-compatible schemas for function calling.
- **Agent State Machine** (`app/core/agent/state.py`): PENDING → RUNNING → {THINKING, TOOL_CALL} → FINISHED/ERROR. Terminal states block further transitions.
- **Workflow Engine** (`app/core/workflow/`): DAG model. `WorkflowGraph` validates acyclicity via Kahn's algorithm, returning parallel-execution layers. `WorkflowExecutor` runs each layer concurrently with `asyncio.gather`, passing a shared `Context` object between nodes. Node types: `agent`, `tool`, `condition`, `transform`.
- **Admin API** (`app/api/admin_routes.py`): All CRUD routes receive a DB session from `app.main.get_db_session()` (module-level global). If DB is down, routes gracefully return empty results / "Database not configured" instead of crashing. Agents are soft-deleted (status → "archived").
- **Lifespan** (`app/main.py` lifespan): DB → Redis → model clients. All three are optional — missing DB/Redis doesn't prevent the app from starting (API routes check before using them).
- **API auth**: Not yet implemented. All endpoints are open. See `app/main.py` — no middleware beyond CORS.

### Frontend

Vue 3 + Vue Router with pages: Dashboard (`/`), Agents list (`/agents`), Agent Form (`/agents/new`, `/agents/:id/edit`), Workflows list (`/workflows`), Workflow Form (`/workflows/new`, `/workflows/:id/edit`), Logs (`/logs`). Vite dev server proxies `/api` → `http://localhost:8000`.

### Data Flow

```
User → Vue SPA → REST/SSE → FastAPI → [ModelRouter → LLM | WorkflowExecutor → DAG]
                             → [ToolRegistry → @tool functions]
                             → [SQLAlchemy → MySQL] + [Redis]
```

### Testing

Tests use pytest-asyncio (auto mode) + httpx ASGITransport. FastAPI routes are integration-tested without a live server by passing the `app` object directly. DB-dependent admin routes are NOT tested (no DB in CI) — the graceful-fallback behavior is tested implicitly via the health endpoint.

### Environment Variables (.env)

| Variable | Default | Purpose |
|---|---|---|
| `MYSQL_*` | localhost / root / root | MySQL connection |
| `REDIS_*` | localhost / 6379 | Redis connection |
| `DEEPSEEK_API_KEY` | — | DeepSeek-compatible API |
| `DASHSCOPE_API_KEY` | — | Alibaba DashScope API |
| `OPENAI_API_KEY` | — | OpenAI API |
| `PORT` | 8000 | Server port |
