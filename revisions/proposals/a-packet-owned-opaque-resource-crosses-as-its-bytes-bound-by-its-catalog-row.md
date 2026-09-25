# A packet-owned opaque resource crosses as its bytes, bound by its catalog row

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `35700ff4b05573624429ba0e341f1c61182eea0b` |
| **Decision domain** | specification |
| **Affects** | Part 03 §§2, 3.1, 10, 11, 11.2 and 11.3; Part 07 §4; Part 09 §5.7; the delivery schema generated from `registry/manifest.schema.json`; the writer's delivery, staging and in-process interfaces; the AIND `video` adapter |

## 1. Problem

An opaque resource is one whose payload Escapewheel does not model. Part 02 §2.3 declares it with
`kind: "opaque"`, Part 03 §2 maps that kind to no generic interface, and a generic reader lists
its identity and location without reading it. The core registry's one opaque declaration is
`core.media_asset_instances`, a catalog family whose instances bind one-to-one to rows of
`core.media_assets` by the row's `resource_id` (Part 02 §2.6). A packet may own such a resource or
reference it (Part 04 §5.1), and Part 03 §3.1 lays out owned media under `media/`.

No adapter can deliver an opaque resource the packet will own. Part 03 §11 names four routes:
rows, a packet-owned dense array written into `array_location`, a `files-v0.1` delivery of Parquet
and a resource document, and a report. A resource document describes only a referenced resource
(Part 03 §11.3), and nothing else carries bytes, so a media instance, a figure or a document reaches
a packet only as a URI into the source. R134 §7 recorded the gap and left the route list open for a
later decision to extend.

The missing route leaves three adjacent statements without a subject:

- Part 03 §10 says what a packet-owned table's and array's digest covers, and nothing about an
  opaque resource's, so whether an owned media instance is one object or a prefix is stated nowhere.
- The portable-profile descriptor states admitted ownership per interface, and `opaque` has none,
  so the profile never says that an opaque resource may be packet-owned.
- The delivery schema admits a resource-document entry that does not declare `external`, and Part
  03 §11.3 gives the document only referenced resources, so such an entry has no stated meaning.

## 2. Evidence

Observations were read from the generated parts, the registries, the schemas and the reference
implementation at the recorded baseline. Packet figures come from the three packets' `packet.json`
files alone, read without building or opening anything else. Published objects were listed one
known prefix level at a time, anonymously, from `aind-open-data`.

### 2.1 Declarations

The core registry and the four repository extension registries declare one opaque resource,
`core.media_asset_instances`, and no family-mode declaration of any kind. Every opaque instance a
current registry can produce is therefore a catalog instance bound by a row's `resource_id`.

`core.media_assets` carries `resource_id` and neither `uri` nor `format`: Part 02 §2.6 assigns
location to Part 04 and physical encoding to Part 03, and Part 03 enumerates no opaque format,
which R129 §3.9 forbids its descriptor to do. A media asset's container is thus recorded nowhere in
a packet built at the baseline. The corpus's only media entries, in four digest fixtures, describe
an external prefix of two PNG frames, so an opaque resource already takes both forms: one object or
a prefix.

### 2.2 Real packets

Three packets built by the reference writer are on local disk. They predate R128's manifest shape,
so their entries carry `kind: "media_asset"` and `physical_profile: "mp4"` where a current entry
carries `declaration_id`.

| packet | built | media entries | media bytes | all external bytes |
|---|---|---|---|---|
| `776259-packet` | 2026-09-17 | 0 | 0 | 6,834,201,570 |
| `786867-packet` | 2026-09-17 | 4, external | 10,568,766,553 | 14,442,737,125 |
| `df-packet` | 2026-09-06 | 4, external | 10,568,766,553 | 14,702,354,428 |

`776259-packet`'s recipe names no video source. The other two record the same four MP4 files of
session `ecephys_786867`: three cameras of 3,495,156,968, 3,538,583,767 and 3,511,662,837 bytes,
and `clip.mp4` at 23,362,981 bytes, which has no timing file and so no rows in `core.media_frames`.
Media is 73% of `786867-packet`'s external bytes, and 18 times the 0.59 GB of tables R117 §2.1
measured the same session's packet owning.

