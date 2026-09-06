# R80 — A Source Resolution Document Locates an External Resource

| | |
|---|---|
| **Status** | **Accepted** 2026-09-05 |
| **Amends** | `03` §"URI rules", R14 §2.3 (the external resource declaration), `04` (manifest schema) |
| **Depends on** | R14 §2.3 (immutability covers packet-owned bytes), R14 §2.3.1, R36 §2.4, R51 §2, R55 §2 (unresolvable as fact or defect) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

### 1.1 One field holds a name and a location

`tables/core/units.parquet` survives being moved because it is a **name**, resolved against a root
the reader supplies when it opens the packet. An LFP series is declared as
`file:///mnt/Data/ephys/776259/…/ElectricalSeries46110-LFP/data`, which survives nothing, because
it is a **location** the writer fixed at build time. Both are the `uri` field of a manifest
resource entry.

Moving a packet is what makes the difference visible. Two were copied to an object store in one
operation, together with the NWB files holding the bytes they reference:

| packet | external resources | what their URIs name |
|---|---:|---|
| `ecephys_776259_2025-04-09_17-25-12` | 12 | `file:///mnt/Data/…` — 12 LFP series |
| `ecephys_786867_2025-09-25_12-43-56` | 14 | `file:///mnt/Data/…` — 10 LFP series, 4 videos |

Twenty-six resources now resolve on one machine. The bytes they name were copied by the same
command that copied the packets, so every reader that can reach a packet can reach them, and
neither manifest can say so.

### 1.2 A location inside the packet is a location that cannot be corrected

R14 §2.3 makes a packet's own bytes immutable, and the manifest is one of them. Any location the
manifest records therefore goes stale and **stays** stale: correcting it is a rebuild, or an R32
amendment for which no `amend` subcommand exists. Recording locations more compactly does not
change that — a `sources` block naming twelve LFP series in one line is still one line inside a
document nothing may edit.

The knowledge that goes stale and the artifact that must not change are different things, so they
belong in different files.

### 1.3 The format already makes reachability the caller's

R14 §2.3.1 declines to promise that external bytes are still there, giving `sha256` and
`verified_at` as a record of what was true rather than a claim about now. That settles whether the
bytes are what they were. It leaves open **where this reader should look**, which the format
answers once, at write time, for every reader that will ever open the packet.

One LFP series at this institute has three locations at once: the canonical `aind-open-data`
prefix, a scratch mirror, and whatever a compute node staged onto local disk before a job ran.
The three hold the same resource and differ in what it costs a reader to reach one. Choosing among
them is the property R14 §2.3 already assigns to the caller, and the choice changes with the
caller rather than with the packet.

### 1.4 Four mechanisms exist, and each puts the knowledge in the wrong file

**A relative external URI** is legal — R14 §2.3 says so in as many words: "a packet may declare a
resource external and still resolve it relatively, which is how a packet published beside its data
records that it does not own it." That covers a referenced resource travelling with the packet in
an unchanged relative arrangement, which these two packets do not have: the build holds them at
`/mnt/Data/776259-packet/packet` against an NWB at `/mnt/Data/ephys/776259/…`, and the store holds
them as siblings under one prefix, so no single relative path is correct in both.

**A rebuild** produces a packet correct for one store and wrong for the next, at the cost of a full
import; 776259 commits in 306 s.

**Editing the manifest in place** is what R14 §2.3 forbids, and R35 §2 spends that prohibition —
an untouched file's verdict is *determined*, which is what keeps an amendment from re-reading
287 M rows.

**A reader-side substitution** works today: `escapewheel-reader` takes a mapping from declared-URI
prefix to replacement at open time, and one entry redirects all twelve LFP series of 776259 to the
store, reading a 2,500 × 8 block out of a 7,983,750 × 96 array in 0.62 s. It touches no bytes and
needs no revision, because it constrains the reader's API rather than the packet. What it costs is
that the caller supplies both prefixes, so the knowledge lives in every consumer's code, repeated
and unversioned.

## 2. Decision

### 2.1 An external resource names a source and a path under it

An external resource entry SHOULD carry `source`, an identifier naming the body of data it belongs
to, where its bytes belong to a nameable one. Where `source` is present the entry's `uri` MUST be a
path relative to wherever that source turns out to be, and MUST NOT be absolute. Neither field is a
location.

