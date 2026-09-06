# R42 — A Prefix Resource Declares Its Members

| | |
|---|---|
| **Status** | **Withdrawn** 2026-09-02 |
| **Amends** | R14 §2.3 (what immutability covers), R32 §2 (what an amendment may add), R36 §3 (the deferred `parquet_dataset` case) |
| **Depends on** | R14 (external resources), R32 (amending a committed packet), R35 (bounded revalidation), R36 (verifying a prefix) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

> **Withdrawn 2026-09-02, unimplemented.** The read case is measured and negative (§4.1); what
> remains is a write cost that no session here has yet had to pay. See §5. R51 no longer depends
> on this and carries the member array it needs, scoped to what needs one.

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
number a project iterating on curation and re-sorting is least likely to keep small. Writing the
twelve members costs 47.6 s, the same work as the rewrite; adding a thirteenth sorting writes one
member of it.

### 4.1 Reading it is not faster, and on the engine that matters it is slower

The same rows staged to S3 four ways — the single file, R42 §2.1's declared member list, the same
members reached by globbing (which §2.1 forbids), and hive layout (which §3 rejects). Cold is the
median of three fresh clients, warm the median of three repeats. Identical rows throughout; the
member arms are 682.2 MB against the single file's 681.6 MB, and hive's stripped column saves
1.9 MB of 682, or 0.3%.

**DuckDB**, cold / warm seconds:

| query | single | members-list | members-glob | hive |
|---|---:|---:|---:|---:|
| `count(*)` whole | **0.20** / **0.08** | 0.28 / 0.16 | 0.32 / 0.16 | 0.44 / 0.14 |
| one run, count | 0.34 / **0.07** | 0.41 / 0.19 | 0.46 / 0.13 | **0.25** / 0.14 |
| one run, 24 units | **0.35** / **0.11** | 0.46 / 0.23 | 0.54 / 0.14 | 0.59 / 0.16 |
| 24 units, all runs | **0.82** / **0.18** | 1.65 / 0.25 | 1.82 / 0.20 | 1.54 / 0.25 |
| 10 s window | **4.24** / **0.15** | 4.60 / 0.26 | 9.58 / 0.18 | 4.78 / 0.18 |

**pyarrow.dataset**, the path R3 §2.1 keeps viable without a SQL engine:

| query | single | members-list | members-glob | hive |
|---|---:|---:|---:|---:|
| `count(*)` whole | **0.11** / 0.00 | 0.68 / 0.00 | 0.46 / 0.00 | 0.39 / 0.00 |
| one run, count | 0.09 / 0.00 | 0.79 / 0.00 | 0.50 / 0.01 | **0.04** / 0.00 |
| one run, 24 units | 0.28 / **0.14** | 0.34 / 0.17 | **0.27** / 0.15 | 0.33 / 0.19 |
| 24 units, all runs | 0.89 / 0.92 | 0.80 / 0.55 | 0.60 / 0.44 | **0.58** / **0.37** |
| 10 s window | 12.57 / 9.18 | 5.76 / 5.30 | **5.87** / **4.79** | 5.65 / 5.98 |

Under DuckDB the single file wins every query in both states, and it wins while being measured
first each round, so it pays the first-touch cost the others do not. `sorting_run_id` is the
second sort column, so a run is already a contiguous span of row groups and one footer prunes it;
twelve files replace that with twelve footers to fetch.

Under pyarrow the member arms win the two queries that cannot prune at all — which is the tell.
**The gain is scan parallelism, not pruning, and not round trips.** The same comparison on local
disk, where there are no round trips, gives 0.38 s for the single file against 0.20 s for the
members: a ratio of 1.9 against S3's 2.2. A layout change is not what buys it, and DuckDB reaches
0.15 s on the single file for the same query, 35 times faster than the best pyarrow arm.

So partitioning does not pay for itself on read. What §1 offers is the write cost above, and §2.1
is what makes that cost safe to take.

## 5. Why this is withdrawn

**The read case does not exist.** §4.1 measures it: under DuckDB the single file wins every query
cold and warm, and under pyarrow the member arms win only the queries that cannot prune — a scan
parallelism effect that reproduces at the same ratio on local disk, where there are no round trips
to skip. The argument that an object store would change the answer was the reason this stayed open
after the local measurement said no, and it does not survive being measured.

**The write case is real and unpaid.** Adding a sorting rewrites 650 MB where partitioning writes
one member of it, quadratic in accumulated sortings. But no session in the corpus has a second
sorting, so the cost is hypothetical, and a revision held open against a hypothetical cost is a
revision that will be re-argued rather than used.

**Most of the machinery exists to make partitioning safe, not to make it useful.** §1's snapshot
failure — an old manifest retroactively acquiring content, because a prefix is resolved by listing
— is *created by* partitioning. Unpartitioned, it does not arise. §2.2's ordering rule exists only
because a multi-file table has rows to concatenate. Both fall with the motivation.

**What was worth keeping is narrower, and R51 now carries it.** §2.1's member array is useful for
a prefix that already exists — an external dense array asset, 208 objects for one LFP series —
where it gives per-member facts a place to live. R51 declares that array itself, as a **MAY** on
an external resource and a record rather than a resolution rule. What it does not take is §2.1's
MUST on packet-owned prefixes, which would have bound one resource in every packet built so far
(`core.waveform_mean`, three objects) for a case nothing has needed.

Revisit this if sortings accumulate, if a session's tables outgrow one file for reasons other than
currency, or if multi-session packets make `session_id` partitioning the natural layout. The
measurement in §4.1 is about one table at one size on one store, and says nothing about those.
