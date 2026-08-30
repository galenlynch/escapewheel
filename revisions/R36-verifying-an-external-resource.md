# R36 — Verifying an External Resource

| | |
|---|---|
| **Status** | **Proposed** 2026-08-30 |
| **Amends** | R14 §2.3, R15 §4 |
| **Depends on** | R14 (external resources), R15 (validation levels), R21 (per-resource Zarr version) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R14 §2.3 gives an external resource entry a `sha256` field meaning "what was verified, if
anything was", and a `size_bytes` meaning "as verified". Neither says what is measured.

For a `table` or a `document_asset` there is no question: the resource is one file, and both
fields mean what they mean everywhere else. A `dense_array_asset` is not one file. Measured on
`ecephys_776259_2025-04-09`, one LFP series is a prefix holding **208 objects** — 206 chunks,
a `.zarray` and a `.zattrs` — and the twelve together are **2,496 objects over 6.83 GB**.

So "the sha256 of the resource" names nothing, and two implementations that both believe they
follow R14 produce different digests, or the same digest over different bytes. The first
implementation of the external mode hit this immediately: the writer summed chunk sizes and
skipped the metadata documents, the validator listed everything, and the two disagreed on a
conforming packet by exactly the size of a `.zarray`.

## 2. Decision

### 2.1 `size_bytes` is the total under the URI

For any resource, `size_bytes` is the sum of the sizes of every object the URI names,
metadata documents included. A prefix's size is a list operation, not a stat.

Including the metadata is not a detail. A Zarr array's `.zarray` carries its shape, dtype,
chunking and codecs; an array whose chunks are untouched and whose `.zarray` was rewritten is
a different resource, and a size that skipped it would not notice.

### 2.2 `sha256` over a prefix is defined, not assumed

Where the URI names **one object**, `sha256` is the SHA-256 of its bytes. This is what the
field means in BagIt, Frictionless, Croissant and everywhere else, and nothing changes.

Where the URI names a **prefix**, `sha256` is the SHA-256 of the UTF-8 encoding of

```json
[["<key>",<size>,"<sha256>"], ...]
```

serialised as compact JSON — `,` and `:` separators, no whitespace, keys ASCII-escaped — with
one entry per object, `<key>` relative to the URI with `/` separators, sorted by `<key>` in
byte order.

Three properties this buys, none of which a concatenation would:

- **Reproducible without knowing the store.** Two implementations enumerate an S3 prefix and a
  local directory in different orders; sorting the keys removes the difference.
- **Members stay independently checkable.** The listing carries each object's own digest, so a
  consumer that fetched three chunks can verify those three without the other 205.
- **A renamed or added object changes the digest.** A concatenation of chunk bytes would not
  notice a chunk moving between keys, which for a Zarr array is a different array.

### 2.3 Verification is layered, because the layers cost differently

R15 §4's level 3 becomes two:

| Level | Check | Cost |
|---|---|---|
| 3a | the URI resolves; `size_bytes` holds; declared `codecs` match the metadata document | one list, one small read |
| 3b | `sha256` holds | reads every byte |

A validator offering level 3 MUST offer 3a and MAY offer 3b, and MUST NOT run 3b unless
separately asked. On this dataset 3a is 2,496 list entries and twelve small reads; 3b is
6.83 GB of transfer, and against an object store that is a bill as well as a wait.

A writer recording `sha256` pays the same, which is why it is not the default. A packet
recording only `size_bytes` and `verified_at` is conforming — R14 §2.3 already makes all three
optional.

### 2.4 A claim not made beats a claim not true

Where a writer cannot reach the URI it is about to record — no credentials, no backend, no
network — it MUST omit `sha256`, `size_bytes` and `verified_at` rather than record what it
measured of a local copy. R14 §2.3.1 makes these a record of what was looked at; bytes beside
the writer are not the bytes the URI resolves to, however likely they are to be identical.

The consequence is worth stating plainly: **a packet built where its data will not live
carries no verified fact about that data.** That is the honest outcome, and the fix is to
verify at publication rather than to weaken what the fields mean.

## 3. What this does not do

- It does not make `sha256` required. R14 §2.3 leaves it optional and this keeps it optional.
- It does not define a digest for a `parquet_dataset`, which is also a prefix. The same rule
  applies by construction, but no packet yet externalises one.
- It does not adopt an existing multihash or content-addressing scheme. Bare hex SHA-256 is
  what R14 already specifies and what `manifest.schema.json` already constrains.

## 4. Prior art

The field set R14 defines — an absolute URI, an optional checksum, an optional size, and a
time — is close to converged practice, which is a reason to keep it rather than invent:

| | How it references | Checksum | Size |
|---|---|---|---|
| BagIt (RFC 8493) | `fetch.txt`: URL, length, path | required, per file, in `manifest-<alg>.txt` | required |
| Frictionless Data Package | `path` may be a URL | optional `hash` | optional `bytes` |
| Croissant (MLCommons) | `fileObject.contentUrl` | optional `sha256` | optional `contentSize` |
| STAC | asset `href` | optional `file:checksum` (multihash) | optional `file:size` |
| **NWB-Lake (R14)** | `uri` + `external` | optional `sha256` | optional `size_bytes` |

Every one of them is per **file**. None defines a digest over a prefix of many objects,
because none of them packages a chunked array store the way Zarr does. §2.2 is therefore new
rather than borrowed, and is stated here so that it is decided once.

NWB-Lake's `verified_at` has no counterpart in any of them. BagIt in particular treats a
checksum as a standing truth; R14 §2.3.1 is explicit that it is not, and the timestamp is what
carries the difference.
