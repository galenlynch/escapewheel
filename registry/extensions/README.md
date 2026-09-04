# Extensions

An extension is a **registry document in R2's format** (R17 §2), namespaced by its `extension_id`.
Nothing here is a second format, and nothing here ships code: a packet embeds these documents, so
reading one of their tables needs nothing installed.

| | tables | columns | drawn from |
|---|---|---|---|
| `dynamic_foraging` | `trials`, `blocks`, `sessions` | 60 | the 67 trial columns of two real sessions, split by which of them vary |
| `aind_unit_qc` | `metrics`, `waveform_metrics`, `synchrony` | 47 | the 32 quality columns of a real NWB's 55, measured |
| `aind_opto` | `stimulations`, `emissions` | 18 | the 17 `laser_*` columns the real NWB's `trials` table carries |
| `vr_foraging` | `sites`, `site_odors`, `sessions` | 38 | the `Site` and `SessionMetadata` pydantic models the packaging library writes its parquet from |

## Why these, and why they are not core

Measured on `ecephys_776259_2025-04-09`, comparing what each NWB `DynamicTable` carries against
what `02` models by name:

```
NWB DynamicTable  columns  unmodelled
units                  74          73
electrodes             21          19
trials                 68          67
```

The comparison is naive — it matches on name, so a renamed equivalent (`num_spikes` against
`n_spikes`, `unit_name` against `local_unit_label`) counts as unmodelled, and R28's
`core.unit_coordinates` covers the CCF columns under different names. It is still the shape of
the thing: **a `DynamicTable` accretes, and what accretes is a task's or a pipeline's vocabulary,
not a format's.** R17 §1 measured the same file and put it plainly — most columns in it conform to
nothing.

That is exactly what an extension is for, and it is why R43 §3, R16 §5, R9 §2 and `09` §2.3 all
send their columns here.

## What varies is what belongs on the row

`dynamic_foraging`'s three tables come from one measurement. Its NWB `trials` table has 67
columns, and `ecephys_776259_2025-04-04` and `ecephys_786867_2025-09-25` carry the same 67 names
exactly — so the shape is the task's rather than one session's. Over 786867's 450 trials:

```
18 vary      49 are constant on every trial
```

The 18 are the trial's own facts and stay on `dynamic_foraging.trials`, joined by the few that
vary by nature and happened not to here — `delay_duration` is fixed only because that session's
`delay_beta` is zero. The 49 are the task's configuration repeated 450 times, and become
`dynamic_foraging.sessions`: the beta/min/max families the delays and blocks are drawn from, the
valve calibrations, the reward sizes, and the six `auto_train_*` columns recording what the
trainer was doing.

The 17 `laser_*` columns are in that constant set too, at `None` and NaN throughout, because
neither session ran opto. They belong to `aind_opto` either way.

