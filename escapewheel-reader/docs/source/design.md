# Design

The reader owns a transformation only where doing it yourself from the documented schema would be
**silently** wrong: a plausible number with nothing to say it is not the right one. Everything else
is a query, left to the caller in Arrow, Polars or SQL. This page explains each transformation the
reader does own, and the shape of the API that offers them.

## Free functions and a thin `Packet`

The reader returns PyArrow tables, and `pa.Table` belongs to PyArrow: it has no `.pipe()` and
cannot take methods of ours. A transformation is therefore a free function taking the packet
first, in three layers:

| layer | shape | examples |
|---|---|---|
| kernels | arrays → arrays | `align(ticks, anchor_t, anchor_p, *, bound)` |
| semantics | `(packet, table) → table` | `on_clock(packet, table)`, `seconds(packet, table)` |
| access | `(packet, ...) → table` | `spike_times(packet, ...)`, `unit_windows(packet)` |

Because every result is a `pyarrow.Table`, the layers compose: `seconds(packet, on_clock(packet,
stored))` puts stored ticks on the reference clock and then in seconds, and the result goes to
Polars, pandas or DuckDB unchanged.

`Packet` resolves resources, reads them, acquires the registries the packet binds and registers
tables with DuckDB. It has no method doing what a free function does: `spike_times(packet, 17)` is
the only spelling of that read.

