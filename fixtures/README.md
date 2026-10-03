# Phase 0 fixtures

A conforming single-session packet per [R1 §6](../revisions/accepted/R1-single-session-primary.md),
four more conforming packets that record Part 04 §4.3's other digests, fifty-eight variants
each violating exactly one rule, two conforming packets whose names differ only in case or
normalization form, two conforming packets that each draw a per-resource `info`
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

`corpus_packets/` declares the packets, and its `PACKETS` is the full list: one record per packet,
carrying how it is written and what a validator must report of it. `build.py` writes each record's
packet and `corpus.py` judges each against its record. `corpus.py`'s `EXPECTED` restates each
packet's finding as a literal for the tools that read that file without importing it, and
`corpus.py` judges nothing while the two disagree. The table below names the variants that have a
prose description, and is not all of them.

| Module of `corpus_packets/` | Holds |
|---|---|
| `record.py` | the record that declares a packet |
| `registry.py`, `numbering.py`, `writing.py` | what writes a packet: the registries it binds, the numbers its names take, and its files, digests and manifest |
| `session.py` | the valid session's rows, and the build of a packet from them once edited |
| `arrays.py` | the Zarr arrays some packets add |
| every other module | one subject's packets, with the functions that build them |

## The corpus

| Packet | Violates | Caught by |
|---|---|---|
| `dup_pk` | duplicate interval key | `core.intervals.primary_key_unique` |
| `shared_name` | two intervals under different keys carry one `interval_name` | `core.intervals.interval_name.unique`, and not `primary_key_unique` |
| `names_differ_in_case` | two `interval_name`s differ only in case | nothing: names compare as scalar sequences, unfolded |
| `names_differ_in_form` | two `interval_name`s differ only in Unicode normalization form | nothing, for the same reason |
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
| `undeclared_column` | an all-null column `core.intervals` does not declare | `schema.column_undeclared` |
| `extension_undeclared_column` | the same column added to the extension's table | `schema.column_undeclared`, filed under `dynamic_foraging` |
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

Four packets exercise Part 02 §8.3's specialising references, where `cue.tones` and
`dynamic_foraging.trials` each declare one naming `core.intervals.interval_kind`. Built on
`two_kinds_one_label`, `trial_names_a_tone` adds a trial row on the tone's interval and draws
`dynamic_foraging.trials.trial_id.names_a_row_of_its_kind` under `dynamic_foraging`, and
`tone_names_a_trial` adds a tone row on the first trial's interval and draws
`cue.tones.tone_id.names_a_row_of_its_kind` under `cue`; the reverse check passes both, since every
interval keeps a row of its own kind. `tone_in_place_of_its_own` moves the tone row onto the first
trial's interval and draws that check and `core.intervals.interval_kind.cue_tones_is_specialised`.
`interval_of_a_session` adds an interval whose kind is `core.sessions`, which declares no
specialising reference, and draws `core.intervals.interval_kind.core_sessions_is_specialised`.

Three packets bind the fixture-local extension `rig`, whose `rig.neuropixels` is a detail table of
`core.devices.device_kind`, a discriminator resolving `optional`, and hold one row for the probe.
`device_detail` names `rig.neuropixels` as the probe's `device_kind` and is clean;
`device_detail_unkinded` leaves it null and `device_detail_other_kind` names `core.probes`, and
each draws `rig.neuropixels.device_id.names_a_row_of_its_kind` under `rig`.

Six packets exercise how Part 02 §12.1 numbers units, whose two units, both in one curation, are
labelled `"17"` and `"42"`. `unit_labels_by_length` relabels them `"7"` and `"007"`, and numbers them
in that order, which is length order; `null_unit_labels` leaves both labels null, and
`null_unit_labels_swapped` numbers the two the other way round; and `later_run_numbered_first` moves
the second unit into a second sorting run's curation and numbers it first. All four are clean.
`units_numbered_by_scalar` relabels them `"10"` and `"2"` in scalar-value order, and
`units_numbered_from_one` numbers them 1 and 2; each draws `core.units.numbered_in_order`.

Ten packets are amendments (Part 05 §15). `build.py` writes each as version 0.1.0, or 1.0.0 for a
replacement, and then at the next patch version over it. Every table whose bytes change is written
at a new `uri`, the superseded manifest's bytes are kept under `manifests/`, and a held name keeps
its number while a new one is numbered after every number the packet holds. Each amendment records
a second import of the session, with both imports scoped to it. Four amendments are clean:

- `amended_intervals` adds 120 `cue.tones` intervals, whose kind sorts before the trials.
- `amended_curation` adds a second curation of the sorting run, with its units, spikes, contacts,
  observation windows and quality labels, and prefers its curation run.
- `amended_preference` replaces the preference for the later curation with one for the earlier.
- `amended_replacement` amends a packet at 1.0.0 that replaces version 0.1.0 of its own
  `packet_id`, keeping the major version and `replaces`.

The rest each break one rule of adding:

- `amended_trial` adds a third trial to the session's trials and draws `amendment.group_grown`.
- `amended_unit_window` adds an observation window for a held unit and draws
  `amendment.group_grown`.
