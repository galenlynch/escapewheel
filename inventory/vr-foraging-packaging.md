# Aind.Behavior.VrForaging.Packaging — pipeline inventory

Part 05 §4.1 discovery, for a **pipeline** rather than a dataset. Most AIND behaviour data will arrive
through this, so what it emits is the import surface that matters. Read at the state of
2026-08-26; three-version dispatch means these details are versioned and will move.

<https://github.com/AllenNeuralDynamics/Aind.Behavior.VrForaging.Packaging>

## 1. Design

A fan-out of independent **processors** over one lazily-loaded dataset. Each processor owns
exactly one output table and optionally one NWB representation:

```
raw session dir -> contraqctor Dataset -> create_processors(dataset)
                                            |
   [SessionMetadata, PositionAndVelocity, SiteTable, Licks, Sniffing, SoftwareEvents, Events]
                                            |
                        compute() -> DataFrame -> one parquet per processor
                        nwbize()  -> one NWBFile -> NWB-Zarr
```

`AbstractProcessor` is the contract: `_compute() -> DataFrame` is the work, `compute()` wraps it
to stamp provenance, `nwbize(nwb)` is an optional no-op. `compute()` and `nwbize()` share no
state, which is why `nwbize` re-enters `compute` and why `cached_frame` is opt-in per processor.

Above one session, `pipeline/batch.py` runs many and concatenates the small tables into flat
per-experiment files joinable on `session_id`; large tables stay per-session under
`sessions/{session_id}/`. The layout is identical on disk and on S3, and the documented way to
read it is DuckDB `httpfs` or Polars over range requests.

**Error policy.** `strict_parsing` gates only *named* anomalies a processor can degrade past;
general exceptions always propagate, and `pipeline/batch.py` contains no `except` at all.

## 2. Data model

The task is hierarchical, and the vocabulary is not ours:

- **Site** — the atomic unit, a stretch of virtual corridor. One row of `sites` = one site.
- **Patch** — contiguous sites sharing an odour identity and reward statistics.
- **Block** — patches sharing a task regime.

`SiteTableProcessor.nwbize()` writes **one NWB trial per site**, so in NWB terms a site *is* a
trial. The `Site` pydantic model carries ~30 fields: a `[start_time, stop_time)` interval, the
site geometry (`start_position`, `length`, `friction`, `odor_concentration`), the outcome
(`has_choice`, `has_reward`, `reward_amount`, `reward_probability`), four **nullable
within-interval moments** — `odor_onset_time`, `choice_cue_time`, `reward_onset_time`,
`last_stop_time` — and **eleven index columns** (site/patch/block, each global, within-parent,
and "by type").

Seven tables: `session`, `sites`, `position_velocity`, `licks`, `sniffing`, `software_events`,
`events`. Every one is indexed by **harp time in seconds**, float64.

`events` and `software_events` are both tall: `event_name` (str), `data` (JSON payload),
indexed by `timestamp`. `software_events` is a passthrough of the raw streams; `events` holds
what had to be computed from several.

## 3. Where it agrees with this format

Independently arrived at, which is worth more than agreement by construction:

| | Packaging | Escapewheel |
|---|---|---|
| Primary tabular format | Parquet | Parquet (Part 03) |
| NWB's role | a secondary projection built from the same processors | a compatibility projection, deferred (Part 00) |
| Event representation | `event_name`, `data` (JSON), `timestamp` | `core.events`: `event_type`, `payload`, `t_tick` |
| Join key | `session_id` on every table | `core.sessions.session_id`, referenced from nine tables |
| Provenance | three versions in parquet schema metadata, readable without pandas | `core.processing_runs`, plus each bound registry's version and digest in the manifest |
| Time base | one harp timeline | one declared reference clock (R27 §2) |
| Cross-session | flat concatenated tables | multi-session packets (R1) |
| Expected reader | DuckDB or Polars over parquet, local or S3 | the same |

## 4. Where it differs, and what that costs an importer

- **Time is float seconds, not integer ticks.** This is the one real gap. Every stream is harp
  seconds as float64; Escapewheel's cross-document invariant is an integer `*_tick` on a declared
  `clock_id`, with float seconds derived. Converting is arithmetic, but the direction matters:
  a float second cannot express exact sample alignment, which is the fault that put LFP 268
  days from the spikes in the ecephys NWB and the reason the sorter is our tick source.
- **`odor_concentration: list[float]` is a list column**, which R3 §2.1 forbids outright. It
  becomes a child table on import, exactly as `core.trial_tags` does.
- **The schema is code, not data.** Pydantic models plus parquet's self-description, guarded by
  pytest. Escapewheel's registry is data (R2 §7) and generates 241 checks. Neither is wrong; they
  are different places to put the same knowledge, and the `Site` model converts mechanically
  into an R17 extension registry document.
- **There is no manifest.** The export is a directory discovered by convention. Escapewheel binds
  every resource in `packet.json` with codecs, checksums and a validation state.
- **Nullable moments are columns.** `odor_onset_time` is null when no odour was delivered.
  `core.events` is where we put those, because absence is a fact about the interval rather than
  a null to carry — and the same argument holds here.
- **The export is rewritten, not versioned.** `clean=True` removes the previous run.
  Part 03 treats a committed packet as immutable and R32 makes an addition a new version.

## 5. Consequence for the importer

**Import the parquet, not the NWB.** The NWB is a lossy projection of the same processors —
list columns flattened, payloads JSON-serialised into NWB's string dtypes — and going
parquet-to-parquet skips a round trip through a format neither side wants. `sites.parquet`,
`events.parquet` and `session.parquet` are already tabular, harp-indexed and
provenance-stamped; what an adapter adds is the tick conversion, the child table for
`odor_concentration`, and splitting the nullable moments into `core.events`.

A `sites` row maps onto `core.trials` for its interval and identity; everything task-shaped —
the geometry, the outcome, the eleven index columns — is an R17 extension, not core.
