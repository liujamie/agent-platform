from app.model.base import ModelClient, ModelResult


class ModelRouter:
    """Registry + router for multiple model providers."""

    def __init__(self):
        self._models: dict[str, ModelClient] = {}
        self._current: str | None = None
        self._fallback_chain: list[str] = []

    def register(self, name: str, client: ModelClient) -> None:
        self._models[name] = client

    def get(self, name: str) -> ModelClient | None:
        return self._models.get(name)

    def list_models(self) -> list[str]:
        return list(self._models.keys())

    def switch_to(self, name: str) -> None:
        if name in self._models:
            self._current = name

    @property
    def current(self) -> str | None:
        return self._current

    @property
    def current_client(self) -> ModelClient | None:
        if self._current:
            return self._models.get(self._current)
        return None

    @property
    def fallback_chain(self) -> list[str]:
        return self._fallback_chain

    @fallback_chain.setter
    def fallback_chain(self, chain: list[str]) -> None:
        self._fallback_chain = chain

    async def invoke_with_fallback(
        self, messages: list[dict], tools: list | None = None, depth: int = 0
    ) -> ModelResult:
        if depth >= len(self._fallback_chain):
            raise RuntimeError(f"All fallback models exhausted ({len(self._fallback_chain)} tried)")

        model_name = self._fallback_chain[depth]
        client = self._models.get(model_name)
        if client is None:
            return await self.invoke_with_fallback(messages, tools, depth + 1)

        try:
            return await client.invoke(messages, model=model_name, tools=tools)
        except Exception:
            return await self.invoke_with_fallback(messages, tools, depth + 1)
