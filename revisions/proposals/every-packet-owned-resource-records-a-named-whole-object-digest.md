# Every packet-owned resource records a named whole-object digest

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `f5f33647eb9c3e29ff8c850afa480468fea0c582` |
| **Decision domain** | specification |
| **Affects** | Part 03 §§1, 8.1, 10 and 11.3; Part 04 §§4.1, 5.2, 5.3, 5.4, 10 and 11; Part 05 §11; Part 08 §§3 and 5; `registry/manifest.schema.json` and the delivery schema generated from it; the validator's store access, owned-digest and member-digest checks; the writer's digest, `verify` and LFP source; packet fixtures |

## 1. Problem

A manifest records what a resource's bytes are in one member, `sha256`, and the rules around it
disagree about what it covers, whether it is present, and what can check it.

[Part 03 §10](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#10-checksums) calls a
packet-owned digest "whole-file, one file per resource".
[Part 04 §5.4](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#54-prefix-resources) defines the
digest of a prefix over its members, and every packet the reference writer builds owns one or two
Zarr arrays, each a prefix. The 2026-09-17 project sanity check recorded this as finding S7.

Part 03 §8.1 says immutability "is verified rather than assumed" because a writer records a
checksum for every packet-owned resource, and Part 03 §9.4 spends that premise to bound
revalidation after an amendment. Part 03 §10 states only that a writer records one "by default",
with no requirement keyword, and a verification report counts the resources that lack one. A
conforming packet can therefore leave the premise uncheckable, and no packet fixture records a
resource digest.

SHA-256 is the only function a resource digest can use, so checking a resource held in an object
store means reading every byte of it. The store already holds a whole-object checksum of every
object it accepted, but a manifest cannot record a digest in the store's algorithm. R51's
`store_digest` is confined to an external prefix's members and is never a substitute for `sha256`.

Two narrower defects sit beside these. The reference validator records any 32-digit hexadecimal
ETag as an MD5, which S3 documents as false for objects encrypted with SSE-KMS or SSE-C. And Part
04 §5.4's construction gives an empty prefix a well-defined digest, of `[]`, so the prose admits a
packet-owned resource that holds nothing; only the implementation refuses one.

## 2. Evidence

Observations were read from the generated parts, the schemas and the reference implementation at
the recorded baseline. Throughputs were measured on this machine over 512 MB of random bytes held in
memory.

### 2.1 Built packets and fixtures

Four packets built by the reference writer are on local disk. Every one records a digest for every
resource it owns and none for any resource it references:

| packet | built | owned, with digest | owned prefixes | external, with digest |
|---|---|---|---|---|
| `df-packet` | 2026-09-06 | 31 of 31 | 2 | 0 of 14 |
| `rebuild-sample/776259` | 2026-09-10 | 42 of 42 | 2 | 0 of 12 |
| `776259-packet` | 2026-09-17 | 42 of 42 | 2 | 0 of 12 |
| `786867-packet` | 2026-09-17 | 42 of 42 | 1 | 0 of 14 |

`776259-packet` owns 46 objects holding 1,219 MB. Its two owned prefixes, `core.waveform_mean` and
`core.waveform_sd`, hold three objects each, and recomputing their digests at the baseline
reproduces the recorded values. The 31 packet fixtures under `fixtures/packets/` carry 926
packet-owned entries, and none records `sha256`; `fixtures/build.py` writes none.

### 2.2 What object stores compute

The S3 user guide ("Checking object integrity for data uploads") lists which checksum types each
algorithm supports for a multipart upload:

| algorithm | full object | composite |
|---|---|---|
| CRC64NVME | yes | no |
| CRC32, CRC32C | yes | yes |
| SHA-1, SHA-256, MD5, and the newer XXHash and SHA-512 entries | no | yes |

A single-part `PutObject` always stores a full-object value, so SHA-256 is a whole-object checksum
on S3 only for an object uploaded in one part. A composite value is derived from part checksums,
and the guide notes that it changes when an object is copied although the data does not. S3
attaches a full-object CRC64NVME when a client sends no checksum, and gives CRC64NVME to the copy of
an object that has none; a copy of an object with a checksum keeps its algorithm. Every value is the
base64 encoding of the checksum's big-endian bytes.

The `Object` type that `ListObjectsV2` returns carries `ChecksumAlgorithm` and `ChecksumType` but
no value, so reading the values costs one `HeadObject` or `GetObjectAttributes` request per object.
Its `ETag` is the MD5 of the data only for an object created by `PutObject`, `PostObject` or
`CopyObject` and stored in plaintext or under SSE-S3.

A client usually sends a checksum. botocore 1.43.75, in the AIND package's environment, sets
`request_checksum_calculation` to `when_supported` and `DEFAULT_CHECKSUM_ALGORITHM` to `CRC32`, so
an upload through boto3 in its default configuration stores CRC32, not CRC64NVME.

Google Cloud Storage gives every object a `crc32c` property, defined as the CRC32c of RFC 4960
Appendix B and encoded as base64 in big-endian byte order, except for an object encrypted with a
customer-managed key. Its `md5Hash` is absent for composite objects. Azure Blob Storage stores a
`Content-MD5` that `Put Blob` sets, while a block blob committed by `Put Block List` carries only a
value the client supplied; Azure stores no CRC for a blob.

### 2.3 Cost and conformance of the implementations

| function | implementation | throughput |
|---|---|---|
| SHA-256 | Python `hashlib` | 2.2–2.4 GB/s |
| CRC64NVME | `awscrt` 0.37 | 15.6 GB/s |
| CRC32C | `awscrt` 0.37 | 16.1 GB/s |
| CRC32C | `google-crc32c` 1.8.0 | 20.4 GB/s |

`google-crc32c` is already in the writer's lock as a dependency of `zarr` 3.3.0; `awscrt` is not.
R52 measured the digest of a packet's owned bytes at 0.60 s for 1,209 MB during a build, because
the bytes are in page cache. Checking `776259-packet`'s owned bytes on S3 against SHA-256 reads
1,219 MB; against a checksum the store holds, it takes 46 `HeadObject` requests. R51 measured the
external LFP arrays of one session at 6.83 GB over 2,496 objects, 102 of them multipart, and their
SHA-256 digest at 75 s from local disk and 88 s from S3.

`awscrt`'s CRC64NVME reproduces all four test vectors of Figure 155 in the NVM Express NVM Command
Set Specification, Revision 1.2 (for example, `6482d367eb22b64e` for 4 KiB of zero bytes). Its value
for the ASCII string `123456789` is `ae8b14860a799888`, the bit-reversal of the `Check` value
`11199E50_6128D175h` that Figure 153 prints. Both CRC32C implementations give `e3069283` for the same
string. Both CRCs of an empty input are zero.

### 2.4 The reference implementation

- `escapewheel_validator.stores.digest` computes each member's SHA-256 while digesting a prefix and
  discards it. The writer's `verify` and its LFP source record `members` with sizes and store
  digests only, so an external prefix digested at `verify = "sha256"` records no member digest, and
  checking three of its chunks later means reading all of them again.
- `stores.store_digest` records a 32-digit hexadecimal ETag as `md5` whatever the encryption. Its
  length check excludes multipart ETags, which carry a `-<parts>` suffix, and that is why 102 of the
  2,496 LFP members get no store digest.
- `packet.resource.member_digest`
  ([Part 04 §10](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-manifest-conformance))
  fires only when every member records `sha256`, so a partly digested member list is never checked.
- The validator reports a packet-owned resource without a digest as the warning
  `owned.no_checksum`, and an empty prefix as `resource.missing` because `stores.listing` refuses
  one.

## 3. Desired outcome and constraints

- **Change detection is the purpose.** A digest detects bit rot, an accidental overwrite or
  amendment, an incomplete copy or stale mirror, and an external resource drifting; each case
  compares a resource with its own recorded value. Identifying bytes across packets is not a goal,
  and neither is resisting tampering, since whoever can rewrite a resource can rewrite the manifest.
- Every packet-owned resource carries a digest a validator can check without guessing its
  construction, whether the resource is one object or a prefix.
- A packet held in an object store can be checked without reading its bytes wherever the store
  holds a whole-object checksum in the recorded algorithm.
- Every SHA-256 value already recorded keeps its meaning and verifies unchanged.
- A registry descriptor's `sha256` stays SHA-256 over the document's exact bytes; Part 03 §9.3
  compares those values across retained manifests.
- An ETag stays evidence that an object changed in place, never a checksum.
- Each admitted function has a language-neutral authority, so no library's behavior becomes its
  definition (Part 00 §10).

## 4. Options and tradeoffs

### 4.1 Admitted functions

**Keep SHA-256 alone.** Rejected: checking a stored resource then costs a full read of it, when the
store holds a checksum it would return for one request per object.

**Admit SHA-256, CRC64NVME and CRC32C, one per resource** (preferred direction). Each is a function
of an object's bytes alone. CRC64NVME is full-object on S3 for every upload and is what S3 attaches
by default; CRC32C is on every Google Cloud Storage object and is full-object on S3 when requested;
SHA-256 is what every existing manifest records. Part 04 alone would invoke the new authorities, so
their entries join FIPS 180-4 in Part 04 §11:

- the NVM Express NVM Command Set Specification, Revision 1.2, §5.3.1.3 (64b CRC), for CRC64NVME;
- RFC 9260, Appendix A, for CRC32C.

**Also admit CRC32.** It is botocore's default upload checksum and is full-object on S3 when
requested. RFC 1952 §8 defines it, and Part 03 §12 already lists RFC 1952 for bound registries, so
invoking it from Part 04 as well would move that entry to Part 00 §10. This is open question 2.

**Admit MD5, SHA-1, or a composite value.** Rejected: a composite value depends on part size, so
the same bytes give different values, and no store offers MD5 or SHA-1 as a full-object value for a
multipart object.

**Leave the algorithm open.** Rejected: a validator cannot check a function it cannot compute.

A 64-bit or 32-bit CRC misses a random corruption with probability 2^-64 or 2^-32 and detects every
burst no longer than its width, which serves change detection. Its weakness against chosen inputs
concerns identity and tampering, which §3 excludes.

### 4.2 Recording the algorithm

**A. Sibling members `sha256`, `crc64nvme` and `crc32c`, exactly one present.** Every existing
manifest stays valid unchanged. A validator dispatches on the member name, the schema states
"exactly one" with `oneOf`, and each further function is a new member.

**B. A `digest` object `{"algorithm", "value"}` in place of `sha256` on a resource, and a `digest`
string on a member in the resource's algorithm** (preferred direction). It has the shape of
`store_digest`, a further function is one enumeration value, and a member row cannot name a
different algorithm from its resource. An existing value carries over as
`{"algorithm": "sha256", "value": …}` without recomputation. The cost is a new manifest schema
version, a rewrite or rebuild of the four built packets, and a reader, validator and writer change.
The fixtures record no resource digest now, so they change only by gaining one.

**Record a CRC value in `sha256`.** Rejected: the member's name would then be false.

**Value form** (preferred direction). A value is lowercase hexadecimal of fixed width, most
significant digit first: 64 digits for SHA-256, 16 for CRC64NVME and 8 for CRC32C. For a CRC that
is the integer whose value for `123456789` is `ae8b14860a799888` or `e3069283`, and so the byte
sequence S3 and Google Cloud Storage encode in base64; converting a store's value means decoding
base64 and encoding hexadecimal. The draft would fix each CRC form by these check values rather than
through RFC 9260's transport byte mapping or the NVMe `Check` value, which are stated for other
layouts, as the bit-reversal in §2.3 shows.

### 4.3 Prefixes

**The algorithm names the function applied to each object, and a prefix's value is the SHA-256 of
Part 04 §5.4's listing with each member's value in that algorithm** (preferred direction). A single
object's value is the function of its bytes. The listing is small, so hashing it costs nothing
measurable, and every existing prefix digest is the SHA-256 case unchanged.

**Combine the members' CRCs into one.** Rejected: a combined CRC carries no keys, so it would not
notice a chunk moving between keys, which for a Zarr array is a different array.

**An empty prefix is a finding** (preferred direction). A listing of nothing describes no resource,
and a Zarr array always holds its metadata document.

### 4.4 Member digests

**Member digests stay optional; where members record them, every member records one and the
resource's digest is the one recomputed from the rows** (preferred direction). A validator checks
that in the manifest's `entries` phase without reading any bytes. Whether a partly digested member
list is itself a finding is open question 3.

**A writer that digests an external prefix records the member digests it computed** (preferred
direction). A 64-digit value adds 76 bytes per member, about 190 KB for the 2,496 LFP members,
and lets a consumer check the chunks it fetched without reading the rest, the property R36 §2.2
gives as the reason for the construction.

**Require member digests for packet-owned prefixes.** Rejected: an owned prefix holds three objects
in the packets above, and its resource digest already detects any change.

### 4.5 Whether a digest is present

**Every packet-owned resource records a digest, and its absence is a finding in the `entries`
phase** (preferred direction). The check needs only `external` and the digest member. The reference
writer already records one for every owned resource; a packet built before R52 gains one through
the writer's `verify`, which already fills a missing owned digest.

**Keep "by default".** Rejected: a conforming packet could still make Part 03 §9.4's premise
uncheckable.

**An external resource's digest stays optional**, under the same functions (preferred direction).
Part 04 §5.2's rule that a writer unable to reach a URI records nothing is unchanged.

### 4.6 Verification and ETags

**A validator checks a recorded digest either by recomputing it or by comparing it with the
full-object checksum in the same algorithm that the store reports for each object** (preferred
direction). The report says which, since a store's value establishes what the store received at
upload and relies on the store's own durability since. A member whose store reports no such value is
read. Part 04 §5.3's levels change with this: level 2 and level 3c each become "the recorded digest
holds", reached by either route, and level 3b stays ETag comparison.

**`store_digest` records an ETag verbatim under the algorithm name `etag`** (preferred direction),
never interpreted as MD5. Any ETag changes when an object is rewritten, so a multipart or SSE-KMS
ETag is change evidence too; rewriting identical bytes with a different part size changes it, which
errs toward reporting a change. This lifts R51 §2.2's exclusion of multipart ETags and covers the
102 members it skips.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged; no concept's meaning changes. |
| logical prose, registry declarations, rules | Unchanged; the `sha256` column of `core.source_files` describes a source, not a packet resource, and is left to the source-cache proposal. |
| physical profiles | Affected: Part 03 §1's statement of which part owns the digest, §8.1, §10's obligation and its "whole-file" wording, and §11.3's sentence naming `sha256`. |
| packet manifest and schemas | Affected: Part 04 §§4.1, 5.2, 5.3, 5.4 and 10, and two entries in §11; `manifest.schema.json` under option B, or three sibling members under option A; the delivery schema regenerates from it. Registry descriptors are unchanged. |
| validation and import | Affected: Part 05 §11's sentence on what a recorded `sha256` says. |
| extension registries | Unchanged; no declaration names a digest. |
| validator | Affected: CRC64NVME and CRC32C computation, store-reported checksum comparison, the missing-digest and empty-prefix findings, the partial member-digest check, and ETag recording as `etag`. |
| writer | Affected: `_digest`, `verify` and the LFP source record the digest shape and external member digests; a configurable owned-digest algorithm. |
| reader | Affected only by a manifest schema version under option B; the reader verifies registry digests and reads no resource digest. |
| adapters | Unchanged; an adapter delivers bytes or a resource document, and the delivery schema follows the manifest schema. |
| existing packets | Under option A, unchanged and conforming. Under option B, the four built packets need a manifest rewrite or a rebuild; their values do not change. |
| conformance fixtures and tests | Affected: fixtures gain owned digests; new cases for each algorithm, an empty prefix, a missing owned digest, a partial member list, and a store-reported match. |
| revision tooling | Unchanged. |
| documentation | Affected: Part 08's manifest excerpt and acceptance checklist, and the validator and writer READMEs where they describe `verify` levels. |

A validator distinguishes the proposed rule from the current one on these cases:

- a packet-owned entry without a digest is a finding, where it is now a warning;
- an entry recording CRC64NVME or CRC32C passes where its bytes match and fails where one byte
  differs, and its prefix value equals the SHA-256 of the listing built from member CRCs;
- every SHA-256 value in the four built packets verifies unchanged;
- an empty packet-owned prefix is a finding;
- a member list in which some members record a digest and others do not is handled as open
  question 3 settles;
- a report states whether each digest was recomputed or matched a store's value.

The writer obligation to record external member digests is tested in the writer, not by a fixture.
A store-reported comparison needs an object-store test double or a live bucket.

## 6. Open questions

1. **Manifest shape.** Preferred: option B, a `digest` object on a resource and a `digest` string
   on a member. Option A keeps existing manifests valid without a rewrite at the cost of one member
   per function.
2. **CRC32.** Recommended: admit it. It is botocore's default upload checksum, S3 stores it as a
   full-object value, and its authority is already a normative reference of this specification; the
   cost is one more function and moving RFC 1952's entry to Part 00 §10. Without it, an object
   uploaded through boto3's defaults can be checked only by reading it.
3. **A partly digested member list.** Preferred: a finding, since the resource digest cannot be
   recomputed from rows some of which lack a value, and today such a list goes unchecked.

Overlaps: the build-order draft amends Part 03 §9.5 and Part 05 §§1–8, none of the sections above.
Moving Part 03 §11 into its own part carries §11.3's `sha256` sentence with it. The source-cache
proposal keys cache entries by URI plus store identity and will rely on this proposal's whole-object
functions. This proposal amends R36 §2.2 (the functions), R51 §2.2 (what `store_digest` records) and
R52 §2.1 (whether a packet-owned digest is present).

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
