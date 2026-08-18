# Status

**Research / Experimental.** Runs locally, for the maintainer's own use
(see [ADR-0006](docs/adr/0006-direct-coupling-to-gemini-sdk.md)) — no public
deployment, no external users.

## What works today

- HTTP endpoint (`GET /fiscal_search`) and an MCP server over stdio
  (`app/mcp_server.py`, see [ADR-0008](docs/adr/0008-mcp-server-over-stdio.md))
  both wrap the same pipeline: intent guardrail → country resolution →
  ChromaDB retrieval → LLM re-rank → structured Gemini output.
- Confidence-gated human-in-the-loop, but implemented in the n8n workflow
  (`n8n/`), not in the API itself — see
  [ADR-0003](docs/adr/0003-confidence-gating-in-n8n-not-api.md).
- Session memory is in-process and non-persistent by design — see
  [ADR-0005](docs/adr/0005-in-memory-non-persistent-session-memory.md).
- 8 ADRs (`docs/adr/`) document the architecture as-built, including one
  rejected direction (NF-e/SEFAZ domain migration,
  [ADR-0007](docs/adr/0007-nfe-sefaz-rejection-domain-migration-rejected.md)).
- CI (`.github/workflows/ci.yml`) runs `ruff check` and `pytest` on every
  push/PR to `main`.

## Known limitations

- **Not agentic.** The pipeline is a fixed, single-pass sequence — no
  branching on intermediate results, no retry-with-different-strategy.
- **No formal eval suite.** There is no labeled dataset or accuracy
  regression gate (unlike `ncm-classifier-ai`'s eval pipeline). Correctness
  is currently checked only via unit tests with mocked LLM/retrieval calls.
- **Domain is U.S. Treasury exchange-rate data**, not Brazilian fiscal data
  — despite the project name and the `fiscal` topic, this is a currency Q&A
  demo, not a tax-calculation or tax-compliance system. See
  `docs/adr/0007-*` for why a fiscal-domain migration was evaluated and
  rejected.
- **Two independent ingest paths.** `app/main.py` (HTTP) and
  `app/mcp_server.py` (stdio) each construct their own `FiscalRagService`
  and re-ingest Treasury data into an in-memory ChromaDB client on startup —
  they share no state.
- **Single LLM provider, directly coupled.** `GeminiService` calls the
  `google.generativeai` SDK directly, no provider abstraction (ADR-0006).
  That SDK is now deprecated upstream in favor of `google.genai`; a
  migration is not yet scheduled.

## Not planned right now

Nothing is currently queued after the MCP server. See the ADRs above for
what was deliberately not built and why.