`aind_unit_qc` was drafted the same way, from `ecephys_786867_2025-09-25`'s 4,559 units and 55
columns. Twenty-three of the 55 are core's under other names — `spike_times`, `waveform_mean`,
`estimated_x/y/z` (R28's `core.unit_coordinates`), `decoder_label` (R16's quality labels),
`extremum_channel_index` (R28's `default_electrode_id`) — and what remains is the quality
pipeline's own vocabulary.

Measuring rather than reading names also says how sparse a column is, which a schema drafted from
a column list cannot: `velocity_above` is finite for **807 of 4,559** units and `velocity_below`
for 757, because the fit needs channels on that side of the peak; the three `drift_*` metrics for
2,531. Every one is nullable, and the descriptions say so.

A rule invented from the column names did not survive the data. `a_peak_is_counted` asserted that
a waveform with a measured `peak_to_valley` has a peak of one sign or the other. **61 of 4,322
units** contradict it, all with a `peak_to_valley` in the ordinary range: the span is measured
extremum to extremum, and the peak *counters* apply a prominence threshold, so a low-prominence
waveform has a width and no detected peak. The rule is struck. `snr` already says what it was
reaching for, and better.

## The source's columns are evidence, not a schema

Taking a `DynamicTable`'s columns verbatim reproduces its shape, and some of that shape is the
thing an extension exists to fix. Two instances here, both the same:

- **`laser_1_power`, `laser_2_power`** — a list smeared across columns, so a third laser needs a
  schema change. R3 §3.0 refuses that for exactly this reason. A laser is a **device**, which core
  already models, so `aind_opto.emissions` is a child table keyed by `device_id`. `wavelength_nm`
  and `location` move there too: they are properties of the emitter, not of the epoch, and two
  lasers may differ in both.
- **`sync_spike_2`, `sync_spike_4`, `sync_spike_8`** — a metric parameterised by a number, with
  the number in the name. The sorter computes it over a list of synchrony sizes, so a fourth size
  needs a schema change. `aind_unit_qc.synchrony` is one row per size.

The other metrics stay verbatim, and the difference is not squeamishness: `snr` and
`presence_ratio` are the **vocabulary** people search by, and renaming them would make the table
match nothing anyone's code expects. `sync_spike_8` is not a name — it is a name with a parameter
glued on.

## Tagging and inactivation are one extension

They differ in the **values**, not the columns: a short pulse train against sustained
illumination, on the same `wavelength_nm`, `power_mw`, `duration_s`, `frequency_hz`,
`ramping_down_s`. So `aind_opto.stimulations` is one table with an open `protocol` saying which,
rather than two schemas of the same shape. Splitting them would be R3 §3.0's duplication with the
intent encoded in a table name.

## Deriving one from a pydantic model

`vr_foraging` was drafted from `aind_behavior_vr_foraging_packaging.models`, where `Site` and
`SessionMetadata` are ordinary `BaseModel`s and the table is literally
`pd.DataFrame([s.model_dump() for s in sites])`. A model like that is a better draft source than a
`DynamicTable`, because it carries three of the four things a registry column needs — type,
optionality, and a description — and in this pipeline it carries the fourth as prose: **every unit
in it lives in a description string**, `centimeter`, `second`, `percentage`, `milliliter`, `cm/s`.
R56 is what gives them somewhere to go.

What it does not carry is `role`. That is R48 §2.2's point and it is not a gap to be closed: a role
is a decision, and one guessed from a name would look deliberate. So the derivation is a scaffold,
not a compiler.

Neither is it a licence to take the columns verbatim. The same test as above — R3 §3.0, does the
duplication buy otherwise-unavailable access — removes seven of `Site`'s fields:

| dropped | because |
|---|---|
| `start_time`, `stop_time` | the interval itself, which lives in core as ticks on a declared clock |
| `site_index` | equals the site's identity; carried once, as `site_id` |
| `has_reward` | `reward_onset_tick IS NOT NULL` |
| `has_choice` | `choice_cue_tick IS NOT NULL` — the same predicate in the source, not merely a similar one |
| `reward_delay_duration` | `reward_onset_tick - choice_cue_tick` |
| `last_stop_duration` | `choice_cue_tick - last_stop_tick` |

The four `Json[Any]` fields on `SessionMetadata` — `session`, `rig`, `task_logic`, `trainer_state`
— are not dropped but *rehomed*: they are the rig and task configuration, which `03` places in
`docs/` and `04` binds as sidecar documents. R3 §2.1 confines JSON to optional columns and these
are required, so a column was never available to them.

## A denormalization is kept only if it is checked

Eight of `Site`'s ten remaining index columns are `groupby(...).cumcount()` over columns the table
already has, so R3 §3.0 would strike them. They are kept on `core.units.n_spikes`' precedent — a
validated denormalization, kept because it is what people filter by — and the validation is the
condition: each of the eight carries a Tier 2 rule comparing it against the window function it came
from. Keeping them cannot drift, and the eight rules were mechanical to write because the source
computation is.

`odor_concentration` is the `list[float]` R3 §2.1 forbids, and it is per **olfactometer channel**:
the source builds `[0.0] * n_channels` and fills the channels an odor is on. So `site_odors` is
dense, and its zeros are load-bearing — a missing row means a channel the rig does not have, not a
channel that was off.

One unit is deliberately absent. `reward_probability` is declared `percentage` on a field named
*probability*, and which of 0–1 or 0–100 is stored has not been checked against data. A wrong
`unit` is worse than none, so it carries none until a real session settles it.

## Known gaps

`registry/check.py` covers `logical_schemas.json` only, so nothing here is checked by the standing
registry run — not the naming conventions, not the JSON Schema, not whether a rule's SQL parses.
Under those conventions `aind_unit_qc` has four columns that would flag today
(`num_spikes`, `rp_violations`, `num_negative_peaks`, `num_positive_peaks`: "no integer column is
plural"). All four are the sorter's own names, which is the case the section above argues should
win, so the fix is four declared exceptions rather than four renames.
