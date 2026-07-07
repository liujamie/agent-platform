from typing import AsyncIterator
from openai import AsyncOpenAI

from app.model.base import ModelClient, ModelResult


class DashScopeClient(ModelClient):
    """Alibaba Cloud DashScope (Tongyi Qianwen) model client."""

    def __init__(self, api_key: str, model: str = "qwen-plus"):
        self.api_key = api_key
        self.model = model
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-api/v1",
        )

    async def invoke(self, messages: list[dict], model: str | None = None, tools: list | None = None) -> ModelResult:
        kwargs = {"model": model or self.model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        response = await self._client.chat.completions.create(**kwargs)
        return ModelResult(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage={
                "input": response.usage.prompt_tokens if response.usage else 0,
                "output": response.usage.completion_tokens if response.usage else 0,
            },
        )

    async def stream(self, messages: list[dict], model: str | None = None, tools: list | None = None) -> AsyncIterator[str]:
        kwargs = {"model": model or self.model, "messages": messages, "stream": True}
        if tools:
            kwargs["tools"] = tools
        response = await self._client.chat.completions.create(**kwargs)
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
