# An Encoding Follows a Rule and Its Declared Exceptions

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `03` §5.5 (two writer SHOULDs beside the tick one, and what a writer reports); adds three subsections to `10` §2 |
| **Depends on** | R68 §2.3 (`DELTA_BINARY_PACKED` is defined for `INT32` and `INT64` alone), R68 §3 (the tick SHOULD `03` §5.5 carries), R10 §2 (a table is sorted by its primary key), R53 §2.1 (an identifier is an integer), R93 §3.4 (a measurement supports a rule that lives elsewhere), R93 §3.5 (what survives replacing the reference implementation), R17 §3 (an extension needs no second code path), R53 §2.5 (a writer mints every assigned identifier) |
| **Profile** | `escapewheel-portable-v0.1` |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`03` §5.5 tells a writer one thing about how to encode a column: a tick column takes
`DELTA_BINARY_PACKED` and not a dictionary, because a dictionary built over millions of distinct
ticks is abandoned at its size threshold and leaves pages larger than either encoding alone. R68 §3
established that from `core.media_frames.pts`, which was **96.9%** of its table before the rule.

Two more rules hold on the same evidence and are stated nowhere, so the columns they govern were
encoded by pyarrow's default. Rebuilding both packaged sessions against a registry twenty-one
revisions newer made that visible: **37 ascending identifier columns carried a dictionary**, where
delta is 5x to 79x smaller. This part states both rules, records why each must carry exceptions,
and puts the readings in `10` beside R68's.

