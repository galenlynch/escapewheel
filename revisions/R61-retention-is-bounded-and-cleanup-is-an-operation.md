# R61 — Retention Is Bounded And Cleanup Is An Operation

| | |
|---|---|
| **Status** | **Accepted** 2026-09-03 |
| **Supersedes** | R32 §4 (what a packet retains), R32 §6 (cleanup as a separate operation) |
| **Depends on** | R14 §2.3 (packet-owned bytes are immutable), R32 (amending a committed packet), R35 (revalidation is bounded by immutability) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R32 §4 retains every superseded manifest under `manifests/nwb.packet.<version>.json`, for a stated
purpose: *"a superseded file is only interpretable if the manifest that named it still exists.
Without the retained manifests, an orphaned file and a stray file are indistinguishable."* R32 §6
makes the cleanup that consumes them a separate operation.

That operation does not exist. Measured across the reference implementation: `manifests/` is
written by `writer.py` and `verify.py` and **read by nothing** — no path in the reader, the
validator or the writer opens one, across 590 tests and 26 conformance packets. The CLI offers
`inspect`, `init`, `extension`, `verify` and `import`, and no pruner.

So retention accumulates without bound to serve a consumer that was never built, which is R42's
shape: machinery kept alive by a motivation that has not arrived.

### 1.1 What the field does

Retention is not the defect; unbounded retention with no pruner is.

| | history | expiry operation | defaults |
|---|---|---|---|
| Iceberg | metadata chain, snapshots | `expireSnapshots`, `removeOrphanFiles` | snapshot age 5 days, min snapshots 1, previous metadata versions 100, **metadata deletion off** |
| Delta Lake | numbered commit log | `VACUUM` | data files 7 days, log files 30 days |

Iceberg's `write.metadata.delete-after-commit.enabled` defaults to `false`, so Iceberg retains
metadata unboundedly too. The difference is that its pruner exists, is named, and is one property
away. Delta's split is instructive as well: **data files and log files expire on separate clocks**,
7 days against 30, because the log is small and the files are not.

## 2. Decision

### 2.1 Cleanup is an operation this specification defines

A conforming implementation **SHOULD** offer cleanup over a committed packet. It removes, in this
order and no other:

1. **Orphans** — files no retained manifest and no current manifest names.
2. **Superseded manifests** — those the retention policy no longer keeps.

**The order is load-bearing.** A manifest identifies the orphans of its own version, so expiring it
first makes an orphan and a stray indistinguishable, permanently. R32 §4's argument for retaining
is exactly this dependency, and it survives.

A stray file — one no manifest ever named — **MUST NOT** be removed. A packet may carry files this
specification does not govern, and cleanup that deletes the ungoverned is a data-loss operation
wearing a maintenance name.

Cleanup **MUST** default to reporting what it would remove without removing it.

### 2.2 A packet declares its retention

The manifest **MAY** carry a `retention` object, and a writer **SHOULD** emit one:

| | | |
|---|---|---|
| `keep_versions` | integer | how many superseded manifests to retain. Default **1** |
| `keep_days` | number | drop a superseded manifest older than this. Default **absent**, meaning age alone never expires one |

Both are floors: a manifest is expired only when **both** permit it. `keep_versions: 1` follows
Iceberg's `min-snapshots-to-keep`, and it is the right default here for a reason Iceberg does not
have — a packet that is never amended retains nothing and carries no `manifests/` directory at all,
so the common case costs nothing.

Age is off by default because a packet is an archival artifact where a table is an operational one.
Delta expires its log at 30 days because a stale commit log has no readers; a packet's history is
cited in a paper.

### 2.3 What is retained is not what is readable

Retention exists to make cleanup decidable. It does not promise that a consumer can read an earlier
version of the packet, and no consumer does: `packet.json` is the packet.

A retained **registry** is different and is not covered by the policy above. `logical_schemas.<version>.json`
is read — `PacketWriter._install_registry` refuses an amendment that would put two different
registries at one `registry_version` — so it is retained for as long as a manifest naming it is.

## 3. Iceberg layers above this, not through it

`03` defers an Iceberg profile and says an Iceberg catalog manages only tables. Two axes follow,
and stating them now costs a paragraph where discovering them in Phase 7 costs a redesign.

**`packet_version` versions the bundle: which resources exist.** An Iceberg snapshot versions a
table's rows. They are not the same clock, and an amendment that only rewrites a table's rows
bumps an Iceberg snapshot and **MUST NOT** bump `packet_version`.

**A correction is a rebuild, not an amendment.** R32 §3 makes an amendment add resources and modify
no file, and R14 §2.3 makes packet-owned bytes immutable, so this profile has no in-place table
mutation to version and needs none. A table that is wrong is fixed by rebuilding the packet, which
re-reads no external resource and costs the packet-owned bytes alone — 0.60 s of digest over
1,209 MB by R52 §3's measurement.

Per-table version history is therefore **not** added here. It would be Iceberg's mechanism built
worse, for a mutation this profile does not permit.

## 4. What this does not change

- **`packet_version` and R32 §2's versioning.** Unchanged.
- **R32 §3's rule that an amendment modifies no file.** Unchanged, and §3 above depends on it.
- **R35.** Revalidation is bounded by what the writer knows it wrote, not by diffing manifests, so
  nothing in R35 reads a retained manifest and nothing in it changes.

## 5. Open

- **Whether cleanup should be able to run against a remote packet.** Every operation here is a
  listing plus a delete, which R14 §2.2 keeps out of structural validation but says nothing about
  a maintenance command. Listing a packet prefix is bounded and cheap; deleting is not reversible.
- **Whether a stray file should be reported.** §2.1 forbids removing one. Naming them in the
  cleanup report would find a half-written commit, at the cost of a listing that scales with the
  packet rather than with its manifests.
