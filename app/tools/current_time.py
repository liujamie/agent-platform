from datetime import datetime

from app.core.tool.decorator import tool


@tool(
    name="current_time",
    description="Get the current date and time",
    parameters={
        "format": {
            "type": "string",
            "description": "Output format: 'datetime', 'date', or 'time'",
        },
    },
)
async def current_time(format: str = "datetime") -> str:
    now = datetime.now()
    if format == "date":
        return now.strftime("%Y-%m-%d")
    elif format == "time":
        return now.strftime("%H:%M:%S")
    return now.strftime("%Y-%m-%d %H:%M:%S")
