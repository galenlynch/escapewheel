# R62 — A File That Restates The Manifest

| | |
|---|---|
| **Status** | **Accepted** 2026-09-03 |
| **Amends** | Part 03 "Directory layout" (`03:75`), R2 §8 (versioning) |
| **Depends on** | R3 §3.0 (duplication must buy otherwise-unavailable access) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Part 03's directory layout lists `schemas/semantic_version.txt`, and R2 §8 defines it: *"contains the
semantic standard version string and nothing else."* The manifest already carries that string, as
`semantic_standard_version`, which R2 §10's schema requires.

So the file restates a field the packet cannot omit. R3 §3.0 admits duplication only where it buys
otherwise-unavailable access, and this buys none: a consumer holding the file holds the manifest,
because the file is 23 bytes inside a packet whose catalog is `packet.json`.

### 1.1 Nothing has written it and nothing has read it

Measured across the reference implementation: `semantic_version` appears in no source file of the
reader, the writer or the validator. The writer has never emitted one, so no packet it has built
carries the file, and no packet has been refused for lacking it.

Only `fixtures/build.py` writes one, implementing `03:75` faithfully, and nothing reads that either.

### 1.2 It was found by being unremovable

R61 §2.1 classes a file no manifest names as a **stray** and forbids removing one. Running
`escapewheel prune` over the conformance packet reports exactly one:

```
stray     kept      schemas/semantic_version.txt
```

A specified file that no manifest declares is permanently outside cleanup's reach — not because
cleanup is wrong, but because the packet never claims the file. Governing it would mean declaring
it as a resource, which is a manifest entry per packet for 23 bytes that restate a manifest field.

## 2. Decision

### 2.1 The file is struck

`schemas/semantic_version.txt` is removed from Part 03's directory layout and R2 §8's definition. A
writer **MUST NOT** be required to emit one, and a validator **MUST NOT** refuse a packet for
lacking one.

A packet that carries one stays conforming. R61 §2.1 makes it a stray, which is reported and never
removed, so an existing packet needs no migration and loses nothing.

### 2.2 The manifest is where a version string lives

`semantic_standard_version` in `packet.json` is the sole record of the semantic standard a
packet was written against, as `logical_standard_version` and `registry_version` already are for
theirs. R2 §10's manifest schema requires it.

`schemas/logical_schemas.json` is **not** struck and is not the same case: it embeds a document the
manifest names but does not contain, so a packet without it is not self-describing (R2 §8).

## 3. What this does not change

- **Part 03's layout otherwise.** `schemas/` still holds the embedded registry.
- **R2 §8's other sentences.** The rule that a packet records its registry version and embeds the
  registry is untouched.
- **No stored value.** No manifest field changes, and no packet becomes invalid.

## 4. Rejected

A plain-text file is readable without a JSON parser, where the manifest is not. That saves nothing
here: `packet.json` is the packet catalog, so no consumer reads a packet without parsing JSON,
and R3 §2.1's floor is about a *reader's* dependency closure rather than a shell script's.
