# R54 — Intervals Are Declared, Not Assumed

| | |
|---|---|
| **Status** | **Accepted** 2026-09-03 |
| **Amends** | `02` (`core.trials`, `core.trial_tags`), R3 §3.0 (one of its child-table examples), R43 §3 (which sent a task's columns to an extension) |
| **Depends on** | R17 (extension registries), R45 (a tick interval is closed), R49 (a kind names a resource), R53 (an identifier is an integer) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

### 1.1 One table, one task

`core.trials` carries `condition_id`, `stimulus_id`, `choice`, `rewarded` and `metadata`. It is
the only interval table in the format that carries a payload at all:

| table | columns |
|---|---|
| `core.clock_observation_intervals` | `session_id, clock_id, start_tick, stop_tick` |
| `core.event_stream_observation_intervals` | `event_stream_id, start_tick, stop_tick` |
| `core.unit_observation_intervals` | + `unit_id, sorting_run_id, curation_id` |
| **`core.trials`** | + five columns of one paradigm's vocabulary |

R43 §3 already ruled on exactly these when it withdrew `analysis.trials_wide` — *"a task's shape,
not a format's"* — and sent `stimulus_id`, `condition_id` and `block_id` to an R17 extension.
`core.trials` was not touched at the time.

### 1.2 A session has several kinds of interval, and this holds one

The sharper problem is not that the columns are task-shaped. It is that a session routinely
declares **several** unrelated sets of intervals — a task's trials, optotagging pulses,
inactivation windows, drug-condition epochs — and one table with one schema can hold one of them.

NWB has the same shape and the same consequence. `NWBFile` can hold many `TimeIntervals` — through
`epochs`, `invalid_times` and `add_time_intervals` — but `nwbfile.trials` is the one tools read.
So in practice a second interval set is either crammed into `trials` as columns that are null for
every row of the other kind, or added as a `TimeIntervals` nothing knows to look for.

Both outcomes are already named in this specification. The first is R43 §3's table of
*"mostly-null columns whose meaning depends on which pipeline wrote it"*. The second is what R17
§1 measured in NWB and rejected: *most columns in that file conform to nothing*.

### 1.3 Measured on the packets that have them

- **`stimulus_id` is null in all 708 rows** of every packet and no adapter has ever written it.
- **`condition_id` is a concatenation**, composed by the importer from `reward_probabilityL` and
  `reward_probabilityR` — both per-trial values in the same row. R3 §3.0 forbids restating what
  the data declares. It is lossy besides: 18 blocks over 8 probability pairs, so two blocks share
  a value and nothing distinguishes them.
- **Neither references anything.** There is no `core.conditions` and no `core.stimuli`, so both
  are identifiers whose table the packet never names — the unsoundness R49 removed from `scope`.
- **`core.trial_tags` has never been written.** No packet declares the resource.

### 1.4 Two paradigms share the interval and nothing else

`Aind.Behavior.VrForaging.Packaging` writes one NWB trial per **site**. Against the dynamic
foraging session this format was built from:

| | dynamic foraging | VR foraging |
|---|---|---|
| interval | closed | `[start_time, stop_time)`, **half-open** |
| "choice" | `choice` ∈ left/right/none — a **string** | `has_choice` — a **bool** |
| "reward" | `rewarded` — a bool | `has_reward` + `reward_amount` + `reward_probability` |
| condition | a derived label | **none**; R43 §3 records it has no condition and no go cue |
| nesting | blocks | site → patch → block, eleven index columns |

No outcome column agrees even by type. `inventory/vr-foraging-packaging.md:104` reached the same
conclusion independently: *"everything task-shaped ... is an R17 extension, not core."*

## 2. Decision

### 2.1 `core.trials` becomes `core.intervals`, and holds many kinds

```
core.intervals
    session_id     int32     required
    interval_kind  string    required    the resource that specialises this interval
    interval_id    int32     required    carried from that kind's own source
    clock_id       int32     required
    start_tick     int64     required
    stop_tick      int64     required
    primary key (session_id, interval_kind, interval_id)
```

`interval_kind` holds a **dotted resource ID** — `dynamic_foraging.trials`,
`optotagging.pulses` — naming the table that says what this interval was. Open, and resolved the
way R49 §2 already resolves `scope_kind`: read the kind, take that resource's primary key from
the registry, join.

This is the **class-table-inheritance** mapping, which is the standard answer to one base concept
with several specialisations. What it buys over the alternatives is not abstract:

| | |
|---|---|
| every interval in the session | one scan |
| just the task's trials | a key-prefix filter, which prunes |
| a new kind of interval | rows, plus one extension table — **no tool changes** |
| what a kind means | a declared schema: typed columns, closed vocabularies, generated Tier 1 checks |

### 2.2 The kind is part of the key

Each kind numbers its own intervals from its own source, and R53 §2.3 makes `interval_id`
**carried** — so optotagging pulse 5 and task trial 5 are different things wearing the same
number. The discriminator in the key is what lets every kind keep its source's numbering.

It also gives the sort `session_id, interval_kind, interval_id`, so each kind is a contiguous
run and filtering to one prunes row groups — the property `core.spike_events` gets from being
sorted unit-major.

### 2.3 Five columns are struck, and `core.trial_tags` with them

`condition_id`, `stimulus_id`, `choice` and `rewarded` leave core; §1.3 and §1.4 are the case.
`registry/extensions/dynamic_foraging.json` already carries `choice` and `rewarded`, with a
closed vocabulary core cannot declare: `none` is not a choice.

`core.trial_tags` is **withdrawn**. It was the one place this format let meaning accrete without
a schema, which is what R17 §3 exists to refuse — *"nothing constrains the name, type, or meaning
of what accretes, so two files cannot be compared and neither can be checked."* An extension
needing a multi-valued attribute declares its own child table, typed, as R3 §3.0 requires of
everything else. R3 §3.0's remaining examples — `core.array_dimensions`,
`core.session_experimenters` — carry the rule unchanged.

### 2.4 Stimulation parameters are not core

An interval's **stimulation** — an optogenetic wavelength, power and pulse width; a visual
stimulus's contrast and orientation; a drug and its concentration — is declared by an R17
extension and **MUST NOT** be added to `core.intervals`.

This is `09`'s metadata minimalism applied where it is easiest to talk oneself out of it. Opto is
near-universal in this field, and universality is not the test: `09` §8 requires evidence a field
is broadly needed *and* a revision, and no two rigs agree on the columns — ramping, multi-site,
sinusoidal and closed-loop stimulation each want different ones. The same session that motivates
this revision carries `laser_wavelength`, `laser_1_power` and `laser_condition` among the 49 keys
that are **constant across every trial**, because that session varied no opto at all.

What core needs an interval for is to locate it in time. What was done during it is what the kind
names.

### 2.4a A kind must name a resource the packet declares

`interval_kind` naming a resource the packet does not carry is an **error**, not a silence.

This is what keeps the discriminator from decaying into a free-form name, which is the failure
mode §1.2 describes: NWB's mechanism works and goes unused partly because a `TimeIntervals` *is*
its name, so two labs' optotagging tables are named differently and nothing generic finds either.
A kind that resolves to nothing is a name again.

The check is an anti-join against the manifest's declared resources, which the validator already
has for `scope_kind` (R49 §2.2), so it costs one more generated rule and no new machinery.

A packet **MAY** declare an interval whose kind is a resource it does not itself carry only where
that resource is external and declared as such -- the same standing R14 §2.3 gives any external
resource, and reported the same way.

### 2.5 `metadata` stays, and stays empty

`core.intervals.metadata` remains an optional `json_string`, which is what R3 §2.1 confines a JSON
string to — an **optional** column, so a conforming reader satisfies every required column without
a JSON parser.

A writer **SHOULD NOT** fill it routinely. Doing so defeats that ban in practice: all 708 trials
of a real session carried 59 keys, so analysing them required parsing JSON on every row, in the
one table where a task actually lives. Of those, 49 were constant and now sit once on
`core.sessions.metadata`; the 10 that vary are typed columns in the extension.

### 2.6 An importer converts a half-open interval

R45 §2 makes every interval closed: `stop_tick` is the last tick observed, and an interval covers
`stop - start + 1`. A source whose intervals are half-open — VR foraging's `Site` is
`[start_time, stop_time)` — **MUST** be converted, and the conversion is a subtraction nothing
currently states. R45 was written without a half-open source in view.

## 3. What this does not do

- **It does not merge the observation tables.** `core.intervals` holds intervals a *design*
  declares; `core.clock_observation_intervals` and its siblings hold intervals a *measurement*
  found. The latter are keyed by the thing observed rather than by a discriminator, and folding
  them in would reintroduce the polymorphic key R49 removed from `scope`.
- **No nesting in core.** Both paradigms have it and disagree on its levels, so it stays with the
  paradigm: `dynamic_foraging.trials` names a `block_id`, and a VR extension would chain
  site → patch → block the same way. `core.intervals.parent_interval_id` was considered and
  rejected — it makes a block an interval that is not one of these intervals.
- **No change to `core.events`.** R11 §5 struck `core.events.trial_id`, and an event still belongs
  to whatever intervals contain it, which may be none or several.
- **No change to R45.** §2.6 records the obligation R45 leaves an importer; it does not restate
  the closure.

## 4. Precondition

**This revision MUST NOT be accepted before a writer can emit an interval kind.** Today it cannot:
`Recipe.problems` rejects any resource the core registry does not define, and `PacketWriter.add`
raises `KeyError` for one, so declaring a kind is impossible through the recipe while adding a
nullable column to core is a one-line registry edit.

That gradient is steeper than the one §1.2 blames for NWB's unused mechanism, where
`add_trial_column` at least has a competitor. A revision whose correct path is unimplementable
does not merely wait — it teaches the wrong habit while people wait, and §2.4's refusal of
stimulation parameters holds only while declaring an extension is easier than arguing for four
columns in core.

What has to exist first:

1. A recipe may name an extension resource, and `PacketWriter` may write one.
2. `escapewheel init` scaffolds a registry document from a source's columns.
   `inventory/vr-foraging-packaging.md:83` already records that the `Site` model *"converts
   mechanically into an R17 extension registry document"*, which is that scaffolder's
   specification.

## 5. Open

- **Whether `core.intervals` reads as including the observation tables.** §3 says it does not, and
  a name that has to be disambiguated in prose is a name doing less work than it should.
  `core.declared_intervals` is more accurate and worse to type.
- **What an existing packet does.** R53 §5 makes migration regeneration and the same applies: the
  columns are struck rather than renamed, so an old packet is read through its own embedded
  registry or rebuilt.
- **Whether the polymorphic query is wanted.** §2.1's case for a base table rests on it: align to
  every interval in a session without knowing the paradigm. Nothing does that yet, and a
  capability nobody consumes does not create its own demand -- which is why `core.trial_tags` was
  never written. This should be **measured after a second paradigm is imported**, not assumed. If
  nobody wants it, that is evidence for concrete tables per extension and `core.intervals` should
  not exist at all.
