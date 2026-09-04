# R73 — A Digest Says What It Covers

| | |
|---|---|
| **Status** | **Proposed** 2026-09-04 |
| **Amends** | `03` §? (the packet-owned digest), R52 §2.1 (which described one file per resource) |
| **Depends on** | R36 §2.2 (the canonical member listing), R52 (a packet-owned resource records a digest) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R52 requires a `sha256` over every packet-owned resource, and `03` describes it as *"whole-file,
not per-row-group"*. R52 §1's cost table reads *"packet-owned, warm, one file per resource"*.

A Parquet table is one file. A packet-owned Zarr array is not.

### 1.1 Measured: an owned resource that is a directory

The built packet owns two dense arrays, and each is a prefix:

```
arrays/core/waveform_mean.zarr     sha256 0c98cc78…  size_bytes 20,992,844
arrays/core/sniff_detector.zarr    sha256 1dadd742…  size_bytes  3,463,092
```

Neither is a file. Between them they are ten objects — `zarr.json` plus shards and chunks — and
the manifest records one digest and one size for each, over bytes the specification does not
identify.

### 1.2 The algorithm exists; the specification does not name it

This is not an unimplemented case. `nwb_lake_validator.stores.digest` routes a prefix through
**R36 §2.2's canonical member listing** — the same construction R36 defined for an external
prefix, where one LFP series is 208 objects and neither `sha256` nor `size_bytes` had a meaning
either.

So the reference implementation is right and the specification is silent. Two conforming
implementations reading `03` alone would hash different bytes and both would believe they had
complied, which is the failure a digest exists to prevent.

## 2. Decision

### 2.1 A digest declares its scope

Every recorded `sha256` covers one of two things, and which one is determined by the resource, not
by the writer's choice:

| the resource is | the digest covers |
|---|---|
| a single file | the file's bytes, in order |
| a prefix of several objects | R36 §2.2's canonical member listing |

A writer **MUST** compute a prefix resource's digest by R36 §2.2's construction and **MUST NOT**
substitute a concatenation of member bytes, a digest of one member, or any order-dependent
traversal.

### 2.2 The same construction, packet-owned or external

R36 §2.2 defined the listing for an external prefix. It applies unchanged to a packet-owned one:
the members are the objects under the resource's `uri`, their relative paths normalised, sorted
lexicographically, each contributing its path and its own digest.

Nothing new is specified here. What this revision does is say that the packet-owned case uses it,
which `03` and R52 §2.1 do not.

### 2.3 `size_bytes` for a prefix

`size_bytes` on a prefix resource is the **sum of its members' sizes**. It is not the size of any
file and **MUST NOT** be read as one.

### 2.4 R52 §1's wording

R52 §1's *"one file per resource"* describes the measurement it made — 1,209 MB of Parquet at
2,019 MB/s — and is struck as a general characterisation. The cost claim stands: the two owned
arrays add 24 MB to a build that already hashes 1.2 GB.

## 3. What this does not change

- **No new field.** No `digest` object, no `scope` discriminator: the resource's own kind decides
  which construction applies, and a writer that must be told is a writer that could get it wrong.
- **No new algorithm.** R36 §2.2 is reused verbatim rather than restated, so a second definition
  cannot drift from the first.
- **No packet becomes invalid.** Every digest in every packet built was already computed this way;
  this states what they mean.
- **No change to R51.** A `store_digest` on a member remains what a store volunteers, distinct
  from a recorded `sha256` and unable to verify one.

## 4. Open

- **Whether a prefix resource should record its members.** R51 adds an optional `members` array to
  an *external* prefix and deliberately does not require one on a packet-owned resource, since a
  reader hands the prefix to Zarr and never enumerates it. A packet-owned member list would make
  §2.1's digest reproducible without re-listing the store; nothing has asked.