`open_dataset` is the second entry point, for many packets at once (see
[Datasets of many packets](#datasets-of-many-packets)).

## Clocks

A spike's tick is exact on its probe's clock and means nothing beside another probe's. Anchors in
`core.clock_anchors` relate the clocks, and `clocks.align` turns that relation into numbers by
R13 §3's piecewise-linear mapping with Part 01 §3.9's bound. It is the only place that arithmetic
is written, and it lives in the reader because the writer needs it too: a packet whose spikes were
mapped at write time and a caller mapping the same spikes at read time agree only if both run one
implementation.

Let *m* be the median interval between a clock's anchors. The mapping follows three rules.

1. Between two anchors no more than 2*m* apart, it interpolates linearly on that pair.
2. Beyond the terminal anchors, it computes ``parent(a) + rate * (t - a)``, where *a* is the
   nearer terminal anchor and `rate` is fitted over the whole sequence (Part 01 §3.9). The rate is
   global because a terminal segment's slope comes from two anchors alone. The offset is the
   terminal anchor's own because a global fit's intercept carries the session's clock wander,
   which a straight line cannot follow (R37 §2).
3. Further than *m* from every anchor, past the ends or inside a wider gap, the mapping is
   undefined, and `align` returns a mask saying so rather than a plausible number. A caller that
   has measured its own clocks may widen `bound`.

The mask matters because the first sync pulse commonly arrives a second or more after a recording
starts. The spikes before it have no defined parent tick, and they are exactly the ones a caller
would otherwise misplace.

`spike_times` and `events` return ticks on the packet's reference clock by default, with
`clock_id` alongside, because a stored tick from one probe compared with another's is the easy
wrong answer. `clock=STORED` asks for the ticks as stored.

## Observation windows and rates

A point process is a set of times *and* the span over which something was looking. Without the
span, a silent unit and an unrecorded one produce the same rows, and counts from units observed for
different spans cannot be compared. Part 01 §2.3 puts the span on the clock and lets a unit or a
stream refine it. A unit's window is therefore its own where it declares one and its clock's
otherwise, and the two live in different tables; `unit_windows` and `stream_windows` resolve that
inheritance.

Nothing defaults a denominator. `rate` takes a count and a duration with no default for either,
because the error this prevents is dividing by the wrong span. A packet that declares no windows
gets an empty table and no invented extent.

`spike_times` for a single unit attaches the unit's windows to its result, so `rate_of` needs no
second lookup. Arrow's schema metadata survives exactly the wrong operations for that:

| operation | metadata kept | support still describes the rows |
|---|---|---|
| `filter` | yes | **no** |
| `slice` | yes | **no** |
| `concat` | yes | **no** |
| `sort_by` | yes | yes |
| `select` | yes | yes |
| `group_by` | no | no |

The attachment therefore records the row count it was computed for, and `support_of` refuses a
table whose count has changed. Row count separates the cases exactly: it catches the three hazards
and passes the two harmless operations.

Intervals are closed: `start_tick` and `stop_tick` are both observed, so a window covers
``stop - start + 1`` ticks (Part 01 §2.3).

## Coexisting runs

A project re-sorts, re-curates and re-runs models over one session, and a packet may hold the
alternatives side by side. Reading `core.units` without saying which result is current returns
every alternative, and every count derived from it is wrong by however many units the other
sorting found. Part 01 §2.6 forbids resolving that silently, so `runs` answers in three states:

- **one run** for a purpose: the preference by construction, with nothing to declare;
- **several, with a preference**: `core.preferred_runs` says which;
- **several, no preference**: refuse, naming the unresolved purpose.

A purpose is `(session_id, activity_type, scope)`. Scope is what a run is about, such as a probe, an
array asset or a camera; it separates twelve probes sorted once each from one probe sorted twice. A
run recording no scope makes its purpose `undeterminable`, which Part 01 §2.6 requires be reported
apart from an ambiguity. An `import` run is in no purpose, since two imports supply disjoint rows
(Part 05 §12).

`units()` applies this check and raises `AmbiguousRun`; `table("core.units")` does not, and is the
way to read every row anyway.

## Spikes against events

Two questions look alike and return different rows, so they are two functions rather than one with
a flag that would select the wrong one by omission.

- `aligned_spikes` gives one row per **(spike, event) pair**. A spike inside two events' windows
  appears twice, which a PSTH needs.
- `assigned_spikes` gives at most one row per **spike**, labelled with the event it belongs to:
  ``preceding`` for the last event underway, ``nearest`` for the closest in either direction.

The two coincide exactly when no spike falls in two windows, which `windows_disjoint` checks. Only
then may an ASOF join answer `aligned_spikes`; elsewhere it drops every pair after a spike's first.
Both run on DuckDB, the `sql` extra; the PyArrow equivalent is two `searchsorted` calls per unit
against sorted trains.

## Channel indices

A sorter drops bad channels before it runs, so a channel index it emits counts the channels it kept
and not the probe's contacts. Read as a position in `core.electrodes`, an index usually names a
plausible but wrong contact (R83 §1). `core.sorting_run_channels` holds the kept list in the run's
own order, and `electrode_at` resolves an index by counting through it (Part 02 §12.2). A packet
whose runs record no list is conforming; `runs_without_channels` names them.

A unit's own peak contact needs none of this: `core.unit_electrodes.is_primary` carries it.

## Array axes

Each axis of a dense array declares its coordinates in one of four forms, in the table its
declaration's `axes_resource` names: ticks on a clock, a numeric origin and step, a 1-D array of
values, or labels naming rows of a resource (Part 03 §6.3). Reading them by hand has a plausible
wrong answer at every step:

- a label table holds every array's labels, and two arrays may share an `array_asset_id`, so an
  unscoped read labels one array's channels with another's;
- label rows are in storage order, not position order;
- a dependent axis stands for different rows at each position of the axis it depends on, so a
  waveform's third channel is a different contact for each unit;
- a null label is padding, which a fill or a cast turns into a row that exists;
- a rational step accumulates rounding if summed in floats;
- scaling may be declared on the array or per channel but not both, so applying one without
  looking for the other double-scales or misses.

`describe` resolves all of it and returns plain numbers and Arrow tables. It needs no array
library, so an xarray, SpikeInterface or DimensionalData adapter can build on it.

## Discriminators

A discriminator column names, row by row, the resource that specialises that row, as
`core.intervals.interval_kind` does. Part 05 §13.4 asks a reader to resolve one, because a
discriminator nothing reads is a free-form name with extra steps. The join takes two shapes, and a
paired value resolves in the kind of its own row, so `resolved` and `specialised` perform it.
`unresolved` reports a kind the packet names and does not hold at the level Part 02 §8.3 assigns: a
defect where `resolves` is `required`, a fact where it is `optional`.

## Datasets of many packets

A writer assigns identifiers packet-wide (Part 05 §4.3), so an identifier means nothing outside
its packet: two packets both hold `unit_id` 0 and neither names the other's unit, and concatenating
their tables conflates them. `open_dataset` gives every session a `session_key` drawn from provenance rather
than a label, and presents each session-scoped table as the union of every packet's rows with that
key alongside (Part 05 §13.1). The relation has the same shape for one packet or twenty, so an
analysis written against one session runs unchanged against many.

## Locations and URIs

A resource's `uri` is a name resolved against a root the reader supplies when it opens the packet:
a local directory or an object-store prefix (Part 00 §3.3). A `Location` is somewhere bytes can be
fetched from, and a declared URI becomes one only once a root and any caller-supplied rewrite have
been applied. A relative reference is resolved by appending its decoded names to the root, never by
RFC 3986's merge, which would drop a location's last segment wherever it lacks a trailing `/`
(Part 03 §4).

## Dictionary-encoded columns

Parquet stores a low-cardinality string column as codes into a dictionary, and a reader meets one
wherever such a column is read without decoding. The helpers in `dictionaries` take the dictionary
where there is one and the column where there is not. Arrow cannot sort a dictionary column, and
`group_by` fails across row groups until `Table.unify_dictionaries` reconciles them; both fail
loudly. The reader, the writer and the validator share these helpers so that they meet those edges
identically.
