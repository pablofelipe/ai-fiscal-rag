# ADR-0004 — Human-in-the-Loop as an Explicit Workflow Branch

**Status:** Accepted — ships
**Date:** 2026-08-09
**Deciders:** Pablo Felipe

---

## Context

In `n8n/workflow-n8n-triagem-fiscal.json`, the `If` node described in
ADR-0003 has two outgoing branches, both wired to a Gmail reply node: the
`TRUE` branch (`confidence >= 0.7`, no error) replies with
`technical_analysis`; the `FALSE` branch replies with a fixed
"human intervention required" message (`n8n/README.md`, node
`Reply to a message1`). Both branches are first-class parts of the
workflow graph — there is no code path where a low-confidence or error
response falls through unhandled.

## Decision

Model the low-confidence/error case as an explicit, declared branch of the
automation graph — not as an exception, a dropped message, or a silent log
entry. Every request that reaches the `If` node produces exactly one of two
defined terminal actions: auto-reply or escalate-to-human.

## Alternatives Considered

- **No escalation branch — silently drop or only log low-confidence
  answers.** Rejected: unacceptable for a fiscal-compliance use case, where
  an autonomously sent wrong answer carries real cost and an unanswered
  email is itself a failure mode a human should see.
- **Escalation via a separate polling job over stored low-confidence rows.**
  Rejected: this would require a persistent store for pending escalations,
  which directly contradicts the accepted non-persistence trade-off in
  ADR-0005, in exchange for capability the synchronous `If`-branch reply
  already provides for email-based triage.

## Consequences

- Escalation correctness depends entirely on the n8n `If` node's condition
  staying in sync with `FiscalResponse`'s `confidence`/`error_code`
  fields — there is no compile-time or test-time check that a schema change
  in `app/fiscal_response.py` doesn't silently break the workflow's routing
  (the same underlying risk noted in ADR-0003).
- The human-reviewer reply is currently a fixed string ("human intervention
  required") and does not surface `technical_analysis`, partial findings, or
  the original question back to the reviewer — a possible improvement, out
  of scope for this ADR.
- This pattern (branch, not exception) is the concrete mechanism ADR-0003's
  confidence gate relies on: gating only has a defensible "or else" if the
  else-branch is itself a defined, reviewable action.
