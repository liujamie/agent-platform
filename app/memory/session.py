from collections import defaultdict
from app.memory.base import BaseMemory


class SessionMemory(BaseMemory):
    """In-memory session storage with sliding window."""

    def __init__(self, window: int = 20):
        self._store: dict[str, list[dict]] = defaultdict(list)
        self.window = window

    def add_message(self, session_id: str, message: dict) -> None:
        self._store[session_id].append(message)
        if len(self._store[session_id]) > self.window:
            self._store[session_id] = self._store[session_id][-self.window:]

    def get_messages(self, session_id: str) -> list[dict]:
        return list(self._store.get(session_id, []))

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)
