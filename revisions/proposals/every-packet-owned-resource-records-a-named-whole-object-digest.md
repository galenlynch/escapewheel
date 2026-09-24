# Every packet-owned resource records a named whole-object digest

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `f5f33647eb9c3e29ff8c850afa480468fea0c582` |
| **Decision domain** | specification |
| **Affects** | Part 03 §§1, 8.1, 10 and 11.3; Part 04 §§4.1, 5.2, 5.3, 5.4, 10 and 11; Part 05 §11; Part 08 §§3 and 5; `registry/manifest.schema.json` and the delivery schema generated from it; the validator's store access, owned-digest and member-digest checks; the writer's digest, `verify` and LFP source; packet fixtures |

## 1. Problem

A packet manifest records a digest of a resource's bytes in one member, `sha256`. The parts
disagree about what that digest covers, whether it is present, and what can check it.

[Part 03 §10](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#10-checksums) calls a
packet-owned digest "whole-file, one file per resource", while
[Part 04 §5.4](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#54-prefix-resources) defines a
prefix's digest over its members. Every packet the reference writer builds owns one or two Zarr
arrays, and each is a prefix.

Part 03 §8.1 says immutability "is verified rather than assumed" because a writer records a
checksum for every packet-owned resource, and
[Part 03 §9.4](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-incremental-revalidation)
relies on that premise to bound revalidation after an amendment. Part 03 §10 has a writer record a
digest only "by default", with no requirement keyword, and a verification report counts the
resources that lack one. A conforming packet can therefore leave the premise uncheckable, and no
packet fixture records a resource digest.

SHA-256 is the only function a resource digest can use, so checking a resource held in an object
store means reading every byte of it. The store already holds a whole-object checksum of each
object it accepted, but a manifest cannot record a digest in the store's algorithm: the member
field `store_digest` appears only on an external prefix's members and never substitutes for
`sha256`.

Two narrower defects sit beside these. The reference validator records any 32-digit hexadecimal
ETag as an MD5, which the S3 documentation says is false for an object encrypted with SSE-KMS or
SSE-C. Part 04 §5.4's construction also gives an empty prefix a well-defined digest, of `[]`, so the
prose admits a packet-owned resource holding nothing, and only the implementation refuses one.

## 2. Evidence

Observations were read from the generated parts, the schemas and the reference implementation at
the recorded baseline. Throughputs were measured on one Intel Core i9-12900K workstation over
512 MB of random bytes held in memory.

### 2.1 Built packets record owned digests, and fixtures record none

Four packets built by the reference writer are on local disk, named here by their directories.
Each records a digest for every resource it owns and none for any resource it references:

| packet | built | owned, with digest | owned prefixes | external, with digest |
|---|---|---|---|---|
| `df-packet` | 2026-09-06 | 31 of 31 | 2 | 0 of 14 |
| `rebuild-sample/776259` | 2026-09-10 | 42 of 42 | 2 | 0 of 12 |
| `776259-packet` | 2026-09-17 | 42 of 42 | 2 | 0 of 12 |
| `786867-packet` | 2026-09-17 | 42 of 42 | 1 | 0 of 14 |

`776259-packet` owns 46 objects holding 1,219 MB. Its two owned prefixes, `core.waveform_mean` and
`core.waveform_sd`, hold three objects each, and recomputing their digests at the baseline
reproduces the recorded values. The 31 packet fixtures under `fixtures/packets/` carry 926
packet-owned entries, none recording `sha256`, because `fixtures/build.py` writes none.

### 2.2 S3 and Google Cloud Storage keep a whole-object CRC

The S3 user guide ("Checking object integrity for data uploads") lists the checksum types each
algorithm supports for a multipart upload:

| algorithm | full object | composite |
|---|---|---|
| CRC64NVME | yes | no |
| CRC32, CRC32C | yes | yes |
| SHA-1, SHA-256, MD5, XXHash, SHA-512 | no | yes |

A single-part `PutObject` always stores a full-object value, so on S3 a SHA-256 covers the whole
object only when the object was uploaded in one part. A composite value is derived from the parts'
checksums, and the guide notes that it changes when an object is copied although the data does not.
S3 attaches a full-object CRC64NVME when a client sends no checksum and gives CRC64NVME to the copy
of an object that has none; a copy of an object with a checksum keeps its algorithm. S3 encodes
every value as base64 of the checksum's big-endian bytes.

Reading those values costs one request per object. The `Object` type that `ListObjectsV2` returns
carries `ChecksumAlgorithm` and `ChecksumType` but no value, so a value needs a `HeadObject` or
`GetObjectAttributes` request. The same type's `ETag` is the MD5 of the data only for an object
created by `PutObject`, `PostObject` or `CopyObject` and stored in plaintext or under SSE-S3.

A client usually sends its own checksum rather than leaving S3 to attach one. botocore 1.43.75, the
version in the AIND package's environment, sets `request_checksum_calculation` to `when_supported`
and `DEFAULT_CHECKSUM_ALGORITHM` to `CRC32`, so an upload through boto3's default configuration
stores CRC32, not CRC64NVME.

Google Cloud Storage gives every object a `crc32c` property, the CRC32c of RFC 4960 Appendix B
encoded as base64 in big-endian byte order, except an object encrypted with a customer-managed key.
Its `md5Hash` is absent for a composite object. Azure Blob Storage stores no CRC for a blob: it keeps
the `Content-MD5` that `Put Blob` sets, while a block blob committed by `Put Block List` carries only
a value the client supplied.

### 2.3 A CRC runs seven times faster than SHA-256 and matches its authority

| function | implementation | throughput |
|---|---|---|
| SHA-256 | Python `hashlib` | 2.2–2.4 GB/s |
| CRC64NVME | `awscrt` 0.37 | 15.6 GB/s |
| CRC32C | `awscrt` 0.37 | 16.1 GB/s |
| CRC32C | `google-crc32c` 1.8.0 | 20.4 GB/s |

`google-crc32c` is already in the writer's lock as a dependency of `zarr` 3.3.0; `awscrt` is not.

Throughput matters most when the bytes are not local. R52 measured the digest of one packet's owned
bytes during a build at 0.60 s for 1,209 MB, read from page cache. Checking `776259-packet`'s owned
bytes on S3 against SHA-256 reads 1,219 MB, and against a checksum the store holds it takes 46
`HeadObject` requests. R51 measured one session's external LFP arrays at 6.83 GB over 2,496
objects, 102 of them multipart, and their SHA-256 digest at 75 s from local disk and 88 s from S3.

`awscrt`'s CRC64NVME reproduces all four test vectors of Figure 155 in the NVM Express NVM Command
Set Specification, Revision 1.2, such as `6482d367eb22b64e` for 4 KiB of zero bytes. Its value for
the ASCII string `123456789` is `ae8b14860a799888`, the bit-reversal of the `Check` value
`11199E50_6128D175h` printed in Figure 153. Both CRC32C implementations give `e3069283` for the same
string. Both CRCs of an empty input are zero.

### 2.4 The reference implementation discards member digests and misreads ETags

- `escapewheel_validator.stores.digest` computes each member's SHA-256 while digesting a prefix and
  discards it. The writer's `verify` and its LFP source record `members` with sizes and store
  digests only, so an external prefix digested at `verify = "sha256"` records no member digest, and
  checking three of its chunks later means reading all of them again.
- `stores.store_digest` records a 32-digit hexadecimal ETag as `md5` whatever the encryption. Its
  length check excludes multipart ETags, which carry a `-<parts>` suffix, and so 102 of the 2,496
  LFP members get no store digest.
- `packet.resource.member_digest`
  ([Part 04 §10](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-manifest-conformance))
  fires only when every member records `sha256`, so a partly digested member list goes unchecked.
- The validator reports a packet-owned resource without a digest as the warning
  `owned.no_checksum`, and an empty prefix as `resource.missing` because `stores.listing` refuses
  one.

## 3. Desired outcome and constraints

- A digest serves change detection: bit rot, an accidental overwrite or amendment, an incomplete
  copy or stale mirror, and an external resource drifting, each found by comparing a resource with
  its own recorded value. Identifying bytes across packets is not a goal, and neither is resisting
  tampering, since whoever can rewrite a resource can rewrite the manifest.
- Every packet-owned resource carries a digest a validator can check without guessing its
  construction, whether the resource is one object or a prefix.
- A packet held in an object store can be checked without reading its bytes wherever the store
  holds a whole-object checksum in the recorded algorithm.
- Every SHA-256 value already recorded keeps its meaning and verifies unchanged.
- A registry descriptor's `sha256` stays SHA-256 over the document's exact bytes, since
  [Part 03 §9.3](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-superseded-manifest-retention)
  compares those values across retained manifests.
- An ETag stays evidence that an object changed in place, never a checksum.
- Each admitted function has a language-neutral authority, so no library's behavior becomes its
  definition
  ([Part 00 §10](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-normative-references)).

## 4. Options and tradeoffs

### 4.1 Admitted functions

**Keep SHA-256 alone.** Rejected: checking a stored resource costs a full read of it, where the
store would return its own checksum for one request per object.

**Admit SHA-256, CRC64NVME and CRC32C, one per resource** (preferred direction). Each is a function
of an object's bytes alone. S3 stores CRC64NVME as a full-object value for every upload and attaches
it by default; Google Cloud Storage keeps CRC32C for every object, and S3 stores it as a full-object
value on request; every existing manifest records SHA-256. Part 04 alone would invoke the two new
authorities, so their entries join FIPS 180-4 in
[Part 04 §11](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-catalog-normative-references):

- the NVM Express NVM Command Set Specification, Revision 1.2, §5.3.1.3 (64b CRC), for CRC64NVME;
- RFC 9260, Appendix A, for CRC32C.

**Also admit CRC32.** botocore uploads with it by default, and S3 stores it as a full-object value
on request. RFC 1952 §8 defines it, and Part 03 §12 already lists RFC 1952 for bound registries, so
invoking it from Part 04 too would move that entry to Part 00 §10. Open question 2 asks whether to
admit it.

**Admit MD5, SHA-1, or a composite value.** Rejected: a composite value depends on part size, so
the same bytes give different values, and no store keeps MD5 or SHA-1 as a full-object value for a
multipart object.

**Leave the algorithm open.** Rejected: a validator cannot check a function it cannot compute.

A 64-bit or 32-bit CRC misses a random corruption with probability 2^-64 or 2^-32 and detects every
burst no longer than its width, which suffices for change detection. Its weakness against chosen
inputs concerns identity and tampering, both outside §3's purpose.

### 4.2 Recording the algorithm

**A. Sibling members `sha256`, `crc64nvme` and `crc32c`, exactly one present.** Every existing
manifest stays valid. A validator dispatches on the member name, the schema states "exactly one"
with `oneOf`, and each further function adds a member.

**B. A `digest` object `{"algorithm", "value"}` in place of `sha256` on a resource, and a `digest`
string on a member in the resource's algorithm** (preferred direction). It has the shape of
`store_digest`, a further function adds one enumeration value, and a member row cannot name an
algorithm different from its resource's. An existing value carries over as
`{"algorithm": "sha256", "value": …}` without recomputation. The cost is a new manifest schema
version, a rewrite or rebuild of the four built packets, and a change to the reader, validator and
writer. The fixtures record no resource digest now, so they change only by gaining one.

**Record a CRC value in `sha256`.** Rejected: the member's name would be false.

**Fixed-width lowercase hexadecimal values** (preferred direction). A value has 64 digits for
SHA-256, 16 for CRC64NVME and 8 for CRC32C, most significant digit first. A CRC's digits are the
checksum as an integer, so `123456789` gives `ae8b14860a799888` under CRC64NVME and `e3069283`
under CRC32C. Those are the bytes S3 and Google Cloud Storage encode in base64, so converting a
store's value means decoding base64 and encoding hexadecimal. The draft would fix each CRC form by
these check values rather than by RFC 9260's transport byte mapping or the NVMe `Check` value, both
stated for other layouts, as the bit-reversal in §2.3 shows.

### 4.3 Prefixes

**The algorithm names the function applied to each object, and a prefix's value is the SHA-256 of
Part 04 §5.4's listing carrying each member's value in that algorithm** (preferred direction). A
single object's value is the function of its bytes. Hashing the listing costs nothing measurable,
and every existing prefix digest is the SHA-256 case unchanged.

**Combine the members' CRCs into one.** Rejected: a combined CRC carries no keys, so it misses a
chunk moving between keys, which makes a different Zarr array.

**An empty prefix is a finding** (preferred direction). A listing of nothing describes no resource,
and a Zarr array always holds its metadata document.

### 4.4 Member digests

**Member digests stay optional; where members record them, every member records one and the
resource's digest is the one recomputed from the rows** (preferred direction). A validator checks
this in the manifest's `entries` phase without reading any bytes. Open question 3 asks whether a
partly digested member list is itself a finding.

**A writer that digests an external prefix records the member digests it computed** (preferred
direction). A 64-digit value adds 76 bytes per member, about 190 KB for the 2,496 LFP members, and
lets a consumer check the chunks it fetched without reading the rest, the property R36 §2.2 gives
as the reason for the construction.

**Require member digests for packet-owned prefixes.** Rejected: an owned prefix holds three objects
in the packets of §2.1, and its resource digest already detects any change.

### 4.5 Digest presence

**Every packet-owned resource records a digest, and a missing one is a finding in the `entries`
phase** (preferred direction). The check reads only `external` and the digest member. The reference
writer already records a digest for every owned resource, and the writer's `verify` fills a missing
owned digest in a packet built before R52.

**Keep "by default".** Rejected: a conforming packet could still leave Part 03 §9.4's premise
uncheckable.

**An external resource's digest stays optional, under the same functions** (preferred direction).
Part 04 §5.2's rule that a writer unable to reach a URI records nothing is unchanged.

### 4.6 Verification and ETags

**A validator checks a recorded digest either by recomputing it or by comparing it with the
full-object checksum the store reports for each object in the same algorithm** (preferred
direction). The report says which route it took, since a store's value establishes only what the
store received at upload and relies on the store's durability since. A member whose store reports
no such value is read. Under this route
[Part 04 §5.3](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-external-resource-verification)'s
levels 2 and 3c each become "the recorded digest holds", reached either way, and level 3b stays
ETag comparison.

**`store_digest` records an ETag verbatim under the algorithm name `etag`** (preferred direction),
never interpreted as MD5. Any ETag changes when an object is rewritten, so a multipart or SSE-KMS
ETag is change evidence too. Rewriting identical bytes with a different part size also changes it,
an error toward reporting a change. This lifts R51 §2.2's exclusion of multipart ETags and covers
the 102 members it skips.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged: no concept's meaning changes. |
| logical prose, registry declarations, rules | Unchanged: the `sha256` column of `core.source_files` describes a source, not a packet resource, and a later source-cache change owns it. |
| physical profiles | Affected: Part 03 §1's statement of which part owns the digest, §8.1, §10's obligation and its "whole-file" wording, and §11.3's sentence naming `sha256`. |
| packet manifest and schemas | Affected: Part 04 §§4.1, 5.2, 5.3, 5.4 and 10, and two entries in §11; `manifest.schema.json` under option B, or three sibling members under option A; the delivery schema regenerates from it. Registry descriptors are unchanged. |
| validation and import | Affected: Part 05 §11's sentence on what a recorded `sha256` says. |
| extension registries | Unchanged: no declaration names a digest. |
| validator | Affected: CRC64NVME and CRC32C computation, comparison with a store-reported checksum, the missing-digest and empty-prefix findings, the partial member-digest check, and recording an ETag as `etag`. |
| writer | Affected: `_digest`, `verify` and the LFP source record the digest shape and external member digests, and the owned-digest algorithm becomes configurable. |
| reader | Affected only by a manifest schema version under option B: the reader verifies registry digests and reads no resource digest. |
| adapters | Unchanged: an adapter delivers bytes or a resource document, and the delivery schema follows the manifest schema. |
| existing packets | Under option A, unchanged and conforming. Under option B, the four built packets need a manifest rewrite or a rebuild, with their values unchanged. |
| conformance fixtures and tests | Affected: fixtures gain owned digests, and new cases cover each algorithm, an empty prefix, a missing owned digest, a partial member list, and a store-reported match. |
| revision tooling | Unchanged: no revision check reads a resource digest. |
| documentation | Affected: Part 08's manifest excerpt and acceptance checklist, and the validator and writer READMEs where they describe `verify` levels. |

A validator distinguishes the proposed rule from the current one on these cases:

- a packet-owned entry without a digest is a finding, where it is now a warning;
- an entry recording CRC64NVME or CRC32C passes where its bytes match and fails where one byte
  differs, and its prefix value equals the SHA-256 of the listing built from member CRCs;
- every SHA-256 value in the four built packets verifies unchanged;
- an empty packet-owned prefix is a finding;
- a member list in which only some members record a digest is handled as open question 3 settles;
  and
- a report states whether each digest was recomputed or matched a store's value.

The writer obligation to record external member digests is tested in the writer, not by a fixture.
A store-reported comparison needs an object-store test double or a live bucket.

The build-order draft amends Part 03 §9.5 and Part 05 §§1–8, none of the sections above. Moving
Part 03 §11 into its own part carries §11.3's `sha256` sentence with it, and a source-cache change
keying entries by URI and store identity would rely on this proposal's whole-object functions. This
proposal amends R36 §2.2 (the functions), R51 §2.2 (what `store_digest` records) and R52 §2.1
(whether a packet-owned digest is present).

## 6. Open questions

1. **Manifest shape.** Preferred: option B, a `digest` object on a resource and a `digest` string
   on a member. Option A keeps existing manifests valid without a rewrite, at the cost of one member
   per function.
2. **CRC32.** Preferred: admit it. S3 stores it as a full-object value, botocore uploads with it by
   default, and its authority is already a normative reference of this specification; the cost is
   one more function and moving RFC 1952's entry to Part 00 §10. Without it, an object uploaded
   through boto3's defaults can be checked only by reading it.
3. **A partly digested member list.** Preferred: a finding, since the resource digest cannot be
   recomputed from rows some of which lack a value, and such a list now goes unchecked.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
