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
| 1 | `a-writer-requires-no-knowledge-of-a-particular-source` | 1,870 | appraised 2026-09-11, re-checked after the rewrite | rests on R63 §2.1's `PRODUCES` and R87 §2.2's `STATES` as the shape a declaration takes |
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

**#1 and #2 were one draft and were split at 3,801 words**, and the split is where they stopped
being read against each other. They are not disjoint. #1 §3.1 closes the list of what a build
supplies an adapter — an object store for the root, the session's reference clock, the first sample
of each stream — and a build supplies the first of those as a live `SourceStore` handed to a
constructor. #2 §3.3 makes **out of process the default**, where §3.2 gives an adapter an argument
list and §3.5 has even an identifier cross as a name. Under both, the ordinary adapter cannot be
given three of the five things #1 says a build supplies it.

**The array crossing is settled in #2 §3.6: an array crosses as a reference.** An adapter writes it
and returns the identifier, the layout it chose and a location. The build names that location and it
is **in staging**, so the array is written once and nothing moves it again but the rename Part 05 §6
already performs at commit; for an array the packet references rather than owns, the build supplies
none and the adapter returns the URI its source already has. `conformance/adapter-boundary/`
measured why: `StagedArray` carries `values, array_asset_id, chunks, shard, codecs, fill_value` and
**five of the six cross already**, so returning those five beside a location is the whole change.
`lfp` needs none of it — `external_arrays` is already that shape, which is R14's external resource.

**Two questions remain open on #2, and both are about the contract rather than a clause.**

*Settled: a transport is a protocol, and protocols come in groups.* A profile names a group for
each way an adapter reaches a build. An adapter **MUST** support at least one protocol in a group;
a build **MUST** support every protocol in every group the profile names.
`escapewheel-portable-v0.1` names one group, out of process, holding `files` and `stream`. The
asymmetry is deliberate: there is one build and there will be many adapters, so the build carries
breadth once and an adapter author implements the one protocol that suits the source in hand and
never both. No negotiation can fail. Adding a protocol costs every build work and no adapter
anything, and adding a group leaves both alone, which is where a version would otherwise have to
go.

*Settled: how many resources cross one stream.* An Arrow IPC stream carries one schema and an
adapter returns thirteen resources on the NWB fixture. Streams concatenate — each ends with an
end-of-stream marker — and the resource identifier rides in the schema's key-value metadata, so
nothing is framed that Arrow does not frame. `conformance/adapter-boundary/` sends three resources
with three schemas over a real pipe and reads all three back.

**The two land together.** #2 §3.6 has a build supply a location, so #1's closed list carries it,
and #1's list was written around the three store-handed adapters — `nwb`, `waveforms`, `lfp` — which
are the three that read big binary and the three the array answer decides.

`conformance/adapter-boundary/` is the evidence, and #1 carries what it settled: a build passes a
collection as records rather than as a mapping. Measured, the units handed the waveform adapter are
keyed by a pair and refuse to serialise, and the electrodes beside them are keyed by an integer,
serialise, and come back with **string** keys — a lookup that misses silently, and only where an
adapter runs elsewhere.

What the same probe could not settle is the array. It also confirmed #1's closed list on the
adapter that receives the most: everything the NWB adapter is passed crosses in 271 bytes of JSON,
and it returns 33 rows across 13 resources identical to the ones it returns constructed with a
`Clock` and a `ZoneInfo` today.

**Settled 2026-09-11 in #1's favour of the boundary**: #1 §3.1 now states what a build passes as
data — a root URI the adapter opens for itself, the reference clock's identifier and rate, first
samples as integers — and forbids a build requiring an adapter to accept a live handle. Sharing one
open store per root survives as an optimisation a build MAY apply in its own process, which it
MUST NOT make part of a declaration. So #1's contract holds on both sides of #2's boundary, and the
in-process path is an optimisation rather than a second interface. Both touch Part 05 §3 by
appending, which renumbers nothing either way.

**None moves a count in the generated block.** No core table, column, reference, rule or vocabulary
changes. Every number in each is measured against the parts, the registries and the three
distributions as they stood when it was drafted and is re-measured at acceptance, which the
pre-acceptance checks in `../CLAUDE.md` require anyway.
