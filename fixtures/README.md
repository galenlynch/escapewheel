# Phase 0 fixtures

A conforming single-session packet per [R1 §6](../revisions/accepted/R1-single-session-primary.md),
four more conforming packets that record Part 04 §4.3's other digests, thirty-seven variants
each violating exactly one rule, and two conforming packets that each draw a per-resource `info`
finding. Together they are the conformance
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
| `non_ucum_unit` | `amplitude_unit` is `microvolts`, not a UCUM code | `core.units.amplitude_unit.ucum_code` |
| `half_transform` | slope without offset | `core.clocks.transform_pair_complete` |
| `unsorted_spikes` | rows out of declared sort order | `core.spike_events.physical_order` (warning) |
| `orphan_manifest_session` | manifest disagrees with `core.sessions` | `core.sessions.manifest_sessions_match` |
| `bad_type` | `start_tick` written as int32 | `schema.column_type` |
| `extension_bad_type` | the extension's `trial_id` written as float64 | `schema.column_type`, filed under `dynamic_foraging`, which fails while core passes |
| `missing_column` | required column absent from the file | `schema.column_absent` |
| `owned_without_digest` | a packet-owned resource records no `digest` | `packet.resource.digest_missing` |
| `crc64nvme_one_byte_off`, `crc32c_one_byte_off`, `crc32_one_byte_off` | a recorded CRC is of the file with one byte flipped | `owned.digest`, with checksums |
| `crc_prefix_disagrees` | an external prefix's CRC32C member digest differs from the one its listing value covers | `packet.resource.member_digest` |
| `member_digest_partial` | a member lacks `digest` beside an entry's | `packet.manifest.schema` |
| `member_digest_width` | a CRC32C-width member digest under a CRC64NVME entry | `packet.manifest.schema` |
| `outside_table_floor` | `core.intervals` written as Parquet format 1.0, whose dictionary pages are `PLAIN_DICTIONARY` | `physical.outside_reader_floor` (warning) |

`crc64nvme`, `crc32c`, and `crc32` record every owned resource's digest under that algorithm, and
`crc_prefix` adds an external prefix whose value is the SHA-256 of its CRC32C member listing; all
four are clean. `build.py` computes each CRC bit by bit from its polynomial rather than through
the validator, and `corpus.py` runs `valid` and the CRC packets with checksums.

`outside_array_floor` carries three packet-owned arrays with the reference writer's default,
sharded, and delta-filtered pipelines; only the delta one is outside the v3 reader floor, so
`physical.outside_reader_floor` fires once, at `info`. `unresolved_externals` references two
external arrays and draws one `external.physical_unassessed` per array. Both packets conform,
and `corpus.py` checks the count; `valid` must draw neither finding (Part 05 §5.3). Each array is
a `zarr.json` with no chunk written, so no Zarr library is needed to build the corpus.

`bad_vocabulary` uses `good` deliberately: it is Phy's label for a single unit, and the
one an importer most plausibly forgets to map to `sua` (R11 §3).

`unsorted_spikes` is a warning, not an error — ordering is a performance property, and a
packet in the wrong order is conforming, only slower (R10 §2).

## Validation layers

Four, in the validator's own order — what each owes is Part 05 §5's:

1. **Manifest conformance** under Part 04 §10: its shape against `manifest.schema.json`, then
   the checks that need only the manifest.
2. **Each bound registry**, acquired through its descriptor, digest-checked, checked against the
   meta-schema, and compared with its descriptor.
3. **Physical schema** per resource — column presence and Parquet type, and each footer's
   compressions and encodings against the Parquet floor.
4. **Rules** — Tier 1 generated from structure, Tier 2 carried in the registry.

Physical sort order is checked between 3 and 4, by reading each file in written order.
**It is not a SQL rule and cannot be**: a query has no access to physical row order. That
was found here, building this fixture, and corrects R2 §7.1 and R5 §7 — see R12.
