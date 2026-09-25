# A Packet-Owned Opaque Resource Crosses as Its Bytes, in a Directory Named by Its Resource ID

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `c5b8e501c4c29faf300ed9d73592dc36effa775e` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 03 §§2, 3.1, 4, 10, 11, 11.2, and 11.3; Part 04 §§4.3, 5.4, 5.5, 10, and 11; Part 05 §§2, 5.3, and 15; Part 07 §4 |
| **Depends on** | R80 §2.1; R117 §§3.1 and 3.2; R134 §3.4; R135 §§3.2 and 3.3; R136 §§3.2 and 3.4 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7 |

Section 3 is normative. Sections 1, 2, 5, and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

An opaque resource is one whose payload Escapewheel does not model: Part 02 §2.3 declares it with
`kind: "opaque"` in any instance mode, and Part 03 §2 maps that kind to no generic interface. A
packet may own such a resource or reference it (Part 04 §5.1), and Part 03 §3.1 lays out owned media
under `media/`.

No adapter can deliver an opaque resource the packet will own. Part 03 §11 names four routes: rows,
a packet-owned dense array written into `array_location`, a `files-v0.1` delivery, and a report. The
resource document of Part 03 §11.3 describes only a referenced resource, and nothing else carries
bytes, so a video, a figure, or a report reaches a packet only as a URI into its source. R134 §7
recorded the gap and left the route list open for a later decision. Three statements lack a subject
as a result: Part 03 §10 says what an owned table's and array's digest covers and nothing about an
opaque resource's; the portable-profile descriptor states ownership per interface and `opaque` has
none; and a resource-document entry that does not declare `external` has no stated meaning.

This revision adds that route. An adapter writes each owned opaque resource, a file or a directory
under its own name, into a directory named by its resource ID in a new build-supplied location,
`opaque_location`. The build binds it by that directory name to a catalog row or to an opaque
singleton declaration, keeps every name the payload carries, and digests the staged bytes. It
refuses only a name a packet cannot hold, and a validator warns where a name would not survive a
copy to Windows or to a filesystem that folds case or normalization.

Two rules the route relies on are made exact for every resource. A relative URI in a manifest is a
relative reference under RFC 3986, percent-encoded in one form by whoever writes it and decoded by
whoever resolves it. A prefix digest's listing writes each key in UTF-8, escaping only what JSON
requires, in RFC 8785's form. A resource document describes only referenced resources, and a build
refuses an entry that does not declare `external: true`. The route carries catalog instances and
singletons; a family instance would need a channel for its `declaration_id`, which a later revision
can add.

The change is structural because it replaces text inside existing sections: Part 03 §11's list of
routes, Part 03 §3.1's `media/` line, Part 04 §4.3's spelling of a listing key, Part 04 §5.4's
statement of which resources are prefixes, Part 04 §5.5's description of a source-relative `uri` as
a path, and Part 05 §2's statement of what a delivery stages. Appended sections would leave each
standing beside its extension.

### 1.1 Structural crosswalk

