# R79 — Two Conformance Classes

| | |
|---|---|
| **Status** | **Accepted** 2026-09-04 |
| **Amends** | `05` §8 (what a conforming importer does), `01` §2.4 (what a conforming packet carries) |
| **Depends on** | R9 §5 (provenance is SHOULD), R31 §4 (MUST and SHOULD are about different claims) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Two clauses of this standard look like a contradiction and are not.

`01` makes provenance **SHOULD**: a packet carrying none is conforming (R9 §5). `05` requires a
conforming importer to record source files, processing runs and run inputs. R31 §4 already
explains why both hold — *"they are not the same requirement"* — but the specification never says
what the two requirements are requirements **of**.

### 1.1 The consequence of leaving it implicit

A validator handed a packet cannot tell which clause it is applying. A packet with no provenance
passes; a packet built by an importer that recorded none should not have been built that way; and
nothing in the report distinguishes "this packet is conforming" from "this packet was produced
conformingly", which are different claims about different things.

It also leaves an obvious question unanswerable: what does a validator say about a packet whose
producer it knows nothing about? Under the implicit reading it must either apply the importer's
obligations to a packet that never had an importer, or drop them entirely.

## 2. Decision

### 2.1 The two classes

> **Packet conformance** is a property of the bytes. It is evaluated on a packet regardless of how
> it was produced, and it is what `validate` reports. Provenance is SHOULD within it: a packet
> carrying none is conforming (R9 §5).
>
> **Importer conformance** is a property of a process. An importer conforms when it satisfies `05`,
> which includes recording provenance for the import activity and the inputs it read. A packet is
> not judged by it.

### 2.2 Which one a report is about

A validator **MUST** report packet conformance, and **MUST NOT** report a packet as
non-conforming for an obligation that binds only an importer. Where a validator also checks
importer obligations — a build-time run inside `import`, which has the process in hand — it
**MUST** report the two separately, as R17 §4 already requires of core and extension verdicts.

### 2.3 An analysis resource is the case where they meet

R31 §3 makes `processing_run_id` **MUST** for an analysis resource, and that is a *packet*
obligation rather than an importer one: the claim is about the resource in front of the reader,
not about who built it. A derived resource naming no run is unreproducible whoever produced it,
which is what `06`'s disposability test requires.

Provenance being SHOULD for a packet and MUST for its analysis resources is therefore consistent,
and §2.1 is what makes it legible.

## 3. What this does not change

- **No table, no column, no rule.** Two named classes and one reporting obligation.
- **No obligation moves.** Everything `05` requires of an importer, it still requires; everything
  `01` permits a packet, it still permits.
- **No change to R17 §4.** Core and extension verdicts stay separable; this is a second axis, not
  a replacement for that one.
- **No packet's verdict changes.** Measured: every packet built carries full provenance, so the
  distinction costs nothing today and exists for the packet someone else produces.

## 4. Open

- **Whether packet conformance should later require minimal provenance.** "Validation is
  importation" (`05`) argues for it, and a packet whose origin is unrecorded is weaker evidence
  than one whose origin is. It would be a breaking change for any packet that omitted it, and no
  packet on hand omits it, so the argument can be had when something is at stake.
