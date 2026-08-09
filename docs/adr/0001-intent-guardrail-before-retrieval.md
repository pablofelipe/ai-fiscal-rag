# ADR-0001 — Intent Guardrail Before Retrieval

**Status:** Accepted — ships
**Date:** 2026-08-09
**Deciders:** Pablo Felipe

---

## Context

`FiscalRagService.handle_fiscal_search` (`app/fiscal_rag_service.py`) runs a
fixed pipeline: readiness/config checks → **intent guardrail** → country
resolution → ChromaDB retrieval → LLM re-rank → structured generation. The
guardrail is `GeminiService.validate_intent(question)`
(`app/gemini_service.py:52-64`) — a single Gemini call that answers
"YES"/"NO" to whether the question relates to exchange rates, fiscal/tax
matters, or U.S. Treasury data. It runs immediately after the
`_data_ready`/`GEMINI_API_KEY` guards, **before** country identification,
before the embedding + ChromaDB query, before the re-rank Gemini call, and
before the `generate_analysis` Gemini call.

When the guardrail returns `False`, `handle_fiscal_search` short-circuits
with `error_code="OUT_OF_SCOPE"`, `confidence=1.0`, and logs
`audit_logger.warning("BLOCKED INTENT | Question: %s", question)`. No
retrieval, re-rank, or generation call happens for rejected questions.

## Decision

Run the intent guardrail as the **first LLM step**, ahead of every other
pipeline stage, and treat a rejection as a terminal, confidently-labeled
response rather than letting the question flow into retrieval/generation.

- The guardrail costs exactly one Gemini call per request, whether the
  question is accepted or rejected.
- A rejection is `confidence=1.0` — the guardrail is *certain* the question
  is out of scope, not merely unable to answer it.
- Rejections are audit-logged at `WARNING`, distinct from the `INFO`-level
  query lifecycle logs, so off-topic traffic is visible without reading
  every request.

## Alternatives Considered

- **No guardrail — let every question reach retrieval and generation.**
  Rejected: an off-topic question would still spend an embedding call, a
  ChromaDB query, a re-rank Gemini call, and a `generate_analysis` Gemini
  call, only to have the final prompt improvise a "this isn't fiscal" answer
  in free text instead of a distinct, gated `error_code`.
- **Gate after retrieval, at the generation step only.** Rejected: retrieval
  (embedding + ChromaDB query) and re-rank (one Gemini call) would still run
  for every off-topic question — the guardrail's entire value is not doing
  that work, not just labeling the final answer correctly.
- **Non-LLM guardrail (keyword/regex match).** Rejected: fiscal/exchange-rate
  questions arrive in free-form natural language, often mixing PT-BR and
  English, and don't reduce reliably to a keyword list without a high
  false-negative rate. The domain needs semantic judgment, which is cheap to
  get from one LLM call relative to the three calls it can save downstream.

## Consequences

- Adds one Gemini call of latency to every request, including ones that pass
  the gate — accepted because it is cheaper than the up-to-three downstream
  calls (embedding/retrieval doesn't call Gemini, but re-rank and generation
  do) it avoids for rejected questions.
- `validate_intent`'s prompt (`app/gemini_service.py:52-64`) is hardcoded to
  "exchange rates ... fiscal, tax, or economic matters ... U.S. Treasury
  data." A migration to a different fiscal domain was evaluated and
  rejected (ADR-0007); the pipeline stays on the Treasury domain for now,
  so this prompt is not scheduled to change.
- A rejected question and a low-confidence in-scope answer are both surfaced
  through the same `confidence` field to any caller that doesn't also check
  `error_code`. The n8n workflow's `If` node (see ADR-0003) currently only
  checks `confidence >= 0.7`, so an `OUT_OF_SCOPE` rejection (`confidence
  = 1.0`) and a genuinely confident in-scope answer both route to the
  auto-reply branch today — a pre-existing gap in that node's condition,
  not introduced by this guardrail, but worth tightening when Fase 2/4 moves
  gating logic into the API.
