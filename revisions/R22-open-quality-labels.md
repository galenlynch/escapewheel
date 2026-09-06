# R22 — Open Quality Labels with a Normalized Projection

| | |
|---|---|
| **Status** | **Accepted** 2026-08-27 |
| **Amends** | R11 §3, R16 §2, R16 §3 |
| **Depends on** | R16 (attributed quality labels) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R11 §3 closed `quality_label` to three values and requires a validator to reject anything
else. R16 §2 carried that closure onto `core.unit_quality_labels.label`, reasoning that "the
categories recur across tools, only the spelling varies", and cited `decoder_label` emitting
exactly `sua`/`mua`/`noise` as vindication.

One source is not the population. Measured over 6781 units in
`inventory/nwb-zarr-776259-2025-04-09.md` §4:

| Column | Values |
|---|---|
| `bombcell_label` | mua 3711, noise 1508, **good** 1077, **non_soma** 485 |
| `decoder_label` | mua 2635, noise 2444, sua 1702 |
| `unitrefine_label` | mua 2635, noise 2444, sua 1702 |
| `default_qc` | False 3445, True 3336 |

`unitrefine_label` is identical to `decoder_label` for all 6781 units — two names for one
classifier, so three sources, not four. `bombcell_label` and `decoder_label` agree on
**53.3%**.

Bombcell emits `good` and `non_soma` on 1562 units, 23% of the sorting. Neither is a spelling
variant of anything in the closed set. `non_soma` in particular is not a quality judgement at
all — it is a claim about what the waveform came from, and mapping it to `noise` asserts
something the classifier did not.

R16 §2's reasoning was right about the *shape* of the problem — quality is many attributed
labels — and wrong about the vocabulary. A conforming packet currently cannot carry real
curation output without discarding a source's distinctions to fit.

Aggregating over scorers and closing the label are not compatible goals.

## 2. What the closure was buying

Two things worth keeping:

1. **A validator catches typos.** `mau` for `mua` is a real error a closed set finds.
2. **A query is portable.** "Give me the good units" answerable across packets from different
   pipelines is most of why `core.units.quality_label` exists at all.

Reopening the vocabulary outright loses both. So the label opens and the projection is added
beside it, rather than the closure simply being struck.

## 3. Rule

`core.unit_quality_labels` gains one column:

| Field | Type | Required | Description |
|---|---|:---:|---|
| `source` | string | yes | What produced the label. Open (R8 §4). |
| `label` | string | yes | **The source's own label, verbatim. Open.** |
| `normalized_label` | string | no | `sua`, `mua`, or `noise`. Closed. Null where the source's label does not project. |
| `confidence` | float64 | no | The source's confidence, where it reports one. |

`label` MUST be recorded as the source emitted it. A writer MUST NOT rewrite `good` to `sua`
in this column; that is what `normalized_label` is for.

`normalized_label` is a **declared projection, not an inference**. A validator MUST reject
values outside `sua`/`mua`/`noise` (R11 §3's rule, now scoped to this column). Where a
source's label has no honest projection — `non_soma` — it MUST be null rather than forced.

The projection observed for the sources above:

| `source` | `label` | `normalized_label` |
|---|---|---|
| `decoder`, `unitrefine` | `sua`, `mua`, `noise` | itself |
| `bombcell` | `good` | `sua` |
| `bombcell` | `mua`, `noise` | itself |
| `bombcell` | `non_soma` | *null* |

This table is illustrative, not normative: a packet declares its own projection in the data.

## 4. The projection must be a function

Within a packet, one `(source, label)` pair MUST project to one `normalized_label`. A source
that called `good` a `sua` in one row and a `mua` in another has not declared a projection;
it has made two unrelated claims.

```sql
-- core.unit_quality_labels.projection_is_consistent  (error)
SELECT source, label, COUNT(DISTINCT COALESCE(normalized_label, '')) AS distinct_projections
FROM core_unit_quality_labels
GROUP BY source, label
HAVING COUNT(DISTINCT COALESCE(normalized_label, '')) > 1
```

The `COALESCE` is load-bearing: a `(source, label)` pair that projects for some rows and is
null for others is inconsistent in the same way as one projecting two different values, and
that is exactly the silent data-loss this revision exists to prevent.

What this does **not** catch is a source emitting a label it never emits — bombcell producing
a `sua`. The global closed vocabulary did not catch that either, and catching it would need a
declared per-source vocabulary, which this revision deliberately does not add: it would
require knowing every label every curation tool may emit, which is the assumption that failed
in §1. The typo-catching R11 §3 bought is therefore reduced, not preserved, and survives only
on `normalized_label`. That is the price of admitting sources whose vocabularies are not
known in advance, and it is worth paying.

## 5. `core.units.quality_label` becomes the normalized value

R16 §3 made `quality_label` the designated label with `quality_label_source` naming where it
came from. The column keeps R11 §3's closed vocabulary, and now does so honestly — it holds
the **`normalized_label`** of the designated source, not the source's raw label.

R16 §3's `core.units.designated_label_is_recorded` rule is amended to join on the projection:

```sql
-- core.units.designated_label_is_recorded  (error)
SELECT u.session_id, u.unit_id, u.quality_label, u.quality_label_source
FROM core_units u
LEFT JOIN core_unit_quality_labels q
  ON  u.session_id = q.session_id AND u.unit_id = q.unit_id
  AND u.sorting_run_id = q.sorting_run_id AND u.curation_id = q.curation_id
  AND u.quality_label = q.normalized_label AND u.quality_label_source = q.source
WHERE u.quality_label IS NOT NULL AND q.source IS NULL
```

A packet whose designated source is bombcell and whose unit is `non_soma` therefore leaves
`quality_label` null. That is correct: there is no `sua`/`mua`/`noise` answer for that unit,
and inventing one is worse than absence.

R16 §3's `designated_label_pair_complete` is unchanged.

## 6. What does not change

- **`source` stays open** (R16 §2, R8 §4).
- **`default_qc` is still not a label.** R16 §2's reasoning holds and is strengthened by the
  measurement: `default_qc` agrees with no label column at all, because it is a policy over
  labels and metrics, which is `06`'s `analysis.good_units` territory.
- **Two names for one classifier are two rows.** `unitrefine_label` and `decoder_label` are
  byte-identical here, but the packet records what the source called itself. Recognising them
  as one classifier is an analysis-layer judgement, not a normalization the importer may make.
- **No table is added or removed.** The count stays 28.

## 7. Consequence

The 53.3% disagreement between bombcell and decoder becomes a fact the packet carries rather
than one it flattens. A `quality_policy_id` in `06` can now name a source *and* choose whether
it wants raw labels or the projection — "bombcell's `non_soma`, excluded" is expressible,
and under R11 §3 it was not.
