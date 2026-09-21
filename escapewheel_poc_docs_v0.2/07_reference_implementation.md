# Part 07 — Reference Implementation and Plan

Informative.

## 1. Scope

This part describes the reference implementation's shape and the phase plan. Nothing here constrains a conforming implementation.

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

This is what Part 02 §5.2's ban on nested types exists to preserve — a native reader stays viable in a language without an embedded SQL engine.

## 3. Command line

```text
escapewheel inspect <kind> <root>      what one source offers (05 §4.1)
escapewheel init --source k=path ...   draft a recipe, flagging contested resources
escapewheel import <recipe> --check    every problem, before any I/O (05 §3.5)
escapewheel import <recipe> --strict   refuse anything an adapter worked around
escapewheel import <recipe>            stages 2 to 7
escapewheel verify <packet>            record what is true of external resources
escapewheel prune <packet>             remove what the packet no longer names (03 §9.3)
```

## 4. Object model

| type | responsibility |
|---|---|
| `Packet` | resolve the catalog; hand back resources |
| `Dataset` | present several packets as one relation per resource |
| `TableResource` | a table, as columnar batches or a scan |
| `ArrayResource` | an array, opened through the array library |
| `Validator` | run the generated and declared checks; return a report |
| `PacketWriter` | accumulate records; stage, validate, commit |

An adapter's return type is records, not a path, and stays records whichever route delivers them. That is what lets an adapter be tested without a filesystem and stops normalization decisions leaking into I/O code. Out of process the transport carries a table and the receiving end returns records again, so nothing downstream of the boundary knows which route was taken.

An adapter carries five static declarations, all readable with nothing open: `PRODUCES`, the resource identifiers it can supply (Part 05 §3.4); `STATES`, the recipe fields it can state, as `block.field` names such as `subject.subject_id` (Part 05 §3.4); `NEEDS`, the values a build must supply it, drawn from Part 03 §11.2's terms and the recipe's options; `ACCEPTS`, the options it reads and can run without, which a recipe may leave unset (Part 03 §11.2); and `CONSUMES`, the kinds whose output it reads, which is what orders a build. For each name in `STATES` the adapter exposes the value it holds. All five are class attributes here, and Part 03 §11.5's document is the same facts for an adapter a build cannot import; the requirements in Part 05 and Part 03 are on what a build can determine, not on how an implementation stores it.

An adapter declares its protocol by naming a constant the implementation exports rather than a string it spells, so an adapter resolves the version it was written against and that version speaks what it names.

Converting records to a table takes the column set from every row and not from the first. `pyarrow.Table.from_pylist` infers its schema from the leading row and silently drops what later rows carry, which loses a column a source populates for some rows only — measured, one of thirteen resources of the NWB adapter. The rule it implements is Part 03 §11.3's, stated about what a delivery says rather than about how a table is built, because an adapter declaring its schema up front meets it by construction.

An adapter that produces a dense array writes it to the location the build supplied and returns the reference, rather than handing the values over for the writer to write (Part 03 §11.3).

A build reports a `metadata` key whose value equals a column of the same row, which is how Part 02 §8.6's prohibition on restating a column reaches whoever wrote the bag. No rule can do it: the content is schemaless, and an adapter names a key in the source's vocabulary where core names a column in its own. The comparison is the same duplicate-value comparison used between two columns, applied to a key and a column; three keys in the packaged sessions restated a column.

## 5. Phases

| phase | scope | state |
|---|---|---|
| 0 | hand-built fixture packet | complete |
| 1 | manifest and table reader | complete |
| 2 | validator | complete |
| 3 | source importer and recipe | complete |
| 4 | analysis materializations | complete; four of five resources withdrawn (06 §6) |
| 5 | dense arrays | complete, owned and referenced |
| 6 | release and version discipline | specified (03 §9); pruning implemented, amendment partial |
| 7 | Iceberg profile experiment | not started |

## 6. Testing

A conformance corpus holds one conforming packet and a set of variants, each with its expected finding recorded as data rather than as a test body. The corpus runs against the reference validator rather than reimplementing the checks.

Run it after changing the registry, the generator, or any rule.

<a id="ew-reference-performance-notes" data-spec-anchor="canonical"></a>
## 7. Performance notes

These are properties of the reference implementation, not requirements. A number that would change if this implementation were replaced belongs here; one that follows from Parquet, Zarr or an object store belongs to Part 10, and this section MUST NOT repeat it.

- **Never convert a column to host objects inside a per-batch loop.** Every performance defect found in the reference writer has been this.
- **Read a large table in batches.** A 10⁸-row spike table decodes to many gigabytes if read whole.
- **Bound memory explicitly** where a job's working set is data-dependent, and give the SQL engine a spill directory: a memory limit without one bounds nothing.
- **Do not measure every column's encoding at write time.** Writing each column three ways over a
  65,536-row sample and keeping the smallest costs about **0.4 s** for a whole packet against a
  467 s build, so cost is not what refuses it: a measured choice records no reason for itself, and
  it differs between a `--sample` build and a full one. Counting each column instead, as
  Part 03 §5.5's rules do, costs 0.12 s to 0.20 s a packet and states its reason in the count
 .
- **Project a constant rather than joining for it.** A reader adding session identity to a view SHOULD emit a scalar expression over `session_id`. A projection a query does not select is pruned and costs 1.02x; the join a reader writes first cannot be pruned, because the planner cannot show it neither filters nor duplicates rows, and costs 2.22x whether its output is read or not.
