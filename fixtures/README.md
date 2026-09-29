# Phase 0 fixtures

A conforming single-session packet per [R1 §6](../revisions/accepted/R1-single-session-primary.md),
four more conforming packets that record Part 04 §4.3's other digests, fifty-seven variants
each violating exactly one rule, two conforming packets that each draw a per-resource `info`
finding, two conforming packets that carry no extracellular data, four conforming packets that
each own an opaque payload, two conforming packets whose payload names draw warnings, one conforming
packet whose origin is the earliest start only once a transform carries it, one conforming
packet whose unit coordinate omits an axis its frame declares, and one conforming packet whose
labelled array pads a unit's channels.
Together they are the conformance corpus: expected findings recorded as data, so any
implementation can be checked against the same evidence rather than against a prose description
of what should happen.

```bash
uv run --project ../escapewheel-writer python build.py   # rewrites packets/ from scratch
uv run --project ../escapewheel-writer python corpus.py  # run them all
```

The writer's environment installs the reader and validator from their sibling directories as
editable packages, so both commands run against the working tree, as `verify.py` does.

The validator under test is `escapewheel_validator`. Nothing is reimplemented here —
a second copy of the checks would be exactly the drift this corpus exists to detect. To
validate one packet directly:

```bash
uv run --project ../escapewheel-validator escapewheel validate packets/valid
```

## The valid packet

30 of the registry's 45 tables, 142 rows. One session, one subject, two clocks with a
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
| `bad_interval` | `stop_tick` before `start_tick` | `core.intervals.interval_valid` |
| `stale_summary` | `n_spikes` disagrees with the spikes | `core.units.spike_summary_consistent` |
| `missing_amplitude_unit` | amplitudes with no declared unit | `core.sorting_runs.amplitude_unit_declared` |
| `non_ucum_unit` | `amplitude_unit` is `microvolts`, not a UCUM code | `core.units.amplitude_unit.ucum_code` |
| `half_transform` | slope without offset | `core.clocks.transform_pair_complete` |
| `non_finite_rate` | a clock's `tick_rate_hz` is NaN | `core.clocks.tick_rate_hz.finite` |
| `negative_slope` | a child clock's `transform_slope` is -1 | `core.clocks.transform_slope_positive` |
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
| `owned_opaque_one_byte_off` | a packet-owned opaque file's recorded SHA-256 is of other bytes | `owned.digest`, with checksums |
| `uri_raw_space`, `uri_lowercase_hex`, `uri_encoded_unreserved`, `uri_dot_segment` | a `uri` outside Part 03 §4's one form: a raw space, `%c3%a9`, `%41`, a `..` segment | `packet.resource.uri_form` |
| `origin_not_earliest` | `t_zero_tick` is the reference's own start, not the earlier one the behavior clock's transform gives | `time.origin_not_earliest` |
| `origin_unmappable` | the behavior clock's start lies twenty intervals before its first anchor | `time.origin_unmappable` |
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
a `zarr.json` with no chunk written, so no Zarr library is needed to build the corpus. Every axis
of these five arrays is only an order, which Part 03 §6.3 declares in the numeric form.

`padded_labels` adds `core.waveform_mean`, a packet-owned array of two units by four channels by
three samples. Its unit axis is labelled with `core.units`, and its channel axis with
`core.electrodes` and depends on the unit axis; the second unit has two contacts, so its last two
channel positions are rows with a null label (Part 03 §6.3). It is clean. Twelve variants each break
one rule of it, and each draws one error: `axis_without_form` and `axis_with_two_forms` break the
sample axis's form; `label_naming_no_row` names `elec_009`; `label_on_unlabelled_axis` puts a label
row on the sample axis; `label_missing` drops a padding row; `chained_dependency` has the unit axis
depend on the sample axis; `independent_label_off_zero` adds a unit label at
`depends_on_position_index` 1; `one_row_two_positions` names one contact twice under one unit;
`label_beyond_axis` adds a channel label at `position_index` 4, one past the axis's end;
`dependent_axis_unlabelled` has the sample axis depend on the unit axis without labels;
`label_outside_core` labels the unit axis with `analysis.array_assets`, every label null; and
`array_without_dimension_names` writes the array without `dimension_names` (Part 03 §6.5).

Eleven packets exercise how Part 02 §12.9 numbers intervals. `two_kinds_one_label` adds a tone of
the fixture-local extension `cue`, labelled `"1"` as the first trial is, and numbers it first,
since `cue.tones` sorts before `dynamic_foraging.trials`; `kinds_out_of_unicode_order` numbers it
after the trials; `equal_bounds` gives the two trials one pair of bounds, and `equal_bounds_swapped`
numbers them the other way round; and `trial_labelled_axis` labels `padded_labels`' unit axis with
the two trials. All five are clean. `trials_numbered_from_one`, `trials_misordered`,
`interval_numbering_gap`, and `trials_numbered_by_tick`, which moves the second trial onto the probe
clock at ticks below the first trial's and numbers it first, each draw
`core.intervals.numbered_in_order`. `repeated_interval_label` labels both trials `"1"` and draws
`core.intervals.label_unique_within_kind`, and `orphan_trial` adds a trial naming no interval and
draws `dynamic_foraging.trials.trial_id_resolves`, filed under `dynamic_foraging`, which fails
while core passes.

Four packets each add one packet-owned opaque payload at `opaque/<resource_id>/<name>` (Part 03
§11), and are clean with checksums: `owned_opaque_object` a single file, `owned_opaque_prefix` a
directory digested as a prefix, `owned_opaque_singleton` a file bound to an opaque singleton of
the fixture-local extension `qc_documents`, since core declares none, and
`owned_opaque_encoded_name` the file `QC report é.pdf` at the `uri`
`opaque/core.qc_report/QC%20report%20%C3%A9.pdf`. Core's payloads are catalog-family instances
with no `core.media_assets` row, so catalog binding is not exercised.

`opaque_name_portability` holds `é.png` in NFC, `É.png` in NFD, and `12:00:00.png`, and
`listing_key_spelling` holds files named `"`, `\`, a newline, U+007F, `é`, and `more/` followed by U+1F600 under
CRC32C. Each passes with checksums while drawing `physical.opaque_name_portability` at `warning`,
two and three times, which `corpus.py` counts (Part 05 §5.3). `build.py` checks the second's
listing against its bytes written out by hand, so its digest holds only for a validator writing
keys as Part 04 §4.3's raw UTF-8, and `corpus.py` requires that it draw no `owned.digest`.

`no_extracellular` is `valid` without its fourteen core tables specific to extracellular
electrophysiology, and `sessions_only` keeps only `core.sessions` and `core.subjects`, its session
naming no reference clock. Both are clean, since the packet mechanism confines no packet to a
recording modality ([Part 00 §1](../escapewheel_poc_docs_v0.2/00_architecture.md#ew-architecture-scope)).
`one_clock` is `no_extracellular` reduced to its behavior clock, with no reference clock named, and
is clean because a session must name its reference only where it declares more than one clock
([Part 01 §3.3](../escapewheel_poc_docs_v0.2/01_semantic_standard.md#ew-session-concept)).

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
