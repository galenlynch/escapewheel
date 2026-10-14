# A reader takes a bound registry from any copy matching its digest

| | |
|---|---|
| **Status** | **Accepted** 2026-10-14 |
| **Opened** | 2026-10-14 |
| **Based on** | `b18c7786154643360120538b38f1b79bdc6a888e` |
| **Change form** | ordinary |
| **Amends** | Part 03 §3.2; Part 04 §10 |
| **Depends on** | None |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Problem

A packet's manifest binds each registry by a descriptor carrying its path in the packet and the
SHA-256 digest of its decompressed document (Part 04 §8). Part 04 §10 has a reader resolving a
declaration acquire the bound registry through that descriptor and verify its digest, and Part 03
§3.2 forbids a reader to resolve a bound registry from anywhere else. A reader therefore fetches
every registry it needs from every packet it opens, even when it already holds the exact bytes
the descriptor's digest names.

Over an object store that fetch is a dependent round trip. Only the manifest records the
descriptor's path, and Part 03 §3.1's layout is a recommendation whose path also carries the
registry's version, so a reader cannot know what to request until the manifest has arrived. A cold open that needs any declaration
waits on at least two round trips in series: the manifest, then the registries. Content class,
selection by class, discriminators, references and declared columns all need a declaration.

The change concerns where a reader may obtain a bound registry's bytes. That a packet stores every
registry it binds, how the copy is stored, and what a validator checks are unchanged. Two further
round trips the reference reader spends are implementation choices, outside this change, and
recorded in §2.

## 2. Evidence

Observations are of the tree at the commit this document is based on.

- The reference reader, instrumented to log each read on `fixtures/packets/valid` (30 tables, core
  and `dynamic_foraging` bound), reads in series: on opening, the configured `sources.json`, then
  `sources.json` at the packet root, then `packet.json`; on the first selection by content class,
  the core registry, then the `dynamic_foraging` registry. Over a store that is four dependent
  round trips before the first class-aware result. Two of them need no specification change: Part
  04 §5.5 ranks resolution documents without saying when they are read, so `sources.json` can wait
  until an entry's `source` is resolved, and every bound registry can be requested concurrently
  once the manifest has arrived. That leaves two, and the second is the one this change removes.
- The 144 corpus manifests under `fixtures/packets/` and `conformance/` bind one core digest
  between them, and 143 of them one `dynamic_foraging` digest. A reader opening many packets built
  from one release fetches the same bytes from each.
- `spec/artifacts/logical_schemas.json`, the incorporated core registry, has that core digest, and
  the validator package already ships a byte-identical copy. A reader shipping the same copy needs
  no registry request for a packet bound to the current core release, even on its first open.
- A digest identifies bytes where a version does not. Part 05 §15.3 refuses two digests under one
  registry ID and version only within one packet, so two packets may bind different documents
  under the same ID and version; any copy a reader reuses has to be keyed by digest.
- The digest covers the decompressed document (Part 04 §8), so a copy matches regardless of the
  gzip header or compression level of the packet's stored member.
- R130 §2.2 rejected binding a registry by reference to a release because a packet would then be
  unreadable to a consumer lacking that release. This change keeps the stored copy mandatory, so
  any reader can still read every packet from its own bytes.
- The round trip's duration is the store's latency for one small object, and was not measured
  here.

Alternatives:

- **Keep the current rule, with concurrent requests.** A cold open costs two dependent round trips
  for good, whatever the reader already holds.
- **Carry resolved declaration facts in the manifest entry.** The declaration stops being the one
  owner of content class, kind and lineage policy (Part 04 §4.2), and every reader still fetches
  the registry for columns, references and discriminators.
- **Embed the registries in the manifest.** About 20 KB gzipped of core per packet enters
  `packet.json`, and the manifest's size then grows with the registry rather than with the packet.
- **Request the registries speculatively by the recommended layout.** A reader may already do
  this, since it resolves the registry through the descriptor once the manifest arrives and uses
  the bytes only where the paths agree and the digest matches. A guess has to name a version,
  though, and the version a reader can guess is its own, which is the case a bundled copy covers
  without any request.

## 3. Decision

### 3.1 A reader takes a bound registry from any copy matching its digest

