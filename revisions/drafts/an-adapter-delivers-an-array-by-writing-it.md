# An Adapter Delivers an Array by Writing It

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Part 03 §11.3 (how a dense array's reference reaches a build), Part 09 §5.8 (what a run's report carries) |
| **Depends on** | R115 §3.8 (a dense array crosses as a reference rather than as rows), R115 §3.11 (a report is the channel for what a build cannot derive), R52 §2 (a build digests the bytes a packet owns), R51 §2 (a referenced prefix may record its members), R80 §2.2 (a referenced resource may name a source rather than a location) |
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

### 2.3 A referenced resource states what no build can look up

A referenced resource is the other case, and it inverts. Its location looks as though it crosses
already: `uri` is declared on `core.array_assets` and on `core.media_assets` and is populated in
**11 of 11** array rows and **4 of 4** media rows of the packet measured, so an adapter delivering
rows is delivering the location with them.

That copy is the consumer's, and it does not reach the manifest. A row identifies its asset by
`array_asset_name`, which is the name the source used — `ElectricalSeries46101-LFP` — where the
manifest entry for the same array names `46101.lfp`, and **0 of 11 rows join to a manifest entry by
name**. A build filling a manifest entry from the rows would have to guess which row is which
resource.

What no row carries at all is what the producer learned by looking at the store. Per referenced
array the manifest holds five such facts — `codecs`, `physical_profile`, `size_bytes`,
`verified_at` and `external` — and a build cannot recover them: structural validation MUST NOT
reach the network (Part 04 §5.3), the referenced arrays here are `zarr_v2` where the packet's own
are v3, and R36 §2.4 and R51 §2 exist precisely because a store may not answer twice.

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

### 3.2 A referenced resource's manifest facts cross in the report

Where a resource is external (Part 04 §5.1), a build supplies no location and the adapter writes no
bytes, so what the manifest needs has nowhere to come from but the adapter.

It crosses in the run's report (Part 09 §5.8), in an optional `referenced` array: one entry per
resource, keyed by the `resource_id` the entry is for, carrying `uri` and whatever else the producer
established — `physical_profile`, `codecs`, `source`, `sha256`, `size_bytes`, `verified_at`,
`members`. The location is among them rather than being taken from the row that also carries it,
because the two are addressed differently and §2.3 measures that they do not join. A build **MUST** read that entry into the
resource's manifest entry, and **MUST NOT** require any field of it: a writer that cannot reach a
URI records nothing rather than copying a value from a local stand-in (Part 04 §5.2), which is a
fact about the store rather than a failure of the run.

A build **MUST NOT** treat an entry naming a resource the delivery did not carry as a failure of
the run, and **MUST** report it: an adapter that names a resource it did not deliver has said
something about a resource this build has no row for, and the mismatch is worth a line rather than
a refusal.

## 4. What this does not change

- **The manifest gains no field.** §3.2 adds a report key carrying manifest facts, which invites
  the reading that the manifest is what grew. It is not: every field named there is one Part 04 §5
  already declares, and this says which channel fills it for a source that ran elsewhere.
- **The layout stays the adapter's choice.** §3.1 has a build read chunking, sharding and codecs
  back off the array rather than stating them, which invites the reading that the build now decides
  them. The adapter decides, as Part 03 §11.3 says; reading them back is how a build learns what
  was decided.

## 5. Consequence

**The three adapters holding a session's bulk become deliverable.** The waveform adapter writes its
array into the location it is given; the LFP and video adapters report what they found at a store
they read. Their references stop being the reason a source must run in the writer's process.

**A packet is unchanged, and nothing is rebuilt.** No table, column, reference, rule or vocabulary
moves, and the manifest a build writes is the one it writes today: this is a channel for facts that
already have a home.

**The reference implementation changes on both sides of the boundary.** Its `StagedArray` carries
values and a layout, and an adapter delivering out of process writes the array rather than handing
the values over; its `ExternalArray` and `ExternalMedia` become what a report entry parses into.
The in-process path keeps both objects and is untouched, which is what keeps a recipe free to run a
source either way.

**One measurement should be taken again at acceptance.** The packet measured here holds one
packet-owned array; the second packet holds none, and a session with per-unit waveforms from more
than one sorting would hold several. The rule is indifferent to the count — each array is a
directory under the supplied location — but the claim that eleven manifest fields are all
recoverable was checked against one array, and checking it against several costs a minute.
