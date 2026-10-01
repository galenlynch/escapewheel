# Design

The validator runs a packet through four layers in order: the manifest's shape, the registries the
packet binds, each resource's physical storage, then the rules. Part 05 §5 says what each layer
must check, and the order is this package's choice. This page explains the choices behind each
layer.

## Rules are SQL; storage checks are Python

A rule is SQL that returns offending rows, so an empty result is a pass. SQL can check what the
data says: values, keys, references and vocabularies. It cannot check how the data is stored,
because a relation has no row order, no file layout and no physical type, and a storage check
written as SQL passes in silence. The validator therefore checks physical order, file presence and
column types in Python, in what Part 05 §5.3 calls the shim.

## Checks are generated from the registry

No check is written by hand for a table. A registry's structure yields the checks for required
columns, primary keys, foreign keys, closed vocabularies and finite values (Part 02 §10.1), and
the registry's Tier 2 rules pass through unchanged (Part 02 §10.2).

The generator checks a discriminator's value for the form of a resource ID as well as for
resolving. The form can be checked without knowing which resources exist, and without that check
`scope_kind` could hold an empty string that no rule sees.

The caller supplies the kinds a discriminator may name, and the generator does not read them from
the registry it is generating for. The mechanism exists for a packet's extension kinds: a union
written over core's kinds alone has no branch for an extension's kind and would pass one in
silence. A kind that resolves to nothing is reported at `info`, including where Part 02 §8.3 makes
that a fact and not a defect.

## The ordering scan settles uniqueness

The ordering scan compares neighbouring rows. Where a table's sort order begins with its primary
key, duplicate keys are adjacent, so the same pass settles uniqueness.
`adjacency_settles_uniqueness` reports those tables, and `generate` then leaves the `GROUP BY`
check out. The `GROUP BY` materialises every key column of every row and spills where they do not
fit in memory, while the scan reads the rows in order and holds one batch.

The scan reads `ORDER_BATCH` rows at a time, because a spike table's sort columns read whole are
one Python object per row and column.

`verify_order` runs the same check for a writer as it writes, which saves the writer from reading
the table again afterwards.

## DuckDB runs under a memory limit with somewhere to spill

Left to itself DuckDB claims 80% of system memory and every core. `LIMITS` bounds it at 4 GB and
four threads. A bound costs time and never correctness: an aggregate that does not fit spills to
disk and runs slower.

A memory limit bounds nothing without somewhere to spill, so the limit and the spill directory are
set as a pair. The spill directory defaults to the packet's filesystem. A temporary directory on
tmpfs would spill into the memory that the limit protects.

## An amendment is checked by comparing rows

Every other check reads the current version alone. A table that gains a row group gains a file, so
only a comparison of rows shows that no superseded row changed and no group grew (Part 05 §15.6).
The validator shares the group test (Part 02 §2.8) with a writer that settles delivered rows
against the packet it amends, so the two cannot disagree about which groups a version holds.

## Each manifest phase stops evaluation on a finding

The `json`, `shape` and `entries` phases need only the manifest's bytes. A finding in any of them
stops evaluation, so a later phase never indexes into a document that an earlier phase rejected.
The `registry_binding` phase acquires each bound registry through its descriptor. Each phase
reports under Part 04 §10's check IDs.

## External resources are checked only on request

A large resource is expected to be referenced and not copied, and in production the reference
points at an object store. Two limits bound what a packet may say about those bytes.

**Nothing in `stores` runs by default.** Part 04 §5.3 keeps structural validation off the network,
because reachability, credentials and whether the caller is offline are properties of a situation
and not of a packet. A caller reaches every function in `stores` by asking for a mode.

**A verification holds for a point in time.** Immutability covers packet-owned bytes, and an
external resource may change or vanish without the packet changing (Part 03 §8.2). The functions
return what was true when they looked, and `verified_at` records when that was.

The `stores` module lives with the validator because no read path uses it. A table resolves to a
local path or goes to DuckDB as a URI, and a Zarr array's own library opens the array's URI. Only
Part 04 §4.3's digest needs a store client, to list a prefix and hash its members. Both users of
that digest are on this side: this package checks what a manifest claims, and `escapewheel-writer`
establishes the claim through its `verify` setting.

A local path needs no library. Any other scheme goes through fsspec, which the `remote` extra
installs. Each scheme needs its own backend as well: `s3fs` for `s3://`, `gcsfs` for `gs://`.

### Reading every byte is a separate mode

The checksum mode is separate from the external mode because of how much it reads. On one session's
LFP, referenced from an object store, reading every byte meant 6.8 GB: 75 s from local disk and
88 s from S3. The packet's own 1,209 MB took 0.60 s. The rest of the external mode is one list
operation of 1.31 s, and comparing store digests costs the same 1.31 s, because the listing already
carries the digests.

One LFP series is 208 chunk objects and a metadata document. Read one object at a time, it digests
at 15.7 MB/s, and across `WORKERS` = 8 at 94 MB/s, which is eight minutes against one. `BLOCK`
bounds memory on an array of that size.
