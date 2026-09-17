# R110 — An Encoding Follows a Rule and Its Declared Exceptions

| | |
|---|---|
| **Status** | **Accepted** 2026-09-10 |
| **Amends** | Part 03 §5.5 (two writer SHOULDs beside the tick one, and what a writer reports); Part 05 §3 (a recipe declares an encoding); adds four subsections to Part 10 §2 |
| **Depends on** | R68 §2.3 (`DELTA_BINARY_PACKED` is defined for `INT32` and `INT64` alone), R68 §1.3 (what the tick rule was worth on `pts`), R10 §2 (a table is sorted by its primary key), R53 §2.1 (an identifier is an integer), R93 §3.4 (a measurement supports a rule that lives elsewhere), R93 §3.5 (what survives replacing the reference implementation), R53 §2.5 (a writer mints every assigned identifier), R109 §3.1 (a writer requires no code of an extension), R109 §3.6 (what an extension may state across the boundary) |
| **Profile** | `escapewheel-portable-v0.1` |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

Part 03 §5.5 tells a writer one thing about how to encode a column: a tick column takes
`DELTA_BINARY_PACKED` and not a dictionary, because a dictionary built over millions of distinct
ticks is abandoned at its size threshold and leaves pages larger than either encoding alone. That rule is
original to Part 03 and predates every revision; R68 §1.3 is what measured it, on
`core.media_frames.pts`, which was **96.9%** of its table before the rule reached it.

Two more rules hold on the same evidence and are stated nowhere, so the columns they govern were
encoded by pyarrow's default. Rebuilding both packaged sessions against a registry twenty-one
revisions newer made that visible: **28 leading identifier columns carried a dictionary**, fifteen
distinct columns across the two packets, where delta is 37x to 79x smaller. This part states both rules, records why each must carry exceptions,
and puts the readings in Part 10 beside R68's.

