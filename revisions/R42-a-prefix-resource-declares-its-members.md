# R42 — A Prefix Resource Declares Its Members

| | |
|---|---|
| **Status** | **Proposed** 2026-09-01 |
| **Amends** | R14 §2.3 (what immutability covers), R32 §2 (what an amendment may add), R36 §3 (the deferred `parquet_dataset` case) |
| **Depends on** | R14 (external resources), R32 (amending a committed packet), R35 (bounded revalidation), R36 (verifying a prefix) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R41 made it expressible which of several sortings a consumer should read. It did not make
carrying a second one cheap: `core.spike_events` is a single file, so adding a sorting rewrites
650 MB and 286,896,563 rows. Partitioning by `sorting_run_id` would make it additive — the sort
order already begins `session_id, sorting_run_id`, so a partition is a contiguous run of the
table and concatenation preserves R30 §3.2's layout.

**The manifest cannot describe the result.** A partitioned resource's `uri` names a *prefix*.
`uri` is one string and `partitioning` lists column names, not files, so nothing in the entry
says what the prefix contained. Two things break, and the first is the one that matters.

**Snapshots stop holding, exactly where they are needed.** R32 retains every manifest so an
earlier version stays readable. A prefix is resolved by *listing* it, so adding a partition
retroactively changes what the **old** manifest resolves to: version 0.2.0 acquires a sorting it
never contained, and the guarantee fails precisely in the amendment case partitioning exists to
serve.

**And a `parquet_dataset` has no defined row order at all.** R10 §2 sorts every table and R30
§3.2 pins this one's order specifically, but across files the order is whatever the filesystem
yields — `pyarrow.dataset` fixes no fragment order and no rule supplies one. So R12's
physical-order check, which is also what lets 14 uniqueness checks skip a `GROUP BY` that spilled
26 GB, has nothing well-defined to check on a partitioned table.

R36 §3 saw the neighbouring half and deferred it: *"It does not define a digest for a
`parquet_dataset`, which is also a prefix. The same rule applies by construction, but no packet
yet externalises one."* A packet-owned partition is the case it set aside.

## 2. Decision

### 2.1 A packet-owned prefix declares its members

A resource entry gains `members`: an **ordered** array of

```json
{"key": "<relative key>", "size_bytes": <int>, "sha256": "<hex>"}
```

with `key` relative to `uri` using `/` separators and `sha256` optional, as R14 §2.3 leaves it.

A resource the packet owns whose `uri` names a prefix **MUST** declare `members`. An external one
**MAY**: R14 §2.3's immutability covers packet-owned bytes only, and R14 already says an external
resource's recorded facts are what was true at validation rather than a promise about now.

A reader resolving a resource that declares `members` **MUST** read exactly those and **MUST NOT**
enumerate the prefix. That is the whole of the snapshot guarantee: what an old manifest names is
what an old manifest gets.

### 2.2 The rows are the members, in the declared order

A table resource's rows are the concatenation of its members in the order `members` gives.

This is what makes R10 §2's sort and R30 §3.2's override checkable across files. The shim
compares neighbours within a member and across each member boundary, exactly as it already does
across batch boundaries — and the boundary comparison is not optional, because a duplicate or a
descent split across two members would otherwise pass unseen.

The array is **ordered, not sorted by key**. A partition's correct position follows the sort
columns, not its filename, and a writer that had to encode order into filenames would be
constrained in naming for a reason no reader should have to infer.

### 2.3 The digest is unchanged

`sha256` on the resource keeps R36 §2.2's meaning: over a prefix it is the digest of that
revision's canonical listing. Where `members` is declared, the listing digested is the declared
one, so the enumeration and the digest cannot disagree.

### 2.4 An amendment adds members

Adding a partition appends members and modifies none, so R14 §2.3's immutability holds literally
rather than by exception — which is what R32 §2 already requires of everything else an amendment
does.

R35 §2's bound applies unchanged: an untouched member's verdict is determined by immutability, so
revalidation covers the added members and the rules naming the resource, not the whole table.
Adding a thirteenth sorting to a session revalidates one member, not 287 M rows.

## 3. What this does not do

- **No requirement to partition.** A single-file resource is unaffected and stays the norm; this
  says what a packet must declare *if* it partitions.
- **No new digest.** R36 §2.2 stands as written.
- **No required checksum.** `sha256` on a member is optional, as it is on a resource.
- **No hive encoding.** A member carries the full schema; a partition column is not stripped into
  its path. R3 §2.1's native reader concatenates members without a path parser, and the physical
  schema keeps matching the registry, which `_check_schemas` compares against.
- **No opinion on what to partition by.** `sorting_run_id` motivates this; `session_id` is what
  `03` already suggests for large tables. The mechanism is indifferent.
- **No cross-packet index.** A dataset-level catalogue is a separate question, and Phase 7.

## 4. Measured

On `ecephys_776259_2025-04-09`, one session, twelve probe streams:

| | today | partitioned by `(session_id, sorting_run_id)` |
|---|---:|---:|
| `core.spike_events` | 1 file, 650 MB, 286,896,563 rows | 12 members, same bytes |
| adding a second sorting | rewrites 650 MB | appends 12 members, rewrites none |
| manifest cost | — | 12 entries |
| revalidation after the amendment | the whole table | the added members (R35 §2) |

The rewrite is not incorrect today — R32 gets immutability by writing a new file and retaining
the old — but it is quadratic in the number of sortings a session accumulates, which is the
number a project iterating on curation and re-sorting is least likely to keep small.
