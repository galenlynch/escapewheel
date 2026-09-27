# Part 08 — Example Packet

Informative. §1 and the results in §4 are measured on a real packet the reference implementation
built from one AIND session. §§2–3 show a small packet the reference writer builds from the current
registries: the conformance corpus's session, with one resource of each kind.

## 1. Shape

One ecephys session with behaviour, ten probes, and two extensions.

| | |
|---|---|
| resources | 42 |
| owned bytes | 482 MB |
| referenced bytes | 4.25 GB, not copied |
| spikes | 131,396,535 |
| units | 4,505 across 10 sorting runs |
| build | 2 min 9 s |

Two files are 99.3% of what the packet owns: `core.spike_events` at 232 MB and `analysis.spike_events` at 247 MB, which is 1.76 bytes per spike while carrying four identifiers, a tick, and a clock per row.

<a id="ew-example-packet-layout" data-spec-anchor="canonical"></a>
## 2. Layout

<!-- BEGIN GENERATED EXAMPLE PACKET: layout -->
```text
packet_root/
  packet.json
  registries/
    core/             0.8.0.json.gz
    aind_opto/        0.8.0.json.gz
    aind_unit_qc/     0.9.0.json.gz
    dynamic_foraging/ 0.9.0.json.gz
    vr_foraging/      0.8.0.json.gz
  tables/
    core/             sessions, subjects, session_experimenters, devices, probes, electrodes,
                      sorting_run_channels, unit_electrodes, coordinate_frames,
                      coordinate_frame_axes, unit_coordinates, unit_coordinate_values,
                      electrode_coordinates, electrode_coordinate_values, clocks, intervals,
                      event_streams, event_stream_observation_intervals, events, sorting_runs,
                      curation_versions, units, unit_quality_labels, clock_observation_intervals,
                      unit_observation_intervals, spike_events, source_files,
                      processing_run_inputs, array_assets, array_dimensions, processing_runs
    analysis/         array_assets, array_dimensions, spike_events
    aind_unit_qc/     metrics
    dynamic_foraging/ trials
  arrays/
    core/             waveform_mean.zarr/
    analysis/         unit_rates.zarr/
```
<!-- END GENERATED EXAMPLE PACKET: layout -->

`core.probe0_lfp` appears nowhere in the tree: the packet references its LFP rather than copying
it, with `external: true` and an absolute URI.

<a id="ew-example-packet-catalog" data-spec-anchor="canonical"></a>
## 3. Manifest excerpt

<!-- BEGIN GENERATED EXAMPLE PACKET: manifest -->
The packet carries 39 resources, 38 of them packet-owned; the excerpt shows one entry of each kind.

```json
{
  "packet_id": "s001",
  "packet_version": "0.1.0",
  "profile_id": "escapewheel-portable-v0.1",
  "semantic_standard_version": "escapewheel-semantic-v0.1",
  "logical_standard_version": "escapewheel-logical-v0.1",
  "registries": {
    "core": {"role": "core", "version": "0.8.0", "path": "registries/core/0.8.0.json.gz", "sha256": "…"},
    "aind_opto": {"role": "extension", "version": "0.8.0", "path": "registries/aind_opto/0.8.0.json.gz", "sha256": "…"},
    "aind_unit_qc": {"role": "extension", "version": "0.9.0", "path": "registries/aind_unit_qc/0.9.0.json.gz", "sha256": "…"},
    "dynamic_foraging": {"role": "extension", "version": "0.9.0", "path": "registries/dynamic_foraging/0.9.0.json.gz", "sha256": "…"},
    "vr_foraging": {"role": "extension", "version": "0.8.0", "path": "registries/vr_foraging/0.8.0.json.gz", "sha256": "…"}
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
      "size_bytes": 880,
      "digest": {"algorithm": "sha256", "value": "…"}
    },
    {
      "resource_id": "analysis.unit_rates",
      "declaration_id": "analysis.array_asset_instances",
      "uri": "arrays/analysis/unit_rates.zarr",
      "validation_state": "passed",
      "size_bytes": 759,
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
<!-- END GENERATED EXAMPLE PACKET: manifest -->

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

<a id="ew-example-acceptance-checklist" data-spec-anchor="canonical"></a>
## 5. Acceptance checklist

A packet of this shape is conforming when:

1. the manifest validates against the manifest schema;
2. every declared resource exists at its URI, or is declared external;
3. every packet-owned resource records a `digest`, and each holds;
4. Tier 1 and Tier 2 produce no error;
5. every table is in its declared physical order;
6. each bound registry is present, matches its descriptor, and validates on its own terms.
