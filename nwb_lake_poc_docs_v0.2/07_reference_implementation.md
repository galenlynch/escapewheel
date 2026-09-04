# Part 07 — Reference Implementation and Plan

Informative.

## 1. Scope

This part describes the reference implementation's shape and the phase plan. Nothing here constrains a conforming implementation.

## 2. Distribution layout

The reference implementation is three distributions with one command-line entry point.

| distribution | contents | depends on |
|---|---|---|
| `nwb-lake-reader` | manifest and resource resolution, tabular access | — |
| `nwb-lake-validator` | the checks of Part 05 | reader |
| `nwb-lake-writer` | source adapters, the recipe, the packet writer | validator |

The split is not cosmetic. The validator's correctness is pinned to a registry version while the reader's API is not, and the writer depends on the validator because commit is validate-then-rename (05 §6).

### 2.1 One command, three providers

`nwb-lake-reader` owns the `nwb-lake` console script. The other two register subcommands through an entry-point group. Two distributions declaring the same script name is a conflict in which the last installed wins silently.

### 2.2 Dependency discipline

Validation requires an embedded SQL engine, because the rules are SQL. Reading does not: a complete read path goes through the columnar library alone, so the SQL engine is an optional extra.

This is what Part 02 §5.2's ban on nested types exists to preserve — a native reader stays viable in a language without an embedded SQL engine.

## 3. Command line

```text
nwb-lake inspect <kind> <root>      what one source offers (05 §4.1)
nwb-lake init --source k=path ...   draft a recipe, flagging contested resources
nwb-lake import <recipe> --check    every problem, before any I/O (05 §3.5)
nwb-lake import <recipe> --strict   refuse anything an adapter worked around
nwb-lake import <recipe>            stages 2 to 7
nwb-lake verify <packet>            record what is true of external resources
nwb-lake prune <packet>             remove what the packet no longer names (03 §9.3)
```

## 4. Object model

| type | responsibility |
|---|---|
| `Packet` | resolve the catalog; hand back resources |
| `TableResource` | a table, as columnar batches or a scan |
| `ArrayResource` | an array, opened through the array library |
| `Validator` | run the generated and declared checks; return a report |
| `PacketWriter` | accumulate records; stage, validate, commit |

An adapter's return type is records, not a path. That is what lets adapters be tested without a filesystem and stops normalization decisions leaking into I/O code.

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

## 7. Performance notes

These are properties of the reference implementation, not requirements.

- **Never convert a column to host objects inside a per-batch loop.** Every performance defect found in the reference writer has been this.
- **Read a large table in batches.** A 10⁸-row spike table decodes to many gigabytes if read whole.
- **Bound memory explicitly** where a job's working set is data-dependent, and give the SQL engine a spill directory: a memory limit without one bounds nothing.
