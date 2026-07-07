"""tests/test_model_router_fallback.py"""
import pytest
from app.model.router import ModelRouter
from app.model.base import ModelClient, ModelResult


class FailingClient(ModelClient):
    async def invoke(self, messages, model=None, tools=None):
        raise ConnectionError("API unavailable")

    async def stream(self, messages, model=None, tools=None):
        raise ConnectionError("API unavailable")
        yield  # pragma: no cover


class SuccessClient(ModelClient):
    async def invoke(self, messages, model=None, tools=None):
        return ModelResult(content="ok", model="fallback")

    async def stream(self, messages, model=None, tools=None):
        yield "ok"


class TestFallbackChain:
    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        router = ModelRouter()
        router.register("primary", FailingClient())
        router.register("backup", SuccessClient())
        router.fallback_chain = ["primary", "backup"]
        result = await router.invoke_with_fallback([{"role": "user", "content": "hi"}])
        assert result.content == "ok"

    @pytest.mark.asyncio
    async def test_all_fallback_fail(self):
        router = ModelRouter()
        router.register("primary", FailingClient())
        router.register("backup", FailingClient())
        router.fallback_chain = ["primary", "backup"]
        with pytest.raises(RuntimeError, match="All fallback"):
            await router.invoke_with_fallback([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_no_fallback_chain(self):
        router = ModelRouter()
        router.register("primary", FailingClient())
        router.fallback_chain = []
        with pytest.raises(RuntimeError, match="All fallback"):
            await router.invoke_with_fallback([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_skip_missing_model_in_chain(self):
        router = ModelRouter()
        router.register("backup", SuccessClient())
        router.fallback_chain = ["nonexistent", "backup"]
        result = await router.invoke_with_fallback([{"role": "user", "content": "hi"}])
        assert result.content == "ok"
