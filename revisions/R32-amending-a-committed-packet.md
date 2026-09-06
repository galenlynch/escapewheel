# R32 — Amending a Committed Packet

| | |
|---|---|
| **Status** | **Accepted** 2026-08-28 |
| **Amends** | `04_packet_catalog_manifest.md` (manifest location and required fields); `05_validation_and_import.md` Stage 5 |
| **Depends on** | R14 (immutability and external resources), R31 (materialization provenance) |
| **Forces** | R31, which cannot be satisfied on an already-committed packet without this |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`05` Stage 5 commits a packet by renaming the manifest into place last, and R14 §2.3 makes
packet-owned bytes immutable afterwards. Neither says what happens next. There is no defined
way to add a resource to a packet that has been committed, so the reference writer refuses a
root that already holds a manifest — which is correct under the rules as written and useless in
practice.

The case that forced this is ordinary. A packet is committed with its core tables. An analysis
resource is derived from them afterwards, because deriving it needs the packet open and the
core tables validated — that is the order `05` puts them in. Under the current rules the only
way to add it is to rebuild the packet from its sources, which discards the validation that
already passed and re-imports data that did not change.

R31 sharpens this into a contradiction. It requires a derived resource to name a row in
`core.processing_runs`, so adding one means that table gains a row, which under a naive reading
of R14 §2.3 mutates packet-owned bytes.

## 2. What an amendment is

An **amendment** produces a new version of an existing packet. It MUST NOT modify any file the
superseded manifest names.

That is the whole of it, and it dissolves the R31 contradiction without carving out an
exception: a table that gains rows is written as a **new file**, and the amended manifest names
the new file. No byte of the old one changes. R14 §2.3 is preserved literally rather than
weakened — immutability is a property of files, and a resource's *content* may be superseded by
naming different bytes.

An amendment MUST set a `packet_version` that sorts strictly after the superseded one, compared
as a semantic version.

## 3. What an amendment may and may not do

| | |
|---|---|
| Add an analysis resource | MAY |
| Add rows to a provenance table (`core.processing_runs`, `core.source_files`, `core.processing_run_inputs`), as a new file | MAY |
| Remove an analysis resource | MAY — `06` makes them disposable |
| Add a core resource | MAY |
| Change the content of a core resource other than the provenance tables | MUST NOT |
| Remove a core resource | MUST NOT |
| Change `packet_id`, `profile_id`, or the standard versions | MUST NOT |

The asymmetry is the design. An amendment extends what a packet says; it does not revise it. A
packet whose core data was wrong is a **new packet**, not a new version of an old one, because
anything already derived from the old core is silently invalidated and nothing in the format
can detect that.

Provenance tables are the exception to the core rule because they are append-only by nature:
a row records that something ran, and a later run does not change what an earlier one did. R9
already treats them as separable from the scientific core.

## 4. The manifest

`04` fixes the manifest at `packet.json`, and it MUST stay there — a reader finds a packet
by that path, not by scanning. So an amendment **rewrites** it, by the same atomic rename `05`
Stage 5 already uses: write a candidate, validate, `rename` it onto the canonical path last.
At every instant that path names a complete, validated manifest.

It is not appended to. JSON has no coherent append, and more importantly a reader MUST be able
to determine the packet's current state in one read, without replaying a history.

**Every manifest a packet has ever had MUST be retained**, at:

```text
manifests/nwb.packet.<packet_version>.json
```

`packet.json` is a copy of the newest. The duplication is a few kilobytes and buys the
property that makes §6 workable: a superseded file is only interpretable if the manifest that
named it still exists. Without the retained manifests, an orphaned file and a stray file are
indistinguishable, and a `sha256` recorded under R14 refers to a state nothing can reconstruct.

The amended manifest MUST be derived from the superseded one, not rebuilt: every packet-level
field the amendment does not change MUST carry over unchanged. `created_at` is the packet's
creation and MUST be preserved; `validation.validated_at` records the latest run and is
replaced. A writer that regenerates the manifest from only the resources it was handed will
silently drop the session inventory, the description, and the codec union — which is what the
reference implementation did before this was written down.

