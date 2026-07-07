from app.core.tool.decorator import tool


@tool(
    name="web_search",
    description="Search the web for real-time information. Use when you need latest news, data, or knowledge not in the local database.",
    parameters={
        "query": {"type": "string", "description": "Search keywords", "required": True},
    },
)
async def web_search(query: str) -> str:
    """Search the web via external search API."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "http://localhost:8080/search",
                params={"format": "json", "q": query},
                headers={"User-Agent": "Agent-Platform/1.0"},
            )
            if response.status_code != 200:
                return f"Search service returned status {response.status_code}"
            data = response.json()
            results = data.get("results", [])
            if not results:
                return "No search results found."
            output = []
            for i, r in enumerate(results[:5], 1):
                title = r.get("title", "Untitled")
                content = r.get("content", "")
                url = r.get("url", "")
                output.append(f"{i}. {title}")
                if content:
                    output.append(f"   {content}")
                if url:
                    output.append(f"   Source: {url}")
            return "\n".join(output)
    except ImportError:
        return "Web search unavailable: httpx not installed"
    except Exception as e:
        return f"Web search unavailable: {e}"
