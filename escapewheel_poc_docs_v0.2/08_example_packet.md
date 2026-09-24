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
  registries/
    core/             0.6.0.json.gz
    dynamic_foraging/ 0.7.0.json.gz
    aind_unit_qc/     0.5.0.json.gz
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
## 3. Manifest excerpt

```json
{
  "packet_id": "ecephys_786867_2025-09-25",
  "packet_version": "0.1.0",
  "profile_id": "escapewheel-portable-v0.1",
  "semantic_standard_version": "escapewheel-semantic-v0.1",
  "logical_standard_version": "escapewheel-logical-v0.1",
  "registries": {
    "core": { "role": "core", "version": "0.6.0",
              "path": "registries/core/0.6.0.json.gz", "sha256": "…" },
    "dynamic_foraging": { "role": "extension", "version": "0.7.0",
                          "path": "registries/dynamic_foraging/0.7.0.json.gz", "sha256": "…" },
    "aind_unit_qc": { "role": "extension", "version": "0.5.0",
                      "path": "registries/aind_unit_qc/0.5.0.json.gz", "sha256": "…" }
  },
  "sessions": ["ecephys_786867_2025-09-25"],
  "resources": [
    {
      "resource_id": "core.units",
      "declaration_id": "core.units",
      "uri": "tables/core/units.parquet",
      "validation_state": "passed",
      "digest": { "algorithm": "sha256", "value": "c53fd91e…" }
    },
    {
      "resource_id": "core.sniff_detector",
      "declaration_id": "core.array_asset_instances",
      "uri": "arrays/core/sniff_detector.zarr",
      "validation_state": "passed",
      "size_bytes": 3463092,
      "digest": { "algorithm": "sha256", "value": "1dadd742…" }
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
      "validation_state": "passed",
      "digest": { "algorithm": "sha256", "value": "…" },
      "derived_from": ["core.spike_events", "core.clock_anchors", "core.clocks"]
    }
  ],
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

<a id="ew-example-acceptance-checklist" data-spec-anchor="canonical"></a>
## 5. Acceptance checklist

A packet of this shape is conforming when:

1. the manifest validates against the manifest schema;
2. every declared resource exists at its URI, or is declared external;
3. every packet-owned resource records a `digest`, and each holds;
4. Tier 1 and Tier 2 produce no error;
5. every table is in its declared physical order;
6. each bound registry is present, matches its descriptor, and validates on its own terms.
