"""tests/test_model_gateway.py"""
import pytest
from app.model.base import ModelClient, ModelResult
from app.model.router import ModelRouter
from app.model.openai_client import OpenAIClient


class TestModelClientABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            ModelClient()  # abstract


class TestModelResult:
    def test_model_result_creation(self):
        r = ModelResult(content="hello", model="test")
        assert r.content == "hello"
        assert r.usage["input"] == 0

    def test_model_result_with_usage(self):
        r = ModelResult(content="hello", model="test", usage={"input": 10, "output": 5})
        assert r.usage["input"] == 10


class TestOpenAIClient:
    def test_init_with_api_key(self):
        client = OpenAIClient(api_key="test-key", base_url="https://api.deepseek.com")
        assert client.api_key == "test-key"
        assert client.model == "deepseek-chat"

    def test_init_custom_model(self):
        client = OpenAIClient(api_key="test-key", base_url="https://api.deepseek.com", model="gpt-4o")
        assert client.model == "gpt-4o"


class TestModelRouter:
    def test_register_and_list(self):
        router = ModelRouter()
        client = OpenAIClient(api_key="test", base_url="https://api.deepseek.com")
        router.register("deepseek", client)
        models = router.list_models()
        assert "deepseek" in models

    def test_get_existing_model(self):
        router = ModelRouter()
        client = OpenAIClient(api_key="test", base_url="https://api.deepseek.com")
        router.register("deepseek", client)
        assert router.get("deepseek") is client

    def test_get_nonexistent_model(self):
        router = ModelRouter()
        assert router.get("nonexistent") is None

    def test_switch_current_model(self):
        router = ModelRouter()
        client = OpenAIClient(api_key="test", base_url="https://api.deepseek.com")
        router.register("deepseek", client)
        router.switch_to("deepseek")
        assert router.current == "deepseek"

    def test_switch_nonexistent_model(self):
        router = ModelRouter()
        router.switch_to("nonexistent")
        assert router.current is None
