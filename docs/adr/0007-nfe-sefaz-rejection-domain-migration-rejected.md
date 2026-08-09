# ADR-0007 — NF-e/SEFAZ Rejection-Code Domain Migration Rejected — Evaluated, Not Pursued

**Status:** Rejected — evaluated, not shipped
**Date:** 2026-08-09
**Deciders:** Pablo Felipe

---

## Context

Prior planning (outside this ADR series) proposed evolving `ai-fiscal-rag`
from its current domain — U.S. Treasury exchange-rate lookup — into a
diagnostic agent for NF-e/NFC-e rejection messages returned by SEFAZ, on the
premise that this would close a real portfolio gap: no existing project in
the portfolio demonstrates genuine multi-step, branch-on-intermediate-result
agentic behavior, only single-shot retrieve→generate pipelines. ADR-0001 and
ADR-0002 (this series) both carry forward-looking notes assuming this
migration as already-planned, ahead of it ever being evaluated as a
standalone decision.

Two rounds of scrutiny changed the picture:

1. **Timing risk in the proposed data source.** The obvious public source —
   the Manual de Orientação do Contribuinte (MOC) v7.00 (2020) on the
   national NF-e portal — predates Brazil's consumption tax reform
   (EC 132/2023, LC 214/2025). Mandatory emission with the new IBS/CBS/IS
   field groups (Nota Técnica 2025.002) took effect **2026-08-03**, six days
   before this ADR — during the exact window this decision was being made.
   A static, pre-reform rejection-code table would already be incomplete for
   part of the domain it claims to cover.
2. **The core "agentic" premise did not survive checking real rejection
   messages.** The working hypothesis was that diagnosing a SEFAZ rejection
   requires multi-step reasoning: identifying which of several plausible
   causes applies, retrieving guidance, proposing a fix, and validating it —
   a genuine branch-on-intermediate-result loop, not a fixed pipeline.
   Checking actual `cStat`/`xMotivo` text against this hypothesis showed the
   opposite for most of the codes with real diagnostic content:
   - Value-mismatch codes (531–538, 564, 610 — e.g. "Total do ICMS difere do
     somatório dos itens") are **fully deterministic**: the correct action is
     recomputing a sum and comparing, which needs no LLM judgment at all.
   - CFOP/CST-direction codes (518–523, 590/591, 233) are equally
     deterministic: a fixed compatibility rule against fields already present
     in the rejected XML.
   - SEFAZ's rejection messages are precise by design (the validator stops
     and reports a specific rule violation), not vague — there was no
     evidence of the kind of genuine multiple-plausible-cause ambiguity that
     would justify an LLM iterating over hypotheses.
   - The one real branch found — codes depending on external registry state
     not present in the document at all (301 "Uso Denegado", 302 "IE do
     destinatário não habilitada", 501 "IE do emitente não cadastrada") —
     is narrow: a router deciding "this is externally-verifiable, not
     document-resolvable" plus an honest "cannot be answered from this input
     alone" response. Real, but small.

A broader alternative — ten "operational fiscal agent" concepts (regulatory
monitoring, impact analysis, tax-engine explainability, tax regression
testing, configuration validation, etc.), proposed independently — was also
evaluated and rejected as a *replacement* direction: nearly all of them
require proprietary inputs (a real company's ERP/tax-engine internals,
source code, transactional volume, or audit outcomes) that are unavailable
for a solo public-data portfolio project, and several would only be
buildable at meaningful fidelity by drawing on the author's employer
experience — directly conflicting with this project's own established
constraint of exposing no proprietary information (the same principle that
led to using the public TIPI table, not a proprietary product catalog, in
the `ncm-classifier-ai` project referenced in earlier planning). Of the ten,
only a narrowly-scoped CFOP×CST configuration-compatibility checker was
judged buildable on public data alone — but it reduces to the same
deterministic-lookup shape found above, not a new source of genuine agentic
behavior.

## Decision

**Do not migrate `ai-fiscal-rag`'s domain to NF-e/SEFAZ rejection-code
diagnosis.** The pipeline stays on its current domain (U.S. Treasury
exchange-rate data) pending a separate decision on the project's future
direction.

The deciding factor was not data availability or reform timing alone — both
were real complications, but solvable ones (a narrower, curated code set;
picking a still-current source) — it was that the central justification for
the migration, a genuine agentic loop, did not hold up once checked against
real rejection message text. What remained after that check was a small,
mostly-deterministic routing task dressed in agent framing, which is not
worth the implementation effort for the differentiation it would deliver.

## Alternatives Considered

- **Proceed with the full NF-e/SEFAZ migration as originally planned.**
  Rejected on the evidence above: the "agentic loop" motivating the
  migration does not exist for most of the domain's rejection codes.
- **Scope down to only the CFOP×CST configuration-compatibility checker.**
  Rejected: still a deterministic lookup with no LLM judgment required for
  the diagnosis itself; would not close the agentic-behavior gap it was
  meant to address, and offers no meaningfully different portfolio signal
  than the existing pipeline already provides.
- **Adopt one of the ten proprietary-leaning "operational fiscal agent"
  concepts instead.** Rejected: nearly all require inputs (real ERP/tax
  engine internals, transactional data, audit outcomes) unavailable without
  drawing on proprietary employer knowledge, which this project has
  committed not to expose.

## Consequences

- The six Fase-0 ADRs already written (0001–0006) remain valid — they
  document the current Treasury-domain pipeline's real, shipped decisions
  and are unaffected by this rejection.
- ADR-0001 and ADR-0002's references to a "planned domain migration to
  NF-e/SEFAZ rejection codes" are corrected by this ADR: that migration is
  not planned, it was evaluated and rejected.
- The underlying goal that motivated this exploration — closing the
  portfolio's gap in demonstrated multi-step, branch-on-intermediate-result
  agentic behavior — remains open. This ADR closes only the specific NF-e/
  SEFAZ direction, not that goal; a future direction is undecided and out of
  scope here.
- Prior planning notes describing Fases 1–4 of the NF-e/SEFAZ migration are
  superseded by this decision. They are kept as a historical record of the
  reasoning that led here, not as an active roadmap.
- **Reopen criterion**: revisit only if a concrete source of genuine,
  document-unresolvable ambiguity is found in a fiscal domain accessible via
  public data — the specific failure mode here was the absence of that
  ambiguity in NF-e/SEFAZ rejection messages, not a general rejection of the
  domain or of agentic framing itself.
