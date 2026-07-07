"""tests/test_workflow_api.py"""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestWorkflowAPI:
    @pytest.mark.asyncio
    async def test_workflow_run_simple(self, client):
        response = await client.post(
            "/api/v1/workflow/run",
            json={
                "nodes": [
                    {"id": "a", "type": "transform", "config": {"transform_type": "upper"}},
                ],
                "edges": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_workflow_run_linear(self, client):
        response = await client.post(
            "/api/v1/workflow/run",
            json={
                "nodes": [
                    {"id": "a", "type": "transform", "config": {"transform_type": "upper"}},
                    {"id": "b", "type": "transform", "config": {}},
                ],
                "edges": [{"source": "a", "target": "b"}],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_workflow_parallel(self, client):
        response = await client.post(
            "/api/v1/workflow/run",
            json={
                "nodes": [
                    {"id": "planner", "type": "agent", "config": {"agent_type": "planner"}},
                    {"id": "search", "type": "tool", "config": {"tool": "search"}},
                    {"id": "write", "type": "agent", "config": {"agent_type": "writer"}},
                ],
                "edges": [
                    {"source": "planner", "target": "search"},
                    {"source": "planner", "target": "write"},
                ],
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_workflow_with_cycle_returns_400(self, client):
        response = await client.post(
            "/api/v1/workflow/run",
            json={
                "nodes": [
                    {"id": "a", "type": "transform", "config": {}},
                    {"id": "b", "type": "transform", "config": {}},
                    {"id": "c", "type": "transform", "config": {}},
                ],
                "edges": [
                    {"source": "a", "target": "b"},
                    {"source": "b", "target": "c"},
                    {"source": "c", "target": "a"},
                ],
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_workflow_stream_sse(self, client):
        async with client.stream(
            "POST",
            "/api/v1/workflow/stream",
            json={
                "nodes": [
                    {"id": "a", "type": "transform", "config": {}},
                ],
                "edges": [],
            },
        ) as response:
            assert response.status_code == 200
            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    chunks.append(line)
            assert len(chunks) > 0