Commit `b8bf7c1` added the canonical anchor `ew-portable-uri-rules` to Part 03 §4 and changed
nothing else. Every other amended section already carried one: `ew-portable-profile-technologies`,
`ew-portable-packet-layout`, `ew-owned-resource-digests`, `ew-reaching-a-source`,
`ew-build-supplied-values`, `ew-referenced-resource-delivery`, `ew-resource-digests`,
`ew-prefix-resources`, `ew-source-resolution`, `ew-packet-manifest-conformance`,
`ew-packet-catalog-normative-references`, `ew-import-pipeline`, `ew-validation-shim`,
`ew-validation-normative-references`, and `ew-reference-object-model`. No section is added, moved,
split, merged, or retired.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 03 §2, "An opaque resource has no generic value interface" | extend in place | same section | an opaque resource may be packet-owned or external | §3.1 |
| Part 03 §11, the list of routes | extend in place | same section | adds the packet-owned opaque route | §3.1 |
| Part 03 §11.2, the table of terms | extend in place | same section | adds `opaque_location` | §3.1 |
| none; no text says how an owned opaque resource crosses | add | Part 03 §11.3 | the payload, its binding by resource directory to a catalog row or singleton declaration, the refusals, and the in-process hand-over | §3.2 |
| Part 05 §2, "a packet-owned array delivered into the staging area is staged by its delivery" | revise in place | same section | a payload is staged by its delivery too | §3.2 |
| Part 07 §4, what an adapter writes where the build points | revise the informative text | same section | names the payload beside the array | §3.2 |
| none; no text governs a payload's names | add | Part 03 §11.3 | representable names and publication under them | §3.3 |
| Part 03 §3.1, the `media/` line | replace in place | same section | recommends `opaque/<resource_id>/<name>` for every packet-owned opaque resource | §3.3 |
| Part 05 §5.3, the physical findings beside `physical.outside_reader_floor` | extend in place | same section | a warning for payload names that are canonical caseless matches or that Windows cannot hold | §3.3 |
| Part 05 §15, the reference table | extend in place | same section | adds the Unicode Standard | §3.3 |
| Part 03 §4, what a relative URI resolves to | extend in place | same section | a manifest `uri` without a scheme is a relative reference with one percent-encoded form, which a reader or validator decodes | §3.4 |
| Part 04 §5.5, "a path relative to wherever that source is" | revise in place | same section | a relative reference resolved against the source's location | §3.4 |
| Part 04 §10, the table of manifest checks | extend in place | same section | adds `packet.resource.uri_form` | §3.4 |
| Part 03 §11.3, the resource-document paragraph | extend in place | same section | a build refuses a malformed relative `uri` and records the rest in the one form; it refuses an entry that does not declare `external: true` | §3.4 and §3.7 |
| Part 03 §10, what a packet-owned resource's digest covers | extend in place | same section | adds the opaque case and its listing keys | §3.5 |
| Part 04 §5.4, "an external store, or a packet-owned Zarr array" | revise in place | same section | also names a packet-owned opaque directory | §3.5 |
| Part 04 §4.3, "ASCII-escaped keys" | replace in place | same section | a key is written in UTF-8 under RFC 8785's string serialization, and a size as a plain decimal integer | §3.6 |
| Part 04 §11, the reference table | extend in place | same section | adds RFC 8785 | §3.6 |

## 2. Background

Section 2 is informative. Registry, corpus, schema, and code observations were read at the recorded
baseline. Packet figures come from the three built packets' `packet.json` files and the
`core.media_assets` and `core.media_frames` tables of `786867-packet`. Published objects were listed
anonymously from `aind-open-data` on 2026-09-25, one known prefix level at a time.

### 2.1 Every current opaque resource is a catalog instance

The core registry declares 43 tables, 2 dense arrays, and 1 opaque resource,
`core.media_asset_instances`, a catalog family whose instances bind to rows of `core.media_assets`
by the row's `resource_id` (Part 02 §2.6). The four repository extension registries declare 11
tables and nothing else. Part 02 §2.4 also admits an opaque singleton, whose one packet
`resource_id` is its declaration ID, and an opaque family, whose instances bind by declaration ID
alone; no registry declares either.

`core.media_assets` carries neither `uri` nor `format`: Part 02 §2.6 assigns location to Part 04 and
physical encoding to Part 03, and Part 03 names no opaque format, which R129 §3.9 forbids its
descriptor to do. The corpus's only media entries, in four digest fixtures, describe an external
prefix of two PNG frames, so an opaque resource already takes both forms, one object or a prefix.

### 2.2 Real packets reference video no consumer can reach

| packet | built | media entries | media bytes | all external bytes |
|---|---|---|---|---|
| `776259-packet` | 2026-09-17 | 0 | 0 | 6,834,201,570 |
| `786867-packet` | 2026-09-17 | 4, external | 10,568,766,553 | 14,442,737,125 |
| `df-packet` | 2026-09-06 | 4, external | 10,568,766,553 | 14,702,354,428 |

The three packets predate R128's manifest shape. The last two record the same four MP4 files of
session `ecephys_786867`: three cameras of 3,495,156,968, 3,538,583,767, and 3,511,662,837 bytes,
and `clip.mp4` at 23,362,981 bytes, which has no rows in `core.media_frames`. Media is 73% of
`786867-packet`'s external bytes, and 18 times the 0.59 GB of tables R117 §2.1 measured the same
session's packet owning.

All four URIs are `file:///mnt/Data/…`, which resolves only on the machine that built the packet.
The session's published raw asset holds three camera MP4s of 5,208,060,078, 5,894,799,405, and
4,601,719,486 bytes and no clip, so no referenced file matches a published object, and a consumer
elsewhere holds frame timing for no video it can open. The local source directory also holds the
AVIs the MP4s were encoded from, 84,234,931,520 bytes for the four.

