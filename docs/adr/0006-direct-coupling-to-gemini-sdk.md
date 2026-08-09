# ADR-0006 — Direct Coupling to the Gemini SDK (No Port/Adapter)

**Status:** Accepted — current state, explicit reopen criterion
**Date:** 2026-08-09
**Deciders:** Pablo Felipe

---

## Context

`GeminiService` (`app/gemini_service.py`) imports `google.generativeai as
genai` directly and calls `genai.configure(api_key=...)` /
`genai.GenerativeModel("gemini-2.5-flash")` in its constructor. All four
methods (`identify_country_context`, `validate_intent`, `rerank_results`,
`generate_analysis`) call `self.model.generate_content` directly — there is
no port/interface the domain code depends on instead. `FiscalRagService`
constructs `GeminiService(settings.gemini_api_key)` directly in
`handle_fiscal_search` (`app/fiscal_rag_service.py:223`), reading the
maintainer's own key from `.env` via `app/core/config.py`.

Introducing a port/adapter layer (a provider-agnostic client protocol, a
generic adapter holding the prompt-building logic, and a factory resolving
"which provider" at runtime) is the standard way to decouple domain logic
from a specific LLM SDK. The question worth deciding explicitly is whether
that indirection is justified here, today, or whether it would be added
ahead of any concrete need.

## Decision

**Do not introduce a port/adapter layer for the LLM integration yet.** Keep
the direct Gemini SDK coupling for the current scope.

Two conditions would make that indirection pay for itself, and neither
holds today:

1. **A second concrete implementation to abstract over.** There is exactly
   one LLM provider in this codebase (Gemini). A protocol/interface with a
   single implementation adds a layer of indirection with no actual
   variation behind it — every call site would still resolve to the same
   `GeminiClient`-shaped object, just reached through one more hop.
2. **A reason the credential needs to be scoped per request rather than
   read once at startup.** `ai-fiscal-rag` runs locally; `GEMINI_API_KEY` is
   read once from `.env` for the maintainer's own use. Nothing here serves
   traffic from users other than the maintainer, so there is no scenario
   where a shared, statically-configured credential is the wrong shape.

Absent both, the port/adapter layer would be built to satisfy a
requirement that doesn't exist yet, on the assumption that it eventually
will.

## Alternatives Considered

- **Introduce the port/adapter layer now, ahead of need.** Rejected: it
  would add a protocol, an adapter, and a factory for exactly one concrete
  implementation and zero forcing use case. The cost is not hypothetical —
  every new `GeminiService` method would need to be threaded through an
  extra interface boundary, for a flexibility (swapping providers,
  per-request credentials) nothing in this project currently exercises.
- **Say nothing / leave the question open.** Rejected: the direct coupling
  is itself a real architectural choice with real consequences (see below),
  and leaving it undocumented would just mean revisiting the same analysis
  from scratch the next time it comes up.

## Consequences

- `GeminiService`'s constructor and all four call sites remain hard-wired to
  `genai.GenerativeModel`. Adding a second provider, or a per-request
  bring-your-own-key capability, later requires extracting a client
  interface and a generic adapter out of the current prompt-building/parsing
  code — this ADR does not do that work, it only names the two conditions
  under which it would become worth doing.
- **Explicit reopen criterion**: revisit this decision if either becomes
  true — (a) this project takes on a public-deployment goal where traffic
  from users other than the maintainer would otherwise spend the
  maintainer's own Gemini budget, or (b) a second LLM provider is actually
  needed. Absent either, the current direct coupling is the simpler,
  correct choice for this project's scope.
