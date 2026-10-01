# Specification changes

This directory preserves proposed, candidate, and accepted specification and revision-process
decisions. The generated v0.2 specification remains the statement of the packet contract; this
guide is the current owner of material revision procedure.

## Lifecycle

| stage | location | status |
|---|---|---|
| proposal | [`proposals/`](proposals/) | Exploratory and non-authoritative. Establishes the problem, evidence, alternatives, and scope. |
| revision draft | [`drafts/`](drafts/) | Candidate normative text, still non-authoritative and unnumbered. |
| accepted revision | [`accepted/`](accepted/) | Historical decision record for a change incorporated into its current owner. |

An accepted revision records why a change was made. It does not override the current generated
specification or process guide. A proposal or draft changes no current rule.

## Starting or reviewing a change

Read the complete [specification-change process](CONTRIBUTING.md) before authoring or appraising a
change. Begin uncertain or exploratory work from the [proposal template](templates/proposal.md).
Use the [draft template](templates/draft.md) only after the problem, scope, and intended direction
are settled.

Acceptance requires explicit authorization. Acceptance and incorporation into the applicable
current owner occur as one reviewable change; the accepted record is then stored under
[`accepted/`](accepted/), with clause evidence under [`evidence/`](evidence/).

Whole-project reviews that fed the roadmap are kept in [`reviews/`](reviews/), named by review
date. [`baseline-v0.1/`](baseline-v0.1/) holds the frozen v0.1 specification the current one was
compiled from, which the earliest accepted records cite. Like accepted records, both are history and
are not updated as the project changes.

The [templates](templates/) describe each authored artifact. The proposal and draft directories
describe how their own contents are maintained.