A reference through Part 04 §5.5's `source` into the published asset reaches what that asset holds,
and serves wherever the published object is the one wanted. The four MP4s here are local
transcodes, and the clip has no published copy, so only a packet owning them makes them reachable
elsewhere; the same holds for every payload a build generates.

### 2.3 Payloads a packet would own carry names with meaning

The same session's published assets hold payloads that are neither rows nor a dense array:

| payload | location in the published asset | bytes |
|---|---|---|
| rig QC report | raw `ecephys/ecephys_clipped/QC.pdf` | 7,275,694 |
| alignment figures | raw `ecephys/ecephys_clipped/`, three PNG files | 169,167 |
| sorting QC figures | sorted `quality_control/`, one directory per experiment and probe, such as `experiment1_50213-1/` with nine PNG files | not totalled |
| task log | raw `behavior/…/behavior/python_gui_log.txt` | 7,572,344 |

No registry declares any of them. A QC figure is not a media asset in Part 01 §3.18's sense, and
asserts no fact, so the sorting QC figures fit an extension's opaque catalog family with
`content_class: "documentation"`, which Part 02 §2.6 lets an extension bind to its own catalog
table. A report a packet holds one of, such as the rig QC report, fits an opaque singleton, with no
table behind it. The route serves either declaration unchanged.

Their names carry what no catalog column records: `QC.pdf` names a report, and `experiment1_50213-1`
names an experiment and a probe. None is a resource ID, which Part 04 §4.1 constrains to
`^[a-z][a-z0-9_]*\.[a-z0-9_.-]+$`, so a payload bound by its own name would have to be renamed. A
resource ID holds only lowercase ASCII letters, digits, `_`, `.`, and `-`, so it needs no
percent-encoding and no two differ only in case, and a directory named by one can carry the binding
while the payload inside keeps its name.

### 2.4 The reference implementation

The AIND `video` adapter references every video it finds; its module text gives the reason, that
three cameras are 10 GB as MP4 and 80 GB as AVI. The writer has no way to stage opaque bytes. Under
`files-v0.1` a build reads `resources.json` and `*.parquet` from `delivery_root` and ignores every
other file there without a finding. Every resource-document entry the reference adapters emit
declares `external: true`.

The validator's owned-digest check, `packet.resource.digest_missing`, and
`packet.resource.catalog_row_binding` apply to every packet-owned entry whatever its kind, so an
owned opaque resource is checked for presence, digest, and binding by existing rules. The validator
and the reader decode percent-encoding in a `file` URI but join a relative URI to the packet root or
a source's location as spelled. That is correct only while no relative URI holds a character a URI
must encode, as none now does: all 1,546 relative URIs in the corpus's packet fixtures and the three
built packets hold only unreserved characters and `/`.

The validator and the fixture builder compute a prefix's listing with Python's JSON encoder in its
ASCII-escaping mode. Part 04 §4.3's phrase "ASCII-escaped keys" does not say whether a newline is
written `\n` or `\u000a`, which hexadecimal case an escape uses, or how a code point above U+FFFF is
written, and encoders differ: Go's escapes `&`, `<`, and `>` by default, and JavaScript's and Rust's
`serde_json` escape nothing outside ASCII. Zarr keys never reach those cases, and payload names do.
None of the 8 members a fixture or built packet records has a key outside printable ASCII.

### 2.5 Alternatives

Keeping opaque resources referenced only leaves Part 03 §3.1's `media/` unfillable and a payload
with no published copy, such as a local transcode or a generated figure, unreachable elsewhere.
Carrying the bytes inside the protocol changes what crosses under `stream-v0.1` and `flight-v0.1`,
which Part 03 §11.1 makes a new protocol version, and a camera MP4 exceeds one Arrow `binary` value,
whose 32-bit offsets cap it at 2,147,483,647 bytes. Having the adapter name a source object for the
build to copy makes the build read from outside the locations it supplied (Part 05 §2), and a
generated payload, such as a transcode or a rendered figure, has no source object. Wrapping the
payload as a `uint8` Zarr array makes an opaque resource a dense array, a different kind, and makes
a consumer need a Zarr reader to recover an MP4.