Every one of the four URIs is `file:///mnt/Data/…`, which resolves only on the machine that built
the packet. The session's published raw asset lists three camera MP4s of 5,208,060,078,
4,601,719,486 and 5,894,799,405 bytes and no clip, so no referenced file matches a published object:
a consumer elsewhere holds the frame timing and no video it describes. The source directory
also holds the AVIs the MP4s were encoded from, 84.2 GB for the four.

### 2.3 Other payloads a packet would own

The same session's published assets hold payloads of the same character, none of them rows or a
dense array:

| payload | location in the published asset | objects | bytes |
|---|---|---|---|
| rig QC report | raw `ecephys/ecephys_clipped/` | `QC.pdf` | 7,275,694 |
| alignment figures | raw `ecephys/ecephys_clipped/` | 3 PNG | 169,167 |
| sorting QC figures | sorted `quality_control/`, per probe | 170 PNG | 152.5 MB |
| sorting visualizations | sorted `visualization/`, per probe | 60 PNG | 216.3 MB |
| task log | raw `behavior/…/behavior/python_gui_log.txt` | 1 | 7,572,344 |
| rig and session snapshots | raw `metadata-dir/`, `ecephys_clipped/metadata/` | JSON | 5,780 to 36,970 each |

Their names carry what no catalog column records: `QC.pdf` names a report, and the sorting figures
sit in one directory per probe. No such name is a resource ID, which Part 04's manifest-entry table
constrains to `^[a-z][a-z0-9_]*\.[a-z0-9_.-]+$`, a namespace and a dot with no capitals or spaces,
so a packet could bind a payload by its name only after renaming it.

No registry declares any of them. A QC figure is not a media asset in Part 01 §3.18's sense, an
image or video whose timing is carried in tables, and asserts no fact, so the fitting declaration is
an extension's opaque catalog family with `content_class: "documentation"`, which Part 02 §2.6
permits an extension to bind to its own catalog table. The route this proposal seeks serves such a
declaration unchanged.

### 2.4 The reference implementation

- The AIND `video` adapter references every video it finds and owns the frame timing instead. Its
  module states why: three cameras are 10 GB as MP4 and 80 GB as AVI, so a packet copying them
  would be mostly video. In process it hands the writer each video as a referenced resource, and out
  of process it sends each as a resource-document entry.
- In process, the writer accepts a referenced media asset and has no way to stage opaque bytes.
- Under `files-v0.1`, the build reads `*.parquet` and `resources.json` from `delivery_root` and
  ignores every other file there without a finding. Under `stream-v0.1` and `flight-v0.1`, only
  rows and the document cross.
- A resource-document entry with a relative URI and no `source` is refused as unable to resolve
  without the packet, and every entry the build accepts is recorded with `external: true`.
- The writer's referenced-media record carries a container `format`, which the delivery drops
  because the manifest has no member for it.
- The validator's owned-digest check and Part 04 §10's `packet.resource.catalog_row_binding` apply
  to every packet-owned entry whatever its kind, so an owned opaque resource would be checked for
  presence, digest and binding without new validation rules.

### 2.5 Measured bounds on the alternatives

Arrow's `binary` type addresses a value with 32-bit offsets, so one value holds at most
2,147,483,647 bytes; each camera MP4 above is larger. At R136 §2's in-memory throughputs, digesting
the four videos' 10,568,766,553 bytes costs 4.4 s under SHA-256 and 0.6 s under CRC64NVME; copying
them is the larger cost and is paid once, since promotion renames (Part 03 §3.4).

## 3. Desired outcome and constraints

A successful resolution gives an adapter one route to deliver a packet-owned opaque resource, and
preserves the following:

- **Binding by `resource_id`.** An instance binds to exactly one catalog row by the row's
  `resource_id`, never by an assigned row ID or a source label, as Part 03 §11.3 binds an array,
  and the one-to-one rule of Part 02 §2.6 holds across owned and referenced instances together.
- **The declaration decides opacity.** The build learns that a resource is opaque from the
  checked declaration its catalog row resolves to. A file name, suffix or directory never selects
  a kind or an interface (Part 03 §2).
