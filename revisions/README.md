# Specification changes

This directory preserves open and accepted specification decisions. The generated v0.2
specification remains the statement of the packet contract; this guide is the current owner of
material revision procedure.

## Lifecycle

| status | location | the document |
|---|---|---|
| Open | [`changes/`](changes/) | Exploratory and non-authoritative. States the problem, evidence, alternatives, a preferred direction and the questions to answer. |
| Ready | [`changes/`](changes/) | Has answered its questions and states candidate normative text, still non-authoritative and unnumbered. |
| Accepted | [`accepted/`](accepted/) | Historical decision record for a change incorporated into its current owner. |

A change keeps one document from Open to Accepted, edited in place. An accepted revision records
why a change was made. It does not override the current generated specification or process guide.
An Open or Ready document changes no current rule.

## Starting or reviewing a change

Read the complete [specification-change process](CONTRIBUTING.md) before authoring or appraising a
change. Start a change from the [change template](templates/change.md).

Acceptance requires the reviewer's explicit authorization. Acceptance and incorporation into the
applicable current owner occur as one reviewable change; the accepted record is then stored under
[`accepted/`](accepted/), with clause evidence under [`evidence/`](evidence/).

[`ROADMAP.md`](ROADMAP.md) coordinates the v0.2 reconciliation: the anticipated changes and their
dependencies. It is not a change document and has no authority.

Whole-project reviews that fed the roadmap are kept in [`reviews/`](reviews/), named by review
date. [`baseline-v0.1/`](baseline-v0.1/) holds the frozen v0.1 specification the current one was
compiled from, which the earliest accepted records cite. Like accepted records, both are history and
are not updated as the project changes.

The [templates](templates/) describe each authored document. The [changes](changes/) directory
describes how its contents are ordered.