Widening `array_location` to take every owned resource that is not rows would misname what it holds,
and renaming it changes every adapter declaration naming it. Naming each payload by its resource ID,
optionally with a suffix, renames every payload whose name carries meaning, and a resource ID may
contain dots, so a suffix would need a rule for an entry that could bind two rows. Carrying a map
from resource ID to path in the resource document or a new channel would need a channel crossing
every protocol, where a directory name states the same map with nothing new crossing. Binding only
catalog instances would make an extension declare a one-row catalog table to deliver a singleton,
whose resource ID already names it.

Restricting names to a portable character set, such as POSIX's portable filename characters, would
rename any payload using a space or a letter outside it. Refusing a name that is not in NFC, or two
names that differ only in case, would stop a build over a name the operator did not choose and the
build may not change. Packaging standards take the same course: BagIt (RFC 8493 §6.1.1) describes
case and normalization collisions and asks an implementation to discourage and tolerate them rather
than refuse them; OCFL 1.1 forbids only empty, `.`, and `..` path elements; and Git stores names as
bytes and warns of a case collision when it writes files out. The preferred rule refuses only what a
packet cannot hold: a name that is not UTF-8 cannot be written in the manifest's JSON, NUL and `/`
cannot occur in a POSIX name, and `.` and `..` are path steps rather than names.

A name that would not survive a copy is a warning, since the packet is sound where it lies. Two
names that fold together under case or normalization become one on macOS and Windows, and Windows
cannot hold a name containing `:`, which timestamped names often do, or one ending in a full stop;
Microsoft's "Naming Files, Paths, and Namespaces" lists the characters and device names §3.3
states. Defining digest keys and name lookup under NFC, as BagIt's tolerance would, changes Part 04
§4.3 for every prefix and makes every reader match names by their normalized form, and is left to a
later decision. Until then, a copy through a filesystem that rewrites names, as HFS+ stores them
decomposed, changes the listing of any payload directory holding a non-ASCII name, colliding or not,
and its digest no longer holds; APFS, NTFS, ext4, and object stores keep a name's bytes. Recording
an IANA media type would change the manifest schema and its version for a claim no validator checks
against the bytes, which identify their own container.

A manifest URI could instead carry a non-ASCII name as itself, an IRI under RFC 3987, as RO-Crate
1.1 prefers. A payload's names are kept unnormalized, so an NFC and an NFD spelling of `é` would
then look identical in the manifest while naming different files, and a tool that normalizes the
text would change which file the URI names; percent-encoded, they are `%C3%A9` and `e%CC%81`. RFC
3987 also still percent-encodes private-use characters, noncharacters, and bidirectional formatting
marks, so it would give non-ASCII two spellings rather than one. Percent-encoding only a
packet-owned URI would make a reader consult `external` to learn whether `%20` is a space.

A listing could instead keep ASCII escaping and pin its exact form. JSON's grammar is Unicode, and
RFC 8785 fixes the escapes it requires, so writing keys in UTF-8 in that form adds no encoding the
carrier does not need, leaves fewer choices to pin, and cites a published scheme rather than one
implementation's behavior. RFC 8785's form and the reference implementation's escaping agree on
every key without U+007F or a code point above it, so no Zarr store's value changes.

### 2.6 Feasibility and overlap

Arrays already cross this way: a build supplies `array_location` under the staging area, one
directory per source, the adapter writes a directory named by the row's `resource_id`, and promotion
renames it into place (Part 03 §3.4). Digesting the four videos of §2.2 costs 4.4 s under SHA-256
and 0.6 s under CRC64NVME at R136 §2's in-memory throughputs of 2.4 and 18.5 GB/s. A copy into
`opaque_location` costs more and is paid once, and a hard link or a copy-on-write clone costs none,
since either is a regular file. A hard link shares its bytes with the source, so Part 03 §8.1's
immutability then holds only while nothing writes the source in place, and level 2 of Part 04 §5.3
detects a write that does.

R142 appended `source_cache` to Part 03 §11.2's table and added §11.7 as the last subsection of
Part 03 §11. This draft appends its row after R142's and adds no subsection. The source-cache
location lies outside the staging area and outlives a build, where `opaque_location` lies inside it
and does not, so neither term can serve for the other. R141 shares no section with this draft. The
later relocation of Part 03 §11 into its own part moves §§11, 11.2, and 11.3 as R142 and this draft
leave them. A reverse-citation query for the sixteen amended sections lists 579 citations outside
this draft, 322 of them outside the revision records; incorporation reads those in Parts 00, 02, 03,
04, 05, 07, and 09, the registry schemas and tooling, the fixture and adapter-boundary tooling, the
writer, the validator, the reader, and the AIND package.

