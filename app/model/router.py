from app.model.base import ModelClient


class ModelRouter:
    """Registry + router for multiple model providers."""

    def __init__(self):
        self._models: dict[str, ModelClient] = {}
        self._current: str | None = None

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
