# ADR-0003 — Confidence-Gated Automation Lives in n8n, Not in the API

**Status:** Accepted — for now, with a committed reopen point
**Date:** 2026-08-09
**Deciders:** Pablo Felipe

---

## Context

`FiscalResponse.confidence` (`app/fiscal_response.py`) is a `0.0`–`1.0` float
produced by `generate_analysis`. Nothing in `app/fiscal_rag_service.py` or
`app/main.py` reads or thresholds this value — `/fiscal_search` always
returns the full `FiscalResponse` regardless of confidence. The threshold
decision lives entirely in `n8n/workflow-n8n-triagem-fiscal.json`: an `If`
node compares `confidence >= 0.7 AND no error_code` and routes to one of two
Gmail reply nodes (auto-reply vs. "human intervention required"), per
`n8n/README.md`.

This was flagged in project planning notes as needing an explicit decision:
conscious design or debt to fix.

## Decision

**Accepted for the current scope**, not treated as an oversight to fix
immediately — but explicitly not the final shape either.

Today there is exactly one signal to gate on (`confidence`), and exactly one
consumer of the API (the n8n workflow). Putting the threshold in n8n rather
than in Python means:

- The API stays a plain data producer — any consumer (n8n, a future web UI,
  a script) can apply its own threshold without a Python code change.
- There is no second gating signal yet — a planned deterministic
  verification gate would require combining two signals, something an `If`
  node alone cannot do, since it only sees fields already present in the
  HTTP response.

This is *not* the same claim as "gating belongs in orchestration
permanently." It is scoped to the current single-signal state.

## Alternatives Considered

- **Move the threshold into the API now.** Rejected for this phase: with
  only `confidence` to gate on, moving the comparison into Python would just
  relocate a single `>= 0.7` check without adding any capability n8n's `If`
  node doesn't already have — duplicating a constant across two systems
  (JSON workflow + Python) with no functional gain yet.

## Consequences

- The `0.7` threshold is embedded in n8n workflow JSON, not in version-
  controlled, tested Python code — no unit test coverage, no diff visibility
  in code review, no single source of truth if a second consumer picks a
  different number.
- **Committed reopen point, not open-ended**: project planning already
  commits to moving this decision into the API once the deterministic
  verification gate exists, combining **two**
  signals — LLM `confidence` *and* the deterministic check's result — which
  an n8n `If` node cannot do on its own. At that point this ADR should be
  superseded, not amended.
- Until then, this is accepted technical debt with a named trigger for
  paying it down, not a permanent architectural stance.
