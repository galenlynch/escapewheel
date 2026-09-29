# Interval kinds — one base table, or one table per kind?

Part 05 §4.1 discovery for a design decision rather than a dataset. R54 §2.1 argues for a base
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
  every interval             520 rows   1 scan of one known name         1.22 ms
  one kind, with detail      120 rows   filter + declared join           2.82 ms

concrete tables
  every interval             520 rows   2 found by guessing at columns   2.25 ms
    ...and wrongly             3 rows   core.clock_observation_intervals,
                                        core.event_stream_observation_intervals,
                                        core.unit_observation_intervals
  one kind, with detail      120 rows   1 scan, name known ahead         0.56 ms
```

The base shape is the registry's own `core.intervals`, keyed by the `interval_id` the packet
assigns (Part 02 §12.9), and each detail table references that identifier alone.

**Timing decides nothing** — everything is under 3 ms, and concrete is *faster* for the query
where the consumer already knows the name.

**Discovery decides it.** Under concrete tables nothing declares that a resource is an alignable
interval set, so a consumer that has not heard of the extensions can only guess from columns —
and the guess is wrong. It matches the three observation-interval tables, which hold intervals a
*measurement* found rather than a *design* declared (R54 §3). A declaration that fixed this would
be a discriminator by another name.

Under the base table it is one scan of one name the consumer already knows, and the detail join
is mechanical: the kind **is** the resource ID, the registry gives the reference, and no extension
is named anywhere in the reading code.

## What this does not show

- **Scale.** 520 intervals. Nothing here says what a million would cost, and the containment
  measurement under the root TODO's **Measured, for reuse** is the one that speaks to that.
- **That two kinds is common.** One synthetic session. The case is drawn from what a real session
  holds — a task, optotagging, inactivation windows — not from a packet that carries it.