## 3. Decision

Seven subsections add the route and its location, bind a payload by the directory that holds it,
keep its names, make a relative manifest URI a percent-encoded reference, say what a payload's
digest covers, spell a prefix listing exactly, and confine the resource document to referenced
resources. The crosswalk in §1.1 places each at its owner.

### 3.1 An opaque resource crosses into `opaque_location` where the packet owns it

An opaque resource MAY be packet-owned or external. The portable-profile descriptor states ownership
per interface, and `opaque` maps to none, so Part 03 §2 states this in prose.

Part 03 §11.2's vocabulary gains one term:

| term | what a build passes |
|---|---|
| `opaque_location` | a location under the build's staging area (Part 05 §2) to write packet-owned opaque resources to (§3.2) |

An adapter that delivers a packet-owned opaque resource declares `opaque_location` in `needs`. A
build MUST supply it one directory per source, since two sources may each deliver a resource of one
resource ID and a shared directory would make them one. Part 03 §11's routes gain a packet-owned
opaque resource, written into `opaque_location` where it crosses a protocol, and in process either
written there or handed to the build with its bytes.

### 3.2 A payload binds by the directory that holds it

A packet-owned opaque resource crosses as a **payload**: one regular file, or one directory whose
every member is a regular file or a directory. An adapter reached by a protocol MUST place each
payload, under its own name, alone in a **resource directory**: a directory directly in
`opaque_location` named exactly by the resource's `resource_id`. A payload that is a file is a
single object, and one that is a directory is a prefix.

A build binds each payload to the opaque resource its resource directory names: the catalog row of
an opaque catalog family whose `resource_id` equals the directory's name, whose declaration it
resolves under Part 02 §2.6, or otherwise the opaque singleton declaration whose ID equals it (Part
02 §2.4). It MUST NOT bind a payload by its name, suffix, or contents. A build MUST refuse a
delivery, naming the source and the path, where:

- `opaque_location` holds anything other than directories;
- a resource directory holds no payload, or more than one;
- a payload holds anything other than regular files and directories, such as a symbolic link, since
  the packet would then own a pointer rather than bytes;
- a directory within a payload, the payload included, holds nothing, since a prefix consists of
  objects and an empty directory does not survive a copy to an object store; or
- a name within a payload, the payload's own included, is not representable (§3.3).

A build MUST refuse, before it validates the staged packet, naming each such directory and resource
ID, where a resource directory's name is the `resource_id` of no catalog row of an opaque catalog
family and the ID of no opaque singleton declaration a loaded registry declares, or is both; where a
catalog row of an opaque catalog family is bound by no payload or referenced resource; or where one
resource ID is bound by more than one payload or referenced resource.

Nothing else crosses for a payload. A build MUST NOT require an adapter to state a payload's format,
media type, size, or digest; it takes `size_bytes` and `digest` from the staged bytes (§3.5) and
records no format. A payload in `opaque_location` is staged by its delivery, as a packet-owned array
in `array_location` is (Part 05 §2), and promotion moves it to its final path by a rename within one
filesystem (Part 03 §3.4).

An adapter a build runs in process MAY instead hand the build each payload's resource ID, name, and
bytes, or for a directory the path of each file relative to it and that file's bytes. The build then
writes the payload into `opaque_location` as an adapter reached by a protocol would, and the
refusals above apply to what it writes.

### 3.3 A payload keeps its names

A name is **representable** where it is nonempty, is valid UTF-8, contains neither NUL nor `/`, and
is neither `.` nor `..`. Nothing else about a name is refused: a name need not be in any Unicode
normalization form, and two names in one directory may differ only in case.

A build MUST publish each payload under its name, and every file and directory within it under
theirs, and MUST NOT rename, normalize, or case-fold any of them. It MUST publish each payload in a
directory under the packet root that holds nothing else, since two payloads may share a name. Part
03 §3.1's recommended layout places that directory at `opaque/<resource_id>/`, so a payload lies at
`opaque/<resource_id>/<name>`, in place of `media/<media_asset_id>.<ext>`. No validator checks that
a payload kept its names, since a packet does not record them as the source spelled them; a build's
own tests are the evidence. A payload's manifest `uri` names the payload itself, the file where the
payload is one and otherwise the directory, as a relative reference (§3.4).

