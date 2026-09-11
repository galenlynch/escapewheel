# Registry codegen prototype

Demonstrates the chain [R2](../../revisions/R2-schema-registry-format.md) specifies:
a registry document is data, a generator turns it into SQL, and that SQL is the validator.

```
registry.json ──generate.py──> 22 SQL checks ──DuckDB──> findings
   (data)          (~40 lines)                              (offending rows)
```

## Running it

```bash
uv run --with pyarrow --with duckdb python fixture.py           # writes packets/
uv run --with pyarrow --with duckdb python validate.py packets/valid    # exit 0
uv run --with pyarrow --with duckdb python validate.py packets/broken   # exit 1
python3 generate.py                                            # print the emitted SQL
```

## What each file is

| File | Role |
|---|---|
| `registry.json` | Registry content in R2 §3 format. Three tables, transcribed from Part 02 once. |
| `generate.py` | Registry → checks. Four cases, no per-table code. |
| `validate.py` | Schema layer (R2 §7.4 shim) plus the generated SQL, executed by DuckDB. |
| `fixture.py` | A conforming packet and one with three deliberate defects. |

## Where the checks come from

Three tables produce 22 checks. Twenty-one are generated from structure; one is hand-written.

| Registry element | Emitted check |
|---|---|
| column with `presence: required` | `WHERE col IS NULL` |
| `primary_key` | `GROUP BY key HAVING COUNT(*) > 1` |
| each `references` entry | `LEFT JOIN parent ... WHERE parent.key IS NULL` |
| each `rules` entry | passed through unchanged (Tier 2) |

At full scale this is 236 generated against 64 hand-written.

Two details are load-bearing rather than incidental:

**Nullable foreign keys are guarded.** `generate.py` reads `presence` when building a
reference check, so a `nullable` foreign key constrains only its non-null values. Without
the guard `core.clocks.parent_clock_id` reports every root clock as a violation — a clock
with no parent is the ordinary case, not a defect. 24 of core's 68 references are
conditional this way.

**The result contract is the whole protocol.** A check's query returns offending rows;
empty is a pass, non-empty is a failure and the rows are the finding (R2 §7.3). Nothing
else has to be defined, which is why failures print the actual duplicate key and the
actual inverted interval.

## Why the registry is not Avro or JSON Schema

Both have better codegen ecosystems, and both would carry `columns`. Neither has a
representation for `primary_key` or `references` — so a generator reading them could emit
row types but not a single uniqueness or referential check, which is what most of the
validation surface consists of.

## Prototype limits

`registry.json` is its own document rather than a slice of `registry/logical_schemas.json`,
and it is kept conforming: `registry/check.py` validates it against the meta-schema, because a
demonstration that the format drives the tooling is worth nothing on input the format rejects.
It went 16 errors out of conformance once, unnoticed, which is why the check exists.

- Three of the registry's tables; no `rules` beyond one example.
- **No discriminator checks.** `core.intervals.interval_kind` names an extension table (R54 §2.1)
  that this packet does not carry, which R54 §2.4a makes an error and R55 §2.4's generated checks
  would catch. `generate.py` implements not-null, uniqueness, references and Tier 2 pass-through;
  the two discriminator checks are the clearest thing to add next.
- No manifest handling, no JSON Schema, no Zarr array checks, no checksums.
- Type checking compares against pyarrow type strings, which is a stand-in for a
  language-neutral comparison.
- Python only. The Julia equivalent rewrites `generate.py` and reuses everything else;
  a shared conformance corpus is what would keep the two honest.
- `registry.json` is hand-written here. The real content artifact is generated against
  R2's format and covers every table.