- **Names kept.** A payload's file or directory name, and every name inside a directory, reaches
  the packet as the source spelled it, since it may carry meaning no catalog column records.
- **Staging before publication.** The bytes land in a location under the staging area that the
  build supplies empty (Part 05 §2), are validated with the whole staged packet, and are promoted
  by a rename within one filesystem only after a `passed` verdict and under the promotion record
  (Part 05 §6).
- **One digest, computed by the build.** The build digests the staged bytes under Part 04 §4.3, as
  a single object or as a prefix, and takes no digest, size or format from the adapter.
- **No format knowledge.** Neither the build, the validator nor a generic reader parses, decodes or
  identifies the payload (R129 §3.9; Part 09 §5.6), so the route works for a format no one has
  enumerated.
- **The manifest unchanged.** A packet-owned opaque entry is an ordinary entry: `resource_id`,
  `declaration_id`, a URI under the packet root, `digest` and `size_bytes`.
- **The bytes themselves.** A packet-owned resource holds its bytes, so a link to a source file
  does not count as delivering one.
- **Every protocol.** Rows cross by `files-v0.1`, `stream-v0.1` or `flight-v0.1`,
  or in process, and an owned opaque resource reaches the build whichever of those the recipe
  selects, without a new protocol version (Part 03 §11.1).
- **Nothing through the report.** A fact a manifest needs does not travel in a report (Part 09
  §5.8).

## 4. Options and tradeoffs

### 4.1 Whether to add a route

**Keep the current rule, opaque resources only referenced.** Rejected: a packet cannot hold a
23 MB clip or a 7 MB QC report, Part 03 §3.1's `media/` can never be filled, and a reference taken
from a local source names bytes no consumer can reach, as every media URI in §2.2 does.

**Add a route** (preferred direction). The choice between owning and referencing stays per
resource, as it is for arrays; Part 04 §5.1 still expects large resources to be referenced.

### 4.2 How the bytes cross

**The adapter writes the bytes into a location the build supplies under the staging area**
(preferred direction). This is the array route with the Zarr rule removed. It crosses every
protocol unchanged, because the bytes never enter the stream, and promotion moves them by rename.
The cost is that an adapter delivering an owned opaque resource writes bytes, which R117 already
accepted for arrays.

**The bytes cross inside the protocol, as an Arrow binary value or a Flight stream.** Rejected:
it changes what crosses under `stream-v0.1` and `flight-v0.1`, which Part 03 §11.1 makes a new
protocol version; `files-v0.1` would still need a location; and a camera MP4 exceeds one `binary`
value (§2.5), so each would need `large_binary` or chunking on top.

**The adapter names the source object in the resource document and the build copies it.**
Rejected: the build would read a delivery from outside the locations it supplied (Part 05 §2) with
access to the source store that the adapter, not the build, holds; and a payload the adapter
generates, such as a transcode or a rendered figure, has no source object to name.

**Wrap the payload as a one-dimensional `uint8` Zarr array.** Rejected: the declaration makes the
resource opaque, a dense array is a different kind (Part 02 §2.3), and a consumer would need a Zarr
reader to recover an MP4.

### 4.3 Which location

**A new Part 03 §11.2 term for a directory under the staging area, one per source, supplied empty**
(preferred direction; working name `opaque_location`). An adapter declares it in `needs` exactly as
it declares `array_location`, and a build supplies it only where declared. Existing declarations
and the waveform adapter are untouched.

**Widen `array_location` to take every packet-owned resource that is not rows.** Feasible, since the
build resolves each entry's kind from its declaration, but the term would then misname what it
holds; renaming it changes every adapter declaration that names it, which in this repository is the
waveform adapter's alone. This is open question 1.

### 4.4 Binding and naming

**A directory named exactly by the catalog row's `resource_id`, holding the payload under its own
name** (preferred direction). The adapter creates `<resource_id>/` in the location and places in it
one entry: a regular file, which is a single-object resource, or a directory of regular files, which
is a prefix. The build binds the entry to the row whose `resource_id` equals the directory's name,
and the packet holds it at `opaque/<resource_id>/<name>`. The manifest URI names the entry itself,
with its name percent-encoded under RFC 3986, so a single object keeps its single-object digest
rather than becoming a one-member prefix. The binding reads only a path segment that the
resource-ID grammar already makes safe on every filesystem and object store, the payload's name is
never parsed, and the binding crosses every protocol because it lies in the location rather than
the stream.

