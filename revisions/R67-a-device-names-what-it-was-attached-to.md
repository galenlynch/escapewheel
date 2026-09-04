# R67 — A Device Names What It Was Attached To

| | |
|---|---|
| **Status** | **Proposed** 2026-09-04 |
| **Amends** | `02` (`core.devices`, `core.probes`), R66 §4 (settles its first open question) |
| **Depends on** | R46 (a reference may be self-referencing), R66 (a device declares its version) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R66 made each element of an acquisition chain a device in its own right, and R66 §4 left the
consequence open: `core.devices` has no way to relate one device to another, so the rows it
permits sit beside each other saying nothing about how they were connected.

The question that needs it is the plainest one about a recording: **which headstage was this probe
in?**

### 1.1 The chain is recorded and the packet cannot express it

Measured on `ecephys_786867`, from Open Ephys `settings.xml`:

| element | identified by | count |
|---|---|---|
| basestation | slot | 3 |
| connect board | slot | 3 |
| headstage | slot, port | 7 |
| probe | its own serial | 7 physical, 10 streams |

Every `NP_PROBE` element states its own `slot`, `port` and `dock`, so the chain is fully
determined: probe → headstage → connect board → basestation. The packet now carries all thirteen
chain devices and cannot say that any of them were connected.

A consumer asking which probes shared a basestation — the question R66 §1.1's differing connect
board revisions make worth asking — has to re-read `settings.xml`, which is the file the packet
exists to replace.

### 1.2 A quad base is one device and several probes

`50213-1` to `50213-4` are four streams of one quad-base probe: one part number, one serial
`23207205101`, one headstage, one `(slot, port, dock)`.

The packet records them as **four devices**, because the importer keyed a device by the stream's
name. `core.probes` and `core.devices` stand at ten rows each, one to one, which asserts four
physical probes where the session had one.

The schema already distinguishes the two: `core.probes.device_id` references `core.devices`, so a
probe is the addressable recording entity and a device is the physical object. Nothing needed
adding; the relation was there and the importer collapsed it. What §2.2 fixes is the writer, not
the schema.

## 2. Decision

### 2.1 A device may name its parent

`core.devices` gains `parent_device_id`: `int32`, **nullable**, R48 role `identifier`, R53 identity
`assigned`, with a self-referencing reference (R46 §2) to `core.devices.device_id`.

It names what this device was **attached to** — a probe's headstage, a headstage's connect board,
a connect board's basestation. A device at the root of a chain, or one whose attachment no source
states, leaves it null.

A writer that knows the attachment **SHOULD** record it.

### 2.2 A device is the object, a probe is the entity

A writer **MUST NOT** create more than one `core.devices` row for one physical instrument. Where a
source presents several recording entities from one object — the bases of a quad-base probe — each
is a `core.probes` row and all reference the same device.

Identity comes from the serial number the source states, not from the name a stream carries.

### 2.3 The chain is well-founded

`parent_device_id` **MUST NOT** contain a cycle: a device MUST NOT be its own parent, directly or
transitively. The same requirement R41 §2.2 makes of a supersession chain, for the same reason —
a consumer walking it must terminate.

### 2.4 What a consumer may then do

A consumer **MAY** walk from a probe to the hardware that acquired it, and **MAY** group probes by
any element of the chain they share.

A consumer **MUST NOT** infer attachment from a device's name. `headstage.slot3.port2` is a name
this specification does not constrain; the reference is the statement.

## 3. What this does not change

- **No new table.** One nullable column, and one reference the registry already permits the shape
  of.
- **No packet becomes invalid.** The column is nullable, so every existing packet stays conforming.
- **No change to `core.probes`.** A probe already names its device; §2.2 corrects how many devices
  a writer creates, not what the table declares.
- **No ordering is implied.** A parent is what a device was attached to, not a container: nothing
  says a chain has a fixed depth, and a consumer MUST NOT assume one.

## 4. Open

- **Whether a dock belongs in the model.** A headstage may carry two probes, distinguished by
  `dock`, and the parent reference alone does not say which dock a probe used. Nothing yet asks;
  a probe that needs it would carry the dock as its own column rather than as part of the
  attachment.
- **Whether attachment is per session.** `core.devices` is per session, so a chain is redeclared
  for each. That is the same shape `core.probes` has, and deduplicating across sessions is the
  question R66 §4 raised and this revision does not answer either.
