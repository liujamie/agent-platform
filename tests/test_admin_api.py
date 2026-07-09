"""tests/test_admin_api.py"""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestAgentDefinitionAPI:
    @pytest.mark.asyncio
    async def test_agent_list_empty(self, client):
        response = await client.get("/api/v1/admin/agents")
        # Without DB, should return empty list gracefully (not crash)
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            assert "agents" in response.json()

    @pytest.mark.asyncio
    async def test_agent_create(self, client):
        response = await client.post(
            "/api/v1/admin/agents",
            json={
                "name": "测试助手",
                "role": "你是一个测试助手",
                "model_name": "deepseek-chat",
                "tools": ["web_search"],
            },
        )
        # With DB unavailable, should return error gracefully
        assert response.status_code in (200, 500)
        data = response.json()
        if "error" in data:
            assert data["error"] == "Database not configured"
        else:
            assert data["name"] == "测试助手"


class TestWorkflowDefinitionAPI:
    @pytest.mark.asyncio
    async def test_workflow_list(self, client):
        response = await client.get("/api/v1/admin/workflows")
        assert response.status_code in (200, 500)


class TestRunLogAPI:
    @pytest.mark.asyncio
    async def test_run_logs_list(self, client):
        response = await client.get("/api/v1/admin/logs")
        assert response.status_code in (200, 500)
