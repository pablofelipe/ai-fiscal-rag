# ADR-0008 — MCP Server Over Stdio

**Status:** Accepted — implemented
**Date:** 2026-08-18
**Deciders:** Pablo Felipe

---

## Context

The RAG pipeline (`FiscalRagService.handle_fiscal_search`,
`app/fiscal_rag_service.py`) was only reachable through the FastAPI HTTP
endpoint (`GET /fiscal_search`, `app/main.py`). Local MCP clients (Claude
Desktop, Claude Code) cannot call an arbitrary HTTP endpoint directly — they
need a process speaking the MCP protocol, most simply over stdio for a
local, single-user integration.

The scope was pre-declared in the README before implementation (see prior
"Roadmap" entry, now removed): one tool wrapping the existing
`question`/`country`/`session_id` inputs and returning the existing
`FiscalResponse`, no new retrieval or LLM logic.

## Decision

Add `app/mcp_server.py`, a thin MCP server exposing a single tool,
`fiscal_search`, that calls `FiscalRagService.handle_fiscal_search` and
returns its result unchanged (dict passthrough for error paths, or
`{"message": "Analysis complete", "result": ...}` for a successful
`FiscalResponse`, mirroring `app/main.py`'s HTTP handler exactly).

The `mcp` SDK's server construct in the installed version (`mcp==2.0.0`) is
`MCPServer` (`mcp.server.MCPServer`) with `Context`
(`mcp.server.mcpserver.Context`) — the SDK renamed `FastMCP`/
`mcp.server.fastmcp` to this shape at some point after the tutorials most
commonly found online were written; **pin to `mcp==2.0.0`'s actual API, not
to `FastMCP` examples**, if this file is touched again.

Startup ingestion is handled the same way as the FastAPI app: an
`asynccontextmanager` lifespan constructs `FiscalRagService()` and awaits
`ingest_data()` before the server accepts tool calls, storing the service on
an `AppContext` dataclass reachable via
`ctx.request_context.lifespan_context.service` inside the tool function.

Run with `poetry run python -m app.mcp_server`.

## Alternatives Considered

- **HTTP transport (SSE/streamable-http) instead of stdio.** Rejected for
  now: this project has no public-deployment goal (ADR-0006), and stdio is
  the standard shape for a local MCP client (Claude Desktop/Code) launching
  a subprocess it owns — no port to bind, no auth to configure. Revisit if
  the "no public deployment" premise ever changes, same reopen criterion as
  ADR-0006.
- **Add new agentic/tool logic in the MCP layer** (e.g. multiple tools,
  server-side reasoning about which tool to call). Rejected: out of the
  declared scope. The MCP server is a transport-level integration point,
  not a place to grow new pipeline behavior — that belongs in
  `FiscalRagService` itself, where it is testable independent of any
  transport.
- **Share one `FiscalRagService` instance between the FastAPI app and the
  MCP server** (e.g. via a module-level singleton). Rejected: the two are
  separate processes in normal use (`uvicorn` for HTTP, a client-launched
  subprocess for MCP), each ingesting Treasury data independently on
  startup — consistent with the existing local, single-user scope. Revisit
  only if running both from one process becomes an actual requirement.

## Consequences

- A new dependency, `mcp` (`>=2.0.0,<3.0.0`), added to `pyproject.toml`.
- Two independent entry points now construct `FiscalRagService` and ingest
  Treasury data on startup: `app/main.py` (HTTP) and `app/mcp_server.py`
  (stdio). They do not share state or a ChromaDB instance; each ingest is a
  fresh in-memory `chromadb.Client()` per `FiscalRagService.__init__`.
- `tests/test_mcp_server.py` covers the tool function's dict-passthrough and
  `FiscalResponse`-wrapping behavior with a mocked service, the same pattern
  as `tests/test_fiscal_rag_service.py` — it does not exercise the real
  stdio transport or a live `FiscalRagService` (that would require Treasury
  network access and Gemini credentials, out of scope for a fast unit test).
