# R50 — Three Columns Are Renamed

| | |
|---|---|
| **Status** | **Proposed** 2026-09-02 |
| **Amends** | R28 §2 (`core.unit_electrodes.channel_ordinal`), R41 §2.2 (`core.processing_runs.supersedes`), R33 §2 (`step_ticks`) |
| **Depends on** | R33 (rational axis steps), R41 (a run may name the run it replaces), R48 (a column declares its role) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Three columns are named against their meaning or against a convention the specification states
elsewhere. None is wrong in behaviour; each costs a reader a moment's doubt, and one of them
misleads about a distinction R48 §3 shows is one letter wide.

They are grouped because they share a deadline rather than a theme. `registry_version` is held at
0.1.0 while the schema is unreleased, so a rename is a rebuild now and an R32 amendment later.

## 2. Decision

### 2.1 `channel_ordinal` becomes `channel_index`

**Rename** `core.unit_electrodes.channel_ordinal` to `channel_index`.

R28 §2 chose *ordinal* to carry a meaning the name had to supply:

> it is **not** an identifier: R5 §5's rule holds, and nothing may join on it.

That was the right call then. **R48 §2.1 makes the name redundant**: `role: structural_index`
says it is a 0-based offset, and says the same thing for every such column rather than once in
prose here.

*Ordinal* is now actively wrong. An ordinal is a position — first, second, third — and this is an
offset, 0-based and contiguous from 0, which the registry's own rule requires because *"a dense
axis indexed by a gapped ordinal addresses rows that are not there"*. Under R48 the six structural
indices become uniformly `*_index`, and `core.array_channels.channel_index` already carries this
name for the same kind of thing: a position on a channel axis. Two tables describing the channel
axes of different arrays should not name it differently.

### 2.2 `supersedes` becomes `supersedes_run_id`

**Rename** `core.processing_runs.supersedes` to `supersedes_run_id`.

It holds a `processing_run_id` and is a declared self-reference. `03`'s convention is `_id` for
stable IDs, and every other reference column in the registry follows it — this is the only one
that does not, and it is a verb where the rest are nouns.

`supersedes_run_id` rather than `superseded_run_id`: the row supersedes the run named, so the
subject is this row. R41 §2.2's *"a run may name the run it replaces"* reads the same way.

### 2.3 `step_ticks` becomes `step_tick_num`

**Rename** `core.array_dimensions.step_ticks` and `analysis.array_dimensions.step_ticks` to
`step_tick_num`.

R33 §2 made an axis step rational — a numerator and `step_tick_den` — so the two halves should
agree in spelling, as `core.clocks.tick_rate_num` and `tick_rate_den` already do two tables over.
Plural against singular for one quantity's two parts is the kind of thing a reader has to stop and
check.

It also removes a genuine trap. `step_ticks` is a **count of ticks**, a duration; `t_tick` is a
**coordinate**. R48 §3 records that one letter of pluralisation is all that separates them, and
that a name-based classification gets it right by luck. `step_tick_num` cannot be read as a
coordinate at all.

### 2.4 `offset` is not renamed

`core.array_assets.offset`, `analysis.array_assets.offset` and `core.array_channels.offset` are
SQL reserved words in DuckDB. They keep their names:

- `offset` is the standard name for the additive term in `value x conversion + offset`, and a
  reader coming from NWB expects it;
- the collision is already handled structurally rather than by avoidance — `nwb_lake_reader.sql`
  quotes every column identifier unconditionally, because *"every engine reserves a different
  set"* and a word list is not portable.

A rename would cost familiarity and buy nothing the quoting does not already provide.

## 3. Cost

| column | rows on disk | non-null |
|---|---:|---:|
| `core.unit_electrodes.channel_ordinal` | 1,541,520 | 1,541,520 |
| `core.array_dimensions.step_ticks` | 171 | 72 |
| `core.processing_runs.supersedes` | 26 | **0** |

One table dominates, and a rename is a column-name change in a rewrite the writer performs
anyway. Nothing else changes: no type, no presence, no key, no rule.

## 4. What this does not do

- **No change to any value or any rule.** `core.unit_electrodes.ordinal_contiguous` and
  `core.processing_runs.supersedes_not_self` are renamed with their columns and otherwise
  unchanged.
- **No renaming for its own sake.** Three columns, each against a stated convention or a
  distinction R48 §3 measures. `offset` is left alone precisely because the case for it is weaker.
- **No claim that the old names caused a defect.** None did. This is a cost paid now to avoid
  paying it later under R32.

## 5. Open

- **Whether `core.unit_electrodes.ordinal_contiguous` should be renamed too.** Its ID contains the
  old column name. Renaming it changes a check ID, which `fixtures/corpus.py` records as data and
  which a downstream consumer may have pinned. Left as an editorial call for whoever applies this.
- **Whether a naming sweep belongs in `registry/check.py`.** These were found by one — reserved
  words, `_id` columns that are not strings, identifier-shaped columns not named `_id`, plural
  integer columns. It would be a report rather than a rule, since every heuristic here has a
  legitimate exception: `offset` is deliberate, and `scope` holds an identifier without being
  named for one.