SHOULD rather than MUST, because the escape below is real: a packet whose external bytes belong to
no named body of data has nothing to name, and every packet built before this revision has no
`source` and stays conforming.

```json
{
  "resource_id": "core.46110.lfp",
  "kind": "dense_array_asset",
  "external": true,
  "source": "ecephys_776259_2025-04-09_17-25-12_nwb_2026-08-17_09-30-31",
  "uri": "…/processing/ecephys/LFP/ElectricalSeries46110-LFP/data"
}
```

A source name is opaque to this specification. It SHOULD be unique beyond the packet, so that one
resolution document serves many packets; where the source is a named data asset, that asset's name
is the obvious choice and is what the example uses.

An entry carrying no `source` keeps today's meaning exactly: absolute is a location, relative is
relative to the packet root. Every packet built before this revision stays conforming and stays
readable.

### 2.2 A resolution document maps source names to locations, and is not part of the packet

A **resolution document** is a JSON document, conventionally named `sources.json`, whose shape
is published as `registry/sources.schema.json` at `$id`
`https://escapewheel.org/schemas/sources/0.1.0`. It is specified the way `04`'s manifest is, and for
the same reason: two implementations that must agree about a file need a schema rather than a
description.

| Field | Type | Required | Meaning |
|---|---|:---:|---|
| `sources_standard_version` | string | yes | `escapewheel-sources-v0.1`. A reader MUST refuse a version it does not know rather than read the document as if it did |
| `sources` | object | yes | source name to source entry |
| `$schema` | string | no | this document's meta-schema by `$id`. Identity, not a fetch instruction: a reader MUST NOT dereference it and MUST NOT require it (R57 §2) |
| `description` | string | no | whose mirror this is. Read by nothing |

A **source entry** is an object, not a bare URI string, so that a field may be added later without
changing the shape of every document in existence:

| Field | Type | Required | Meaning |
|---|---|:---:|---|
| `uri` | string | yes | where this source is: an absolute URI, or an absolute filesystem path for data staged locally. A resource's own `uri` is a path relative to this |
| `description` | string | no | human context. Read by nothing |

```json
{
  "$schema": "https://escapewheel.org/schemas/sources/0.1.0",
  "sources_standard_version": "escapewheel-sources-v0.1",
  "sources": {
    "ecephys_776259_2025-04-09_17-25-12_nwb_2026-08-17_09-30-31": {
      "uri": "s3://aind-open-data/ecephys_776259_…/ecephys_776259_…_experiment1_recording1.nwb"
    },
    "ecephys_786867_2025-09-25_12-43-56_behavior_videos": {
      "uri": "/scratch/staged/ecephys_786867_2025-09-25_12-43-56/behavior-videos"
    }
  }
}
```

Both objects are closed: an unrecognised field is a defect, as it is in the manifest, because a
misspelled `uri` that validated would resolve nothing and say nothing.

The document MUST NOT be a packet resource. Living outside the packet is the whole point: R14
§2.3's immutability does not reach it, so it may be corrected when a mirror moves, shared by every
packet a site holds, and versioned by whoever operates the storage rather than by whoever wrote the
packet. A packet MUST NOT be invalidated by a resolution document, and validating a packet MUST NOT
require one (§2.4).

A reader MUST accept one or more from its caller. How a caller supplies them — argument,
configuration file, environment — is the reader's business, as credentials have been since
R14 §2.3; §2.3 gives the order they are consulted in.

### 2.3 A packet carries a default resolution document that it does not own

A writer SHOULD write `sources.json` at the packet root, naming every source the packet
references and where it read each one. That file MUST NOT be a declared resource. It sits under
the root so that copying a packet copies it, and outside the manifest so that R14 §2.3's
immutability does not reach it: a mirror that moves is corrected by editing the default in place,
which is the one thing the manifest cannot offer.

The consequences of not owning it are the point and MUST be stated rather than assumed. R52's
checksums do not cover it, structural validation MUST NOT require it, and a reader MUST NOT infer
that the packet vouches for what it says. A default that could be verified could not be corrected.

Resolution order is therefore three lines:

1. the documents the caller supplied, in the order supplied;
2. `sources.json` at the packet root, if it is there;
3. otherwise the source is unresolved, which §2.4 makes a fact.

