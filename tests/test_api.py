"""tests/test_api.py"""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestToolAPI:
    @pytest.mark.asyncio
    async def test_list_tools(self, client):
        response = await client.get("/api/v1/tool/list")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data

    @pytest.mark.asyncio
    async def test_list_tools_contains_current_time(self, client):
        response = await client.get("/api/v1/tool/list")
        data = response.json()
        tool_names = [t["name"] for t in data["tools"]]
        assert "current_time" in tool_names

    @pytest.mark.asyncio
    async def test_execute_tool(self, client):
        response = await client.post(
            "/api/v1/tool/execute",
            json={"tool_name": "current_time", "args": {"format": "date"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["output"]) == 10  # YYYY-MM-DD


class TestModelAPI:
    @pytest.mark.asyncio
    async def test_list_models(self, client):
        response = await client.get("/api/v1/model/list")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "current" in data


class TestAgentAPI:
    @pytest.mark.asyncio
    async def test_agent_run_no_model(self, client):
        response = await client.post(
            "/api/v1/agent/run",
            json={"message": "hello", "agent_config": {"name": "test", "role": "helper", "model": "deepseek-chat"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_agent_stream_sse(self, client):
        async with client.stream(
            "POST",
            "/api/v1/agent/stream",
            json={"message": "hello", "agent_config": {"name": "test", "role": "helper", "model": "deepseek-chat"}},
        ) as response:
            assert response.status_code == 200
            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    chunks.append(line)
            assert len(chunks) > 0