- `amended_trial_bounds` moves the first trial's end and draws `amendment.row_changed`.
- `amended_packet_id` changes `packet_id` and draws `amendment.identity_changed`.
- `amended_replacement_unlinked` drops `amended_replacement`'s `replaces`, and
  `amended_replacement_major` moves it to 2.0.0; each draws `amendment.identity_changed`.

Five packets are `valid` with a `replaces` (Part 04 §3), whose item names a version by a digest of
no real manifest, since a validator given no named packet does not check it. `replaces_own_packet`
is at 1.0.0 naming version 0.1.0 of its own `packet_id`, and `replaces_another_packet` is at 0.1.0
naming version 3.0.0 of another; both are clean. `replaces_same_major` is at 0.1.0 naming version
0.1.0 of itself and draws `packet.replaces.major_version`. `replaces_item_with_location` gives its
item a `uri`, and `replaces_item_without_digest` omits `sha256`; each draws `packet.manifest.schema`.

`two_imports` is `valid` with two imports of the one session, which are not alternatives, and is
clean. `preference_of_another_scope` prefers, for the sorting run, a curation run whose scope is the
probe, and draws `core.preferred_runs.scope_matches_run` (Part 05 §12).

Three packets add `valid`'s 42 spikes as `analysis.spike_events` (Part 06 §4).
`spikes_on_reference_clock` puts them on the session's reference clock, `imec_ap_s001`, and is
clean. `spikes_off_reference_clock` puts them on `behavior_s001`, and
`spikes_without_reference_clock` puts them on the only clock of a session declaring no reference
clock; each draws `analysis.spike_events.on_reference_clock` and nothing else.

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

Twelve packets list sidecars (Part 02 §12.10), each an instance of `core.sidecar_instances` bound to
its `core.sidecars` row by `resource_id`. `sidecars` lists three: `core.readme`, a packet-owned
file with a null type and media type and no scope; `core.viewer_state`, a packet-owned directory
of media type `application/json`, scoped to the subject; and `core.surgery_protocol`, a referenced
resource whose type and media type no list holds, scoped to two sessions and to a row of the
fixture-local extension `lab_records`, whose `lab_records.surgeries` is keyed by one string column.
It adds a second session, `s002`, for that scope. `sidecars_without_scopes` carries no
`core.sidecar_scopes`. Both are clean with checksums. Ten variants each draw one error:

| Packet | Violates | Caught by |
|---|---|---|
| `sidecar_row_unbound` | a `core.sidecars` row no entry binds | `packet.resource.catalog_row_binding` |
| `sidecar_entry_unbound` | a sidecar entry no row binds | `packet.resource.catalog_row_binding` |
| `sidecar_listed_twice` | two rows of one `resource_id` | `core.sidecars.primary_key_unique` |
| `sidecar_scope_unlisted` | a scope of a `resource_id` no sidecar row holds | `core.sidecar_scopes.resource_id_resolves` |
| `sidecar_scope_undeclared_table` | a scope naming a table no bound registry declares | `core.sidecar_scopes.scope_kind.kind_declared` |
| `sidecar_scope_uncarried_table` | a scope naming `core.probes` in `no_extracellular` | `core.sidecar_scopes.scope_kind.kind_declared` |
| `sidecar_scope_composite_key` | a scope naming `core.coordinate_frames`, keyed by two columns | `core.sidecar_scopes.scope_kind.key_fits_paired_value` |
| `sidecar_scope_absent_row` | a scope naming subject `m999` | `core.sidecar_scopes.scope_kind.core_subjects_resolves` |
| `sidecar_scope_null` | a null `scope` | `core.sidecar_scopes.scope.not_null` |
| `sidecar_with_lineage` | a sidecar entry carrying `derived_from` | `packet.resource.derived_from_forbidden` |

`no_extracellular` is `valid` without its fourteen core tables specific to extracellular
electrophysiology, and `sessions_only` keeps only `core.sessions` and `core.subjects`, its session
naming no reference clock. Both are clean, since the packet mechanism confines no packet to a
recording modality ([Part 00 §1](../spec/parts/00_architecture.md#ew-architecture-scope)).
`one_clock` is `no_extracellular` reduced to its behavior clock, with no reference clock named, and
is clean because a session must name its reference only where it declares more than one clock
([Part 01 §3.3](../spec/parts/01_semantic_standard.md#ew-session-concept)).

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

## The suites' shared fixtures

`shared/packet_fixture.py` is not part of the corpus. It writes the small packet the reader's and
the validator's unit suites each build in a temporary directory, and it lives here so that
neither package's tests import the other's. `core_registry` cuts the core registry down to the
resources and columns a suite names, keeping each as core declares it, and `write_packet` writes
the rows for them. A suite states its columns in its own `tests/conftest.py`.

`shared/nwbfixture.py` writes the miniature NWB-Zarr file the writer's and aind's suites read, and
the helpers that write a Zarr v2 group or array. It holds what core NWB declares; aind's
`tests/nwbfixture.py` adds its producer's columns over that file with the same helpers.
`shared/adapter_columns.py` lists the columns an adapter hands a build and which of them no
registry in the tree declares, and each of those two suites runs its own adapters through it.

Each of the four suites reaches `shared/` through `pythonpath` in its pytest configuration, so a
suite runs from a checkout of the monorepo and not from its package alone.
