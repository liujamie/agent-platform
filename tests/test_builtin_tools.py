"""tests/test_builtin_tools.py"""
import pytest
from app.tools.current_time import current_time


class TestCurrentTimeTool:
    @pytest.mark.asyncio
    async def test_current_time_default(self):
        result = await current_time()
        assert len(result) == 19  # YYYY-MM-DD HH:MM:SS

    @pytest.mark.asyncio
    async def test_current_time_date(self):
        result = await current_time(format="date")
        assert len(result) == 10  # YYYY-MM-DD

    @pytest.mark.asyncio
    async def test_current_time_time(self):
        result = await current_time(format="time")
        assert len(result) == 8  # HH:MM:SS
