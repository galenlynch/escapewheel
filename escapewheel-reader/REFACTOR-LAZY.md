# Arrow-lazy reading

The reader's accessors return eager `pyarrow.Table`s, and the steps they take on the way — mapping
ticks onto a clock, cutting a time range, adding seconds — accept only a `pa.Table`. A caller who
wants to stay lazy holds a `pyarrow.dataset.Dataset` from `Packet.scan` and has no way to apply
those steps without materializing first. This document records the design that makes every read
stay lazy until the caller chooses, and the work in the order it will be done.

It changes no packet contract. Tick an item when its commit lands. Figures were measured on
`ecephys_776259` (12 probes, 286,896,563 spikes, 6,781 units) on NVMe, between commits `3cd086d4`
and `ae61f869`, and are not maintained.

## 1. What was found

**Constraints reach the Parquet scan, but only from inside the reader.** `Packet.table` and
`Packet.scanner` turn `columns=` and keyword constraints into a scanner projection and filter, and
every accessor reads through them. The expression builder, `Packet._predicate`, is private, so a
caller holding a `Dataset` cannot reuse it.

**A range on the output clock exists only inside two accessors.** `spike_times` and `events` widen
a range into stored ticks (`access._span`, through `clocks.stored_span`) and cut it exactly after
mapping (`access._narrowed`). `Packet.table` applies a coordinate constraint to stored values
whatever `on_clock` says. `stored_span` takes the union of every clock's widened range, which on
this packet spans probe tick 53,965,808 to harp tick 361,804,256,862 and prunes nothing.

**The conversions take only an eager table.** `attach_clocks`, `on_clock` and `seconds` accept a
`pa.Table`, so a Scanner or a batch stream has to be materialized before it can be put on a clock.

**Many packets have no lazy Arrow form.** `Dataset.table` reads every packet eagerly and takes
`columns=` but no row constraint; the only lazy path across packets is `Dataset.duckdb`, which
needs the optional `sql` extra. The class name also collides with `pyarrow.dataset.Dataset`.

**The interpolation inverts exactly.** Every clock map is monotone in a valid packet:
`core.clock_anchors.monotonic` and `core.clocks.transform_slope_positive` are error-level rules,
interpolation between increasing anchors increases, extrapolation continues at the end slope,
and `rint` and composition preserve order. The stored ticks that land in `[lo, hi]` on a target
clock therefore form one interval per clock, which the reader can find by inverting the endpoints
and refining them against the forward map.

### Evidence from the return-contract spike

`bench/lazy_spike.py` stated the clock mapping in DuckDB, Polars and Narwhals and compared return
contracts; `bench/results/history.md` records it.

| finding | holds |
|---|---|
| The relational mapping equals the kernel on every row when it rounds half to even; DuckDB's `ROUND` misplaces 2,792,142 spikes by one tick. | yes |
| Mapping stored ticks relationally takes 12–19 s against the kernel's 5.1 s. | yes |
| No engine pushes a filter on a mapped tick into the scan. | yes, and moot once the reader inverts the range itself |
| `core.spike_events` is sorted by unit, so every one of its 293 row groups spans the session and no time filter prunes it; 60 s took 4.09 s through `spike_times` and 0.07 s from `analysis.spike_events`. | yes |
| A `RecordBatchReader` through the kernel peaks at 0.9 GiB for the go-cue analysis. | yes; it is `Packet.scanner` plus the kernel, not a new contract |
| DuckDB needs 14.0 s and 31 GiB for the go-cue analysis. | no: the arm mapped stored ticks in SQL and ran one unsliced ASOF join, where `aligned_spikes` reads `analysis.spike_events`; sliced, that path takes 6.9 s at 2.0 GiB |

Narwhals needed three workarounds to express the mapping, and its PyArrow backend has no
`join_asof`.

## 2. Settled decisions

| subject | decision |
|---|---|
| return contract | Accessors return `pa.Table`. Lazy access is Arrow's own: a `pyarrow.dataset.Dataset` or Scanner, narrowed by `pyarrow.compute` expressions the reader builds. The reader returns no lazy relation and no dataframe API, so Narwhals is not used. |
| DuckDB | Stays the optional `sql` extra. Every answer is reachable through PyArrow; an engine adds speed and laziness, never an answer. |
| transforms | One name each. `attach_clocks`, `on_clock` and `seconds` accept a `pa.Table`, `pa.RecordBatch`, `pa.RecordBatchReader`, Scanner or Dataset; a Table or RecordBatch comes back as its own type and anything else as a `RecordBatchReader`. |
| stored-value constraints | Without `on_clock`, a constraint on `Packet.table` applies to stored values, and the documentation says that across several clocks it compares ticks of different clocks. With `on_clock`, a coordinate constraint applies on the output clock. |
| default clock | `spike_times`, `events`, `intervals` and `units` return ticks on the reference clock; `clock=STORED` returns them as stored. |
| spike routing | Where the output clock is the reference and the packet carries `analysis.spike_events`, `spike_times` reads it. That table omits a spike the mapping cannot place, as the mapped path does. |
| rename | `Dataset` becomes `PacketSet`, `open_dataset` becomes `open_packets`, and the module `dataset` becomes `packet_set`. No alias, since nothing is released. |

## 3. Design

### 3.1 Sources

| call | returns |
|---|---|
| `Packet.scan(rid)` | `pyarrow.dataset.Dataset` |
| `Packet.scanner(rid, *, columns=None, filter=None, **where)` | `pyarrow.dataset.Scanner`; `filter=` is ANDed with `**where` |
| `PacketSet.scan(rid)` | `pyarrow.dataset.Dataset` over every packet holding the resource |
| `PacketSet.scanner(rid, *, columns=None, filter=None, **where)` | `pyarrow.dataset.Scanner` |

