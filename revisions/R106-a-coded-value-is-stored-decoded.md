# R106 — A Coded Value Is Stored Decoded

| | |
|---|---|
| **Status** | **Accepted** 2026-09-09 |
| **Amends** | `dynamic_foraging.trials.animal_response` (int32 becomes a closed string vocabulary); adds a subsection to `02` §8 |
| **Depends on** | R101 §3.1 (every string column declares its vocabulary), R8 §4 (an open vocabulary a validator MUST NOT reject a value from), R8 §2 (a source's own token is a string, never an offset), R66 §1.4 (a value a rule cannot read), R17 §5 (an extension versions independently) |
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

The registry declares 351 core columns and 161 across four extensions, and `animal_response` is
the only one whose values are codes for something the packet does not name. Two columns look like
it and are not: `core.array_dimensions.step_tick_den` is a denominator, and
`aind_unit_qc.synchrony.synchrony_size` is a count of units.

Everything else in `dynamic_foraging.trials` is self-interpreting — `rewarded_history_left` is a
`bool`, `reward_probability_left` a probability, `iti_duration` a duration. The one coded column
is the exception in its own table.

`escapewheel_writer.sources.nwb` records the gap in the shape it left: a `#:` comment reading
"`animal_response` in AIND's dynamic-foraging trials, per the column's own description" sits above
a blank line, attached to nothing. The map it was written for was never added, and could not have
been reached from there — §5 says where the column's rows come from instead.

### 2.2 The licks decide what each code means

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

### 2.3 R101 §3.1 left the column mute

R101 §3.1 requires a vocabulary of every string column and forbids one on a column of any other
type, and this column declared `vocabulary: open` on an `int32` — the one place in the registry
that did, struck at R101's acceptance because an integer's values are not a vocabulary this
format can describe.

Striking it was right and it leaves the column mute. R66 §1.4 refused to let a fact live inside a
JSON string because a rule cannot read one; an integer code is the same defect one level in, the
column being readable where its values are not, and no integer column can declare otherwise.

## 3. Decision

### 3.1 Columns store decoded values

A writer that can decode a source's code **MUST** store the decoded value, and the vocabulary it
decodes onto is declared under R101 §3.1 like any other.

A writer that cannot decode one stores the code itself, verbatim, in a `string` column declaring
`vocabulary: open`, whose description names where the key lives. An undecoded code is a label
carrying no contract, and an open vocabulary is how this format declares one (`01` §3.17). An
integer column declares nothing of the sort: R101 §3.1 permits a vocabulary on no other type, so a
code stored as one sits among the registry's 20 integer `data` columns with nothing separating it
from the counts `core.units.n_spikes` and `aind_unit_qc.synchrony.synchrony_size`.

Recording the token rather than dropping it is R22 §3's rule for a scorer's label and R8 §2's for
`local_unit_label`: a source's own token is a string, kept as the source emitted it, and MUST NOT
be used as an offset.

Nothing structural tells a code from a count, so no rule checks the first clause. It binds the
writer, the only party that knows whether it had a key (R67 §2.4).

### 3.2 `animal_response`

`dynamic_foraging.trials.animal_response` becomes a `string`, staying `nullable` and role `data`,
with `vocabulary: closed` and an `enum` of:

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

The column stays **nullable**, and a null is not a `no_response`. The first says the source stated
nothing about this trial, the second that the task scored the response window empty, and a consumer
**MUST NOT** read either as the other — doing so turns an unrecorded trial into a measurement
nobody made. Both packets fill every trial, 708 and 450 against §1's 1,158, so the distinction
costs nothing today and is what a rebuild from a partial source would need.

## 4. What this does not change

- **The column is replaced, not accompanied.** R59 §2.1 kept `region_id` beside `region_label` and
  R22 §3 keeps a scorer's own label beside a normalized one, so a reader may expect the integer to
  survive next to the string. It does not: the code carries no meaning the decoded value lacks.
- **The lick events stay.** §2.2 reads them to prove the decode; it does not make them the
  storage. A response is one value per trial where `core.events` holds every lick, which is a
  different fact at a different grain.

## 5. Consequence

`dynamic_foraging.trials.animal_response` goes from `int32` to `string`, so a packet embedding
this extension runs **5** closed-vocabulary checks where it ran 4. The generated count stays at 4:
Tier 1 is generated from the merged registry a packet carries, and that block counts core. The extension's `registry_version` bumps, which R17
§5 makes independent of core's. `02` §8 gains a subsection for §3.1's rule.

**The decode lands outside this repository.** No adapter here writes `dynamic_foraging.trials`:
the table reaches a packet through a `TablesSource` reading a Parquet file, which each session's
own `extract.py` produces beside it, and that script is where the source's floats become `0`, `1`
and `2`. Requiring no code of ours is what an extension is offered that route for, so §3.1's
obligation binds those scripts and this part ships no writer change at all.

The closed vocabulary is what makes ignoring it impossible. Each staged file holds `int64` where
the registry now declares a `string` with an `enum`, so the next build of either packet is refused
on the column's type before a rule runs. Both packets are rebuilt — which R87 §2.1, R88 §2, R91
§5, R95, R96, R97, R98, R99, R101, R103 and R105 already require — and this is the first of those
rebuilds gated on a source this repository does not ship. After it, `ecephys_776259` carries 434
`left`, 54 `right` and 220 `no_response`, and `ecephys_786867` 189, 232 and 29.

`fixtures/build.py` writes `left` and `right` where it wrote `0` and `1`.

## 6. Open

- **Whether the response window should be recorded.** §2.2 counts licks between `go_cue_start_tick`
  and `reward_outcome_tick` because those are the columns on hand, and
  `dynamic_foraging.sessions.response_duration` says how long a response was accepted for without
  saying from when. The decode does not need it; a reanalysis checking the task's own scoring
  would.
