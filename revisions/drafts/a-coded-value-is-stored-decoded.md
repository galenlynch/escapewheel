# A Coded Value Is Stored Decoded

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `dynamic_foraging.trials.animal_response` (int32 becomes a closed string vocabulary); adds a subsection to `02` §8 |
| **Depends on** | R101 §3.1 (every string column declares its vocabulary), R97 §3.3 (what `metadata` carries), R66 §1.4 (a value a rule cannot read), R17 §5 (an extension versions independently) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`dynamic_foraging.trials.animal_response` is an `int32` holding `0`, `1` and `2`, and its
description says what the packet does about that: *"what each means is the task's and is not
restated here."* A consumer therefore needs a document the packet does not contain, and no rule,
no query and no reader can tell one response from another.

This part stores the decoded value instead, and states the rule that only this column breaks.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25),
which hold **1,158 trials** between them.

## 2. Background

Informative.

### 2.1 The coded columns in the registry

The registry declares 330 core columns and 161 across four extensions, and `animal_response` is
the only one whose values are codes for something the packet does not name. Two columns look like
it and are not: `core.array_dimensions.step_tick_den` is a denominator, and
`aind_unit_qc.synchrony.synchrony_size` is a count of units.

Everything else in `dynamic_foraging.trials` is self-interpreting — `rewarded_history_left` is a
`bool`, `reward_probability_left` a probability, `iti_duration` a duration. The one coded column
is the exception in its own table.

`escapewheel_writer.sources.nwb` records the gap in the shape it left: a `#:` comment reading
"`animal_response` in AIND's dynamic-foraging trials, per the column's own description" sits above
a blank line, attached to nothing. What it was going to annotate is the map this part adds.

### 2.2 What the licks say the codes mean

A code whose key is elsewhere is worth writing down only if the key is right, and here the packet
settles it without consulting anything. `core.events` holds each session's licks on
`left_lick_time` and `right_lick_time` streams, and `dynamic_foraging.trials` gives each trial a
`go_cue_start_tick` and a `reward_outcome_tick`. Counting licks in that window, by response code:

| `animal_response` | `ecephys_776259` | `ecephys_786867` |
|---|---|---|
| `0` | left only 356 of 434 (82%), no lick 78 | left only 183 of 189 (97%), no lick 6 |
| `1` | right only 49 of 54 (91%), no lick 5 | right only 215 of 232 (93%), no lick 17 |
| `2` | no lick 220 of 220 | no lick 29 of 29 |

**No trial contradicts the reading**: not one `0` trial has a right lick and no left one, not one
`1` trial the reverse, and every one of the 249 `2` trials is silent. The residue on `0` and `1`
is the window, which ends at the outcome rather than at the trial, and not a disagreement.

So `0` is a left response, `1` a right response and `2` no response — recoverable today from
1,158 trials, and recoverable only because both packets happen to carry the lick streams. A packet
carrying the trials and not the licks would hold the code and no way to read it.

### 2.3 What R101 §3.1 left the column

R101 §3.1 requires a vocabulary of every string column and forbids one on a column of any other
type, and this column declared `vocabulary: open` on an `int32` — the one place in the registry
that did, struck at R101's acceptance because an integer's values are not a vocabulary this
format can describe.

Striking it was right and it leaves the column mute. R66 §1.4 refused to let a fact live inside a
JSON string because a rule cannot read one; a code whose key is in another repository is further
out still, since no amount of reading the packet recovers it.

## 3. Decision

### 3.1 Columns store decoded values

A column **MUST NOT** hold a code whose key is not in the packet. Where a source emits one, a
writer **MUST** store the decoded value, and the vocabulary it decodes onto is declared under
R101 §3.1 like any other.

A writer that cannot decode a source's code **MUST NOT** give it a typed column. The raw value
goes to the table's `metadata`, which R97 §3.3 reserves for what a source stated and the standard
does not model, so the value stays visible without being mistaken for a fact the format defines.

R66 §1.4 refused to let a fact live inside a JSON string because no rule can read one. A code
whose key is in another repository is further out still: no amount of reading the packet recovers
what it means.

### 3.2 `animal_response`

`dynamic_foraging.trials.animal_response` becomes a `string` with `vocabulary: closed` and an
`enum` of:

```text
left           the animal licked the left spout
right          the animal licked the right spout
no_response    the animal did not respond within the response window
```

Closed rather than open, on R8 §3's test: the set is complete, because a two-spout task admits a
left response, a right response and neither. Closing it is also what makes Tier 1 generate the
membership check, which is what would catch an adapter decoding wrongly. A task variant with a
third spout is a different extension version, which R17 §5 already provides for.

`no_response` rather than `ignored`: the packet records that no response arrived inside the
window, where "ignored" asserts something about the animal the trial does not measure.

## 4. What this does not change

- **The column is replaced, not accompanied.** R59 §2.1 kept `region_id` beside `region_label` and
  R22 §3 keeps a scorer's own label beside a normalized one, so a reader may expect the integer to
  survive next to the string. It does not: the code carries no meaning the decoded value lacks.
- **No core column changes.** §2.1 measures that none holds a code, though §3.1's rule binds them
  the same; `animal_response` is a task's fact in a task's extension, which is where R43 §3 sent
  it.
- **The lick events stay.** §2.2 reads them to prove the decode; it does not make them the
  storage. A response is one value per trial where `core.events` holds every lick, which is a
  different fact at a different grain.

## 5. Consequence

`dynamic_foraging.trials.animal_response` goes from `int32` to `string`, so Tier 1's
closed-vocabulary checks go from 4 to **5**. The extension's `registry_version` bumps, which R17
§5 makes independent of core's. `02` §8 gains a subsection for §3.1's rule, beside `02` §8.6's free-form metadata, which is
where the rule sends a code it cannot decode.

The NWB adapter gains the map its dangling comment was written for, and both packets are rebuilt —
which R87 §2.1, R88 §2, R91 §5, R95, R96, R97, R98, R99 and R101 already require. After the
rebuild `ecephys_776259` carries 434 `left`, 54 `right` and 220 `no_response`, and
`ecephys_786867` 189, 232 and 29. `fixtures/build.py` writes `left` and `right` where it wrote
`0` and `1`.

## 6. Open

- **Whether the response window should be recorded.** §2.2 counts licks between `go_cue_start_tick`
  and `reward_outcome_tick` because those are the columns on hand, and
  `dynamic_foraging.sessions.response_duration` says how long a response was accepted for without
  saying from when. The decode does not need it; a reanalysis checking the task's own scoring
  would.
