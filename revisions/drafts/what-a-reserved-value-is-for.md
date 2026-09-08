# What a Reserved Value Is For

| | |
|---|---|
| **Status** | Draft |
| **Amends** | R11 §4 (strikes `event_type`'s reserved set), R8 §4 (states the test a reservation must pass), the registry declarations of `kind` and `event_type` |
| **Depends on** | R8 (open vocabularies and reserved values), R11 (the reserved event types), R91 §3.1 (which table declares `event_type`), R43 §3 and R54 §2.3 (a task's shape is not the format's) |
| **Profile** | all |

Normative, except §2 and §5, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

R8 §4 declares a vocabulary **open** so a packet may name what the standard has not seen, and
**reserves** some values so two packets cannot spell one thing two ways. Reservation is worth its
cost where a value is read whole across packets, and one of the two sets reserved so far is not.

This part gives reservation a test, strikes the set that fails it, and records in the registry the
set that passes.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25).

## 2. What has been reserved, and what the packets write

Informative.

### 2.1 Two sets, one recorded

R8 §4 reserved four values for `core.array_assets.kind` — `raw`, `ap`, `lfp`, `waveform` — with
declared meanings, and R11 §4 reserved six for `event_type`, which R91 §3.1 has since moved onto
`core.event_streams`. The registry received one of the two sets:
of its **24** open vocabularies, `event_type` is the only column carrying a `reserved_values`
array, and `kind` — the column the mechanism was invented for — carries none.

Nothing reads the field where it is carried. `registry/rules.json` names `reserved_values` **0
times**, and `check.py`'s three matches for "reserved" are about SQL reserved words.

### 2.2 The six are not one kind of thing

R11 §4 took its set from `01`'s examples, which mix two vocabularies:

| reserved value | what it names |
|---|---|
| `sync_pulse`, `ttl_edge` | the instrument: every rig produces them, and they mean one thing |
| `threshold_crossing` | a signal, generic but incomplete — of what, past which threshold |
| `stimulus_onset`, `reward`, `lick` | the experiment |

`raw`, `ap`, `lfp` and `waveform` are all of the first kind. An array's `kind` names what a signal
**is**, which is a property of acquisition and preprocessing, so a consumer asking any packet for
its LFP asks one question and gets a comparable answer.

### 2.3 What the packets write, and why

Both packets declare seven kinds of event: `delay_start`, `go_cue`, `reward_outcome`,
`left_lick`, `right_lick`, `left_reward_delivery`, `right_reward_delivery`. Since R91 §3.1 each is
a stream's `event_type` rather than a column on every event, which changes where the value is
written and nothing about what it says.

Four of them name something the reserved set describes, so R11 §4 read literally forbids them —
and reading it as intended does not help, because the adapter is not inventing a synonym. It is
adding **which spout**, a distinction the reserved vocabulary has no room for. Nor is the side
carried anywhere else: each of the seven streams holds exactly one event type, but what a stream
contributes is `core.event_streams.name` holding `left_lick_time`, the source's own field name,
which this specification constrains no more than a device's (R67 §2.4, R85 §2.2). Reading a side
out of it means parsing a name.

The refinement is not an accident of this adapter. An event is named for what happened in an
experiment, and an experiment refines: a lick has a spout, a reward has a size, a TTL edge has a
line and a direction — both packets already declare `FIP_rising_time` and `FIP_falling_time`
streams, so even the instrument-side values would want refining once those carried events.

## 3. Decision

### 3.1 The test a reservation must pass

A value **MAY** be reserved only where it is read **whole**: where a consumer comparing two packets
learns something from the value alone, without knowing what either packet was doing.

`lfp` passes. It names what a signal is, which acquisition determines, so `kind = 'lfp'` selects
comparable arrays from packets built by different labs.

`reward` does not. Two experiments' rewards are not comparable without knowing each paradigm, so
matching the string returns rows a consumer cannot use and suggests an alignment that is not there.
A task's shape is not the format's (R43 §3, R54 §2.3), and its vocabulary is not either.

