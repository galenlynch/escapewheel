# R53 — An Identifier Is an Integer

| | |
|---|---|
| **Status** | **Accepted** 2026-09-02 |
| **Amends** | R2 §4 (the Arrow type vocabulary's use), R5 §5 and R8 §2 (what a label is, restated), R48 §2.1 (what `identifier` implies), `02` (every identifier column) |
| **Depends on** | R2 (registry format), R32 (a committed packet is immutable), R46 (declared references), R48 (column roles) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

All 110 identifier columns are strings, and 70 references join on them. The choice was never
argued; it followed from the first fixture and nothing revisited it.

**Storage was measured and used to settle a question it does not answer.** Five identity columns
over 287,896,563 spikes are 8.1 MB, 1% of the table, because a sorted column run-length encodes
to 0.06 bit/row. That is true, and it says nothing about what anyone does with the column.

Measured on 20 M rows and 800 units, in DuckDB:

| | string | int32 | |
|---|---:|---:|---:|
| join to `core.units` | 55 ms | 5 ms | **10.2x** |
| filter 24 units | 33 ms | 2 ms | **13.8x** |
| `GROUP BY` unit | 58 ms | 9 ms | **6.5x** |
| `ORDER BY` unit, tick | 380 ms | 71 ms | **5.3x** |
| parquet | 23.5 MB | 23.2 MB | −1.1% |

Storage is a wash. Everything a reader does is five to fourteen times faster.

### 1.1 The dictionary is the identifier, badly

A string identity column is stored as integer codes plus a lookup — a dictionary. So the format
already keys on integers; it just refuses to say so, and pays for the refusal at every boundary.

Measured over 20 M rows and four identity columns, keeping the dictionary rather than decoding it
is 0.32 GB against 3.42 GB and 0.08 s against 0.52 s — and then:

| operation | decoded | dictionary |
|---|---:|---:|
| `is_in`, 24 units | 1.19 s | **16.81 s** |
| `group_by` | 0.03 s | `ArrowNotImplementedError: Unifying differing dictionaries` |
| `sort_indices` | 1.03 s | **unimplemented, unified or not** |

`Table.unify_dictionaries` costs 0.01 s and fixes the first failure. Nothing fixes the second:
Arrow cannot sort a dictionary column. So a reader either materialises ten times the memory or
loses sorting — and the whole dilemma is an artifact of storing an integer under a string's type.

An `int32` column has no dictionary to keep, decode, unify, or fail to sort.

## 2. Decision

### 2.1 An identifier column is `int32`

Every column whose R48 role is `identifier` **MUST** be `int32`, except where §2.4 requires
`int64`. This covers all 110 and the 70 references that join on them.

`int32` gives 2,147,483,647 values against a real session's 6,781 units, 708 trials and 12
sorting runs.

### 2.2 Signed, not unsigned

Deliberately, and not for range. Neither PostgreSQL nor Apache Iceberg nor the JVM has an
unsigned integer type, and R2 §4's vocabulary has none either. Adding two types that three of the
four systems this format expects to reach cannot express would buy one bit nothing needs.

Tick columns stay signed `int64` and are unaffected: a tick is a **coordinate**, not an
identifier (R45 §5).

### 2.3 An identifier declares whether it was carried or assigned

Every column with `role: identifier` also declares `identity`, closed to two values and with no
default, for R48 §2.2's reason: a default makes a forgotten classification look deliberate.

- **`carried`** -- the value is the source's own, copied unchanged. Two packets built
  independently from one source agree on it, because neither invented it.
- **`assigned`** -- the writer chose the number. Two independent builds need not agree.

The distinction is not derivable, which is why it is declared. `core.trials.trial_id` comes from
the NWB's `intervals/trials/id`, already `int64` and already `[0, 1, 2, ...]`; `core.units.unit_id`
comes from the sorter's `unit_ids`, `int64` and strictly increasing. Both are **carried**, and
this revision stops the writer converting them to strings and back. `core.sessions.session_id`
names an asset called `ecephys_776259_2025-04-09_17-25-12` and `core.probes.probe_id` a device
called `Neuropix-PXI-100.46110`; a number standing for either is **assigned**.

Note what `unit_id` shows: the source supplies an integer *and* the writer replaces it, so
"the source is an integer" is not the test. What matters is whether the value survives the write.

### 2.3.1 An assigned identifier carries its name

A table whose primary key includes an **assigned** identifier **MUST** carry a `*_name` string
holding what that number stands for -- the identifier its source used, or an earlier packet did.
It lives in the **dimension** table, one row per thing rather than one per spike, so a session's
name costs one string and never 287 million.

A **carried** identifier gets no name, and MUST NOT be given one. The value is already the
source's, so a name beside it would restate the column next to it -- which R3 §3.0 forbids for
the same reason it sends a repeated value to a child table. `trial_name` holding `"trial_0000"`
beside `trial_id` holding `0` is exactly the duplication this format refuses everywhere else.

That is what makes this checkable rather than conventional: `registry/check.py` reads the
declaration and requires the name where it is owed, which a list of exceptions in prose could
never do.

### 2.4 Where `int64` is required

An identifier **MUST** be `int64` where the number of distinct values may exceed `int32`. No core
table is near it, and none is expected to be: `core.spike_events` has 287 M rows and no identifier
of its own, because a spike is identified by the unit and tick it carries.

An R17 extension declaring an identifier over more than 2^31 rows declares `int64` for it.

### 2.5 Keys are assigned at commit and never move

A writer assigns identifiers when it commits (`05`). R32 §3 forbids an amendment modifying
anything it did not write, so an identifier is stable for the life of the packet: an amendment
adding a sorting run assigns new numbers to its new units and leaves every existing one alone.

An **assigned** identifier is not stable across packets, and this is the cost. Two packets built
independently from one session may number the same probe differently; §2.3.1's `*_name` is what
recovers the correspondence, through a join on the dimension table rather than on the fact table.
A **carried** identifier has no such problem, because neither build invented it.

### 2.6 The analysis layer moves with core

`analysis.*` identifier columns change on the same schedule, not a later one. `06` makes an
analysis resource disposable, which is an argument for rebuilding it cheaply rather than for
letting it key differently: a packet whose `analysis.spike_events` joins on strings and whose
`core.spike_events` joins on integers cannot be joined to itself.

## 3. What this does not do

- **No change to `local_*_label`.** R5 §5 and R8 §2 stand: a source-provenance label is a string
  and MUST NOT be used as an offset. This revision is about the packet's own identifiers, which
  those sections never governed — a distinction the argument for strings had been eliding.
- **No change to R48's roles.** An integer identifier is still `identifier`, not
  `structural_index`. R48 §3 already established that the distinction is not derivable from type;
  this makes that the only way to tell, which is what the role is for.
- **No new types.** §2.2 declines unsigned; the vocabulary is unchanged.
- **No UUIDs.** Parquet has a UUID logical type and pyarrow round-trips it, but a per-row UUID is
  129 bit/row against a sorted identifier's 0.05 — 2,500x — because sixteen random bytes neither
  dictionary-encode nor compress. UUIDs answer a coordination problem this format does not have:
  a packet is written by one writer at one time.
- **No change to the manifest.** Resource IDs stay dotted strings; they name schemas, not rows.

## 4. Open

- **Whether `identity` belongs on the column or on the table.** It is declared per column here,
  matching `role`, but a table's key is what actually decides whether it owes a name.
- **What `registry/check.py`'s naming report should now say.** One of its nine conventions is
  "an `_id` column is a string", which this inverts. It is the check that would have caught a
  half-finished migration, so it has to move with the rest rather than after it.
- **Whether a reader should refuse a string-keyed packet or read it.** §5 makes regeneration the
  migration, so nothing needs to read both -- but a reader meeting an old packet should say which
  shape it found rather than fail on a type it did not expect.

## 5. Migration is regeneration

A packet is **rebuilt**, not converted. Every packet in existence is reproducible from its
sources through its recipe, which is recorded in `core.processing_runs.parameters` for exactly
this kind of reason, so a conversion tool would be a second implementation of the writer that
only ever runs once.

A rebuilt packet is a **new packet**, not a new version of the old one. R32 versions a packet
whose bytes are immutable and whose manifests are retained; changing the type of every identifier
is not an amendment to that packet, it is a different packet built from the same sources.

A reader tells the two apart by `registry_version`. Nothing is required to read both.
