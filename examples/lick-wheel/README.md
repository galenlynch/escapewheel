# A lick-and-wheel adapter

This is a complete source adapter for one session of a head-fixed task: a lick sensor and a
reward valve log events on the rig's HARP clock, and a wheel encoder samples at 250 Hz on a
counter of its own. It is written against `escapewheel_writer.adapter`, registered by an entry
point, and delivered by `escapewheel deliver`, as an adapter released apart from the writer is.
`extensions/AUTHORING.md` explains the decisions; this shows them in code that a test builds into
a validated packet.

| what | where |
|---|---|
| events, their streams and the windows each stream was observed over | `LickWheelSource.records` |
| a reward's volume, carried as the event's payload | the `payload` of each `reward` event |
| a sampled signal as a packet-owned Zarr array | `staged_arrays`, and the `core.array_assets` and `core.array_dimensions` rows of `_wheel_tables` |
| a second clock, regular for its samples and anchored to HARP | the `wheel` clock and its `core.clock_anchors` |
| a source on an object store | `source_root`, and `test_a_store_root_is_read_as_a_disk_is` |
| a fact the source states, which the build checks against the recipe | `STATES` |
| a note on what the run worked around, which reaches the run's report | `notes`, and `test_a_delivered_adapter_reports_what_it_states` |
| the same packet in process and over both protocols | `ROUTES` in `tests/test_build.py` |

## The source

A session directory holds three files, every time in HARP seconds as Bonsai writes them:

```
session.json   {"subject_id": "m001", "harp_start_seconds": 3600.0, "harp_stop_seconds": 3610.0}
events.csv     harp_seconds,event,volume_ul
               3601.2,lick,
               3601.350016,lick,
               3602.9,reward,2.5
wheel.csv      harp_seconds,position_deg
               3600.0,0.0
               3600.004,0.019998665899038315
```

`wheel.csv` holds one row per sample, stamped with the HARP time the sample arrived at. The
encoder's oscillator and HARP's differ by tens of parts per million, so the stamps are not evenly
spaced on HARP although the samples are evenly spaced on the encoder. That is why the wheel gets a
clock of its own: its time axis is regular on the `wheel` clock, where tick k is sample k, and one
anchor a second records where that tick fell on HARP. A reader aligning the wheel to a reward
interpolates between anchors (`escapewheel_reader.clocks.align`) rather than trusting a rate.

## Running it

```bash
uv sync
uv run escapewheel registry --out core.json      # the core registry the recipe names
uv run python tests/session.py s001              # a synthetic session, where the recipe looks
uv run escapewheel import recipe.toml --check    # every problem, before any source is opened
uv run escapewheel import recipe.toml
uv run escapewheel ls packet/
uv run pytest                                    # builds it in process and over both protocols
```

`recipe.toml` runs the adapter in a process of its own, which is how a build reaches any adapter
it does not import. Replacing its `[source.delivery]` table with `in_process = true` constructs the
adapter in the build's process instead, which a recipe may say only where the adapter is installed
beside the writer (Part 05 §3.9). Both build the same packet.

`src/lick_wheel/declaration.json` is generated, by `escapewheel declare lick_wheel --out
src/lick_wheel/declaration.json`. A recipe names it under `[source.delivery].declaration` where the
build runs in an environment that does not install this package, and so cannot read the class.