**An entry named by the resource ID, optionally followed by a suffix.** Rejected: it renames every
payload whose name carries meaning (§2.3), and a resource ID may contain dots, so a suffix needs a
rule refusing an entry that could bind two rows.

**A mapping from resource ID to path, carried in the resource document or a new channel.**
Rejected: the resource document describes referenced resources (§4.7), and a new channel would have
to cross each protocol, where a directory name states the same mapping with nothing new crossing.

Under the preferred direction, the build refuses:

- anything in the location other than a directory whose name is a catalog row's `resource_id`;
- a per-resource directory holding no entry, or more than one;
- a catalog row bound by no entry and no referenced resource, or by more than one;
- an entry whose row resolves to a declaration that is not opaque;
- a symbolic link anywhere in an entry, since the packet would then own a pointer rather than
  bytes;
- an entry directory holding no regular file, which is a prefix that does not exist (Part 04 §4.3);
  and
- a name that cannot be reproduced on another filesystem or object store, under open question 2.

Each source writes into its own directory, as for arrays, so two sources delivering one resource ID
reach the build as two entries binding one row, which the third refusal catches.

Part 03 §3.1's `media/<media_asset_id>.<ext>` line becomes `opaque/<resource_id>/<name>`: an owned
QC report is not media, and an assigned ID contradicts §11.3's binding by `resource_id`.

### 4.5 Digest, form and ownership

**Part 03 §10 gains the opaque case** (preferred direction): a packet-owned opaque resource's
`digest` covers its one object where the entry is a file, and its objects under Part 04 §4.3's
prefix construction, keyed relative to the entry, where the entry is a directory. The profile
states in prose that an opaque resource may be packet-owned or external, which the descriptor cannot
state for a kind with no interface.

### 4.6 In process

**An adapter run in process may hand the build the payload's name and bytes, or for a prefix each
object's relative key and bytes, instead of writing them, and the build writes them into the
location under the same naming and refusals** (preferred direction), as Part 03 §11.3 lets it hand
an array's values over. Forbidding it would impose a write for a process boundary that is not there.

### 4.7 What the resource document describes

**The document describes only referenced resources, and a build refuses an entry that does not
declare `external: true`** (preferred direction). The owned route then has one channel, and the
schema's admission of an unmarked entry gains a stated consequence. An entry may still declare
`external: true` with a relative URI, as Part 04 §5.1 permits.

### 4.8 Recording a media type

**Record none** (preferred direction). A container identifies itself by its own bytes, Part 04 §6
keeps self-describing physical facts out of the manifest, and R129 §3.9 keeps formats out of the
profile. The cost is that a consumer learns a payload's format only by opening it or reading the
suffix its kept name carries. Adding an IANA media type member to the manifest would change its
schema and its version and give a writer a claim no validator checks against the bytes. This is open question 3.

### 4.9 Family instances