**Provenance is a separate question with an existing answer.** Where the writer read the bytes is
recorded in `core.source_files`, whose `uri` is required and which already carries `sha256`,
`size_bytes` and `modified_at` (R9 §4). That table is packet-owned and immutable, which is what a
historical record wants and the opposite of what a location wants. Putting the same URI in both is
not duplication under R3 §3.0: one says where the bytes were read from and cannot change, the
other says where to look now and must be able to.

### 2.4 An unresolvable source is a fact, not a defect

A `source` that no available resolution document names MUST be reported as unresolved and MUST NOT
fail structural validation. R55 §2 draws exactly this line: an unresolvable scope is a fact about
the packet's situation, where an unresolvable interval kind is a row nobody can interpret. Which
mirrors a reader can reach is a property of the reader, so a packet does not become invalid by
being read somewhere its data is not.

Structural validation MUST NOT require a resolution document, and MUST NOT reach the network to
check one (R14 §2.3.2 unchanged).

### 2.5 Resolution is by name, and verification stays what R36 and R51 defined

Resolving through a different document MUST NOT be read as invalidating a recorded `sha256`,
`size_bytes` or `members`. Those describe the resource, so a mirror holding different bytes under
the same name is a finding: a reader that verifies a resolved source and finds a mismatch MUST
report it against the resource entry, and MUST NOT silently prefer either the recorded digest or
the bytes it found.

Resolving by **content** would make location irrelevant, and neither half of that is available.
R36 measured a whole-resource digest at 88 s over 6.83 GB, and R51 measured 2,394 of 2,496 members
as single-part, leaving 102 with no store digest to compare at all. So a reference resolves by
name and is verified by digest, which is what the packet could already do.

### 2.6 What a consumer may then do

Read any packet from a mirror by holding one document that names the mirror. Hand a packet to a
compute node that staged its referenced data locally, by pointing that node's document at the
staging directory. Correct a location for every packet at a site at once, by editing one file that
no immutability rule covers — where today the same correction is 26 manifest edits across two
packets, each forbidden.

## 3. What this does not change

- **No new table, no new reference, no vocabulary.** Two string fields on a resource entry, and a
  document the packet does not contain.
- **No packet becomes invalid.** `source` is required only of entries that use it; an entry
  without one resolves as it does today.
- **No change to R14 §2.3.** An external resource is still declared, its bytes are still outside
  immutability, and structural validation still MUST NOT reach the network.
- **No change to packet-owned resources.** Their portability already comes from resolving a
  relative name against a root supplied at open time; this gives references the same shape.
- **No fallback, health checking, or retry policy.** A source resolves to one URI per document,
  and several documents are tried in the order the caller gave. Noticing that a mirror is down and
  deciding how long to wait have been the caller's since R14 §2.3.

## 4. What this adds to the repository

`registry/sources.schema.json` is the published shape, hand-written beside `manifest.schema.json`
and vendored into `escapewheel-reader` by `build.py` exactly as that one is — a vendored copy is a
build artifact, and `check.py` compares it, because a stale copy has broken every packet three
times already (R48, R53, R56). `registry/sources.example.json` is a document that validates, so
the schema is exercised rather than merely well-formed.

`escapewheel-sources-v0.1` joins the version strings that must stay consistent, beside
`escapewheel-portable-v0.1`, `escapewheel-semantic-v0.1` and `escapewheel-logical-v0.1`.

Validation is where the two documents part. `escapewheel validate` checks a packet, and a resolution
document is not in one, so a document is checked against its schema by whatever loads it rather
than by the packet validator. A reader MUST reject a document that does not conform, and MUST NOT
let that rejection change a verdict about the packet.

## 5. Open

- **How a source name stays unique.** §2.1 says SHOULD and recommends the asset's own name, which
  is unique in the ecosystem that prompted this and is not a rule the format can enforce. A
  collision across two sites merging their documents is the failure; nothing here detects it.
- **Whether a default that travels is worse than no default.** A packet copied to a second store
  carries a `sources.json` naming the first, and a reader that finds it stops looking. It is
  editable, which is the whole difference from a manifest entry, but nothing makes anyone edit it;
  the alternative is that a locally built packet needs a second file to be read at all.