`PacketSet.scan` makes each packet's files fragments of one dataset, with `session_key` and
`session_name` as partition fields, so a filter on either skips other packets' files unopened. A
multi-session packet's fragments cannot carry one constant; there `session_key` is projected from
`session_id`, and a filter on it is translated into `session_id` values before the scan.

### 3.2 Predicates

Each returns a `pyarrow.compute.Expression`, usable on any Dataset or Scanner.

- `where(**constraints)` — the public form of `Packet._predicate`: a scalar is equality, a tuple a
  closed range, a list or set membership, `None` no constraint.
- `tick_range(source, resource_id, span, *, clock=None, column=None)` — exactly the rows whose
  coordinate lands in `span` on `clock`, the reference clock by default. For every clock that
  reaches `clock`, the span is inverted and refined against the forward map into the exact stored
  interval, clamped to the clock's reach under the declared bound. Where the table carries its
  clock column the expression is an OR of `(clock_id == c) & t_tick in [a_c, b_c]`; a term for a
  clock the table does not hold matches nothing, so which clocks are present need not be known.
  Where the clock comes through a reference, as `core.spike_events` reaches it through
  `core.units`, each term is `unit_id in (units on c) & t_tick in [a_c, b_c]`. Over a `PacketSet`
  the per-packet expressions are ORed under `session_key`, since a clock ID is unique only within
  its packet. `column` defaults to the table's one coordinate and is required where it has several.
- `tick_bounds(...)` — the same arguments, returning the intervals as a table of `session_key`,
  `clock_id`, `lo` and `hi`, for a predicate written in SQL or Polars.
- `seconds_expression(packet, column="t_tick", *, session_id=None)` — `(t - t_zero) * den / num`
  as float64, for data already on the reference clock, so seconds can be projected inside a scan.

The reader checks a clock's anchors increase as it builds the clock's map, and refuses a range on
a clock whose anchors do not, since the inverse is wrong there.

### 3.3 Transforms

```python
attach_clocks(source, data, resource_id)
on_clock(source, data, clock=None, *, resource_id=None, bound=None)
seconds(source, data, *, resource_id=None, session_id=None)
```

`source` is a `Packet`, or a `PacketSet` with rows dispatched by `session_key`. A stream is mapped
batch by batch; the unit-to-clock lookup `attach_clocks` makes is cached per source rather than
read per batch.

Pushdown happens while the data is a Dataset or Scanner. `on_clock` over stored ticks returns a
single-pass stream that takes no further pushdown, so a caller narrows first; with `tick_range`
exact, a range never has to wait for the mapping. Data already on the reference clock stays a
Dataset through `seconds_expression`.

```python
scanner = packet.scanner(
    "core.events",
    filter=where(stream_id=3) & tick_range(packet, "core.events", (lo, hi)),
)
timed = seconds(packet, on_clock(packet, scanner, resource_id="core.events"))
```

### 3.4 Accessors

`Packet.table` and `PacketSet.table` share `(rid, *, columns=None, on_clock=False, seconds=False,
**where)`. `spike_times`, `events`, `intervals` and `units` each become a scanner, a `tick_range`,
`on_clock` and `seconds`, plus the one step each adds: resolving an event type, attaching a unit's
support, the semi join on composite unit keys. `access._span`, `access._narrowed` and the union in
`stored_span` are removed.

`aligned_spikes`, `assigned_spikes`, the observation windows, `runs.check`, channels, axes and
discriminators are unchanged: each encodes a rule a declaration cannot express.

## 4. Performance

Delaying materialization costs nothing on the eager path: `Packet.table` is already
`scanner(...).to_table()`. Three things could cost, and each is measured in the step adding it.

- `tick_range` on `core.spike_events` evaluates a 6,781-value `isin` per clock on every row in the
  scan, against one `BETWEEN` today, and removes the exact cut after mapping. With spike routing a
  reference-clock range never reaches it. If it is slower, the fallback is the per-clock widened
  interval plus the cut.
- A stream mapped batch by batch forgoes the kernel's threading over one large array. This touches
  stream inputs only.
- Dispatch on the input's type is one check per call.

Each step holds `spike_times` over every unit at 4.7 s and `on_clock` at 2.6 s.

## 5. Verification

- A property test for `tick_range`: random anchors, transforms, chains of up to three hops,
  bounds and spans. The rows it selects on stored ticks must equal the rows whose mapped tick falls
  in the span. Repeated on the real packet for several spans.
- Each rebuilt accessor returns what it returns today, on the test packet.
- Each transform over every input form returns the same rows as over a Table.
- Real-packet timing: `spike_times` over every unit, a 60 s range by both routes, and a range on
  `core.events`, which should now prune row groups.

## 6. Order of work

- [ ] 1. Rename `Dataset` to `PacketSet` and `open_dataset` to `open_packets`; add `filter=` to
  `Packet.scanner`; make `where` public.
- [ ] 2. `tick_range` and `tick_bounds` with the exact inverse, the monotonicity check and the
  property test; remove the union in `stored_span`.
- [ ] 3. `attach_clocks`, `on_clock` and `seconds` over every Arrow form; `seconds_expression`.
- [ ] 4. Rebuild `Packet.table`, `spike_times`, `events`, `intervals` and `units` on these, with
  the reference-clock default and spike routing.
- [ ] 5. `PacketSet.scan`, `PacketSet.scanner` and `PacketSet.table`.
- [ ] 6. The README's lazy-reading section; the inverse and its monotonicity in `design.md`; the
  support tier in `api.rst`; the spike's entry in `bench/results/history.md` corrected per §1.