Measured on **`ecephys_776259`** (twelve probes, 6,781 sorted units, recorded 2025-04-09) and
**`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25). The population is the **80
numeric columns that reach 2 kB under pyarrow's default** across the two packets — 48 integer and
32 float — and it is defined on the default rather than on what the packets now carry, because a
threshold on compressed size otherwise removes the columns a rule fixed: `core.units.unit_id` is
26.3 kB dictionary-encoded and **0.5 kB** delta-encoded, so measuring the rules against their own
result drops it from the very set that justifies them. Every figure is the encoding and its
compression together, since Part 03 §5.1 puts Zstandard over whatever the encoding produced.

## 2. Background

Informative.

### 2.1 Table identifiers are ascending

R10 §2 sorts a table by its primary key, so the first key column climbs across the whole table
where every later one only climbs within the group above it. An identifier has been an integer
since R53 §2.1, and an ascending integer is what delta encoding exists for — its residuals are
ones and twos where the values are thousands.

Nothing said so, and pyarrow's default is a dictionary on everything:

| column | dictionary | delta | |
|---|---:|---:|---:|
| `aind_unit_qc.synchrony.unit_id` | 48.6 kB | 0.6 kB | **79x** |
| `core.unit_coordinate_values.unit_id` | 46.8 kB | 0.6 kB | **75x** |
| `core.units.unit_id` | 26.3 kB | 0.5 kB | 57x |
| `core.unit_coordinates.unit_id` | 25.3 kB | 0.5 kB | 53x |
| `core.electrode_coordinates.electrode_id` | 24.3 kB | 0.5 kB | 48x |
| `core.electrodes.electrode_id` | 17.5 kB | 0.5 kB | 37x |

A dictionary over a near-unique ascending column stores the values once and an index into them
again: `core.unit_coordinates.unit_id` cost **30.95 bits a row** for an `int32`, which is almost
the 32 bits the raw values take.

### 2.2 A float column's values rarely repeat

Of the **32 float columns** above 2 kB, **27 are smaller written plain**, by 1.15x to 1.76x —
`axis_value` in both coordinate child tables, `core.unit_quality_labels.confidence`, and most of
`aind_unit_qc.metrics`. A dictionary is an index over repetition, and a measurement repeats about
as often as a measurement does.

The five that do repeat decide more than the twenty-seven. `core.spike_events.amplitude` is
quantised to the sorting run's amplitude step, so 286,896,563 rows hold few distinct values and the
dictionary is **1.85x** better across **209 MB** — the largest single encoding decision a packet
makes, and the one a rule without exceptions discards.

### 2.3 Every packet read downloads the entirety of small tables

A packet is two spike tables and everything else. `core.spike_events` and `analysis.spike_events`
are **1,168 MB** of `ecephys_776259` and are read behind a filter, a row group at a time; the
other **38 tables come to 1.375 MB and are read entire**, because a consumer wanting the units,
the electrodes, the coordinates or the trials wants all of each.

Those 38 are **2.622 MB** under pyarrow's default, so the rules take **1.91x** off what a consumer
transfers before a filter can prune anything. `ecephys_786867` is **1.80x** over its 37 comparable
tables, 1.686 MB against 0.934 MB, and **23.94x** with `core.media_frames` counted, where
7,570,450 rows go from 30.949 MB to 0.429 MB.

Decoding gives none of it back. Over the same 38 tables, warm and with the two arms interleaved,
the written files decode in **15.6 ms against 15.8 ms** for the default ones, and in 28.8 ms
against 57.7 ms where `core.media_frames` is among them (pyarrow 25.0.1, Python 3.13.15,
2026-09-10). Delta unpacking is arithmetic on registers where a dictionary is a gather, and at
these sizes both disappear beside the Zstandard pass that shrinks with the bytes.

Round trips are the one cost this leaves alone. Part 10 §4.1 puts an endpoint at about **120 requests
a second** whatever the concurrency, and a column chunk is one ranged read at either size, so what
an encoding changes is what each request carries. Across the twenty sessions R86 §1.1 measures
that plateau against, a packet's small tables are **52 MB by default and 27 MB as written**.

### 2.4 A declaration-derived rule picks the wrong encoding

What delta exploits is small successive differences and what a dictionary exploits is repetition,
and the registry declares neither. Deriving the choice from the sort key — delta for a key column,
a dictionary for everything else — was measured over the **116 column-and-packet pairs** that reach
2 kB under either choice, and picked worse on **82**:

- `core.media_frames.pts` **188x worse** and `core.clock_anchors.t_tick` 57x, both climbing
  steadily without being key columns at all;
- `core.unit_electrodes.electrode_id` 1.84x worse, a trailing key component (R28 §2) that climbs
  within each unit and resets, which is a sawtooth neither encoding reads well.

A role says what a column means. It does not say how the values are spread, and a storage choice
turns on the second.

### 2.5 A measured encoding records no reason for itself

Writing each column three ways over a 65,536-row sample and keeping the smallest costs **12 ms for
four columns**, about **0.4 s** for a whole packet against a 467 s build. Cost is not what refuses
it.

Two other things do. The choice becomes invisible, because nothing records why a column got its
encoding where a declared exception carries the number that justified it. And it stops being a
property of the packet's schema: a `--sample` build measures different values from a full one, so
the sampled packet is no longer a faithful preview of the layout the full one gets.

## 3. Decision

### 3.1 Ascending identifiers are delta-encoded

A writer **SHOULD** encode with `DELTA_BINARY_PACKED`, and **SHOULD NOT** dictionary-encode, the
first column of a table's sort order whose role is `identifier`. R10 §2 makes that column ascend
across the whole table, which is the property delta exists for and which no later key column has.

`session_id` is not that column, being one value in a single-session packet (R1) and already
0.03 bits a row under run-length encoding. A writer skips it and takes the next.

### 3.2 A float column is not dictionary-encoded

A writer **SHOULD NOT** dictionary-encode a floating-point column, and **SHOULD** write one whose
values repeat as a declared exception under §3.3. Repetition is what a dictionary indexes, and
§2.2 measures that four floats in five do not repeat enough to pay for one.

### 3.3 An exception carries the measurement that justifies it

Neither rule above is the property it stands in for, so a writer **MUST** be able to override each
per column, and every override **MUST** record what it measured and on what. An exception that
records nothing cannot be re-judged when the data changes, and it will not be: the alternative is a
list that grows by accident and is never read again.

A writer **SHOULD** refuse an exception naming a column no table declares, which is decidable with
no packet in hand and is what keeps such a list from going stale.

### 3.4 An extension declares an exception in the recipe

A writer's own exceptions **MUST** name only tables of the layer it implements, and an extension's
**MUST** be declarable without the writer importing anything the extension ships. A recipe carries
them, in an `[encoding]` table keyed `resource.column`, each entry naming one of `delta`, `plain`
or `dictionary` and the reason it was measured.

R109 §3.1 is why the recipe carries them rather than the extension handing them over: a writer may
require no code of an extension, so a declaration that arrived as a Python object would be one an
extension could make only by being importable. R109 §3.6 puts what an extension states about its own
run in a file the recipe names, and an encoding is the same kind of statement one level down.

The recipe is also the right granularity rather than the only reachable one. An encoding is a fact
about **one packet's values** — `aind_unit_qc.metrics.presence_ratio` repeats often enough to want a
dictionary in these two sessions and may not in a third — where a schema-level declaration would
claim it of every packet the extension ever appears in. R87 §2.5 already puts a chosen value and its
reason in a recipe for the same reason: the choice belongs to the build.

An entry **MUST** carry a reason. A bare choice cannot be re-judged when the data moves, which is
what §3.5's report exists to prompt.

### 3.5 A writer reports when rules guess wrong about columns

A writer **SHOULD** report, at `info`, a column whose encoding costs more than **1.5x** the smallest
available to it, measured over a sample of the rows it wrote. Part 03 §5.5's tick rule and the two above are
good guesses, and a report is how the author of a table learns that theirs is one the guess misses.

Measured on the two packaged sessions before §3.4's declarations were written, three columns drew
one and all were in one extension: `aind_unit_qc.metrics.num_spikes_used` at 1.7x, `presence_ratio`
and `sliding_rp_violation` at 1.8x. Rebuilt with those three declared, none does.
That is the mechanism working as intended rather than a defect — those are the columns core stopped
naming under §3.4, and the report is what tells a recipe author which entries to write.

A report and not a refusal, because Part 03 §5.5 permits every encoding and a packet is conforming
whichever it uses. The level is R97 §3.1's, which reports a declared `metadata` column no row fills
for the same reason: a judgement someone should revisit is not a defect.

### 3.6 Part 10 carries the readings

R93 §3.4 puts a measurement where it supports a rule that lives elsewhere, so §2.1's table, §2.2's
count, §2.3's denominator and §2.4's regressions go to Part 10 §2 beside R68's `pts` measurement.
§2.5's 0.4 s is
Part 07 §7's instead: it is a property of one implementation's libraries, which R93 §3.5 separates from
what survives replacing them. §3.5's tolerance goes to Part 03 §5.5 with the rule it qualifies, being a
number a writer acts on rather than a reading.

## 4. What this does not change

- **No packet already written becomes invalid.** Part 03 §5.5 makes dictionary, RLE and delta
  encodings all permitted and all required of readers, so a packet's encoding was never part of
  what makes it conforming; what changes is which encoding a writer reaches for first.
- **No column's type changes.** R68 changed one — `pts` from `float64` to `int64` — because
  `DELTA_BINARY_PACKED` is defined for integers alone (R68 §2.3), so a reader may expect a type to
  move here too. Both rules apply to types the registry already declares.

## 5. Consequence

Part 03 §5.5 gains two SHOULDs beside the tick one, and Part 10 §2 gains four subsections: an ascending
identifier's cost, a float's dictionary, what the rules take off the tables a consumer reads whole,
and what a rule read off the declaration does to `pts`. Part 07 §7 gains one line for the cost of
measuring instead.

**No table, column, reference, rule or vocabulary changes**, and both packets carry the new
encodings, having been rebuilt for other reasons.

Both recipes exercise §3.4, and the result is §3.4's argument rather than an illustration of it.
`aind_unit_qc.metrics.presence_ratio` is declared `dictionary` in `ecephys_776259` and declared
nothing in `ecephys_786867`, because it repeats across 6,781 units and not across 4,505; rebuilt,
the column carries `RLE_DICTIONARY` in the first packet and `PLAIN` in the second. One schema-level
declaration would have had to be wrong for one of the two. Measured over the 80 columns after the rules and the exceptions declared at the time, **three**
remained more than **15%** off the smallest encoding available to them, all in `aind_unit_qc.metrics`
and worth 12.6 kB between them: `amplitude_median` at **1.32x**, `firing_range` at 1.31x and
`isi_violations_count` at 1.15x. Each is a column §3.4 reaches and no core rule does, so each was
declared in the recipe that produces it; with those three entries written, none exceeds 15%.

What the rules recover is **1.247 MB of the 2.622 MB** a consumer transfers before it can filter
anything (§2.3), and the largest single number in the exercise is one they **keep**:
`core.spike_events.amplitude` holds the dictionary §2.2 measures, under §3.3's exception, which a
float rule admitting none would have spent.
