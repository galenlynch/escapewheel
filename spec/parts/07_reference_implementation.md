# Part 07 — Reference Implementation

Informative.

<a id="ew-reference-implementation-scope" data-spec-anchor="canonical"></a>
## 1. Scope

This part describes the reference implementation's shape. Nothing here constrains a conforming implementation.

## 2. Distribution layout

The reference implementation is three distributions with one command-line entry point.

| distribution | contents | depends on |
|---|---|---|
| `escapewheel-reader` | manifest and resource resolution, tabular access | — |
| `escapewheel-validator` | the checks of Part 05 | reader |
| `escapewheel-writer` | source adapters, the recipe, the packet writer | validator |

The split is not cosmetic. The validator's correctness is pinned to a registry version while the reader's API is not, and the writer depends on the validator because commit is validate-then-rename (05 §6).

### 2.1 One command, three providers

`escapewheel-reader` owns the `escapewheel` console script. The other two register subcommands through an entry-point group. Two distributions declaring the same script name is a conflict in which the last installed wins silently.

### 2.2 Dependency discipline

Validation requires an embedded SQL engine, because the rules are SQL. Reading does not: a complete read path goes through the columnar library alone, so the SQL engine is an optional extra.

## 3. Command line

```text
escapewheel inspect <kind> <root>      what one source offers (05 §4.1)
escapewheel init --source k=path ...   draft a recipe, flagging contested resources
escapewheel import <recipe> --check    every problem, before any I/O (05 §3.5)
escapewheel import <recipe> --strict   refuse anything an adapter worked around
escapewheel import <recipe>            steps 2 to 8 (05 §2)
escapewheel verify <packet>            record what is true of external resources
escapewheel prune <packet>             remove what the packet no longer names (05 §15.5)
```

<a id="ew-reference-object-model" data-spec-anchor="canonical"></a>
## 4. Object model

| type | responsibility |
|---|---|
| `Packet` | resolve the manifest; hand back resources |
| `Dataset` | present several packets as one relation per resource |
| `TableResource` | a table, as columnar batches or a scan |
| `ArrayResource` | an array, opened through the array library |
| `Validator` | run the generated and declared checks; return a report |
| `PacketWriter` | accumulate records; stage, validate, commit |

An adapter returns its rows as records, not a path, and they stay records whichever route delivers them. That is what lets an adapter be tested without a filesystem and stops normalization decisions leaking into I/O code. Out of process the transport carries a table and the receiving end returns records again, so nothing downstream of the boundary knows which route was taken. A packet-owned array or opaque payload crossing a protocol and a report are written where the build points (Part 05 §2).

An adapter carries six static declarations, all readable with nothing open: `PRODUCES`, the resource identifiers it can supply (Part 05 §3.4); `CONTRIBUTES`, those of them whose rows it supplies only in part, such as the clocks of its own streams (Part 05 §3.4); `STATES`, the recipe fields it can state, as `block.field` names such as `subject.subject_id` (Part 05 §3.4); `NEEDS`, the values a build must supply it, drawn from Part 12 §4's terms and the recipe's options; `ACCEPTS`, the options it reads and can run without, which a recipe may leave unset, and `source_cache` where it keeps source data in the build's source-cache location (Part 12 §4); and `CONSUMES`, the kinds whose output it reads, which is what orders a build. For each name in `STATES` the adapter exposes the value it holds. All six are class attributes here, and Part 12 §7's document is the same facts for an adapter a build cannot import; the requirements in Parts 05 and 12 are on what a build can determine, not on how an implementation stores it.

An adapter released independently of the writer declares its protocols by naming constants the implementation exports rather than strings it spells, so an adapter resolves the versions it was written against and each speaks what it names. An adapter the writer ships declares none, and the writer runs it in process or serves it over any protocol of the group (Part 12 §3).

Converting records to a table takes the column set from every row and not from the first. `pyarrow.Table.from_pylist` infers its schema from the leading row and silently drops what later rows carry, which loses a column a source populates for some rows only — measured, one of thirteen resources of the NWB adapter. The rule it implements is Part 12 §5's, stated about what a delivery says rather than about how a table is built, because an adapter declaring its schema up front meets it by construction.

An adapter that produces a dense array across a protocol writes it to the location the build supplied and returns the reference (Part 12 §5). An adapter the writer runs in process may instead hand the array's values over, and the writer writes them to that location. An adapter delivering a packet-owned opaque resource writes the file or directory under its own name into a directory, named by the resource ID, in the location the build supplied, or hands the writer its bytes in process.

A build reports a `metadata` key whose value equals a column of the same row, which is how Part 02 §8.6's prohibition on restating a column reaches whoever wrote the bag. No rule can do it: the content is schemaless, and an adapter names a key in the source's vocabulary where core names a column in its own. The comparison is the same duplicate-value comparison used between two columns, applied to a key and a column; three keys in the packaged sessions restated a column.

<a id="ew-reference-testing" data-spec-anchor="canonical"></a>
## 5. Testing

A conformance corpus holds one conforming packet and a set of variants, each with its expected finding recorded as data rather than as a test body. The corpus runs against the reference validator rather than reimplementing the checks.

<a id="ew-reference-performance-notes" data-spec-anchor="canonical"></a>
## 6. Performance notes

These are properties of the reference implementation and the libraries it uses, not requirements. Part 10 carries what follows from Parquet, Zarr or an object store.

- **The reference writer converts no column to host objects inside a per-batch loop.** Every performance defect found in it has been one.
- **It reads a large table in batches.** A 10⁸-row spike table decodes to many gigabytes if read whole.
- **It bounds memory explicitly** where a job's working set is data-dependent, and gives its SQL engine a spill directory: a memory limit without one bounds nothing.
- **It does not measure every column's encoding at write time.** Writing each column three ways over a
  65,536-row sample and keeping the smallest costs about **0.4 s** for a whole packet against a
  467 s build, so cost is not what refuses it: a measured choice records no reason for itself, and
  it differs between a `--sample` build and a full one. Counting each column instead, as
  Part 03 §5.5's rules do, costs 0.12 s to 0.20 s a packet and states its reason in the count.
- **Its reader projects a constant rather than joining for it.** It adds session identity to a
  view as a scalar expression over `session_id`. An engine can prune a projection a query does not
  select; it generally cannot prune a join whose output might filter or duplicate rows.

Part 06 §3's test weighs two costs of subject 776259's session of 6,781 units, which follow from the
libraries measured (by 2026-09-01; versions not kept):

- aligning all its units' spikes to one event and window costs **0.13 s to 1.72 s** with numpy, two
  `searchsorted` calls per unit against trains already in memory; and
- a wide trial table of **708 rows** returns in **7.5 ms** from DuckDB as a view.
