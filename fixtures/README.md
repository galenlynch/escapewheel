# Phase 0 fixtures

A conforming single-session packet per [R1 §6](../revisions/R1-single-session-primary.md),
and twenty-five variants each violating exactly one rule. Together they are the conformance
corpus: expected findings recorded as data, so any implementation can be checked against
the same evidence rather than against a prose description of what should happen.

```bash
uv run --with pyarrow python build.py                            # writes packets/
uv run --no-cache --with ../escapewheel-validator --with duckdb python corpus.py  # run them all
```

`--no-cache` matters: uv caches the built wheel of the sibling package, and without it a
run can silently test a stale copy of the validator rather than the working tree.

The validator under test is `escapewheel_validator`. Nothing is reimplemented here —
a second copy of the checks would be exactly the drift this corpus exists to detect. To
validate one packet directly:

```bash
uv run --with '../escapewheel-validator' --with duckdb escapewheel validate packets/valid
```

## The valid packet

30 of the registry's 43 tables, 142 rows. One session, one subject, two clocks with a
declared transform between them, one probe with four electrodes, two trials, four events,
one sorting run, one curation version, two units and their spikes, and provenance.

The five absent tables are arrays (Phase 5) and media (in no phase of Part 07). A packet need
not carry every table; `validate.py` checks what the manifest declares.

The packet carries one extension, `dynamic_foraging`, holding the two rows its `trials` table
contributes. Not decoration: R54 §2.4a makes an `interval_kind` naming a resource the packet does
not declare an error, and no core table specialises an interval, so a packet with intervals in it
carries an extension by construction.

`corpus.py`'s `EXPECTED` is the full list; the table below names the variants that have a prose
description, and is not all of them.

## The corpus

| Packet | Violates | Caught by |
|---|---|---|
| `dup_pk` | duplicate interval key | `core.intervals.primary_key_unique` |
| `orphan_fk` | an interval names an absent clock | `core.intervals.clock_id_resolves` |
| `null_required` | null in a required column | `core.events.event_type.not_null` |
| `bad_vocabulary` | `quality_label` is `good` | `core.units.quality_label.in_vocabulary` |
| `inconsistent_projection` | one `(source, label)` pair projects two ways | `core.unit_quality_labels.projection_is_consistent` |
| `stream_clock_mismatch` | an event's clock disagrees with its stream's | `core.events.clock_matches_stream` |
| `bad_interval` | `stop_tick` before `start_tick` | `core.intervals.interval_valid` |
| `stale_summary` | `n_spikes` disagrees with the spikes | `core.units.spike_summary_consistent` |
| `missing_amplitude_unit` | amplitudes with no declared unit | `core.sorting_runs.amplitude_unit_declared` |
| `half_transform` | slope without offset | `core.clocks.transform_pair_complete` |
| `unsorted_spikes` | rows out of declared sort order | `core.spike_events.physical_order` (warning) |
| `orphan_manifest_session` | manifest disagrees with `core.sessions` | `core.sessions.manifest_sessions_match` |
| `bad_type` | `start_tick` written as int32 | `schema.column_type` |
| `missing_column` | required column absent from the file | `schema.column_absent` |

`bad_vocabulary` uses `good` deliberately: it is Phy's label for a single unit, and the
one an importer most plausibly forgets to map to `sua` (R11 §3).

`unsorted_spikes` is a warning, not an error — ordering is a performance property, and a
packet in the wrong order is conforming, only slower (R10 §2).

## Validation layers

Four, in the validator's own order — what each owes is Part 05 §5's:

1. **Manifest shape** against `manifest.schema.json`, when the packet is opened.
2. **The embedded registry** against the meta-schema, and its version against the manifest's.
3. **Physical schema** per resource — column presence and Parquet type.
4. **Rules** — Tier 1 generated from structure, Tier 2 carried in the registry.

Physical sort order is checked between 3 and 4, by reading each file in written order.
**It is not a SQL rule and cannot be**: a query has no access to physical row order. That
was found here, building this fixture, and corrects R2 §7.1 and R5 §7 — see R12.
