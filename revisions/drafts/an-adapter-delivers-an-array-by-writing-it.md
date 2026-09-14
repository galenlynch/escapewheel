# An Adapter Delivers an Array by Writing It

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Part 03 §11.3 (how a dense array's reference reaches a build, and what a delivery says about a referenced one), Part 03 §11.4 (a second reserved resource identifier) |
| **Depends on** | R115 §3.8 (a dense array crosses as a reference rather than as rows), R115 §3.3 (rows cross by a protocol of a group, each carrying a resource by name), R52 §2 (a build digests the bytes a packet owns), R51 §2 (a referenced prefix may record its members), R80 §2.2 (a referenced resource may name a source rather than a location) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

This settles how a dense array or a media asset reaches a build from an adapter running out of
process, which Part 03 §11.3 leaves open. It changes nothing about what a packet holds: no manifest
field, no column, no table and no rule.

## 2. Motivation

### 2.1 Three adapters wait on a channel the profile leaves unnamed

Part 03 §11.3 says an adapter's arrays MUST NOT cross as rows, and that a dense array crosses as a
reference: its `array_asset_id`, the layout the adapter chose, and a location. It does not say
through what. Rows are excluded by the sentence itself, and no other channel is named, so an
adapter with an array to deliver has nowhere to put the reference.

Three of the ten adapters the reference implementation ships are stopped there, and they are the
three that hold the bulk of a session. Measured on `ecephys_786867`, an AIND ecephys session of ten
probes: the waveform adapter writes **one packet-owned array** of shape `[4505, 26, 150]` —
17,569,500 values, 12.8 MB written — and the LFP and video adapters reference **10 arrays and 4
media assets** between them, which is why a packet whose tables are 1.2 GB points at 6.8 GB it does
not copy.

### 2.2 A written array declares its own layout

An array written as Zarr v3 states in its own `zarr.json` everything the manifest says about it
except what the build decides. Read off the packet-owned array above: `zarr_format` 3, `data_type`
`int16`, `shape`, `fill_value` 0, a chunk of `[1, 26, 150]` inside a shard of `[4096, 26, 150]`, and
a codec chain of `sharding_indexed` wrapping `blosc`.

Its manifest entry carries eleven fields, and every one of them is recoverable from that array and
the name it was written under. `physical_profile` is `zarr_format`. `codecs` is the chain's names,
outermost first, descending through the shard — measured against the entry, both are
`['sharding_indexed', 'blosc']`. `size_bytes` and `sha256` are the bytes, which a build digests for
anything the packet owns whatever wrote it (R52 §2). The remaining six are the build's own:
`resource_id`, `layer`, `kind`, `uri`, `canonical` and `validation_state`.

So a reference for a packet-owned array would restate what the array declares, which R3 §3.0
refuses, and it would introduce the one thing worse than restating: two statements that can
disagree, one of them checkable and one of them not.

### 2.3 A referenced resource states what no row carries

A referenced resource is the other case, and it inverts. Much of what a manifest says about one
crosses already, because an array and a media asset each have rows: `core.array_assets` carries
`uri` alongside the asset's identity, `core.media_assets` carries `uri` and `format`, and both are
populated — **11 of 11** array rows and **4 of 4** media rows in the packet measured. An adapter
delivering rows delivers the location with them.

What no row carries is what the producer learned by opening the store. Per referenced array the
manifest holds five such facts — `codecs`, `physical_profile`, `size_bytes`, `verified_at` and
`external` — and they are not a table's to hold: a resource's location, its codecs and what was
true of its bytes when someone looked are the catalog's (Part 04 §5), and a column restating them
is the duplication R3 §3.0 refuses. Nor can a build recover them. Structural validation MUST NOT
reach the network (Part 04 §5.3); the referenced arrays here are `zarr_v2` where the packet's own
are v3, so the profile is not a constant; and R36 §2.4 and R51 §2 exist because a store may not
answer twice.

A build could open the store itself rather than being told. That is the work the adapter was run to
do, done a second time and over the network, and it fails exactly where Part 04 §5.3 says a build
must not go.

## 3. Decision

### 3.1 A packet-owned array crosses as bytes under the supplied location

Where the packet will own a dense array, a build **MUST** supply `array_location`, a directory under
the staging area (Part 05 §1), and the adapter **MUST** write each array it delivers into that
directory as Zarr v3 (Part 03 §6.1), in a directory named by the array's `array_asset_id` with the
suffix `.zarr`. A build **MUST** take that name as the asset's identifier.

Nothing else crosses for such an array. A build **MUST** settle the manifest entry by reading what
was written — `physical_profile` from the array's `zarr_format`, `codecs` from its codec chain
outermost first and descending through a shard, and `size_bytes` and `sha256` from the bytes — and
**MUST NOT** require an adapter to state any of them.

An array written this way is validated as one written in process is: a build's own checks run over
every staged resource whatever produced it (R109 §3.5), so a rank, a codec outside the floor or a
profile below Part 03 §6.1 is a finding rather than something an adapter is trusted about.

### 3.2 A referenced resource crosses with the delivery

Where a resource is external (Part 04 §5.1), a build supplies no location and the adapter writes no
bytes, so what the catalog needs has nowhere to come from but the adapter.

An adapter that delivers a referenced resource **MUST** deliver a **resource document** with it,
under the reserved resource identifier `resources`: one entry per such resource, each a manifest
resource entry as Part 04 §5 declares one — `resource_id`, `external`, `uri`, and whatever the
producer established of `physical_profile`, `codecs`, `source`, `sha256`, `size_bytes`,
`verified_at` and `members`. A build **MUST** merge each entry into the manifest it writes, and
**MUST NOT** require any field but `resource_id` and `uri`: a writer that cannot reach a URI records
nothing rather than copying a value from a local stand-in (Part 04 §5.2), which is a fact about the
store rather than a failure of the run.

**It travels the way every other resource travels.** Under `files-v0.1` it is a file named
`resources.json` under the delivery root; under `stream-v0.1` a stream whose `resource_id` metadata
is `resources`; under `flight-v0.1` a descriptor of that name, which `ListFlights` reports and
`DoGet` fetches as it does any other. A resource identifier is dotted, so no undotted token can
collide with it — the argument §11.4 already makes for `end`.

**Nothing about it is a second mechanism**, and that is the point. It needs no term of its own,
because a build already supplies where a delivery goes; no action of its own, because a descriptor
is the format's and inventing a key is what §11.1's choice of Flight avoided; and no rule of its
own about arriving, because a resource that does not arrive is already a failed run (Part 05 §4.4).
A build **MUST NOT** count it among the resources the recipe left the source owning, since it is
what the delivery says *about* them.

**It is not a report, and the difference is why it is not in one.** A report is a courtesy: a build
MUST NOT require one and MUST NOT fail on its contents (Part 09 §5.8), so a fact a packet's catalog
cannot be written without has no business in it — and for these arrays the absent fact is not a
missing one but a false one, `physical_profile` being `zarr_v2` where a default would say v3.

Manifest entries rather than a vocabulary of this revision's own, because a build already writes
exactly this shape. Under a protocol that carries Arrow, the document travels as text in a
single-row table rather than as a column per field: the manifest's schema then stays the one
description of an entry, where a column per field would be a second one to keep in step with it,
and `members` is a list no column holds.

### 3.3 A resource document has a published shape

The shape of a resource document **MUST** be published as `registry/resources.schema.json`, as
Part 04 §5.5 publishes the source resolution document's shape and Part 03 §11.5 the adapter
declaration's, and a build **MUST** refuse a document that does not satisfy it, naming what is
wrong, before it writes a manifest.

Refused rather than reported, which is the opposite of what a build does with a report and for the
same reason: this is the catalog's own content arriving from elsewhere, and a malformed entry
merged into a manifest is a packet that misdescribes its own resources. The manifest's schema
already describes an entry, so this one is a wrapper around it rather than a second description of
the same thing.

## 4. What this does not change

- **The manifest gains no field.** §3.2 has manifest entries arriving from an adapter, which
  invites the reading that the manifest is what grew. It is not: every field named there is one
  Part 04 §5 already declares, and this says which channel fills it for a source that ran
  elsewhere.
- **The layout stays the adapter's choice.** §3.1 has a build read chunking, sharding and codecs
  back off the array rather than stating them, which invites the reading that the build now decides
  them. The adapter decides, as Part 03 §11.3 says; reading them back is how a build learns what
  was decided.

## 5. Consequence

**The three adapters holding a session's bulk become deliverable.** The waveform adapter writes its
array into the location it is given; the LFP and video adapters deliver what they found at the
store they read. Their references stop being the reason a source must run in the writer's process.

**A packet is unchanged, and nothing is rebuilt.** No table, column, reference, rule or vocabulary
moves, and the manifest a build writes is the one it writes today: this is a channel for facts that
already have a home.

**The report is unchanged.** It keeps carrying `problems`, `read` and `stated`, and nothing here
leans on it.

**The location is stated twice, and this does not settle which is right.** `core.array_assets.uri`
and the manifest entry's `uri` hold the same location, and §2.3 leans on the row's copy for what a
consumer does while §3.2 fills the manifest from the delivery. Striking one of the two is a question
about Part 04 and the tables rather than about this channel, and it is left where it was found.

**The reference implementation changes on both sides of the boundary.** Its `StagedArray` carries
values and a layout, and an adapter delivering out of process writes the array rather than handing
the values over; its `ExternalArray` and `ExternalMedia` become what an entry of the resource document parses
into.
The in-process path keeps both objects and is untouched, which is what keeps a recipe free to run a
source either way.

**The schema is a new artifact with three hookups**, which `registry/sources.schema.json` is the
template for: hand-written beside `manifest.schema.json`, copied by `build.py`'s `VENDORED` map into
the package that reads it — the writer, since a build is what merges a resource document — and
checked by `check.py` against an example.

**One measurement should be taken again at acceptance.** The packet measured here holds one
packet-owned array; the second packet holds none, and a session with per-unit waveforms from more
than one sorting would hold several. The rule is indifferent to the count — each array is a
directory under the supplied location — but the claim that eleven manifest fields are all
recoverable was checked against one array, and checking it against several costs a minute.