Measured on **`ecephys_776259`** (twelve probes, 6,781 sorted units, recorded 2025-04-09) and
**`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25), over the **75 numeric columns
above 2 kB** the two hold between them. Every figure is the encoding and its compression together,
since `03` §5.1 puts Zstandard over whatever the encoding produced.

## 2. Background

Informative.

### 2.1 The identifier a table sorts by ascends

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

### 2.2 A dictionary over values that do not repeat

Of the **32 float columns** above 2 kB, **27 are smaller written plain**, by 1.15x to 1.76x —
`axis_value` in both coordinate child tables, `core.unit_quality_labels.confidence`, and most of
`aind_unit_qc.metrics`. A dictionary is an index over repetition, and a measurement repeats about
as often as a measurement does.

The five that do repeat decide more than the twenty-seven. `core.spike_events.amplitude` is
quantised to the sorting run's amplitude step, so 286,896,563 rows hold few distinct values and the
dictionary is **1.85x** better across **209 MB** — the largest single encoding decision a packet
makes, and the one a rule without exceptions discards.

### 2.3 A rule read off the declaration picks wrongly

What delta exploits is small successive differences and what a dictionary exploits is repetition,
and the registry declares neither. Deriving the choice from the sort key was measured against all
138 numeric columns of the two packets and picked worse on **38**:

- `core.media_frames.pts` **195x worse** and `core.clock_anchors.t_tick` 57x, both climbing
  steadily without being key columns at all;
- `core.unit_electrodes.electrode_id` 1.84x worse, a trailing key component (R28 §2) that climbs
  within each unit and resets, which is a sawtooth neither encoding reads well.

A role says what a column means. It does not say how the values are spread, and a storage choice
turns on the second.

### 2.4 Measuring every column at write time is affordable and still wrong

Writing each column three ways over a 65,536-row sample and keeping the smallest costs **12 ms for
four columns**, about **0.4 s** for a whole packet against a 467 s build. Cost is not what refuses
it.

Two other things do. The choice becomes invisible, because nothing records why a column got its
encoding where a declared exception carries the number that justified it. And it stops being a
property of the packet's schema: a `--sample` build measures different values from a full one, so
the sampled packet is no longer a faithful preview of the layout the full one gets.

## 3. Decision

### 3.1 An ascending identifier is delta-encoded

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

### 3.4 An extension declares exceptions for its own tables and no others

A writer's exceptions **MUST** name only tables of the layer that writer implements, and a writer
**MUST** accept exceptions an extension supplies for the extension's own tables. Core naming an
extension's table makes the extension unmaintainable by anyone but core: a fourth extension arriving
tomorrow could declare nothing, and one shipped as a document alone (R17 §2) has no code to patch.

The division costs an extension almost nothing, because the columns where an encoding is worth 37x
to 79x are not its own. An extension hands the writer Arrow with its identifiers as **names**, and
R53 §2.5 has the writer mint the integers packet-wide, so `aind_unit_qc.metrics.unit_id` is core's
column by the time an encoding is chosen for it — which is why §2.1's table includes it at 57x
without the extension being consulted. What an extension owns is its own measurements, and §3.2
reaches those by rule.

### 3.5 A writer reports a column a rule guessed wrong about

A writer **SHOULD** report, at `info`, a column whose encoding costs more than **1.5x** the smallest
available to it, measured over a sample of the rows it wrote. R68 §3's rule and the two above are
good guesses, and a report is how the author of a table learns that theirs is one the guess misses.

Measured on the two packaged sessions, three columns draw one, all in one extension:
`aind_unit_qc.metrics.num_spikes_used` at 1.7x, `presence_ratio` and `sliding_rp_violation` at 1.8x.
That is the mechanism working as intended rather than a defect — those are the columns core stopped
naming under §3.4, and the report is what tells their owner to declare them.

A report and not a refusal, because `03` §5.5 permits every encoding and a packet is conforming
whichever it uses. The level is R97 §3.4's, which reports a declared `metadata` column no row fills
for the same reason: a judgement someone should revisit is not a defect.

### 3.6 `10` carries the readings

R93 §3.4 puts a measurement where it supports a rule that lives elsewhere, so §2.1's table, §2.2's
count and §2.3's regressions go to `10` §2 beside R68's `pts` measurement. §2.4's 0.4 s is
`07` §7's instead: it is a property of one implementation's libraries, which R93 §3.5 separates from
what survives replacing them. §3.5's tolerance goes to `03` §5.5 with the rule it qualifies, being a
number a writer acts on rather than a reading.

## 4. What this does not change

- **No packet already written becomes invalid.** `03` §5.5 makes dictionary, RLE and delta
  encodings all permitted and all required of readers, so a packet's encoding was never part of
  what makes it conforming; what changes is which encoding a writer reaches for first.
- **No column's type changes.** R68 changed one — `pts` from `float64` to `int64` — because
  `DELTA_BINARY_PACKED` is defined for integers alone (R68 §2.3), so a reader may expect a type to
  move here too. Both rules apply to types the registry already declares.

## 5. Consequence

`03` §5.5 gains two SHOULDs beside the tick one, and `10` §2 gains three subsections: an
ascending identifier's cost, a float's dictionary, and what a rule read off the declaration does to
`pts`. `07` §7 gains one line for the cost of measuring instead.

**No table, column, reference, rule or vocabulary changes, and no packet is rebuilt for this
part** — though both packets are rebuilt for other reasons, and they carry the new encodings when
they are. Measured over the 75 columns after the rules and their exceptions: none more than **15%**
off the smallest encoding available to it, the worst being
`aind_unit_qc.metrics.isi_violations_count` at 1.15x.

The saving is small and the ratios are not. Across both packets the three rules recover about
**1.9 MB of 1.76 GB**, because the columns that dominate a packet were already right: 17 tick
columns at 1,422 MB and 72 measurement columns at 327 MB are unchanged. What the rules buy is per
table rather than per packet — `core.unit_coordinates` goes 30 kB to 5 kB, which is what a consumer
reading that table alone pays.

## 6. Open

- **Where an extension shipped as a document alone declares an exception.** §3.4 has a writer accept
  what an extension supplies, which serves a distribution carrying code. An extension that is
  entirely data — a registry document and Parquet files, which R17 §2 permits and the `tables`
  source exists for — has nothing to supply it from, so §3.5's report is all it gets. A recipe could
  carry the declaration, being the per-build document where R87 §2.5 already puts a value someone
  chose and the reason they chose it, and an encoding is a fact about one packet's values rather
  than about the schema. Nothing here needs it yet: the three columns §3.5 reports are in an
  extension that ships an adapter.