Two names in one directory of a packet-owned opaque payload **collide** where they differ and are a
canonical caseless match under the Unicode Standard, Section 3.13, definition D145, which equates
names differing only in case, only in normalization form, or in both. A name within such a payload,
or a segment of the payload's path under the packet root, is **unportable to Windows** where it
contains a code point from U+0001 through U+001F or any of `"`, `*`, `:`, `<`, `>`, `?`, `\`, and
`|`; ends in a full stop or a space; or, compared without regard to ASCII case, is `CON`, `PRN`,
`AUX`, `NUL`, or `COM` or `LPT` followed by one of the digits `1` through `9` or the superscripts
`¹`, `²`, and `³`, whether alone or followed by a full stop and anything else.

A validator MUST report each set of colliding names and each name unportable to Windows, one
finding per set and one per name, at `warning` under the check ID
`physical.opaque_name_portability`, naming the resource, the path under the packet root of the
directory holding the names, and the names. The packet is
conformant: each name holds its own file under the packet root, and it fails only on a copy to a
filesystem that folds case or normalization or that Windows governs. The finding concerns one
resource, so Part 05 §9.5 attributes it to the registry whose declaration the resource's entry
names. Part 05 §15 identifies the Unicode Standard, Version 16.0.0, as an exact reference for
canonical caseless matching.

### 3.4 A relative URI in a manifest is a percent-encoded reference

A manifest entry's `uri` that has no scheme is a relative reference under RFC 3986, Section 4.2,
consisting of a path alone, with no authority, query, or fragment. It resolves against the packet
root, or, where the entry names a `source`, against that source's location (Part 04 §5.5). Each
segment of its path spells a name: a reader or validator resolving it MUST decode each
percent-encoded octet of a segment and read the octets as the name's UTF-8 encoding, forming the
path or object key from those names.

A writer MUST write each segment of such a URI in one form: every unreserved character of RFC 3986,
Section 2.3, as itself, and every other octet of the name's UTF-8 encoding as a percent-encoded
octet with uppercase hexadecimal digits. A checker MUST report an entry whose `uri` has no scheme
and is not in that form, or has a segment that is not valid UTF-8 once decoded, at `error` in Part
04 §10's `entries` phase, under the check ID `packet.resource.uri_form`, naming the entry's
`resource_id`.

An adapter MUST write a resource-document entry's `uri` that has no scheme as a relative reference
of that kind, in any form RFC 3986 admits. A build MUST refuse an entry whose `uri` has no scheme
and is not such a reference, or has a segment that is not valid UTF-8 once decoded or that decodes
to a name containing NUL or `/`, naming the source and the entry's `resource_id`. A build MUST
record each entry it accepts with its `uri` rewritten in the one form above.

### 3.5 A packet-owned opaque resource's digest covers its payload

In the portable profile, a packet-owned opaque resource's `digest` covers its payload: the one
object where the payload is a file, and otherwise its files, as Part 04 §4.3 defines a prefix's
value. Each file's key in that listing is its path relative to the payload, spelled with its names
as they are and not percent-encoded. `size_bytes` covers the same bytes. Part 04 §5.4's prefix
resources are an external store, a packet-owned Zarr array, and a packet-owned opaque resource whose
payload is a directory.

### 3.6 A prefix listing writes its keys in UTF-8

Part 04 §4.3's listing is UTF-8 JSON text whose entries are sorted by the bytes of each key's UTF-8
encoding. Each key is a string serialized under RFC 8785, Section 3.2.2.2: `"` and `\` as `\"` and
`\\`; U+0008, U+0009, U+000A, U+000C, and U+000D as `\b`, `\t`, `\n`, `\f`, and `\r`; every other
code point from U+0000 through U+001F as `\u` followed by four lowercase hexadecimal digits; and
every other code point as itself. Each size is a decimal integer with no sign, leading zero,
fraction, or exponent. This replaces the listing's ASCII escaping of keys. Part 04 §11 identifies
RFC 8785 as an exact reference for that serialization.

### 3.7 A resource document describes only a referenced resource

A build MUST refuse a resource-document entry that does not declare `external: true`, naming the
source and the entry's `resource_id`. A packet-owned opaque resource crosses only as a payload
(§3.2).