### 3.2 `event_type` reserves nothing

R11 §4's reserved set is **struck**, and `core.event_streams.event_type` declares no
`reserved_values`.
The column stays required and its vocabulary stays open, so a validator still **MUST NOT** reject
any value.

R11 §4's six stay in that revision as **examples**, which is what `01` offered them as, and what
`02` should have said instead of "etc." A writer naming an event may use them and is not obliged
to, and `left_lick` becomes conforming rather than a breach nothing could see.

### 3.3 `core.array_assets.kind` records its four

`core.array_assets.kind` **MUST** declare `reserved_values` of `raw`, `ap`, `lfp` and `waveform`,
which R8 §4 reserved and the registry never received. Each **MUST** carry the meaning R8 §4
declares for it. `analysis.array_assets.kind` declares the same set, being the same vocabulary one
layer down.

`semantic_type`, `activity_type` and `core.unit_quality_labels.label` declare none: R8 §4 opens
`semantic_type` "on the same terms, for the same reason" and reserves nothing for it, and no
revision has reserved a value for the other two. Declaring an empty set and declaring nothing are
the same claim, so the field stays absent.

### 3.4 What a validator does

A validator **SHOULD** report, at `info`, a value outside the reserved set for any column declaring
one. It **MUST NOT** report a failure: the vocabulary is open, and an unrecognized value is exactly
what openness admits.

Whether a value is a *synonym* for a reserved one stays uncheckable — `local_field_potential`
describes what `lfp` describes and no query can see it — so R8 §4's prohibition binds a writer and
no rule. That is the shape R67 §2.4 has: a named actor bound to a determinable behaviour, with
nothing able to observe a breach, which is a requirement rather than a wish because the actor can
comply.

## 4. What this does not change

- **No vocabulary closes, and none opens.** All 24 open vocabularies stay open, `event_type`
  included; what changes is which of them makes a claim about particular values.
- **No column, table, reference or Tier 2 rule is added or removed.** `reserved_values` is an
  existing registry field, filled on two more columns and emptied on one.
- **No packet changes and nothing is rebuilt.** `left_lick` and its three companions are conforming
  after §3.2 where they were arguably a breach before, so the writer emits what it emits today.
- **`core.units.quality_label` is untouched.** It is `enum`, a closed vocabulary (R11 §3, R22 §3),
  and reservation is a mechanism for open ones.
- **R11 §4's meanings are not restated.** They stay in R11 as examples with the definitions it gave
  them.

## 5. Consequence

`core.array_assets.kind` and `analysis.array_assets.kind` gain a `reserved_values` array,
`core.event_streams.event_type` loses one, and a validator gains §3.4's report. `registry/check.py` gains
a check that a declared set is snake_case and free of duplicates.

Nothing else. No table, column, reference or rule changes, no packet is invalidated, and no rebuild
is owed — which is the point: the alternative considered was a `<reserved>_<qualifier>` convention
that would have renamed four event types, required the NWB adapter to hold a table mapping each
source field to the reserved value it describes, and rebuilt both packets, all to keep a set that
§3.1 says should not cover those values.

## 6. Open

- **Whether `sync_pulse` and `ttl_edge` should be reserved somewhere.** They pass §3.1's test — a
  sync pulse means one thing in every rig — and this part strikes them with the rest because they
  are reserved on `event_type`, where the surrounding values do not. A vocabulary naming what a
  **stream** carries, rather than what an event is, would be the place, and `core.event_streams`
  has no such column.
- **Whether an extension should make a refinement structural.** §3.2 leaves `lick_left` or
  `left_lick` a string a consumer filters on and cannot join. Making the spout structural is an
  extension's work, keyed through `event_type` in R90 §3.5's shared-key shape; nothing has asked
  for it, and `dynamic_foraging.trials` already carries the seven `_left`/`_right` pairs this task
  needs.
- **Whether the four array kinds are the right four.** R8 §4 took them from `02`'s examples rather
  than from what sources emit. This part records them and does not revisit them.
