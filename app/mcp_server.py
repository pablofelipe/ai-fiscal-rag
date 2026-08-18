"""MCP server exposing the fiscal RAG pipeline as a tool over stdio.

Local, maintainer-only integration point (see ADR-0006) — no new retrieval
or LLM logic, just a thin wrapper around FiscalRagService.handle_fiscal_search.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from app.fiscal_rag_service import FiscalRagService


@dataclass
class AppContext:
    service: FiscalRagService


@asynccontextmanager
async def lifespan(_server: MCPServer) -> AsyncIterator[AppContext]:
    service = FiscalRagService()
    await service.ingest_data()
    yield AppContext(service=service)


mcp = MCPServer("ai-fiscal-rag", lifespan=lifespan)


@mcp.tool()
async def fiscal_search(
    ctx: Context,
    question: str,
    country: str = "",
    session_id: str = "default",
) -> dict[str, Any]:
    """Answer a fiscal or exchange-rate question via the RAG pipeline."""
    service = ctx.request_context.lifespan_context.service
    result = await service.handle_fiscal_search(question, country, session_id)

    if isinstance(result, dict):
        return result

    return {"message": "Analysis complete", "result": result.model_dump()}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
