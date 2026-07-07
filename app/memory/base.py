from abc import ABC, abstractmethod


class BaseMemory(ABC):
    @abstractmethod
    def add_message(self, session_id: str, message: dict) -> None:
        ...

    @abstractmethod
    def get_messages(self, session_id: str) -> list[dict]:
        ...
