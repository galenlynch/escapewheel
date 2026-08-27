# R8 — Column Types and Vocabularies

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `02_core_logical_schemas.md` |
| **Depends on** | R5 (the `*_label` rename) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Two defects remain in `02`'s column declarations after R3–R7.

Three columns are typed `int64` while being defined as opaque source values, which excludes
sources that do not label with integers.

Five required columns declare their permitted values as a list ending in "etc.", which is
not a vocabulary a validator can check.

## 2. Source label columns become `string`

R5 §5 renames three columns to `*_label` on the grounds that they hold values copied
verbatim from acquisition or sorting software, with undefined base, which MUST NOT be used
as offsets. It leaves them `int64`.

That is inconsistent. A value constrained to be an integer is an index whatever it is
called, and the constraint excludes real sources: SpikeInterface channel identifiers are
frequently strings (`AP0`, `imec0.ap#AP0`), and unit identifiers may be either.

| Column | Was | Becomes |
|---|---|---|
| `core.electrodes.local_electrode_label` | int64 | string |
| `core.electrodes.local_channel_label` | int64 | string |
| `core.units.local_unit_label` | int64 | string |

All three remain optional. A source labelling with integers stores their decimal
representation; `"42"` is expressible as a string, `"AP0"` is not expressible as an int64.

Nothing is lost by the change. Numeric ordering of these columns was never permitted, since
R5 §5 forbids their use as offsets into any packet resource.

## 3. `status` — closed vocabulary

`core.processing_runs.status` is required and declares "succeeded, failed, partial, etc."

The permitted values are exactly:

```text
succeeded   the run completed and its outputs are usable
failed      the run did not complete; its outputs MUST NOT be committed
partial     the run completed for some inputs only; committed outputs are incomplete
```

A validator MUST reject any other value. This is closeable because the set is complete:
a run either finished, did not, or finished incompletely, and a committed packet contains no
runs still in progress.

Closing it makes a check possible that the open form does not:

```sql
-- core.processing_runs.no_failed_runs  (error)
SELECT processing_run_id, activity_type FROM core_processing_runs WHERE status = 'failed'
```

Under `05`'s principle that validation is importation, a failed run has no business having
produced committed resources.

Where `core.provenance_activities` retains a `status` column, the same vocabulary applies.

## 4. `kind` — declared open vocabulary

`core.array_assets.kind` is required and declares "`raw`, `ap`, `lfp`, `waveform`, etc."

This is NOT closeable now. The set of array kinds a packet may hold depends on acquisition
and preprocessing systems this specification has not been tested against, and enumerating it
from the four examples in `02` would exclude legitimate data on no evidence.

It is therefore declared open rather than left ambiguous:

- `kind` is an open vocabulary. A validator MUST NOT reject an unrecognized value.
- The following values are reserved and MUST carry these meanings:

```text
raw        unfiltered wideband extracellular voltage
ap         action-potential band
lfp        local field potential band
waveform   spike waveform snippets
```

- A value outside the reserved set MUST NOT be used for data the reserved set describes.

"etc." implied a closed set existed and had merely been elided. Stating openness explicitly
is what the field actually needs; it tells an implementer that unrecognized values are
conforming, which "etc." does not.

`semantic_type` is open on the same terms, for the same reason.

## 5. Not addressed here

`entity_type`, `relationship_type`, and `activity_type` are also open vocabularies. They sit
on tables R9 restructures, and are resolved there.
