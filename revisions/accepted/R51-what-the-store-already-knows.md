# R51 — What the Store Already Knows

| | |
|---|---|
| **Status** | **Accepted** 2026-09-02 |
| **Amends** | R14 §2.3 (what an external resource records), R36 §2.2 (the digest over a member listing), R36 §2.3 (the two verification levels) |
| **Depends on** | R14 (external resources), R36 (verifying a prefix) |
| **Supersedes** | R42 §2.1 (the member array), for external prefixes only — R42 is withdrawn |
| **Profile** | `escapewheel-portable-v0.1` |

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

For a **single-part** object an S3 ETag is the MD5 of its content. 2,394 of the 2,496 members a
real packet references are single-part (§3), and the values arrive in the same `list_objects_v2`
response that R36 level 3a already issues. A HEAD per object would also yield `ChecksumCRC32` with
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

### 2.1 An external prefix resource may declare its members

R36 §2.2 computes a listing to digest it and keeps nothing; a manifest has no place to record a
per-member fact. R42 §2.1 proposed one and is withdrawn — its motivation was partitioning a table,
which measured negative on read. The array itself is still needed here, so this revision declares
it, scoped to the prefixes that already exist.

A resource with `external: true` whose `uri` names a **prefix** rather than a single object
**MAY** declare `members`: an array of

```json
{"key": "c/0/0", "size_bytes": 3054612, "sha256": "…", "store_digest": {…}}
```

with `key` relative to `uri` using `/` separators, and `sha256` and `store_digest` each optional.

**It is a record of what was seen, not a resolution rule.** A reader does not consult it: an
external dense array asset is handed its URI and opened by its own library, which addresses chunks
by key and never enumerates. R14 §2.3.1 already fixes the standing of such a record — what was
true at validation, not a promise about now — and this changes nothing about that.

Where `members` accompanies R36 §2.2's `sha256`, the listing digested **MUST** be the declared
one, so the enumeration and the digest cannot disagree.

Declaring members also makes level 3a per-member rather than aggregate. `size_bytes` on the
resource is a total, so two members changing in opposite directions leave it correct; the same
listing that produces the total can compare each member instead, at no additional request.

### 2.2 A member may record what the store said about it

Each member **MAY** carry:

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

### 2.3 A third verification level, between listing and reading

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

### 2.4 What a passing check may be reported as

A store-digest pass **MUST NOT** be reported as a checksum verification. It establishes something
weaker and store-specific, so it gets its own finding — as R36 §2.3's levels already do, where
exactly one of `external.unverified` and `external.verified` is always reported so a passing run
says which mode produced it.

A validator that skipped every member because none recorded a `store_digest` reports that it
verified nothing, not that everything passed.

## 3. Evidence

`s3://aind-open-data`, the twelve LFP prefixes a real packet references — 2,496 objects and
6.83 GB:

| | |
|---|---|
| members single-part, so their ETag is a content hash | **2,394 of 2,496 (96%)** |
| ETags returned by the listing R36 level 3a already performs | **all of them, at no extra request** |
| additional checksum available per object | `ChecksumCRC32`, at one HEAD each |
| recording every member from the store | **2.09 s** |
| validating them against the store, whole packet | **3.3 s** |
| sha256 over every byte, whole packet | **88 s** |

**The 96% is the point, not a footnote.** Eleven of the twelve prefixes are single-part
throughout; one — `core.46110.lfp`, the largest at 950 MB — has 102 of its 208 chunks uploaded
multipart, at 5.8–5.9 MB each. §1.1 anticipated multipart in the abstract; measured, it is
present in the first real packet asked, and it is not a property of the array's role or its
writer but of how large its individual chunks happened to be.

So a validator that reported a store-digest pass without saying what it skipped would report a
clean check on an array where **half the members were never looked at**. That is what §2.3's
skipped count is for, and why it is a requirement rather than a nicety.

The digest itself was verified identical computed from S3 and from local disk
(`3660170e5c3f2205…`), so R36 §2.2's canonical listing is store-independent as intended. This
revision does not disturb that; it adds a cheaper question with a weaker answer.

Recording members costs no requests and 304 KB of manifest against 15.7 KB without them, which
is why a writer opts in (`verify = "members"`) rather than getting it by default.

## 4. What this does not do

- **No change to the digest.** R36 §2.2's definition and value are untouched, and `sha256`
  remains what a manifest records for content identity.
- **No new requirement.** `store_digest` is MAY, and a packet recording none behaves exactly as
  it does today.
- **No dependence on S3.** `algorithm` is open, and a store offering nothing simply yields
  nothing to record. The mechanism is "write down what the store said", not "write down an ETag".
- **No change to how a resource resolves.** `members` records what was seen; it does not tell a
  reader what to read, and does not forbid enumeration. That rule belonged to R42, where a
  partitioned table's rows *were* its members; here the reader never enumerates in the first place.
- **Nothing about packet-owned prefixes.** R42 §2.1 would have made `members` a MUST for them,
  binding `core.waveform_mean` in every packet built so far. This says nothing about them: their
  bytes are covered by R14 §2.3's immutability, which is a stronger guarantee than a record.
- **No claim that MD5 is sufficient.** §1.1 and §2.3 exist to stop a store-digest pass being read
  as a checksum pass.

## 5. Settled on acceptance

- **Is a `MAY` no writer exercises worth the schema?** The writer exercises it: `verify` gains a
  `members` level between `size` and `sha256`, costing the requests `size` already makes. It is
  not the default, because 2,496 members is 304 KB of manifest against 15.7 KB without them.
- **What the writer should record.** Unchanged by this: the default stays `size` on the
  measurement in R42 §4.1's neighbourhood — 0.33 s to list against 75 s to digest, on a build of
  1 min 51 s. What this adds is a level that costs the listing, so a packet that wants any content
  check without paying for a digest now has one.
- **Whether this substitutes for verifying at publication.** It does not. R36 §2.4's workflow —
  verify once the bytes have landed where the manifest says — is still unbuilt, and a
  `store_digest` recorded at build time answers "has this changed since the build", which is the
  question a publication step would ask better.