**Confine the route to catalog instances** (preferred direction). No current declaration is a
family, and a family instance has no row from which a build could learn its declaration, so a name
alone could not bind it. Admitting families would need the adapter to state each instance's
`declaration_id` through a channel that crosses every protocol; that can follow once a family
declaration exists. This is open question 4.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged; Part 01 §3.18's media asset keeps its meaning whoever owns the bytes. |
| logical prose, registry declarations, rules | Unchanged; the route reads the existing `kind` and catalog binding, and no declaration changes. |
| physical profiles | Affected: Part 03 §11's route list gains the owned opaque route; §11.2 gains the location term, or widens `array_location` under open question 1; §11.3 states the binding, naming, refusals and in-process hand-over; §10 states what an opaque digest covers; §2 says an opaque resource may be packet-owned; §3.1's `media/` line becomes `opaque/<resource_id>/<name>`, and its `arrays/` line, which names an entry by an assigned asset ID where §11.3 binds by `resource_id`, is corrected with it. The descriptor and its schema are unchanged. |
| packet manifest and schemas | The manifest schema is unchanged under §4.8. The delivery schema is generated from it, so refusing an unmarked resource-document entry is a Part 03 §11.3 rule the build applies, or a generator change requiring `external: true`. |
| validation and import | Part 05 §2's delivery-location rule and §6's promotion already cover a new location; unchanged unless the draft cites the route. |
| extension registries | Unchanged; an extension that declares an opaque catalog family gains the route without registry change. Part 09 §5.7's statement of how an extension's rows reach a build gains the owned opaque case. |
| reader | Unchanged; R129 §3.9's listing of identity and location applies, and an owned entry's URI resolves under the packet root. |
| writer | Affected: supply the new location, bind entries to catalog rows by directory name, percent-encode kept names in URIs, apply the refusals, stage and digest owned opaque resources, accept bytes in process, refuse an unmarked resource-document entry. |
| validator | Unchanged; §2.4's generic checks cover an owned opaque entry. |
| adapters | The AIND `video` adapter can own a resource it now references, such as the clip, where a recipe option tells it to; its default stays referencing. |
| existing packets | Unchanged in shape. The three built packets predate R128 and are rebuilt anyway; a rebuild may own media only where the recipe asks. |
| conformance fixtures and tests | Affected: writer tests for each refusal in §4.4, a single-object and a prefix entry, a name holding a space and capitals, each protocol and in process, and an unmarked resource-document entry; a packet fixture with an owned opaque single object and one with an owned opaque prefix, each checked for binding and digest. |
| revision tooling | Unchanged. |
| documentation | Affected: Part 07 §4's informative description of what an adapter writes, the writer's README, and the AIND `video` adapter's module text. |

These cases distinguish the proposed rule from the current one:

- an adapter writing `core.clip/clip.mp4` into the location, with a `core.media_assets` row whose
  `resource_id` is `core.clip`, yields a packet-owned entry at `opaque/core.clip/clip.mp4` whose
  digest is the file's single-object value, where the current build ignores the file;
- an entry named `QC report.pdf` keeps that name on disk and records the URI
  `opaque/<resource_id>/QC%20report.pdf`;
- a directory of two PNG frames yields a prefix entry whose digest follows Part 04 §4.3, keyed by the
  frames' names;
- a file written directly into the location, or a per-resource directory holding two files, is
  refused;
- the same payload delivered over each protocol and in process yields the same entry;
- the build refuses each case §4.4 lists, and an entry whose row names a dense-array catalog;
- a resource-document entry without `external: true` is refused, where the current writer records
  it as external or refuses it only for its relative URI.

## 6. Open questions

1. **Location term.** Preferred: a new term beside `array_location`, so no existing declaration
   changes and an adapter declares only what it writes. The alternative, one widened and renamed
   term for every owned non-row resource, costs one term fewer and changes every declaration that
   names `array_location`.
2. **Name restrictions.** Preferred: refuse only a name that cannot be reproduced elsewhere: one
   that is not valid UTF-8, contains NUL or `/`, or is `.` or `..`, and two names in one directory
   that differ only in case, which collide on a case-insensitive filesystem. Every other name,
   spaces and non-ASCII included, is kept and percent-encoded in the URI. The alternative, a
   portable character set such as POSIX's portable filename characters, renames any payload whose
   name uses a space or a character outside it, which the names-kept constraint forbids.
3. **Media type.** Preferred: none recorded; the payload describes itself. Recording one would add a
   manifest member and a schema version, and a claim nothing checks.
4. **Family instances.** Preferred: out of this decision, since no declaration is a family and a
   name cannot carry a declaration. Admitting them needs a channel for `declaration_id`.

Overlaps. Relocating Part 03 §11 into its own part moves every section this proposal amends except
§§2, 3.1 and 10, so the two drafts need an order. The source-cache proposal adds a Part 03 §11.2
location that lies outside the staging area and outlives a build, where this one lies inside it and
does not, so neither term can serve for the other. This proposal extends R117 §3.1 and R134 §3.4's route list, and depends on
R135 §§3.2–3.3 for staging and promotion and on R136 for the digest.

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