## 5. Consequence

Packet shape is unchanged. The manifest and delivery schemas are unchanged: an owned opaque entry is
an ordinary entry, with `resource_id`, `declaration_id`, a URI under the packet root, `digest`, and
`size_bytes`, and no member records a format or media type. No existing packet changes: each current
media entry is external, every relative URI a fixture or built packet records is already in §3.4's
form, and no listing key they record holds U+007F or a code point above it. The three built packets
predate R128 and are rebuilt for other reasons; a rebuild owns media only where an adapter delivers
it as a payload.

Behavior changes in five places. A build supplies a new location and stages what it finds there,
where it now ignores files it does not expect. A build refuses a resource-document entry not marked
external, which it now records as external, and one whose relative `uri` is malformed, and rewrites
the rest in one form. A reader and a validator decode every relative URI, which they now use
verbatim, and a checker reports one not in that form. A prefix listing writes a key holding U+007F
or a code point above it in UTF-8, where it now escapes it. A validator warns of payload names that
collide or that Windows cannot hold. Every existing adapter declaration stays valid, and the
reference adapters already mark every resource-document entry.

No accepted clause is superseded. R136 §3.2's listing keeps its construction and changes only how a
key is spelled, and R80 §2.1's source-relative `uri` becomes a relative reference; the ledger
entries of both gain notes. R117 §3.1's array route gains a sibling, R117 §3.2's resource document
gains the refusals of an unmarked entry and a malformed relative URI, and R134 §7's missing opaque
route is settled without amending R134 §3.4, whose route list is open. The ledger entries of R117
§§3.1 and 3.2 gain notes.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged; Part 01 §3.18's media asset keeps its meaning whoever owns the bytes. | None required. |
| logical prose and registry | Unchanged; the route reads the existing `kind`, instance modes, and catalog binding, and no declaration changes. | None required. |
| physical profiles | Part 03 §2 states opaque ownership; §3.1's `media/` line becomes `opaque/<resource_id>/<name>`; §4 makes a manifest `uri` without a scheme a relative reference in one percent-encoded form, which a reader or validator decodes; §10 gains the opaque digest and its listing keys; §11's routes gain the opaque route; §11.2 gains `opaque_location`; §11.3 states the payload, its binding to a catalog row or singleton declaration, the refusals, the in-process hand-over, names, and the resource-document refusals. The descriptor and its schema are unchanged. | `evidence/R<N>.json` names `ew-portable-profile-technologies`, `ew-portable-packet-layout`, `ew-portable-uri-rules`, `ew-owned-resource-digests`, `ew-reaching-a-source`, `ew-build-supplied-values`, and `ew-referenced-resource-delivery`. |
| packet manifest and JSON Schemas | Manifest, delivery, recipe, and adapter schemas unchanged; the adapter schema's `needs` already admits any term. Part 04 §4.3 writes listing keys under RFC 8785, §5.4 names the new prefix case, §5.5 calls a source-relative `uri` a relative reference, §10 gains `packet.resource.uri_form`, and §11 gains RFC 8785. | `registry/check.py`, the vendoring check, and `evidence/R<N>.json` naming `ew-resource-digests`, `ew-prefix-resources`, `ew-source-resolution`, `ew-packet-manifest-conformance`, and `ew-packet-catalog-normative-references`. |
| validation and import | Part 05 §2 says a payload is staged by its delivery. Part 05 §5.3 gains `physical.opaque_name_portability` at `warning`, and Part 05 §15 the Unicode Standard, Version 16.0.0, which Python 3.14's `unicodedata` implements. Part 05 §6's promotion record already lists every promoted resource directory. | The writer tests below and the corpus fixtures. |
| extensions | Registry content unchanged. An extension declaring an opaque catalog family or singleton gains the route without registry change, and Part 09 §5.7, which states how an extension's registry document and rows reach a build, is unchanged. The AIND `video` adapter is unchanged; it may own a video once it declares `opaque_location`, which this decision permits and does not require. | The AIND suite. |
| reader, writer, validator, adapters | The writer supplies `opaque_location`, binds payloads by resource directory to catalog rows and singleton declarations, applies the refusals, publishes payloads under their names in their own directories, writes every relative URI in §3.4's form, rewrites and refuses resource-document URIs, digests payloads, writes listings under §3.6, accepts payload bytes in process over every protocol, and refuses an unmarked resource-document entry. The reader and validator decode every relative URI; the validator reports `packet.resource.uri_form` and payload names that collide or that Windows cannot hold, and writes listings under §3.6, as the fixture builder does. Digest, binding, and presence checks are otherwise unchanged (§2.4). | Writer, validator, and reader suites. |
| conformance fixtures and tests | Packet fixtures for an owned opaque single object, an owned opaque prefix, and an owned opaque singleton, one with a name needing percent-encoding, each checked for binding and digest; a negative fixture whose owned opaque digest disagrees; a prefix holding `é.png` in NFC beside `É.png` in NFD and a file named `12:00:00.png`, which passes with two `physical.opaque_name_portability` warnings; a negative fixture whose relative `uri` holds a raw space, failing `packet.resource.uri_form`; and a prefix whose keys hold `"`, `\`, a newline, U+007F, `é`, and a code point above U+FFFF, pinning §3.6's value. Writer tests in §6. | The corpus and the writer suite. |
| revision process and tooling | Ordinary ledger and evidence records, with the notes stated above. | `ledger.py` and `evidence.py`. |
| generated publications and developer documentation | The combined specification and heading index regenerate. Part 07 §4 names a payload beside an array. The writer README and the AIND `video` module text describe the route. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied` by canonical anchor: §3.1 at `ew-portable-profile-technologies`,
`ew-reaching-a-source`, and `ew-build-supplied-values`; §3.2 at `ew-referenced-resource-delivery`
and `ew-import-pipeline`; §3.3 at `ew-referenced-resource-delivery`, `ew-validation-shim`,
`ew-validation-normative-references`, and `ew-portable-packet-layout`; §3.4 at
`ew-portable-uri-rules`, `ew-source-resolution`, `ew-packet-manifest-conformance`, and
`ew-referenced-resource-delivery`; §3.5 at `ew-owned-resource-digests` and `ew-prefix-resources`;
§3.6 at `ew-resource-digests` and `ew-packet-catalog-normative-references`; and §3.7 at
`ew-referenced-resource-delivery`.

