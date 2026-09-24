# Every Packet-Owned Resource Records a Named Whole-Object Digest

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `96f5e5809aedadfd827bfd552797876116e4f5a5` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §10; Part 03 §§1, 10, 11.3, and 12; Part 04 §§1, 4.1, 5.2, 5.3, 5.4, 10, and 11, and a new last subsection of Part 04 §4; Part 05 §11; Part 08 §§3 and 5; `registry/manifest.schema.json` and the delivery schema generated from it |
| **Depends on** | [R36 §§2.1–2.3](../accepted/R36-verifying-an-external-resource.md#2-decision); [R51 §§2.1–2.4](../accepted/R51-what-the-store-already-knows.md#2-decision); [R52 §§2.1 and 2.3](../accepted/R52-immutability-is-a-premise-nothing-checks.md#2-decision); [R130 §§3.1, 3.10, and 3.11](../accepted/R130-a-packet-binds-the-exact-registries-that-declare-its-resources.md#3-decision) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6 |

Section 3 is normative. Sections 1, 2, 5, and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A packet manifest records a digest of a resource's bytes in one member, `sha256`, and the parts
disagree about what that digest covers, whether it is present, and how it can be checked.
[Part 03 §10](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#10-checksums) calls a
packet-owned digest "whole-file, one file per resource", while Part 04 §5.4 defines a prefix's
digest over its members, and every packet the reference writer builds owns one or two Zarr arrays,
each a prefix. Part 03 §8.1 says immutability "is verified rather than assumed" because a writer
records a digest for every packet-owned resource, and
[Part 03 §9.4](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-incremental-revalidation)
bounds revalidation on that premise, yet Part 03 §10 has a writer record one only "by default",
with no requirement keyword.

SHA-256 is the only function a digest can use, so checking a resource held in an object store means
reading every byte of it, although the store already holds a whole-object checksum of each object
it accepted. Part 04 §5.4 also forbids recording an S3 multipart ETag, and lets a member list
record digests for some members and not others.

This revision names the function beside every value, admits three CRCs beside SHA-256, defines a
prefix's digest in each, makes a packet-owned digest required, lets a validator check a digest
against a store's checksum, and has a writer record every ETag verbatim as change evidence.

The change is structural because it replaces rules in existing sections: Part 03 §10's optional
obligation, Part 04 §5.4's SHA-256-only construction and its ETag exclusion, Part 04 §5.3's level
3c, and the `member_digest` check of Part 04 §10. It moves the digest definition out of Part 04
§5, whose subject is external resources, into a new last subsection of Part 04 §4, because the definition governs
packet-owned resources equally. It moves RFC 1952's bibliographic entry from Part 03 §12 to Part
00 §10, because Parts 03 and 04 would both invoke it.

### 1.1 Structural crosswalk

Five affected sections have no canonical anchor: Part 03 §10, Part 04 §§5.2 and 5.4, Part 05 §11,
and Part 08 §5. A metadata-only bootstrap commit adds `ew-owned-resource-digests`,
`ew-external-resource-record`, `ew-prefix-resources`, `ew-writer-acceptance-criteria`, and
`ew-example-acceptance-checklist` before them, and this draft's `Based on` becomes that commit. The
new digest subsection takes `ew-resource-digests` when it is created. No section is retired.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 04 §5.4, the prefix `sha256` construction | move and generalize | a new last subsection of Part 04 §4, `ew-resource-digests` | the listing carries each member's value in the resource's algorithm and is hashed with SHA-256; a prefix holds at least one object | §3.2 |
| none; a single object's digest is implicit in the member name | add | the new digest subsection | four named functions, one value form each, and their check values | §3.1 |
| Part 03 §10, "records a `sha256` … by default" and the skipped-resource count | replace in place | the new digest subsection for presence; Part 03 §10 for what a portable resource's digest covers | a packet-owned resource MUST record a digest | §3.4 |
| [Part 04 §4.1](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-resource-entry-fields), the generated field table and its pointer to Part 03 §10 | regenerate and revise | same section | `digest` replaces `sha256`; the pointer names the new digest subsection | §3.3 |
| Part 04 §5.2, what `sha256`, `size_bytes`, and `verified_at` record | revise in place | same section | names `digest` | §3.3 |
| [Part 04 §5.3](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-external-resource-verification), levels 2 and 3c | replace in place | same section | a recorded digest holds when computed or matched against store checksums, and a report says which | §3.5 |
| Part 04 §5.4, `members`, `store_digest`, and the no-read level | revise in place | same section | members record `digest` in the resource's algorithm, all or none; an ETag is recorded verbatim as `etag` | §§3.3, 3.6 |
| [Part 04 §10](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-manifest-conformance), `packet.resource.member_digest` | replace in place | same section | reads `digest`; a new `packet.resource.digest_missing` | §§3.3, 3.4 |
| [Part 04 §11](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-catalog-normative-references), one entry | extend in place | same section | gains CRC64NVME's and CRC32C's authorities | §3.1 |
| [Part 03 §12](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-portable-profile-normative-references), the RFC 1952 row | move | [Part 00 §10](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-normative-references) | none: the entry's application gains CRC-32 | §3.1 |
| [Part 04 §1](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-catalog-scope) and [Part 03 §1](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-portable-profile-scope), schema `$id`s and member lists | revise in place | same sections | name `manifest/0.5.0`, `resources/0.5.0`, `digest`, and the new digest subsection | §3.3 |
| [Part 03 §11.3](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-referenced-resource-delivery), "`size_bytes` and `sha256` come from" | revise in place | same section | names `digest` | §3.3 |
| Part 05 §11, "a recorded `sha256` therefore says" | revise in place | same section | names a recorded digest | §3.3 |
| [Part 08 §3](../../escapewheel_poc_docs_v0.2/08_example_packet.md#ew-example-packet-catalog) and §5, the example and its checklist | revise the informative text | same sections | the excerpt records `digest` objects, including one for `analysis.spike_events`, which records none | §§3.3, 3.4 |

## 2. Background

Section 2 is informative. Observations were read from the generated parts, the schemas, the
reference implementation, and the packets on local disk at the recorded baseline. Throughputs were
measured on one Intel Core i9-12900K workstation over 512 MiB of random bytes held in memory, best
of three runs, under Python 3.14.7.

### 2.1 Built packets record owned digests, and fixtures record none

Four packets built by the reference writer are on local disk. Each records a SHA-256 for every
resource it owns, none for any resource it references, and no `members` on any entry:

| packet | built | owned, with digest | owned prefixes | external, with digest |
|---|---|---|---|---|
| `df-packet` | 2026-09-06 | 31 of 31 | 2 | 0 of 14 |
| `rebuild-sample/776259` | 2026-09-10 | 42 of 42 | 2 | 0 of 12 |
| `776259-packet` | 2026-09-17 | 42 of 42 | 2 | 0 of 12 |
| `786867-packet` | 2026-09-17 | 42 of 42 | 1 | 0 of 14 |

`776259-packet` owns 46 objects holding 1,219 MB. Its two owned prefixes hold three objects each,
and recomputing their digests reproduces the recorded values. All four manifests predate R130:
each carries `extensions`, `registry_version`, and `required_codecs` and lacks `registries`, and
each fails the current `manifest/0.4.0` schema with 92 to 114 errors. They need a rebuild
whatever this revision decides.

The 31 packet fixtures under `fixtures/packets/` carry 926 packet-owned entries and no prefix, and
none records a digest, because `fixtures/build.py` writes none.

### 2.2 S3 and Google Cloud Storage keep a whole-object CRC

The S3 user guide ("Checking object integrity for data uploads") lists the checksum types each
algorithm supports for a multipart upload:

| algorithm | full object | composite |
|---|---|---|
| CRC64NVME | yes | no |
| CRC32, CRC32C | yes | yes |
| SHA-1, SHA-256, MD5, XXHash, SHA-512 | no | yes |

A single-part upload always stores a full-object value, so on S3 a SHA-256 covers the whole object
only when the object was uploaded in one part. A composite value is derived from the parts'
checksums and changes when an object is copied, although its data does not. S3 attaches a
full-object CRC64NVME when a client sends no checksum, and encodes every value as base64 of the
checksum's big-endian bytes. Reading a value costs one `HeadObject` or `GetObjectAttributes`
request per object, since a `ListObjectsV2` entry names the algorithm without the value. An ETag
is the MD5 of an object's data only for a single-part object stored in plaintext or under SSE-S3.

Clients usually send their own checksum. botocore 1.43.75, the version in the AIND package's
environment, sets `request_checksum_calculation` to `when_supported` and its default algorithm to
CRC32, so an upload through boto3's default configuration stores a CRC32 rather than a
CRC64NVME, and a full-object one where the upload has one part.

Google Cloud Storage gives every object except one encrypted with a customer-managed key a
`crc32c` property, encoded as base64 in big-endian byte order. Azure Blob Storage stores no CRC for
a blob.

### 2.3 A CRC is seven times faster than SHA-256

| function | implementation | throughput |
|---|---|---|
| SHA-256 | Python `hashlib` | 2.4 GB/s |
| CRC64NVME | `awscrt` 0.37.0 | 18.5 GB/s |
| CRC32C | `awscrt` 0.37.0 | 17.9 GB/s |
| CRC32C | `google-crc32c` 1.8.0 | 22.9 GB/s |
| CRC32 | Python `zlib` (zlib-ng 1.3.1) | 17.7 GB/s |

`google-crc32c` is already in the writer's lock as a dependency of `zarr` 3.3.0, and `zlib` is in
the standard library; `awscrt` is not a dependency.

Throughput matters most when the bytes are remote. R52 measured the digest of one packet's owned
bytes at 0.60 s for 1,209 MB read from page cache. Checking `776259-packet`'s owned bytes on S3
against SHA-256 reads 1,219 MB, and against checksums the store holds takes 46 `HeadObject`
requests. R51 measured one session's external LFP arrays at 6.83 GB over 2,496 objects, 102 of
them multipart, and their SHA-256 digest at 75 s from local disk and 88 s from S3.

### 2.4 Check values fix each CRC's form

Each CRC's authority states it for its own transport. RFC 9260 Appendix A maps CRC32C onto an SCTP
packet's bytes, and Figure 153 of the NVM Command Set Specification prints CRC64NVME's `Check` as
`11199E50_6128D175h`, the bit-reversal of the `ae8b14860a799888` that S3 reports for the same
input. The value of the nine ASCII bytes `123456789` pins the form a manifest records. A bitwise
implementation of each CRC from its reflected polynomial, `awscrt` 0.37.0, `google-crc32c` 1.8.0,
and `zlib` agree on:

| algorithm | value of `123456789` |
|---|---|
| `sha256` | `15e2b0d3c33891ebb0f1ef609ec419420c20e320ce94c65fbc8c3312448eb225` |
| `crc64nvme` | `ae8b14860a799888` |
| `crc32c` | `e3069283` |
| `crc32` | `cbf43926` |

The CRC64NVME implementation also gives `6482d367eb22b64e` for 4 KiB of zero bytes, one of the four
vectors in Figure 155 of that specification. Each CRC of an empty input is zero. Converting a
store's value means decoding base64 and encoding hexadecimal: S3's `rosUhgp5mIg=` is
`ae8b14860a799888`.

### 2.5 The reference implementation discards member digests and misreads ETags

The validator computes each member's SHA-256 while digesting a prefix and discards it, and the
writer's external-prefix paths record `members` with sizes and store digests only. An external
prefix digested today therefore records no member digest, and checking three of its chunks later
means reading all of them. The validator records a 32-digit hexadecimal ETag as `md5` whatever the
object's encryption, and skips the 102 multipart LFP members. `packet.resource.member_digest` fires
only when every member records `sha256`, so a partly digested member list goes unchecked. A
packet-owned resource without a digest is reported as a warning.

### 2.6 Alternatives

Keeping SHA-256 alone makes checking a stored resource cost a full read of it, where the store
would answer one request per object. Admitting MD5, SHA-1, or a composite value fails because a
composite depends on part size and no store keeps MD5 or SHA-1 whole for a multipart object.
Leaving the algorithm open fails because a validator cannot check a function it cannot compute.
Sibling members `sha256`, `crc64nvme`, and `crc32c` would keep every existing manifest valid, but
every built manifest already fails the current schema, and each further function would add a
member where a `digest` object adds an enumeration value. Combining the members' CRCs into one
CRC misses a chunk moving between keys, which makes a different Zarr array. Requiring member
digests on every prefix adds nothing for a packet-owned array, whose three objects the resource
digest already covers. Keeping "by default" leaves Part 03 §9.4's premise uncheckable on a
conforming packet.

A 64-bit or 32-bit CRC misses a random corruption with probability 2^-64 or 2^-32 and detects every
burst no longer than its width, which suffices for change detection: bit rot, an overwrite, an
incomplete copy, or an external resource drifting. Its weakness against chosen inputs concerns
identity across packets and tampering, and neither is a digest's purpose here, since whoever can
rewrite a resource can rewrite the manifest.

### 2.7 Overlap

A draft on the Zarr reader floor amends Part 03 §§6.4 and 12 and Part 05 §5.3. Both drafts edit
Part 03 §12's table, the other adding codec rows and this one moving the RFC 1952 row out, so they
commute. The proposal on nomenclature references would add an entry kind to Part 00 §10, where this
draft adds a row. A proposed move of Part 03 §11 into its own part would carry §11.3's sentence
naming `digest` with it, and a proposed source cache keyed by URI and store identity would rely on
§3.1's whole-object functions. `core.source_files.sha256` describes a source rather than a packet
resource and is unchanged.

## 3. Decision

Six subsections define the digest functions and a prefix's digest, state the manifest's
representation, require a packet-owned digest, and say how a validator checks a digest and what a
store digest records.

### 3.1 Digest functions

A resource digest names its function, its **algorithm**, which is one of:

| algorithm | function | authority | single-object width |
|---|---|---|---|
| `sha256` | SHA-256 | FIPS 180-4 | 64 digits |
| `crc64nvme` | the NVMe 64-bit CRC | NVM Express NVM Command Set Specification, Revision 1.2, §5.3.1.3 | 16 digits |
| `crc32c` | CRC32C | RFC 9260, Appendix A | 8 digits |
| `crc32` | the gzip CRC-32 | RFC 1952, §8 | 8 digits |

A single object's digest value is the function of the object's bytes, written as lowercase
hexadecimal of exactly the width above, most significant digit first. For a CRC, the digits are
the checksum as an unsigned integer. The value of the nine ASCII bytes `123456789` is
`15e2b0d3c33891ebb0f1ef609ec419420c20e320ce94c65fbc8c3312448eb225` under `sha256`,
`ae8b14860a799888` under `crc64nvme`, `e3069283` under `crc32c`, and `cbf43926` under `crc32`.

Part 04 §11 lists FIPS 180-4, the NVM Command Set Specification, and RFC 9260 as exact entries.
RFC 1952 has one shared exact entry in Part 00 §10, applied to the gzip member format of a bound
registry and to CRC-32.

### 3.2 Prefix digests

A resource whose URI names a prefix holds one or more objects; a prefix holding none does not
exist, and a validator reports it as it reports a resource that does not exist.

A prefix's digest value is the SHA-256 of the UTF-8 encoding of
`[["<key>",<size>,"<value>"], ...]`, where each `<value>` is that object's digest value under the
resource's algorithm. The listing is compact JSON with `,` and `:` separators, no whitespace, and
ASCII-escaped keys, with one entry per object, `<key>` relative to the resource's URI with `/`
separators, and entries sorted by `<key>` in byte order. A prefix's value therefore has 64 digits
under every algorithm. `size_bytes` is the sum of the objects' sizes.

### 3.3 Manifest representation

A resource entry records its digest as `digest`, an object carrying `algorithm` and `value`, in
place of `sha256`. A member of `members` records its object's single-object value as `digest`, a
string under its entry's algorithm, in place of `sha256`. A registry descriptor's `sha256` is
unchanged.

`registry/manifest.schema.json` takes the `$id` `https://escapewheel.org/schemas/manifest/0.5.0`
and changes as follows:

- `$defs/digest` is a closed object requiring `algorithm`, one of `sha256`, `crc64nvme`, `crc32c`,
  or `crc32`, and `value`, a string. Its `value` matches `^[0-9a-f]{64}$` under `sha256`,
  `^(?:[0-9a-f]{16}|[0-9a-f]{64})$` under `crc64nvme`, and `^(?:[0-9a-f]{8}|[0-9a-f]{64})$` under
  `crc32c` and `crc32`.
- `$defs/resource` replaces `sha256` with `digest`, a `$ref` to `$defs/digest`, and requires
  `members`, where present, to hold at least one item.
- `$defs/member` replaces `sha256` with `digest`, a string matching `^[0-9a-f]+$`.
- `$defs/resource` adds three conditions: where the entry records `digest` and `members`, every
  member requires `digest`; where it records no `digest`, no member records one; and each member's
  `digest` matches the single-object width of the entry's algorithm.
- `verified_at`'s description names `digest` in place of `sha256`.

The delivery schema Part 03 §1 incorporates regenerates from it with the `$id`
`https://escapewheel.org/schemas/resources/0.5.0`, and its entry admits `digest` in place of
`sha256`.

A checker reports `packet.resource.member_digest` in the `entries` phase when an entry records
`digest` and `members` and its value differs from the §3.2 value of that member list.

### 3.4 Presence

A writer MUST record a `digest` for every resource the packet owns. An external resource's
`digest` is optional, and Part 04 §5.2's rule that a writer unable to reach a URI records nothing
is unchanged. A checker reports `packet.resource.digest_missing` in the `entries` phase for each
entry that does not declare `external: true` and records no `digest`.

In the portable profile a packet-owned table's digest covers its one Parquet file and a
packet-owned array's covers its Zarr prefix under §3.2. A writer MAY record any admitted algorithm.

### 3.5 Verification

A validator MAY establish that a recorded digest holds by comparing it with checksums the store
reports, object by object, in place of computing it from the bytes. A store's checksum counts only
where the store reports it as a full-object value in the resource's algorithm; a validator MUST
NOT compare a composite value, and MUST read any object for which the store reports no full-object
value. For a single object it compares the store's value, converted to §3.1's form, with the
recorded value. For a prefix it builds §3.2's listing from those values and compares its SHA-256.

A report MUST state, for each digest it establishes, whether the validator computed it, matched
the store's checksums, or combined the two. Part 04 §5.3's level 2 establishes that packet-owned
resources' recorded digests hold, and level 3c that an external resource's recorded digest holds,
each reached by either route. Level 3b remains the comparison of recorded store digests.

### 3.6 Store digests

A member's `store_digest` records evidence that an object changed in place. A writer MUST record a
store's entity tag, where it records one, verbatim under the algorithm `etag`, whether the object
was uploaded in one part or several and whatever its encryption. A writer MUST NOT record an entity
tag under any other algorithm name, and a validator MUST NOT read one as a digest of the object's
bytes. A store digest never establishes that a `digest` holds, and Part 04 §5.4's requirement that
a report not call a store-digest pass a checksum verification stands.

## 5. Consequence

The change is incompatible in manifest shape. Every generated manifest and delivery document is
regenerated, and each existing SHA-256 value carries over as
`{"algorithm": "sha256", "value": …}` without recomputation. The four built packets need a rebuild
under R130 regardless, and the rebuild writes the new shape. The reader is unchanged, because it
reads the manifest without the schema and verifies only registry descriptors' digests.

An independent validator gains three CRCs, the store-checksum route, and one entries check. An
independent writer can keep SHA-256 alone. A packet-owned resource without a digest now fails
manifest conformance where it drew a warning, and since an `entries` finding withholds the later
phases, such a packet gets no declaration findings until it is corrected.

R36 §2.2's construction is generalized to the admitted algorithms and moves to Part 04's new
digest subsection. R51 §2.2's rule that a writer record only a single-part content-hash ETag is
replaced by §3.6, and its open `algorithm` string stands. R52 §2.1's SHOULD becomes §3.4's MUST,
which the ledger already records as compiled. No clause is superseded whole; the ledger entries of R36 §2.2, R51 §2.2, and
R52 §§2.1 and 2.3 gain notes, and 27 numeric destinations in the affected sections migrate to
their canonical anchors.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. No concept's meaning changes. | None required. |
| logical prose and registry | Unchanged. `core.source_files.sha256` describes a source, and no declaration names a resource digest. | None required. |
| physical profiles | Part 03 §1 names `resources/0.5.0`, `digest`, and Part 04's new digest subsection; §10 states what a portable resource's digest covers and loses its optional obligation and skip count; §11.3 names `digest`; §12 loses the RFC 1952 row. | `evidence/R<N>.json` owners by anchor. |
| packet manifest and JSON Schemas | Part 04 gains a digest subsection at the end of §4; §§1, 4.1, 5.2, 5.3, 5.4, 10, and 11 change as §1.1 lists. `manifest.schema.json` changes as §3.3 states, and `registry/build.py` regenerates the delivery schema at `resources/0.5.0` and Part 04's field tables. `registry/resources.example.json` names the new `$id`. | `registry/check.py`; the vendoring check; `registry-targets.toml` pointers for §3.3. |
| validation and import | Part 05 §11 names a recorded digest. Part 05 §5.3's shim still checks digests outside SQL. | Covered by the validator tests below. |
| extensions | Unchanged. No extension registry declares a digest, and an extension resource's entry follows the same schema. | The AIND suite, which builds manifests through the writer. |
| reader, writer, validator, adapters | The reader is unchanged. The writer records `digest` objects for owned resources in SHA-256, and its `verify` command and LFP source record external member digests beside the resource digest and ETags as `etag`. The validator computes the four functions, checks against store-reported full-object checksums, reports its route, adds `packet.resource.digest_missing`, revises `packet.resource.member_digest`, reads an empty prefix as missing, and records ETags as `etag`. Adapters that deliver a resource document emit `digest` in place of `sha256`. | Writer, validator, and AIND suites. |
| conformance fixtures and tests | `fixtures/build.py` records a digest for every owned resource. New fixtures cover an owned entry without a digest, an entry with members missing some digests, a CRC64NVME, a CRC32C, and a CRC32 resource that pass and fail by one byte, a CRC-algorithm prefix whose value is the listing's SHA-256, and a member digest of the wrong width. Validator tests cover a store-checksum match with an object-store double, a composite value refused, an empty owned prefix, and a report's route. Writer tests cover external member digests and a multipart ETag recorded as `etag`. | The conformance corpus and package suites. |
| revision process and tooling | `framework.py`'s reference allocation moves RFC 1952 to Part 00 and adds Part 04's two rows. The ledger changes as stated above. | `framework.py`, `ledger.py`, and `evidence.py`. |
| generated publications and developer documentation | The combined specification and heading index regenerate. Part 08 §§3 and 5 show `digest`. The validator and writer READMEs describe the verification route and `verify`. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied`, each by its canonical anchor: §3.1 at `ew-resource-digests`, Part 04
§11, and Part 00 §10; §3.2 at `ew-resource-digests`; §3.3 at Part 04 §§1, 4.1, 5.4, and 10, whose
evidence also names the manifest schema's pointers; §3.4 at `ew-resource-digests`, Part 04 §10,
and Part 03 §10; §3.5 at Part 04 §5.3; and §3.6 at Part 04 §5.4.

The negative cases distinguish the new rule from the current one:

- a packet-owned entry without a digest yields `packet.resource.digest_missing`, where it now yields
  a warning;
- an entry recording `digest` and `members`, one member lacking `digest`, fails the schema, where
  it now goes unchecked;
- a member digest whose width differs from its entry's algorithm fails the schema;
- a resource whose bytes differ by one byte from a recorded CRC64NVME, CRC32C, or CRC32 value fails
  the digest check;
- an empty packet-owned prefix is reported as missing, and an empty `members` array fails the
  schema; and
- a store that reports only a composite checksum does not satisfy level 3c without a read.

The positive cases are a resource recording each CRC over matching bytes; a CRC-algorithm prefix
whose value is the SHA-256 of the listing built from member CRCs; every SHA-256 value carried from
a built packet verifying unchanged; a digest matched against a store's full-object checksums with
the report naming that route; and a multipart ETag recorded as `etag` and compared at level 3b.
