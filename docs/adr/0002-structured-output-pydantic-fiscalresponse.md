# ADR-0002 — Structured Output via Pydantic (`FiscalResponse`)

**Status:** Accepted — ships
**Date:** 2026-08-09
**Deciders:** Pablo Felipe

---

## Context

The final pipeline stage, `GeminiService.generate_analysis`
(`app/gemini_service.py:97-134`), calls Gemini with
`generation_config={"response_mime_type": "application/json",
"response_schema": FiscalResponse}` and parses the result with
`FiscalResponse.model_validate_json(...)`. `FiscalResponse`
(`app/fiscal_response.py`) declares six fields: `country`, `error_code`,
`technical_analysis`, `confidence`, `sources_used` (list of context IDs the
model cites), and `next_action`. Every early-exit branch in
`handle_fiscal_search` (data not ready, missing API key, out-of-scope,
country required, internal error) also returns a dict shaped to match this
same field set, even though those branches never call Gemini.

## Decision

Enforce Gemini's native structured-output schema (`response_schema`) against
the `FiscalResponse` Pydantic model, rather than parsing free text or hoping
the model's prose follows an implied format. `generate_analysis` is also
wrapped in `@retry(stop_after_attempt(3), wait_exponential(...))` via
`tenacity`, absorbing transient malformed-JSON or API errors without
surfacing them as request failures.

## Alternatives Considered

- **Free text + regex/manual extraction** of confidence, sources, or
  error codes from a prose answer. Rejected: fragile against any prompt or
  model-version drift, and gives no validation guarantee before the response
  leaves the service.
- **Function calling / tool use** to force structure. Rejected as
  unnecessary: Gemini's `response_schema` support already produces
  schema-validated JSON directly from a Pydantic model, with no extra
  indirection needed.

## Consequences

- `error_code` was already modeled as a free-form string with no fixed enum
  of values (`error_code: str = Field(description="Fiscal error code if
  identified; use empty string if none")`), not something Treasury-specific.
  It is currently always empty on the success path in production use. A
  migration to a domain that would have populated it (NF-e/SEFAZ rejection
  codes) was evaluated and rejected (ADR-0007); the field's generic shape
  means it stays ready for a different domain if one is chosen later,
  without a schema-breaking change.
- Validation and prompting are coupled: every prompt in `GeminiService`
  explicitly instructs Gemini to "respond strictly following the defined
  JSON schema" or to format specific fields (e.g. the `sources_used`
  citation instruction) — changing `FiscalResponse`'s fields means updating
  both the Pydantic model and the prose instructions that describe it to the
  model, since `response_schema` constrains shape but not the semantic
  content of each field.
- Early-exit error branches (data not ready, missing key, out of scope,
  country required, internal error) hand-build a dict with a matching shape
  instead of constructing a `FiscalResponse` instance directly — they never
  call Gemini, so there is nothing to validate, but the shape must be kept
  in sync by convention rather than by the type system.