Writer tests distinguish the new rules from the current ones:

- `core.clip/clip.mp4` written into `opaque_location`, with a `core.media_assets` row whose
  `resource_id` is `core.clip`, yields a packet-owned entry at `opaque/core.clip/clip.mp4` whose
  digest is the file's single-object value, where the current build ignores the file;
- a payload directory `frames/` of two PNG files yields a prefix entry whose listing keys are
  `0.png` and `1.png`;
- `QC.pdf` written into a resource directory named by an extension's opaque singleton declaration
  binds to that declaration with no catalog row;
- a payload named `QC report é.pdf` is published under that name with the URI
  `opaque/<resource_id>/QC%20report%20%C3%A9.pdf`, and the reader opens it and the validator
  verifies its digest;
- the same payload delivered over `files-v0.1`, `stream-v0.1`, and `flight-v0.1`, and handed over in
  process, yields the same entry;
- the build refuses, naming the path: a file directly in `opaque_location`; a resource directory
  holding two payloads or none; a symbolic link; an empty directory within a payload; a name that is
  not UTF-8; a resource directory named by neither a catalog row nor a singleton declaration; and
  one named by a dense-array catalog row;
- a payload holding `a.png` beside `A.png`, a name in NFD, and `12:00:00.png` is published with
  every name unchanged, and the build's validation reports two `physical.opaque_name_portability`
  warnings and passes;
- the build refuses a `resource_id` delivered as a payload by two sources, or as a payload and a
  resource-document entry;
- a resource-document entry whose `uri` is `videos/cam 1.mp4` is refused, and one whose `uri` is
  `videos/cam%201.mp4` is resolved by the reader against its source, and one spelled
  `videos/r%c3%a9sum%c3%a9.pdf` is recorded as `videos/r%C3%A9sum%C3%A9.pdf`; and
- a resource-document entry without `external: true` is refused, where the current writer records it
  as external.

The positive case beside them is an adapter declaring no `opaque_location`, which delivers rows,
arrays, and referenced resources as today. The corpus fixtures of §5 check what a validator decides:
binding, digest, a percent-encoded URI, the URI form, the listing's spelling, and the portability
warnings. Name preservation and the refusals are a build's obligations, which a validator cannot
observe after the fact, so writer tests are their evidence.