The manifest gains one optional field:

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `supersedes` | string | no | The `packet_version` this manifest replaces. Absent on a first commit. |

### 4.1 The embedded registry

R2 §8 has a packet embed the registry it was written against, at the convention path
`schemas/logical_schemas.json` — the same situation as the manifest, and it needs the same
treatment. An amendment that adds a resource whose schema the embedded registry does not
describe MUST update it, and MUST retain the superseded copy at:

```text
schemas/logical_schemas.<registry_version>.json
```

An amendment MUST NOT install a registry whose `registry_version` equals the superseded one
unless the content is identical. Two registries with the same version and different content
make R2 §8's guarantee vacuous: a packet that carries its registry so it stays readable as the
reference moves on is not helped by a copy that cannot be told apart from a different one.

The registry MUST be installed **before** validation, not after. A validator checks the
embedded copy against the version the manifest declares (R2 §9), so an amendment that declares
the new version while the old copy is still in place fails on a version mismatch that says
nothing about the data. An amendment that does not pass MUST restore the previous registry, so
a refusal leaves the packet exactly as it was — which means there is a window, between install
and either swap or rollback, in which the packet on disk carries a registry its manifest does
not declare. §7's note that concurrent amendment is undefined covers it.

This was found by implementation, twice. The reference registry gained R30's column and kept
its version, so the packet's embedded copy still described the six-column table with the old
order; and once the version was bumped, installing it after validation produced a
`registry.version_mismatch` on a packet whose data was fine.

## 5. Validation

An amendment MUST validate the whole packet, not only what it added.

The narrower path is tempting and is left out on purpose. Validating only the added resource
and the rules that mention it is sound only if no existing rule can reference a resource added
later, and nothing in the registry enforces that. The cost of being wrong is a packet that
claims a validation state it does not have, which is the one failure the format exists to
prevent. A writer MAY offer incremental validation, but a packet MUST NOT record
`validation.status` of `passed` on the strength of it.

An amendment that fails validation MUST leave the superseded manifest in place, so the packet
remains at its previous version rather than becoming unreadable.

## 6. Superseded files

A file that no manifest version names any longer MAY be deleted. Nothing requires it, and an
amendment MUST NOT delete anything as part of amending.

Cleanup is a separate operation because it is the only one that destroys bytes, and it is only
safe with respect to a stated set of manifest versions to keep. Folding it into an amendment
would mean every amendment silently breaks readers holding an older manifest — which is exactly
the case R14's immutability exists to protect.

A packet therefore grows monotonically until something explicitly prunes it. That is the
correct default: bytes are cheap, and a packet that quietly stopped being reconstructible is
not.

## 7. What this does not do

- **No new validation tier and no new rule.** The checks are the ones a commit already runs.
- **No release semantics.** `04` has `release_id` and `06` mentions pinning to a source packet
  release; whether an amendment constitutes a new release is a policy question this does not
  answer.
- **No detection of stale derivations.** If a core resource is added and an analysis resource
  derived from its neighbours becomes misleading, nothing here notices. `06` already says
  dependent resources SHOULD be invalidated when sources change, and still nothing implements
  it.
- **No concurrency.** Two writers amending one packet at once is undefined. The atomic rename
  means one of them wins and the other's resources become orphans, which is survivable but not
  a design.

## 8. Open

- **Whether `packet_version` should mean anything beyond ordering.** Additive amendments and
  removals are different in kind, and semantic versioning has a place to say so, but nothing
  here requires a writer to use it.
- **Whether a reader should be able to open a superseded version.** The bytes and the manifest
  are both retained, so it is mechanically possible, and no API exposes it. Doing so would make
  `manifests/` a first-class feature rather than a record.
- **Whether the provenance-table exception should be a general append mechanism.** `03` already
  permits partitioned Parquet datasets, where adding a part is the natural append, and this
  revision instead writes a whole new file for a table that gains rows. For tables the size of
  `core.processing_runs` the difference does not matter; for a large one it would.
