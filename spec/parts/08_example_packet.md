# Part 08 — Example Packet

Informative. §1 and the results in §4 are measured on a real packet the reference implementation
built from one AIND session. §§2–3 show a small packet the reference writer builds from the current
registries: the conformance corpus's session, with one resource of each kind. Part 05 §10 defines
when a packet conforms.

<a id="ew-example-packet-shape" data-spec-anchor="canonical"></a>
## 1. Shape

One ecephys session with behaviour, ten probes, and two extensions, as the reference writer built it
on 2026-09-26.

| | |
|---|---|
| resources | 58, 14 of them referenced |
| owned bytes | 605 MB |
| referenced bytes | 14.4 GB, not copied |
| spikes | 131,396,535 |
| units | 4,505 across 10 sorting runs |
| build | 10 min 16 s |

Two files are 97.6% of what the packet owns: `core.spike_events` at 345 MB and `analysis.spike_events` at 246 MB. The first is 2.62 bytes per spike carrying two identifiers, a tick and an amplitude, and the amplitude is a third of it.

<a id="ew-example-packet-layout" data-spec-anchor="canonical"></a>
## 2. Layout

```text
packet_root/
  packet.json
  registries/
    core/             0.16.0.json.gz
    aind_opto/        0.12.0.json.gz
    aind_unit_qc/     0.13.0.json.gz
    dynamic_foraging/ 0.14.0.json.gz
    vr_foraging/      0.13.0.json.gz
  tables/
    core/             sessions, subjects, session_experimenters, devices, probes, electrodes,
                      sorting_run_channels, unit_electrodes, coordinate_frames,
                      coordinate_frame_axes, unit_coordinates, unit_coordinate_values,
                      electrode_coordinates, electrode_coordinate_values, clocks, intervals,
                      event_streams, event_stream_observation_intervals, events, sorting_runs,
                      curation_versions, units, unit_quality_labels, clock_observation_intervals,
                      unit_observation_intervals, spike_events, source_files,
                      processing_run_inputs, array_assets, array_dimensions, array_labels,
                      processing_runs
    analysis/         array_assets, array_dimensions, array_labels, spike_events
    aind_unit_qc/     metrics
    dynamic_foraging/ trials
  arrays/
    core/             waveform_mean.zarr/
    analysis/         unit_rates.zarr/
```

`core.probe0_lfp` appears nowhere in the tree: the packet references its LFP rather than copying
it, with `external: true` and an absolute URI.

<a id="ew-example-packet-catalog" data-spec-anchor="canonical"></a>
## 3. Manifest excerpt

The packet carries 41 resources, 40 of them packet-owned; the excerpt shows one entry of each kind.

```json
{
  "packet_id": "s001",
  "packet_version": "0.1.0",
  "profile_id": "escapewheel-portable-v0.1",
  "semantic_standard_version": "escapewheel-semantic-v0.1",
  "logical_standard_version": "escapewheel-logical-v0.1",
  "registries": {
    "core": {"role": "core", "version": "0.16.0", "path": "registries/core/0.16.0.json.gz", "sha256": "…"},
    "aind_opto": {"role": "extension", "version": "0.12.0", "path": "registries/aind_opto/0.12.0.json.gz", "sha256": "…"},
    "aind_unit_qc": {"role": "extension", "version": "0.13.0", "path": "registries/aind_unit_qc/0.13.0.json.gz", "sha256": "…"},
    "dynamic_foraging": {"role": "extension", "version": "0.14.0", "path": "registries/dynamic_foraging/0.14.0.json.gz", "sha256": "…"},
    "vr_foraging": {"role": "extension", "version": "0.13.0", "path": "registries/vr_foraging/0.13.0.json.gz", "sha256": "…"}
  },
  "created_at": "…",
  "sessions": ["s001"],
  "resources": [
    {
      "resource_id": "core.units",
      "declaration_id": "core.units",
      "uri": "tables/core/units.parquet",
      "validation_state": "passed",
      "digest": {"algorithm": "sha256", "value": "…"}
    },
    {
      "resource_id": "core.waveform_mean",
      "declaration_id": "core.array_asset_instances",
      "uri": "arrays/core/waveform_mean.zarr",
      "validation_state": "passed",
      "size_bytes": 948,
      "digest": {"algorithm": "sha256", "value": "…"}
    },
    {
      "resource_id": "analysis.unit_rates",
      "declaration_id": "analysis.array_asset_instances",
      "uri": "arrays/analysis/unit_rates.zarr",
      "validation_state": "passed",
      "size_bytes": 814,
      "digest": {"algorithm": "sha256", "value": "…"},
      "derived_from": ["core.spike_events", "core.units"]
    },
    {
      "resource_id": "core.probe0_lfp",
      "declaration_id": "core.array_asset_instances",
      "uri": "s3://example-bucket/s001/probe0_lfp.zarr",
      "validation_state": "passed",
      "external": true,
      "size_bytes": 402053057,
      "verified_at": "2026-08-20T16:00:00Z"
    },
    {
      "resource_id": "analysis.spike_events",
      "declaration_id": "analysis.spike_events",
      "uri": "tables/analysis/spike_events.parquet",
      "validation_state": "passed",
      "digest": {"algorithm": "sha256", "value": "…"},
      "derived_from": ["core.spike_events", "core.clocks"]
    }
  ],
  "retention": {"keep_versions": 1},
  "validation": {"status": "passed", "validated_at": "…", "validator_name": "escapewheel_validator", "validator_version": "0.1.0"}
}
```

<a id="ew-example-queries" data-spec-anchor="canonical"></a>
## 4. Queries

Resource identifiers are dotted; a SQL engine registers them with underscores.

Units by quality, joined across core and an extension:

```sql
SELECT q.normalized_label, count(*) AS units,
       round(avg(m.isi_violations_ratio), 3) AS isi
FROM core_units u
JOIN aind_unit_qc_metrics m USING (unit_id)
JOIN core_unit_quality_labels q USING (unit_id)
WHERE q.source = 'decoder'
GROUP BY 1 ORDER BY units DESC;
```

On the packet of §1:

| normalized_label | units | isi |
|---|---|---|
| sua | 1,446 | 1.04 |
| mua | 1,923 | 37.25 |
| noise | 953 | 33.29 |

A population time window, which is what `analysis.spike_events` exists for:

```sql
SELECT count(*) FROM analysis_spike_events
WHERE t_tick BETWEEN ? AND ?;
```
