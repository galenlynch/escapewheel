# R66 — A Device Declares What Version It Was

| | |
|---|---|
| **Status** | **Accepted** 2026-09-04 |
| **Amends** | Part 02 (`core.devices`), Part 09 §4.4 (the minimum a device records) |
| **Depends on** | R65 (an array names the device that made it) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`core.devices` identifies a physical instrument: `name`, `manufacturer`, `model`, `serial_number`.
Those say **which** instrument it is. Nothing says **what version of itself** it was during the
session.

The distinction is not pedantic. A serial number identifies the object; its firmware determines
what the object does. Two sessions can record the same instrument, by the same manufacturer, with
the same model and serial, and produce data that must be interpreted differently — with nothing in
either packet to say so.

### 1.1 It is recorded, it varies, and it varies within one session

Measured on `ecephys_786867`'s Open Ephys settings, twenty `NP_PROBE` elements:

| attribute | values |
|---|---|
| `bs_firmware_version` | `3.0196` ×10, `4.0215` ×10 |
| `bsc_firmware_version` | `4.0215` ×10 |
| `bsc_hardware_version` | `2.1` ×3, `2.2` ×7 |
| `bs_hardware_version` | `UNKNOWN` ×10 |

Two firmware versions and two hardware revisions **inside a single session**, because the probes
hang off different basestations. A packet that records only `model` and `serial_number` cannot
express that, and a consumer comparing two probes cannot discover it.

The values describe a chain: each probe names the basestation (`bs_*`) and basestation connect
board (`bsc_*`) it is attached to, each with its own part number, serial number, hardware version
and firmware version.

`UNKNOWN` is itself informative and MUST be carried as written where a source says it: it
distinguishes an instrument that reported no version from one nobody asked.

### 1.2 A device that states its own version, into a column that does not exist

The Open Ephys case is a chain of acquisition hardware. The clearer one is a single instrument
that declares its version itself, in a file inside the packet:

```yaml
# sniff/sniffing_neuroscience_786867_*.harp/device.yml
device: SniffDetector
whoAmI: 1401
firmwareVersion: "0.1"
hardwareTargets: "0.1"
```

That is the Harp protocol's device schema, written beside the device's own data. It is the **only**
statement of this instrument anywhere in the packet's sources: measured, zero occurrences across
`rig.json`, `metadata.nd.json`, `processing.json`, `quality_control.json` and the behaviour JSON,
because the sensor was acquired by a separate workflow that contributed its data and none of its
metadata.

An importer reading it today has nowhere to put two of the four fields, so they go to
`core.devices.metadata` as JSON — a column the same session's firmware argument says they should
not be in, since the register this schema documents is what sets the signal's sampling rate.

### 1.3 The names are already the upstream vocabulary

`aind-data-schema` declares `hardware_version` and `firmware_version` on a Harp device, and Open
Ephys writes `bs_firmware_version` and `bsc_hardware_version`. Two independent producers reached
for the same two words, so adopting them costs no translation and matches the `*_version`
convention `core.sorting_runs.sorter_version` and `core.processing_runs.software_version` already
follow.

The AIND rig JSON declares both on all four of its Harp devices and leaves them **null**, which is
why neither §1.1 nor §1.2 argues from it. A field a producer models and never fills is not evidence
that anyone needs it; two producers filling it with differing values is.

### 1.4 Why not `metadata`

`core.devices.metadata` could hold both today, and Part 09 §3 would keep them there while they are
rarely queried.

That test is met and passed. A firmware version changes how a signal must be interpreted while
every other column stays identical — §1.2's sensor dispatches on an interval set by a register its
own schema documents, so its sampling rate is a firmware fact — and Part 09 §3 puts anything needed to
*interpret* a recording in core. A value inside a JSON string is also unavailable to a rule: no
Tier 2 check can compare firmware across the probes of one session while it lives there.

## 2. Decision

### 2.1 Two columns

`core.devices` gains:

| column | type | presence | role |
|---|---|---|---|
| `hardware_version` | `string` | nullable | `data` |
| `firmware_version` | `string` | nullable | `data` |

Both are **strings**, not numbers. `3.0196`, `2.1` and `UNKNOWN` are all real values from one
session, and only a string holds all three. A writer **MUST** record the value verbatim and
**MUST NOT** normalise, pad, or parse it into components.

A writer that knows either **SHOULD** record it. Absent means the source did not say, which is
distinct from a source that said `UNKNOWN`.

### 2.2 The vocabulary is open and unparsed

Neither column has a closed vocabulary and neither is ordered. A consumer **MUST NOT** compare two
version strings for precedence: `3.0196` and `4.0215` come from different manufacturers' schemes,
and nothing in this specification says either is a number.

A consumer **MAY** compare them for **equality**, which is the operation the motivating case needs:
whether two devices in one session ran the same firmware.

### 2.3 What a device is, for this purpose

Each element of an acquisition chain that reports its own versions is its own `core.devices` row.
A basestation and its connect board are two devices, not two columns of one.

## 3. What this does not change

- **No new table**, and no existing column changes type or presence.
- **No packet becomes invalid.** Both columns are nullable, so every existing packet stays
  conforming and gains the values on its next rebuild.
- **No change to `core.probes`.** A probe already names its device (Part 02); which basestation that
  device hangs off is §4's question, not this one.
- **`metadata` still holds what is not queried.** This promotes two fields, not a policy.

## 4. Open

- **Whether a device declares its parent device.** The measured chain is probe → connect board →
  basestation → slot, and `core.devices` has no `parent_device_id`, so the three rows this
  revision permits cannot be related to each other. Worth adding when something needs to traverse
  it; nothing does yet, and adding it now would be the capability-nobody-consumes that R54 §5
  warns about.
- **Whether a firmware reference belongs beside a version.** One device in the same rig records
  `firmware` as a repository URL, a branch and a commit rather than a version string. That is
  provenance of a different kind — it identifies source code, where a version identifies a build —
  and folding it into `firmware_version` would put two meanings in one column.
