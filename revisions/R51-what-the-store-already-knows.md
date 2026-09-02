# R51 — What the Store Already Knows

| | |
|---|---|
| **Status** | **Proposed** 2026-09-02 |
| **Amends** | R36 §2.2 (the digest over a member listing), R36 §2.3 (the two verification levels) |
| **Depends on** | R14 (external resources), R36 (verifying a prefix), R42 (a prefix declares its members — *proposed*) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R36 §2.2 defines a prefix's digest as sha256 over a canonical listing of `[key, size, sha256]`
per member. Verifying it **reads every byte**: 6.83 GB for one session's LFP, measured at 88 s
against S3 and about eight minutes before the digest was made concurrent.

**The store already holds a per-object content hash, and hands it over with the listing we
perform anyway.** Measured on the objects a real packet references:

```text
.zarray  size=344       ETag="bf93d78c73e82f8080709fec330faa26"  multipart=False
0.0      size=3054612   ETag="4bb679e9a7658fca582eee9456244ebf"  multipart=False
```

For a **single-part** object an S3 ETag is the MD5 of its content. All 208 members of that array
are single-part, and the values arrive in the same `list_objects_v2` response that R36 level 3a
already issues. A HEAD per object would also yield `ChecksumCRC32` with
`ChecksumType: FULL_OBJECT`, but that costs one request per member where the ETag costs none.

So there is a check available at **list cost** — 1.31 s for a whole packet against 88 s — that
R36 currently has no way to express.

### 1.1 What it cannot do, which is what shapes the decision

An ETag **cannot verify a recorded sha256**. They are different functions of the same bytes, so a
manifest carrying sha256 and a store offering MD5 have nothing to compare. Three further limits:

- **Multipart objects have no content ETag at all.** A multipart upload's ETag is a hash of part
  hashes with the part count appended (`…-12`), so the same bytes uploaded with a different part
  size give a different value.
- **It is not stable across a copy.** Copying an object may re-chunk it, so an ETag identifies
  bytes *in place*, not bytes.
- **MD5 detects corruption, not tampering.** That matches what R36 §2.4 already claims — "what
  was true when someone looked" — and would not support a stronger claim.

The useful question it *can* answer is therefore not "are these the bytes the manifest describes"
but **"has anything changed since someone looked"** — which is exactly what R14 §2.3 says an
external resource's recorded facts mean.

## 2. Decision

### 2.1 A member may record what the store said about it

Where a manifest records per-member facts — R42 §2.1's `members` array, or R36 §2.2's listing —
each member **MAY** additionally carry:

```json
{"key": "0.0", "size_bytes": 3054612, "sha256": "…",
 "store_digest": {"algorithm": "md5", "value": "4bb679e9a7658fca582eee9456244ebf"}}
```

`algorithm` is an open string naming what the store computed, and `value` is that value verbatim.
A writer records it only when the store supplies one it understands to be a **content** hash of
the whole object; for S3 that means an ETag on a single-part object, and it MUST NOT record a
multipart ETag (§1.1).

`store_digest` is never a substitute for `sha256`. It is the store's word, in the store's
algorithm, about the object as the store holds it.

### 2.2 A third verification level, between listing and reading

R36 §2.3 defines two: `external=True` lists and checks sizes and codecs; `checksums=True` also
recomputes sha256. **Add a third, between them:**

> A validator asked to verify content **without reading** compares each member's recorded
> `store_digest` against the value the store reports now. A member whose value differs has
> changed. A member with no recorded `store_digest`, or whose store reports none, is **not
> checked**, and the report MUST say how many were skipped.

The three levels stay separate flags, as R36 §2.3 requires and for the same reason: they differ
by orders of magnitude in cost, and the difference is a bill as well as a wait.

| level | what it establishes | measured, one session's LFP |
|---|---|---|
| list | the resource resolves; sizes and codecs agree | **1.31 s** |
| store digest | nothing has changed in place since recording | **~1.31 s** (same listing) |
| sha256 | the bytes are the bytes the manifest describes | **88 s** |

### 2.3 What a passing check may be reported as

A store-digest pass **MUST NOT** be reported as a checksum verification. It establishes something
weaker and store-specific, so it gets its own finding — as R36 §2.3's levels already do, where
exactly one of `external.unverified` and `external.verified` is always reported so a passing run
says which mode produced it.

A validator that skipped every member because none recorded a `store_digest` reports that it
verified nothing, not that everything passed.

## 3. Evidence

`s3://aind-open-data`, the LFP array a real packet references, 208 objects and 508,986,967 bytes:

| | |
|---|---|
| members that are single-part, so their ETag is a content hash | **208 of 208** |
| ETags returned by the listing R36 level 3a already performs | **208, at no extra request** |
| additional checksum available per object | `ChecksumCRC32`, at one HEAD each |
| whole packet, 2,496 objects and 6.83 GB: list | **1.31 s** |
| whole packet: sha256 over every byte | **88 s** |

The digest itself was verified identical computed from S3 and from local disk
(`3660170e5c3f2205…`), so R36 §2.2's canonical listing is store-independent as intended. This
revision does not disturb that; it adds a cheaper question with a weaker answer.

## 4. What this does not do

- **No change to the digest.** R36 §2.2's definition and value are untouched, and `sha256`
  remains what a manifest records for content identity.
- **No new requirement.** `store_digest` is MAY, and a packet recording none behaves exactly as
  it does today.
- **No dependence on S3.** `algorithm` is open, and a store offering nothing simply yields
  nothing to record. The mechanism is "write down what the store said", not "write down an ETag".
- **No claim that MD5 is sufficient.** §1.1 and §2.3 exist to stop a store-digest pass being read
  as a checksum pass.

## 5. Open

- **Whether this should wait for R42.** R42 §2.1 adds the `members` array this hangs on, and is
  held because partitioning buys nothing measurable. Without it, `store_digest` has nowhere per
  member to live and would have to sit on the resource as a digest-of-digests — expressible, but
  it loses the per-member checkability R36 §2.2 chose deliberately.
- **Whether a writer should record `sha256` at all for a large external resource.** The packets
  built so far set `verify="size"` and record none, so R36's level 3b currently verifies nothing
  on any packet in existence. At 88 s per packet rather than eight minutes, recording it is now
  affordable, and this revision is a poor substitute for simply doing so.
