# Specification changes

This directory preserves proposed, candidate, and accepted changes to the Escapewheel
specification. The generated v0.2 specification remains the statement of what currently holds;
these documents explain possible changes and the decisions that produced it.

## Lifecycle

| stage | location | status |
|---|---|---|
| proposal | [`proposals/`](proposals/) | Exploratory and non-authoritative. Establishes the problem, evidence, alternatives, and scope. |
| revision draft | [`drafts/`](drafts/) | Candidate normative text, still non-authoritative and unnumbered. |
| accepted revision | [`accepted/`](accepted/) | Historical decision record for a change incorporated into the specification. |

An accepted revision records why a change was made. It does not override the current generated
specification. A proposal or draft changes no conformance requirement.

## Starting or reviewing a change

Read the complete [specification-change process](CONTRIBUTING.md) before authoring or appraising a
change. Begin uncertain or exploratory work from the [proposal template](templates/proposal.md).
Use the [draft template](templates/draft.md) only after the problem, scope, and intended direction
are settled.

Acceptance requires explicit authorization. Acceptance and incorporation into the generated
specification occur as one reviewable change; the accepted record is then stored under
[`accepted/`](accepted/), with clause evidence under [`evidence/`](evidence/).

The [templates](templates/) describe each authored artifact. The proposal and draft directories
describe how their own contents are maintained.
