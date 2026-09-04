# R73 — A Digest Says What It Covers

| | |
|---|---|
| **Status** | **Withdrawn** 2026-09-04 |
| **Amends** | nothing |
| **Depends on** | R36 §2.2 (the canonical member listing), R52 (a packet-owned resource records a digest) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

> **Withdrawn 2026-09-04, unimplemented and never accepted.** The defect it was drafted for is
> real and is fixed, but it was never a gap in the revisions: R36 §2.2 defines a prefix digest
> and R52 §2.1 says in as many words that the definition "applies unchanged where a packet-owned
> resource is one". Both were already binding. What went wrong was the **compilation** of them
> into the v0.2 prose, and a revision cannot repair a compilation.

## 1. What it was drafted for

The built packet owns two dense arrays, and each is a prefix rather than a file:

```
arrays/core/waveform_mean.zarr     sha256 0c98cc78…  size_bytes 20,992,844   (7 objects)
arrays/core/sniff_detector.zarr    sha256 1dadd742…  size_bytes  3,463,092   (3 objects)
```

The v0.2 prose described a packet-owned digest as *"whole-file, not per-row-group"*, R52 §1's cost
table read *"one file per resource"*, and Part 04 §5.4 stated that for a prefix `sha256` and
`size_bytes` are **undefined**. Two implementations reading only that prose would hash different
bytes and both would believe they had complied.

## 2. Why it is not a revision

R36 §2.2 defines the construction exactly — SHA-256 over the compact JSON encoding of
`[["<key>",<size>,"<sha256>"], ...]`, sorted by key in byte order, with `size_bytes` the sum of
member sizes. R52 §2.1 extends it to packet-owned prefixes explicitly. The reference
implementation has always used it: `nwb_lake_validator.stores.digest` routes a prefix through
R36 §2.2 and `PacketWriter` calls it for every owned resource.

So the specification and the implementation agreed; the compiled prose disagreed with both, and in
the strongest way available — it declared undefined a thing two accepted revisions define. That is
a compiler defect, repaired on 2026-09-04 by restoring R36 §2.2's algorithm to Part 04 §5.4 and
striking the *"whole-file"* and *"one file per resource"* characterisations.

## 3. What the episode is evidence for

A citation sweep cannot find this class: R36 and R52 are both cited in the compiled spec, for
their other clauses. Two independent reviews of v0.2 each found dropped clauses and each found a
different subset — R53 §2.4's `int64` escape, R21's codec floor, R55 §2.5's extension coverage,
R61 §2.2's retention declaration, this one.

The response was a ledger rather than a third audit: `nwb_lake_poc_docs_v0.2/ledger.py` enumerates
every Decision clause of every accepted revision, `applied.toml` records where each went, and a
clause with no disposition fails the build. R73 is retained as the case that shows why a revision
was the wrong instrument — the rule already existed, and nothing was checking that anyone had
written it down.
