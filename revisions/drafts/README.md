# Drafts

A draft has no number. It gets one when the user accepts it, taken from the end of the accepted
range, so the numbered space reads in the order revisions were **applied** rather than the order
they were written. Nothing outside this directory may cite a draft by number, because it has none.

Why: an `R<N>` is permanent once accepted — `applied.toml` keys on it, `build.py` stamps it into
every column's `since`, the registry's `derived_from` lists it, and the compiled spec cites it. A
number assigned at drafting time forces the application order to match the drafting order, and
renumbering later would break all four.

A draft cites another draft by its file name in backticks. At acceptance those citations become
`R<N> §<x>`, which is a step in the acceptance sequence in `../CLAUDE.md`.

## Application order

Dependencies run downward: a draft may depend on the ones above it and on nothing below.

| # | draft | words | appraised | why here |
|---|---|---|---|---|
| 1 | `a-writer-requires-no-knowledge-of-a-particular-source` | 1,355 | appraised 2026-09-11 | rests on R63 §2.1's `PRODUCES` and R87 §2.2's `STATES` as the shape a declaration takes |
| 2 | `an-adapters-rows-cross-a-process-boundary` | 2,925 | not since the split | takes R109 §2.3's argument about a dependency closure and applies it to an adapter, and amends R109's own clauses in Part 05 §3.7 and Part 09 §5.7 |

Each cites a part for every requirement it states, which R112 §3.1 requires of a Decision.

**#1 replaces `an-extension-declares-the-core-it-was-authored-against`,** which was appraised and
found to name a real defect its instrument could not reach. That draft had an extension declare the
`registry_version` it was authored against; the disagreement it was recording is computable from
the registry a packet already embeds, and its §3.2 reported rather than refused, so the field
changed nothing. The defect stands: Part 02 §7 requires a reference to relate columns of the same
role and the same identity and says nothing of their type, `registry/check.py` follows that
exactly, and R53 §2.1 turning `unit_id` from `string` to `int32` would have left an extension still
declaring `string` passing every check there is. #1 states the type instead. The withdrawn draft is
in git history at `32288d0`.

**What stands between the other two and acceptance is the pre-acceptance checks** in
`../CLAUDE.md`, which neither has been through in its current form. #2 and #3 were appraised as one
document forty minutes before they were split, so each now carries a Scope, a Consequence and a
status table that no appraisal has read; #1 has not been appraised at all. Every number in all
three is measured against a registry that has moved since — R112 and R113 were accepted after they
were written — and re-measuring is the first of those checks.

**#1 and #2 were one draft and were split at 3,801 words.** They amend disjoint sections and neither
depends on the other: #1 says what a build learns *about* a source, #2 says how a source's rows reach
it. Both touch Part 05 §3 by appending, which renumbers nothing either way.

**None moves a count in the generated block.** No core table, column, reference, rule or vocabulary
changes. Every number in each is measured against the parts, the registries and the three
distributions as they stood when it was drafted and is re-measured at acceptance, which the
pre-acceptance checks in `../CLAUDE.md` require anyway.
