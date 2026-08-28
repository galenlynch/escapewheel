# R30 — What `analysis.spike_events` Is For

| | |
|---|---|
| **Status** | **Proposed** 2026-08-28 |
| **Amends** | `06_analysis_layer.md` §23 (`analysis.spike_events`) |
| **Depends on** | R5 (flat spike representation), R13 (anchor-point alignment), R27 (clock graph integrity) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`06` introduces the table like this:

> Long spike table derived from `core.unit_spike_chunks` when chunked spikes are canonical.

**R5 withdrew `core.unit_spike_chunks`.** `core.spike_events` became canonical, one row per
spike, all primitives — which is exactly the long flat table `06` described building. So the
table's stated derivation is from a table that no longer exists, to produce a shape core now
has. The schema survived R5 and the reason for it did not.

Meanwhile R27 created a need the analysis layer is the right home for. A packet's spikes are
on their probes' sample clocks, which is what makes them exact and what makes two probes
incomparable without conversion. A reader's default is to return times on the session's
reference clock, and doing that conversion on every read is work a writer can do once.

This revision gives the table that purpose. Nothing about its schema changes.

## 2. Replacement

**Strike** `06`'s sentence introducing `analysis.spike_events` and replace it with:

> Spikes on the session's reference clock (R27 §2), mapped from `core.spike_events` through
> `core.clock_anchors`. Its `clock_id` is the reference; `core.spike_events` keeps each
> spike's exact tick on the clock it was measured on.

The column list, types and recommended ordering in `06` are unchanged and remain the schema.

### 2.1 Rows are not preserved

A spike whose tick falls outside the region where the mapping is defined (R27 §5.3) MUST be
omitted rather than given an extrapolated value. So this table MAY have fewer rows than
`core.spike_events`, and a consumer MUST NOT assume the two are row-aligned or that a count
from one applies to the other.

On the session this was built against, none were dropped: all 247,758,402 spikes fell within
one median anchor interval of an anchor. That is a property of a well-anchored recording and
not a guarantee — a session whose sync pulses start late will lose the spikes before them,
which is the honest outcome and the reason the omission is specified rather than left to a
writer.

### 2.2 It is still disposable

R30 does not make this table canonical, and `06`'s promotion rules are untouched. It is
derived, regenerable from `core.spike_events` and `core.clock_anchors`, and a packet without
it is complete. `06` already requires an analysis resource to declare lineage to core; for
this table that lineage is those two resources and `core.clocks`.

## 3. Why the analysis layer and not core

Because the value is derived and the layer is what says so.

Putting reference-clock ticks in `core.spike_events` would mean either replacing the measured
tick — losing the only exact number in the table — or carrying both, which doubles the
largest table in a packet to save a conversion measured at 29 M spikes a second. Neither is
worth it. A query touching a few units pays single-digit milliseconds to convert, and only a
full-session scan benefits from the materialization, which is precisely `06`'s own test for
when to materialize rather than use a view.

## 4. What this does not do

- **No schema change.** Same columns, same types, same ordering. A packet that already
  carries this table under `06`'s reading stays conforming; it simply claims something the
  data may not support, which is what the amendment fixes.
- **No new rule.** That the ticks really are on the reference clock is a foreign key to
  `core.clocks`, which Tier 1 already generates. That they were mapped *correctly* is not
  checkable in SQL — the anchors and the mapping are both in the packet, but re-deriving
  them to compare is a computation, not a query.
- **No treatment of the other analysis resources.** `06` names six more, and
  `analysis.spikes_by_trial` in particular has the same problem in a milder form: it says
  spikes carry `t_abs_tick` and `t_rel_tick` without saying which clock either is on. That
  wants its own revision once something builds it.
- **No `since` stamp.** Under R29 §2 this table carries none, because its *schema* comes from
  `06` unamended. Only its purpose is amended, and R29's field records where a column came
  from rather than why.

## 5. Open

- **Whether a dropped spike should be recorded anywhere.** §2.1 omits it silently, and a
  count of what the mapping could not place is a real quality signal — a session losing
  thousands is one whose sync started late. `core.processing_runs` could carry it as a
  materialization parameter, which is `06` §169's mechanism, and nothing currently writes one.
- **Whether the reference clock should be named in the resource rather than the rows.**
  Every row carries the same `clock_id`, which dictionary-encodes to nothing but is still a
  column restating a per-resource fact. R3 §3.0 would normally strike it; it stays because
  the foreign key to `core.clocks` is what makes the claim checkable at all.