A reader resolving a declaration MUST use, as the bound registry that declares it, a document
whose SHA-256 equals its descriptor's `sha256`. Where the reader already holds such a document,
from any source, it MAY use it without acquiring the stored copy. Otherwise it MUST acquire the
stored copy through the descriptor, decode it as the packet's physical profile requires, and
verify its digest, and where that copy is missing, unreadable, or fails the digest, it MUST fail
the operation that needed it and name the registry ID. A reader MUST NOT use a document whose
digest differs from the descriptor's or silently omit a bound registry, and need not report where
a document it used came from. No checker verifies which document a reader used.

### 3.2 The portable profile's stored copy binds a writer and a validator

A conforming packet MUST contain every bound registry. A writer MUST NOT bind a registry by remote
location or omit the stored copy, and a validator MUST NOT resolve a bound registry from anywhere
else. A reader obtains a bound registry under Part 04 §10.

## 4. Questions

1. Does a reader holding a matching copy still owe a failure where the packet's stored copy is
   missing or damaged?
   **Answered 2026-10-14:** No. A document matching the digest is the document the packet binds,
   so declaration lookup cannot differ, and checking the stored copy would spend the round trip
   the change saves. A validator still reports `packet.registry.missing`,
   `packet.registry.unreadable` and `packet.registry.digest`.
2. Does the rule name the places a copy may come from, or state only the digest condition?
   **Answered 2026-10-14:** The digest condition alone, so a reader's cache, a copy bundled with
   it and a copy its caller supplies need no rule each.
3. Does the reader report that it used a copy other than the packet's?
   **Answered 2026-10-14:** No. The bytes are identical, so the report would carry nothing a caller
   could act on.

## 5. Consequence

No packet, registry or schema changes, and every packet now conforming stays so. A reader that
acquires every stored copy stays conforming. A reader holding a matching copy reads a packet whose
stored registry copy is missing or damaged, where today it fails; a validator still rejects that
packet.

A validator built on a reader has to acquire each stored copy itself under §3.2 and Part 05 §14.5,
since a reader's matching copy would hide `packet.registry.missing`. The reference validator opens
packets through the reference reader, so its acquisition path cannot take the reader's copies.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged: no concept's meaning moves. | None required. |
| logical prose and registry | Unchanged: a declaration's content and lookup are unchanged. | None required. |
| physical profiles | Part 03 §3.2's second paragraph takes §3.2's text; its storage rule and the conforming packet's obligation stand. | `spec/tools` checks. |
| packet manifest and JSON Schemas | Part 04 §10's paragraph on a reader resolving a declaration takes §3.1's text. The descriptor and the manifest schema are unchanged. | `spec/tools` checks. |
| validation and import | Unchanged: Part 05 §14.5 already forbids a validator to substitute a bundled, caller-supplied or remotely resolved registry, and a writer still stores each one. | The validator suite's missing-registry tests. |
| extensions | Unchanged: an extension registry is acquired under the same rule as core. | None required. |
| reader, writer, validator, adapters | The reference reader ships the incorporated core registry and keeps verified registry documents by digest across the packets it opens, consulting them before the stored copy. The reference validator acquires stored copies only. The writer is unchanged. | The reader and validator suites. |
| conformance fixtures and tests | Reader tests for §6's cases. The corpus is unchanged, since it judges packets and a packet's verdict does not move. | The reader and validator suites. |
| revision process and tooling | The ledger places §§3.1 and 3.2. | `ledger.py`, `evidence.py`. |
| generated publications and developer documentation | The combined specification regenerates, and the reader's README states which copies it holds and where it keeps them. | `verify.py`. |

## 6. Conformance and implementation evidence

These cases distinguish the new rule from the current one, and each is a reader or validator test
rather than a corpus packet, since no packet's verdict changes:

- a reader holding a copy whose digest matches resolves a declaration without reading the stored
  copy;
- a reader holding a copy under the same registry ID and version whose digest differs ignores it
  and acquires the stored copy;
- a packet whose stored core copy is deleted resolves its declarations through a reader holding a
  matching copy, and fails naming `core` through a reader holding none;
- a packet whose stored copy fails its digest, and for which the reader holds no matching copy,
  fails naming the registry ID; and
- a validator holding a matching core copy, run on a packet whose stored core copy is deleted,
  reports `packet.registry.missing`, as
  `escapewheel-validator/tests/test_validator.py::test_a_missing_bound_registry_fails_the_packet`
  asserts today.

The probe of §2 counts reads by patching the reader's location reads, and establishes the round
trips the reference reader spends; a test asserting no read of the stored copy uses the same
technique.
