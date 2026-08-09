# ADR-0005 — In-Memory, Non-Persistent Session Memory

**Status:** Accepted — trade-off, not a gap
**Date:** 2026-08-09
**Deciders:** Pablo Felipe

---

## Context

`MemoryService` (`app/memory_service.py`) keeps a
`dict[str, list[dict[str, str]]]` (`defaultdict(list)`) in process memory,
keyed by `session_id`, capped at the last 5 messages per session
(`limit: int = 5`, FIFO eviction via `pop(0)`). There is no database, cache,
or file backing it. `FiscalRagService` owns one `MemoryService` instance for
the lifetime of the process (`app/fiscal_rag_service.py:83`).

## Decision

Keep session memory in-process and non-persistent. This is a deliberate
scope decision for the project's current form (single FastAPI/uvicorn
process, portfolio/demo-scale traffic), not an oversight to be fixed later
by default.

## Alternatives Considered

- **Redis- or database-backed session store.** Rejected for now: there is no
  evidence of a need beyond single-process, single-instance operation, and
  introducing an external dependency ahead of a proven requirement adds
  operational surface (a new credential, a new failure mode) without a
  corresponding capability gain today — the same reasoning ADR-0006 applies
  to not adding a port/adapter layer ahead of a concrete need.

## Consequences

- Conversation history resets on every process restart — a follow-up
  question sent after a restart loses prior turns for that `session_id`.
- `MemoryService` is a plain instance attribute, not shared external state.
  A multi-worker or multi-instance deployment (e.g. `uvicorn --workers N`,
  or multiple replicas behind a load balancer) would fragment a single
  session's history across workers with no coordination — acceptable for
  the current single-process dev/demo deployment, but a concrete blocker to
  flag before any horizontally-scaled production deployment.
- No data-retention or privacy-cleanup logic is needed today, since nothing
  survives past process lifetime — revisit if persistence is ever added.
