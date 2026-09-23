# Part 08 — Example Packet

Informative. Figures are from a real packet built by the reference implementation.

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

```text
packet_root/
  packet.json
  schemas/logical_schemas.json
  extensions/
    dynamic_foraging.json
    aind_unit_qc.json
  tables/
    core/            sessions, subjects, clocks, clock_anchors, electrodes,
                     units, spike_events, unit_quality_labels, …
    analysis/        spike_events.parquet
    dynamic_foraging/ trials, blocks, sessions
    aind_unit_qc/    metrics, waveform_metrics, synchrony
  arrays/
    core/            waveform_mean.zarr/  sniff_detector.zarr/
```

The LFP is referenced rather than copied: ten entries instantiating the dense-array family, with
`external: true` and absolute URIs.

<a id="ew-example-packet-catalog" data-spec-anchor="canonical"></a>
## 3. Catalog excerpt

```json
{
  "packet_id": "ecephys_786867_2025-09-25",
  "packet_version": "0.1.0",
  "profile_id": "escapewheel-portable-v0.1",
  "registry_version": "0.5.0",
  "sessions": ["ecephys_786867_2025-09-25"],
  "resources": [
    {
      "resource_id": "core.units",
      "declaration_id": "core.units",
      "uri": "tables/core/units.parquet",
      "validation_state": "passed",
      "sha256": "c53fd91e…"
    },
    {
      "resource_id": "core.sniff_detector",
      "declaration_id": "core.array_asset_instances",
      "uri": "arrays/core/sniff_detector.zarr",
      "validation_state": "passed",
      "size_bytes": 3463092, "sha256": "1dadd742…"
    },
    {
      "resource_id": "core.46101.lfp",
      "declaration_id": "core.array_asset_instances",
      "uri": "file:///…/recording1",
      "external": true,
      "size_bytes": 402053057,
      "verified_at": "2026-09-04T04:22:45Z"
    },
    {
      "resource_id": "analysis.spike_events",
      "declaration_id": "analysis.spike_events",
      "uri": "tables/analysis/spike_events.parquet",
      "derived_from": ["core.spike_events", "core.clock_anchors", "core.clocks"],
      "processing_run_id": "materialize.analysis.spike_events"
    }
  ],
  "extensions": {
    "dynamic_foraging": { "version": "0.1.0", "registry": "extensions/dynamic_foraging.json" }
  },
  "validation": { "status": "passed", "validated_at": "2026-09-04T04:24:49Z",
                  "validator_name": "escapewheel_validator", "validator_version": "0.1.0" }
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

## 5. Acceptance checklist

A packet of this shape is conforming when:

1. the catalog validates against the manifest schema;
2. every declared resource exists at its URI, or is declared external;
3. every packet-owned resource matches its recorded `sha256`;
4. Tier 1 and Tier 2 produce no error;
5. every table is in its declared physical order;
6. each declared extension registry exists and validates on its own terms.
