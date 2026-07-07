"""tests/test_dashscope_client.py"""
import pytest
from app.model.dashscope_client import DashScopeClient
from app.model.base import ModelClient


class TestDashScopeClient:
    def test_init(self):
        client = DashScopeClient(api_key="test-key")
        assert isinstance(client, ModelClient)
        assert client.api_key == "test-key"
        assert client.model == "qwen-plus"

    def test_init_custom_model(self):
        client = DashScopeClient(api_key="test-key", model="qwen-max")
        assert client.model == "qwen-max"

    def test_instance_of_model_client(self):
        client = DashScopeClient(api_key="test")
        assert isinstance(client, ModelClient)
