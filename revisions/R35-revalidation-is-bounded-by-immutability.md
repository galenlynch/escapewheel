# R35 — Revalidation Is Bounded by Immutability

| | |
|---|---|
| **Status** | **Accepted** 2026-08-30 |
| **Amends** | R32 §5 |
| **Depends on** | R12 (physical order is not a SQL rule), R14 (external resources), R32 (amending a committed packet) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base
specification.

## 1. Motivation

R32 §5 requires an amendment to validate the whole packet, and rejects the
narrower path deliberately. The reasoning is sound; the cost is not small.
Measured on a session of 286,896,563 spikes, adding `analysis.spike_events` of
the same size to a 22-resource packet:

```text
physical order scan            65.3 s   core.spike_events 28.0, analysis.spike_events 37.3
Tier 1 and Tier 2 rules        80.6 s   6.2 s for the same packet without the added table
schemas                         0.0 s
```

Every second of that re-derives an answer from bytes that cannot have changed.

R32 §5 turns *add one resource* into *re-read and re-query every resource*, so
the price of an amendment scales with the packet rather than with the amendment.
The packet that has grown large is exactly the one on which adding a small table
should be cheap.

## 2. Scope: an amendment, not a build

A packet whose recipe fully describes it does not amend. `05` stages 8 and 9
place materialization inside the import pipeline, and a staged packet is
openable, so a commit derives its analysis resources from the resources it has
staged and validates the whole packet once. Such a packet is complete at its
first version.

This revision governs what is left: adding a resource to a packet already
committed, where nothing can be derived from staging because the staging is long
gone. An extension registry arriving after the fact (R17), or an analysis wanted
a year later, is that case, and it pays R32 §5 in full.

## 3. What an amendment cannot change

R32 §3 requires that an amendment modify no file the superseded manifest names.
R14 §2.3 declares packet-owned bytes immutable. Together they give a fact
stronger than a convention: a file the amendment does not name is
**byte-identical** to one a previous validation already read.

A check is a query returning offending rows (R2 §7.3). A check whose every input
is such a file has already been evaluated over exactly these bytes and returned
empty. Running it again is not caution; it is recomputation of a known value.

This holds only for **packet-owned** files. R14 §2.3.1 is explicit that an
external resource's `sha256` records what was true at validation rather than
what is true now, so nothing below applies to one.

## 4. Physical order

An amendment MUST establish the physical order (R10 §2, R12 §2) of the resources
it writes, and MUST NOT be required to re-establish it for any other
packet-owned resource.

Order is a property of bytes alone. No addition elsewhere in the packet can
reorder a file that was not rewritten, so a scan of one can reach only the
verdict it reached before.

## 5. Rules

A check MUST be re-run when it is attached to a resource the amendment writes,
**or when its query names one**. A check meeting neither condition MAY be
skipped.

R32 §5's objection is that this is "sound only if no existing rule can reference
a resource added later, and nothing in the registry enforces that." The
objection is answered by making the test syntactic rather than declared. A
generated check refers to a resource by its flattened name (R2 §7; `core.trials`
becomes `core_trials`), so an existing rule that references a resource added
later **names it in its own SQL**, and the test catches it without the registry
having to promise anything.

The test MUST be over-inclusive where it is uncertain. Matching a resource name
inside a string literal or a comment re-runs a check that did not need it, which
costs time; failing to match one skips a check that did, which costs
correctness. A conforming implementation therefore errs toward running.

## 6. A packet may still record `passed`

R32 §5 permits incremental validation but forbids a packet from recording
`validation.status` of `passed` on the strength of it. That restriction is narrowed, not
removed.

A packet MAY record `passed` after an amendment that skipped checks under §3 and §4, because
those checks were not *assumed* to pass — their verdict is determined. Every input is a file
whose bytes a previous validation read, and the same check over the same bytes returns the
same rows. The status means what it has always meant: every required check has passed over
the bytes the manifest names.

Skipping a check whose inputs *could* have changed remains forbidden, and that is what R32 §5
was protecting. An implementation that cannot show an input is immutable MUST run the check.

## 7. What this does not do

- **Does not touch `commit`.** A commit writes every resource, so §3 and §4 exempt nothing.
- **Does not narrow a standalone `validate`.** A validator handed a packet it did not build
  knows nothing about what is immutable relative to what, and MUST check everything. The
  bound is available to a caller that performed the amendment, not to a reader.
- **Does not apply to external resources** (§2), whose bytes are outside the packet's
  immutability guarantee.
- **Does not permit trusting the writer.** Both bounds rest on the inputs being unchanged, not
  on the producer being careful. A writer that establishes a property while writing (rather
  than by reading back) is a separate matter, and is bounded the same way: the check runs, it
  simply runs earlier.
