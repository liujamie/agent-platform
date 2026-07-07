from typing import AsyncIterator
from openai import AsyncOpenAI

from app.model.base import ModelClient, ModelResult


class OpenAIClient(ModelClient):
    """OpenAI-compatible model client (works with DeepSeek, OpenAI, etc.)."""

    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

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
