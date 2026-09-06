# Interval kinds — one base table, or one table per kind?

`05` Stage 1 for a design decision rather than a dataset. R54 §2.1 argues for a base
`core.intervals` on the strength of a **polymorphic query** — align to every interval in a session
without knowing the paradigm — and R54 §5 records that nothing does that yet, so the argument was
unmeasured. This builds both shapes over the same rows and asks what each costs a consumer.

Run: `uv run --project ../../escapewheel-writer --all-extras python probe.py`

## The session

400 task trials and 120 optotagging pulses, interleaved on one clock — the case a real session
has and NWB holds badly, since `nwbfile.trials` is the one table tools read.

## Result

```
base table (R54)
  every interval             520 rows   1 scan of one known name         0.93 ms
  one kind, with detail      120 rows   filter + declared join           2.18 ms

concrete tables
  every interval             520 rows   2 found by guessing at columns   1.74 ms
    ...and wrongly             4 rows   core.clock_observation_intervals,
                                        core.event_stream_observation_intervals,
                                        core.trials, core.unit_observation_intervals
  one kind, with detail      120 rows   1 scan, name known ahead         0.43 ms
```

**Timing decides nothing** — everything is under 3 ms, and concrete is *faster* for the query
where the consumer already knows the name.

**Discovery decides it.** Under concrete tables nothing declares that a resource is an alignable
interval set, so a consumer that has not heard of the extensions can only guess from columns —
and the guess is wrong. It matches the three observation-interval tables, which hold intervals a
*measurement* found rather than a *design* declared (R54 §3), and `core.trials`, which is the
table R54 replaces. A declaration that fixed this would be a discriminator by another name.

Under the base table it is one scan of one name the consumer already knows, and the detail join
is mechanical: the kind **is** the resource ID, the registry gives the reference, and no extension
is named anywhere in the reading code.

## What this does not show

- **Scale.** 520 intervals. Nothing here says what a million would cost, and the containment
  measurement in the root TODO §3 is the one that speaks to that.
- **That two kinds is common.** One synthetic session. The case is drawn from what a real session
  holds — a task, optotagging, inactivation windows — not from a packet that carries it.
- **Anything about R55.** `interval_kind` is declared `role: data` here, because the
  `discriminator` role R55 proposes does not exist yet.
