# R52 — Immutability Is a Premise Nothing Checks

| | |
|---|---|
| **Status** | **Accepted** 2026-09-02 |
| **Amends** | R14 §2.3 (what immutability covers), R35 §2 (an untouched file's verdict), R15 §4 (what each validation level establishes) |
| **Depends on** | R14 (external resources and immutability), R32 (amending a committed packet), R35 (bounded revalidation), R36 (verifying a prefix) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R14 §2.3 makes a packet's own bytes immutable. R35 §2 spends that promise:

> An untouched file's verdict is **determined** by immutability, so revalidation covers the
> added members and the rules naming the resource, not the whole table.

That is what keeps adding a thirteenth sorting from re-reading 286,896,563 rows, and it is a
deduction, not a measurement. **Nothing verifies the premise it deduces from.** A packet-owned
file modified in place — by a script pointed at the wrong directory, a partial restore, a
well-meant "fix" to one column — makes R35 return a stale verdict, silently, and the packet
reports `passed`.

**No packet-owned resource records a checksum.** Measured on a real packet: **0 of 26**. The
manifest schema has carried `sha256` on a resource since `04`, and `checksums=True` reaches only
`_resolve_external`, so there is neither a value to compare nor a path that would compare it.

### 1.1 This is the opposite case from an external resource

R14 §2.3.1 says an external resource's recorded facts are what was true at validation, "not a
promise about now". So for external bytes there is no promise to verify, and a digest answers a
question the packet never asked — which is why R36's digest and R51's store digest are both
opt-in and neither is the default.

Packet-owned bytes are the inverse. The promise is made, another revision's bound depends on it,
and it is the one case where a checksum verifies something the packet actually claims.

### 1.2 The cost is not the external cost

The two are routinely quoted together and should not be:

| | bytes | rate | cost |
|---|---:|---:|---:|
| external LFP, cold, 2,496 objects | 6,830 MB | 91 MB/s | **75 s** |
| packet-owned, warm, one file per resource | 1,209 MB | 2,019 MB/s | **0.60 s** |

The writer has just written these bytes, so they are in page cache and in one file per resource
rather than 208. Against a whole-packet build of 1 min 51 s, hashing every byte the packet owns
is **0.5%**.

## 2. Decision

### 2.1 A packet-owned resource records a digest

A writer committing a packet **SHOULD** record `sha256` for every resource the packet owns,
over the bytes of the file at its `uri`.

This is a plain digest of one file. R36 §2.2's canonical listing is for a resource whose `uri`
names a *prefix*, and applies unchanged where a packet-owned resource is one; a single Parquet
file is its own bytes, which is what every other format means by a checksum.

`SHOULD` and not `MUST`: a packet that records none is conforming, and behaves as every packet
built so far does.

### 2.2 The digest covers what immutability covers

A resource's `sha256` describes the bytes as committed. R32 §3 forbids an amendment modifying
anything it did not write, so a recorded digest stays true for the life of the packet — which is
precisely the property R35 §2 assumes and this makes checkable.

`verified_at` is **not** recorded beside it. R14 §2.3.1 pairs that with an external resource, to
date a fact that may since have changed; a packet-owned digest is not dated, because it is not a
observation that decays but a statement about what the packet is.

### 2.3 Validation checks it where asked

`checksums=True` (R15 §4 level 3b) **MUST** also recompute the digest of every packet-owned
resource that records one, and report a disagreement as an **error** — not a warning. An external
resource that changed is the world moving under a packet that never promised otherwise; a
packet-owned file that changed is the packet being wrong about itself.

A packet-owned resource recording no digest is **not checked**, and the report MUST say how many
were skipped, as R51 §2.3 already requires of its own level.

### 2.4 What an amendment re-establishes

R35 §2's bound is unchanged, and gains a way to be audited: an amendment recomputes the digest of
what it wrote and **MAY** leave the rest, because that is exactly the deduction R35 licenses.
A caller wanting the deduction checked rather than trusted runs `checksums=True` over the whole
packet, which is 0.60 s.

## 3. What this does not do

- **No change to R36.** The prefix digest, its canonical listing and its value are untouched.
- **No new requirement on external resources.** Their digests stay optional and stay undated in
  neither direction — R14 §2.3.1's `verified_at` continues to apply to them and only to them.
- **No change to R35's bound.** An untouched file's verdict is still determined; this adds the
  means to check the premise, not an obligation to.
- **No granularity below a file.** A per-row-group digest would let a bound reach inside a file,
  and nothing needs that: R32 amends by adding resources, not by rewriting part of one. Parquet
  cannot be appended to either -- extending a table rewrites it -- so "which pages moved" is not
  a question the format can be asked. Its own page CRC32 does not serve it: the values live in page
  headers inline with the data rather than the footer, pyarrow exposes none, and a rewritten file
  carries perfectly valid ones. Measured at 0.06% of bytes and no measurable time, it is a
  corruption detector and not an identity check.
- **No signature.** sha256 detects change, not tampering by someone who can also rewrite the
  manifest. That is a different problem and needs a different mechanism.
