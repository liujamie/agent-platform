from app.core.tool.decorator import tool


@tool(
    name="rag_query",
    description="Query the knowledge base (RAG) for information related to uploaded documents.",
    parameters={
        "query": {"type": "string", "description": "Search query", "required": True},
    },
)
async def rag_query(query: str) -> str:
    """Query vector store for relevant documents."""
    return f"RAG query for '{query}' — vector store not configured. Integrate Milvus/Chroma to enable."
