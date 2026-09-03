# R54 — A Trial Is an Interval

| | |
|---|---|
| **Status** | **Proposed** 2026-09-02 |
| **Amends** | `02` (`core.trials`), R11 §5 (which struck `core.events.trial_id`), R43 §3 (which sent a task's columns to an extension) |
| **Depends on** | R17 (extension registries), R43 (an alignment is a query), R45 (a tick interval is closed), R53 (an identifier is an integer) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`core.trials` is the only interval table in the format that carries a payload:

| table | columns |
|---|---|
| `core.clock_observation_intervals` | `session_id, clock_id, start_tick, stop_tick` |
| `core.event_stream_observation_intervals` | `event_stream_id, start_tick, stop_tick` |
| `core.unit_observation_intervals` | + `unit_id, sorting_run_id, curation_id` |
| **`core.trials`** | + `condition_id, stimulus_id, choice, rewarded, metadata` |

The five extra columns are one paradigm's vocabulary. R43 §3 already ruled on exactly these when
it withdrew `analysis.trials_wide` — *"a task's shape, not a format's"* — and sent `stimulus_id`,
`condition_id` and `block_id` to an R17 extension. `core.trials` was not touched at the time.

### 1.1 Two paradigms share the interval and nothing else

`Aind.Behavior.VrForaging.Packaging` is the pipeline most AIND behaviour data will pass through,
and `SiteTableProcessor.nwbize` writes **one NWB trial per site**. Against the dynamic foraging
session this format was built from:

| | dynamic foraging | VR foraging |
|---|---|---|
| interval | `start_tick`/`stop_tick`, **closed** | `[start_time, stop_time)`, **half-open** |
| "choice" | `choice` ∈ left/right/none — a **string** | `has_choice` — a **bool** |
| "reward" | `rewarded` — a bool | `has_reward` + `reward_amount` + `reward_probability` |
| condition | a derived label | **none**; R43 §136 records it has no condition and no go cue |
| stimulus | `stimulus_id` | none; odour identity instead |
| nesting | blocks | site → patch → block, eleven index columns |

They share no outcome column **even by type**. A union of both is a table of mostly-null columns
whose meaning depends on which pipeline wrote it, which is the shape `09`'s metadata minimalism
exists to prevent. `inventory/vr-foraging-packaging.md:104` reached the same conclusion
independently: *"everything task-shaped ... is an R17 extension, not core."*

### 1.2 Measured on the packet that has them

- **`stimulus_id` is null in all 708 rows** of every packet and no adapter has ever written it.
- **`condition_id` is a concatenation.** Its eight values are `p0.7_0.1` and the like, composed by
  the importer from `reward_probabilityL` and `reward_probabilityR` — both per-trial values in the
  same row's metadata. R3 §3.0 forbids restating what the data already declares.
- It also **loses information it appears to carry**: the session has 18 blocks over 8 probability
  pairs, so two different blocks share a `condition_id` and nothing distinguishes them.
- Neither references anything. There is no `core.conditions` and no `core.stimuli`, so both are
  identifiers whose table the packet never names — the unsoundness R49 removed from `scope`.

## 2. Decision

### 2.1 `core.trials` is an interval and an identity

The table is `session_id`, `trial_id`, `clock_id`, `start_tick`, `stop_tick`. Nothing else.

That is what the *format* knows about a trial, and it is what every other interval table already
is. It is also exactly what core needs a trial **for**: to locate it in time, so that spikes,
events and an array's time axis can be aligned to it. None of that needs to know what the trial
was.

### 2.2 `stimulus_id` and `condition_id` are struck

Both are removed from `core.trials`. §1.2 is the case: never written, or derived and lossy;
neither references anything; neither exists in the second paradigm.

A packet that wants either declares it in an R17 extension, where the extension can also declare
the table it references — which is what makes it an identifier rather than a string that looks
like one.

### 2.3 `choice` and `rewarded` move to an extension

Both leave `core.trials`. `registry/extensions/dynamic_foraging.json` already carries them, with
a closed vocabulary for `choice` that core cannot declare: `none` is not a choice, and a foraging
task's outcomes are not a two-alternative task's.

### 2.4 `metadata` stays, and stays empty

`core.trials.metadata` remains an optional `json_string`, which is what R3 §2.1 confines a JSON
string to — an **optional** column, so that a conforming reader satisfies every required column
without a JSON parser.

A writer **SHOULD NOT** fill it routinely. Doing so defeats that ban in practice: all 708 trials
of a real session carried 59 keys, so analysing them required parsing JSON on every row, in the
one table where a task actually lives. Of those, 49 were constant across the session and are now
recorded once on `core.sessions.metadata`; the 10 that vary are typed columns in the extension.

### 2.5 An importer converts a half-open interval, and says so

R45 §2 makes every interval in this format **closed**: `stop_tick` is the last tick observed and
an interval covers `stop - start + 1`. A source whose intervals are half-open — VR foraging's
`Site` is `[start_time, stop_time)` — **MUST** be converted, and the conversion is a subtraction
that nothing currently states.

R45 was written without a half-open source in view. This does not change R45; it records the
obligation R45 leaves an importer, which is exactly the off-by-one that R3 §6's counts, positions
and indices exist to keep apart.

## 3. What this does not do

- **No new core table.** Nesting is not added to core. Both paradigms have it and they do not
  agree on its levels, so it stays with the paradigm: `dynamic_foraging.trials` names a
  `block_id`, and a VR extension would chain site → patch → block the same way.
- **No self-reference.** `core.trials.parent_trial_id` was considered and rejected: it makes a
  block a trial that is not a trial, and pushes a paradigm's structure into core.
- **No change to R45.** §2.5 records an obligation, it does not restate the closure.
- **No change to `core.events`.** R11 §5 struck `core.events.trial_id`, and a trial's events are
  still found by the interval rather than by a column. That is unaffected and remains right: an
  event belongs to whatever intervals contain it, which may be none or several.

## 4. Open

- **Whether `core.trials` still earns its own table.** Reduced to §2.1 it is
  `core.<something>_observation_intervals` with a different name, and a fourth interval table
  whose only distinction is that a human chose its boundaries. Keeping it is the conservative
  answer and this revision takes it; merging the four is a larger question about whether the
  format wants one interval table with a discriminator, which R49's experience with `scope`
  argues against.
- **What a packet does with a trials table it has already written.** R53 §5 makes migration
  regeneration, and the same applies here: the columns are struck, not renamed, so an old packet
  is read by its own embedded registry or rebuilt.
