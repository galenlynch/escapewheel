# R84 — Escapewheel Replaces nwb-lake

| | |
|---|---|
| **Status** | Proposed |
| **Amends** | `00`–`09` and `03` §2 (the profile identifier), `04` §2 (the catalog filename), R2 §9 (published schema `$id`s), R17 §2 (`extends`), R80 §2.2 (the sidecar's version string) |
| **Depends on** | R32 (a packet version is the bundle), R61 (a correction is a rebuild), R71 (canonical is a property of a resource) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

This project is currently called **nwb-lake**. The name appears in three distributions, one CLI,
the catalog filename every packet carries, and three version strings every packet declares:
`profile_id`, `semantic_standard_version` and `logical_standard_version`, which on
`ecephys_776259` read `nwb-lake-portable-v0.1`, `nwb-lake-semantic-v0.1` and
`nwb-lake-logical-v0.1`.

## 1. Motivation

### 1.1 The name claims an affiliation the project does not have

`nwb-lake` reads as an NWB sub-project. Neurodata Without Borders has not blessed this work, is
not consulted on it, and would have no way to correct the impression: a reader meeting
`nwb-lake-portable-v0.1` in a manifest has no signal that the two are unrelated.

The relationship is the opposite of what the name suggests. This format exists because of NWB's
shortcomings — implicit float seconds, identity by file path, a metadata model with no
computable floor — and its every design decision is a departure rather than an extension. A name
implying endorsement misdescribes the work to the one audience most likely to read it.

### 1.2 The name will outlast the format's ephys focus

Naming the format after its current domain would be the same mistake one level down. The clock
model — integer ticks on a declared clock, with an explicit alignment graph — is **72% of core**
and is true of behaviour, photometry, imaging and EMG alike; spikes are true of none of them. A
name drawn from the invariant survives a second modality arriving, where `ephys-lake` or
`spikelake` would need renaming again, and a format renamed twice is worse than one named
carefully once.

An **escape wheel** is the toothed wheel a clock's pallet releases one tooth at a time. It is the
part that emits ticks, which is what this format commits to and what NWB leaves implicit.

### 1.3 `escapement` is taken by an adjacent package

The mechanism as a whole would have been the better word. PyPI carries `escapement` already, at
version 0.2.0, described as a **"Composable time code encoder/decoder"** — close enough in
subject that a search for one returns the other and a reader has to work out which is which.
`escapewheel` is free, as are `escapewheel-reader`, `-validator` and `-writer`.

Publishing the bare name is not required — the three distributions are what would be uploaded,
and `escapement-reader` was free — but a name that collides in *meaning* costs more than one
that collides in the index, and neither is worth paying when a free alternative names the same
mechanism.

## 2. Decision

### 2.1 The project is called escapewheel

The repository, the CLI and the distributions take the new name: `escapewheel-reader`,
`escapewheel-validator` and `escapewheel-writer`, importing as `escapewheel_reader` and so on,
with one console script `escapewheel` and the entry-point group `escapewheel.commands`.

### 2.2 A packet's declared identifiers carry the new name

The three standard version strings become `escapewheel-portable-v0.1`,
`escapewheel-semantic-v0.1` and `escapewheel-logical-v0.1`; an extension's `extends` names the
last of these (R17 §2); the source resolution document declares
`escapewheel-sources-v0.1` (R80 §2.2); and published schema `$id`s move from
`https://nwb-lake.org/schemas/…` to `https://escapewheel.org/schemas/…`.

The version component does not move. `v0.1` names the standard's revision, the rename changes no
clause of it, and bumping it would assert a change to the format that this revision does not
make.

### 2.3 The catalog filename drops its prefix

`nwb.packet.json` becomes `packet.json`. Inside a packet root the directory *is* the packet, so
the prefix disambiguates against nothing — R80 already wrote the sidecar as `sources.json` on
that reasoning, and this makes the two agree.

### 2.4 No alias is added for the old identifiers

A consumer meeting `nwb-lake-portable-v0.1` **MUST NOT** treat it as this profile. An alias is a
compatibility promise, and there is nobody outside this repository to keep it for: two packets
exist, both rebuildable, and R61 §5 already makes a correction a rebuild that re-reads no
external resource. Refusing an unrecognised profile is what a reader does today, so this clause
adds no code — it records that the absence is deliberate.

### 2.5 The compatibility layer keeps the name `nwb`

The third layer — `core` / `analysis` / `nwb` — is the compatibility **projection to** NWB, and
naming a projection after its target is accurate. It keeps its name, as do the `nwb` source
adapter and every reference to the NWB format as a format.

## 3. What this does not change

- **`nwb_lake_poc_docs/` keeps its name.** It is the frozen v0.1 specification, which R1's
  process forbids editing even to correct an error, and seven revisions cite paths into it. The
  live amended copy, `nwb_lake_poc_docs_v0.2/`, moves.
- **No resource ID changes.** `core.*` and `analysis.*` carry no project name, so no table, column
  or rule is touched and no packet's data is rewritten.
- **`registry_version` does not move.** It versions the registry's content, which this revision
  leaves alone.
- **No clause of the standard changes.** Every MUST and SHOULD in `00`–`09` means afterwards what
  it meant before; only the strings naming the standard differ.

## 4. Consequence

Mechanical, and large: **186 files** contain `nwb-lake`, **129** contain `nwb_lake`, **104**
contain the profile string, **47** contain `nwb.packet.json`, and five directories are named for
the project. Every occurrence is in this repository.

Both measured packets must be rebuilt, at roughly 300 s each, because their manifests declare the
old identifiers and R14 §2.3 forbids editing a manifest in place. Neither rebuild re-reads an
external resource (R61 §5), and no table's bytes change.

`verify.py` makes the change safe to do mechanically. It regenerates the registry, the spec
rendering, the fixtures and the tracking documents and then demands a clean tree, so a
find-and-replace that misses a generated file fails rather than drifting.

## 5. Open

- **Whether `registry_version` should bump now.** It has stood at `0.1.0` while R48, R53, R56 and
  R83 each changed the registry's content, and §3 declines to move it here as well. Two packets
  claiming one version with incompatible schemas is what the field exists to prevent, and it is
  free to settle while nobody outside holds a packet.
- **Whether `escapewheel.org` should be registered.** §2.2 puts schema `$id`s there, and R57 §2.1
  makes an `$id` an identity rather than a fetch instruction, so nothing dereferences it. Serving
  it would deliver the editor integration R57 §5 recorded as unpaid, and not serving it leaves
  the claim exactly as verifiable as it is today.
- **Whether the three distributions should become four.** R84 renames what exists. The typed
  ephys accessors — `units()`, `spike_times()`, R38's observation-window inheritance — are the
  part of the reader a non-ephys modality would not want, and splitting them is the change a
  second modality would force. Nothing has asked yet, which R66 §1.4 makes the reason to wait.
