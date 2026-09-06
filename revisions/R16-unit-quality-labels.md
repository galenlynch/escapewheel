# R16 — Unit Quality Labels

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `02_core_logical_schemas.md`, R11 §3 |
| **Depends on** | R3 §3.0 (multiplicity rule), R11 §3 (the closed vocabulary) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R11 §3 closed `core.units.quality_label` to `sua`, `mua`, and `noise`, and told importers to
map source labels onto it while recording the original in `core.units.metadata`.

That treats unit quality as one assessment with one provenance. It is not. A single sorted
stream carries several, from different tools, which disagree
(`inventory/ecephys_776259_2025-04-09.md` §8.1):

```text
KSLabel          mua 345   good 241
decoder_label    mua 291   noise 149   sua 146      + decoder_probability
default_qc       True 338  False 248
```

They disagree for 111 of 586 units on one probe. A fourth appears in the same pipeline's phy
export — `cluster_group`, phy's canonical curation slot, where manual judgement lands —
carrying `good`/`mua`/`noise`. So one sorting is serialized three ways (SpikeInterface
properties, NWB dynamic columns, phy TSVs) with four label sources under three spellings of
the same three categories. That is not a defect in the data: they are
different judgements by different methods, and a consumer may reasonably prefer any of them.
The available sources also differ between sessions from the same pipeline — one carries
`KSLabel`, another `bombcell_label`.

Nor does anything upstream designate one. The NWB packaging step produces a units table of
55 columns carrying `decoder_label`, `decoder_probability` and `default_qc`, and **no
designated quality column at all** — NWB's conventional slot for one is simply absent. It
also drops `KSLabel` entirely, keeping `ks_unit_id` but not Kilosort's judgement, so a source
is already lost before import begins.

A scalar column forces the packet to pick one and lose the rest to an unqueryable JSON
field, and makes `06`'s `analysis.good_units` rest on a choice the packet does not expose.

R3 §3.0's multiplicity rule already decides the shape: a field whose semantic type is "zero
or more X" is a child table.

## 2. New table: `core.unit_quality_labels`

| Field | Type | Required | Description |
|---|---|:---:|---|
| `session_id` | string | yes | Session ID. |
| `unit_id` | string | yes | Unit ID. |
| `sorting_run_id` | string | yes | Sorting run ID. |
| `curation_id` | string | yes | Curation ID. |
| `source` | string | yes | What produced the label, e.g. `kilosort`, `decoder`, `bombcell`, `manual`. |
| `label` | string | yes | `sua`, `mua`, or `noise`. |
| `confidence` | float64 | no | The source's confidence, where it reports one. |

Primary key: `(session_id, unit_id, sorting_run_id, curation_id, source)`.

References: `(session_id, unit_id, sorting_run_id, curation_id)` -> `core.units`.

Sort: the primary key (R10 §2).

`label` keeps R11 §3's closed vocabulary and its reasoning: the categories recur across
tools, only the spelling varies, and `sua` avoids colliding with
`analysis.good_units.is_good`. The data vindicates the choice — `decoder_label` emits exactly
`sua`/`mua`/`noise`.

`source` is an open vocabulary on R8 §4's terms. Closing it would require knowing every
curation tool a lab may run, which this specification does not. `kilosort`, `decoder`,
`bombcell`, and `phy` are the values observed so far; `phy` denotes `cluster_group`, which is
where manual curation is recorded.

A boolean assessment such as `default_qc` is not a label and does not belong here. It is a
policy applied to labels and metrics, which is `06`'s `analysis.good_units` territory. NWB
carries `default_qc` beside `decoder_label` rather than in place of it, which is the same
distinction.

## 3. `core.units.quality_label` becomes the designated label

The column is retained and joined by one more:

| Field | Type | Required | Description |
|---|---|:---:|---|
| `quality_label` | string | no | The label this packet stands behind, from `core.unit_quality_labels`. |
| `quality_label_source` | string | no | Which `source` it was taken from. |

Both MAY be absent, and absence is the honest state where the source designated nothing —
which, per §1, is what every upstream artifact here does. If either is present, both MUST be,
and the pair MUST appear in `core.unit_quality_labels`:

```sql
-- core.units.designated_label_is_recorded  (error)
SELECT u.session_id, u.unit_id, u.quality_label, u.quality_label_source
FROM core_units u
LEFT JOIN core_unit_quality_labels q
  ON  u.session_id = q.session_id AND u.unit_id = q.unit_id
  AND u.sorting_run_id = q.sorting_run_id AND u.curation_id = q.curation_id
  AND u.quality_label = q.label AND u.quality_label_source = q.source
WHERE u.quality_label IS NOT NULL AND q.source IS NULL
```

```sql
-- core.units.designated_label_pair_complete  (error)
SELECT session_id, unit_id FROM core_units
WHERE (quality_label IS NULL) <> (quality_label_source IS NULL)
```

This satisfies R3 §3.0: the duplication buys join-free access to the one label the packet
stands behind, which the child table alone cannot express, and a rule keeps the two
consistent. Without it a consumer must either join and then guess, or trust an undeclared
convention.

## 4. Consequence for `analysis.good_units`

`06` derives `is_good` from a `quality_policy_id`. With labels attributed, a policy can name
its source — "the decoder's `sua`" rather than "whatever the packet chose" — and two packets
from different pipelines become comparable in a way R11 §3 could not deliver.

R11 §3's claim that closing the vocabulary makes `analysis.good_units` portable holds, and is
strengthened: the label is now portable *and* attributable.

## 5. What stays out of core

**Continuous quality metrics.** `presence_ratio`, `snr`, `isi_violations_ratio`, `d_prime`,
`l_ratio`, `silhouette`, `nn_hit_rate`, the `drift_*` family, and the waveform-shape metrics
are pipeline-specific in both membership and meaning. They belong in a **namespaced
extension** (`09` §5), registered in the packet catalog per `09` §6, with the extension
declaring its own schema and validation rules. A core validator verifies that declared
extension files exist and MUST NOT require their schemas.

This diverges from NWB, which carries roughly forty such metrics as columns of its units
table. The divergence is deliberate. `09`'s metadata-minimalism rule is that core carries
what is needed to interpret, validate, join, filter, or reproduce — not everything a pipeline
computed. A metric set that changes with the sorter version is not a stable core surface, and
promoting one into core later is available on `09` §8's terms if a field proves broadly
necessary.

`core.units.firing_rate_hz` remains the single exception, as `02` already defines it. It is
not a precedent for admitting the rest.

**Boolean gates.** `default_qc` and similar are policies, not labels (§2).

## 6. Table count

24 tables, from R13 §6's 23. `conformance/spec-sweep/tables.py` gains the step.
