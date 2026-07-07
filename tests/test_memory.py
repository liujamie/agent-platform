"""tests/test_memory.py"""
import pytest
from app.memory.base import BaseMemory
from app.memory.session import SessionMemory


class TestBaseMemory:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            BaseMemory()


class TestSessionMemory:
    def test_add_and_get_messages(self):
        mem = SessionMemory()
        mem.add_message("s1", {"role": "user", "content": "hello"})
        msgs = mem.get_messages("s1")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"

    def test_get_nonexistent_session(self):
        mem = SessionMemory()
        assert mem.get_messages("nonexistent") == []

    def test_multiple_sessions_isolated(self):
        mem = SessionMemory()
        mem.add_message("s1", {"role": "user", "content": "hello"})
        mem.add_message("s2", {"role": "user", "content": "world"})
        assert len(mem.get_messages("s1")) == 1
        assert len(mem.get_messages("s2")) == 1

    def test_window_limits_messages(self):
        mem = SessionMemory(window=3)
        for i in range(5):
            mem.add_message("s1", {"role": "user", "content": str(i)})
        msgs = mem.get_messages("s1")
        assert len(msgs) == 3

    def test_clear_session(self):
        mem = SessionMemory()
        mem.add_message("s1", {"role": "user", "content": "hello"})
        mem.clear("s1")
        assert mem.get_messages("s1") == []
