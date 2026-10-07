"""A recipe for one AIND ecephys session, rendered from its chosen assets and their facts.

- :class:`Layout` -- what the chosen assets hold, read one prefix at a time.
- :func:`render` -- the recipe's TOML, commented where a value was inferred or a source left out.

The sources and their ownership are those an AIND ecephys session with a dynamic-foraging NWB
needs, so a resource two of them can supply is already settled. The sources' adapters must be
installed beside the writer: each AIND kind runs in the build's process.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from escapewheel_reader.resource_ids import (
    CORE_ARRAY_ASSETS,
    CORE_ARRAY_CHANNELS,
    CORE_ARRAY_DIMENSIONS,
    CORE_ARRAY_LABELS,
    CORE_CALIBRATION_DEVICES,
    CORE_CALIBRATION_POINTS,
    CORE_CALIBRATIONS,
    CORE_CLOCK_ANCHORS,
    CORE_CLOCK_OBSERVATION_INTERVALS,
    CORE_CLOCK_PHASE_STEPS,
    CORE_CLOCKS,
    CORE_COORDINATE_FRAME_AXES,
    CORE_COORDINATE_FRAMES,
    CORE_CURATION_VERSIONS,
    CORE_DEVICES,
    CORE_ELECTRODE_COORDINATE_VALUES,
    CORE_ELECTRODE_COORDINATES,
    CORE_ELECTRODES,
    CORE_EVENT_STREAM_OBSERVATION_INTERVALS,
    CORE_EVENT_STREAMS,
    CORE_EVENTS,
    CORE_INTERVALS,
    CORE_MEDIA_ASSETS,
    CORE_MEDIA_FRAMES,
    CORE_PROBES,
    CORE_PROCESSING_RUNS,
    CORE_SORTING_RUN_CHANNELS,
    CORE_SORTING_RUNS,
    CORE_SPIKE_EVENTS,
    CORE_SUBJECTS,
    CORE_UNIT_COORDINATE_VALUES,
    CORE_UNIT_COORDINATES,
    CORE_UNIT_ELECTRODES,
    CORE_UNIT_QUALITY_LABELS,
    CORE_UNITS,
)

from ..resource_ids import AIND_UNIT_QC_METRICS, AIND_UNIT_QC_SYNCHRONY, AIND_UNIT_QC_WAVEFORM_METRICS
from .assets import Choice

#: Extension registries the drafted sources fill, keyed by the kind that fills one.
EXTENSION_OF = {"aind_unit_qc": "aind_unit_qc"}

#: The rig's zone, which every AIND ecephys rig shares.
ZONE = "America/Los_Angeles"


@dataclass(frozen=True)
class Layout:
    """What the chosen assets hold, as far as a recipe depends on it.

    Attributes
    ----------
    experiments : sequence of str
        The Open Ephys experiments the sorted asset's curated sorted assets cover, as `experiment1`.
    clipped : bool
        Whether the raw asset holds `ecephys/ecephys_clipped`, the Open Ephys tree.
    videos : str or None
        The raw asset's `behavior-videos` prefix, where the published MP4s and CSVs live.
    nwb_file : str or None
        The `.nwb` store inside the chosen NWB asset, which carries the behaviour.
    ephys_nwbs : sequence of str
        The sorted asset's own NWB stores, one per experiment, which carry units and electrodes
        and no behaviour.
    """

    experiments: Sequence[str] = ()
    clipped: bool = False
    videos: str | None = None
    nwb_file: str | None = None
    ephys_nwbs: Sequence[str] = ()
    notes: tuple[str, ...] = field(default=())


#: What a drafted option holds: TOML's scalars a recipe uses, and a list of strings.
Value = bool | int | str | Sequence[str]


def _value(value: Value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        # A JSON string is a TOML basic string: both escape with backslashes and \uXXXX.
        return json.dumps(value)
    return "[" + ", ".join(json.dumps(v) for v in value) + "]"


def _list(key: str, values: Sequence[str]) -> list[str]:
    if len(values) <= 2:
        return [f"{key} = {_value(values)}"]
    return [f"{key} = [", *(f"  {_value(v)}," for v in values), "]"]


def _comment(text: str) -> list[str]:
    return [f"# {line}" if line else "#" for line in text.splitlines()]


@dataclass
class _Source:
    kind: str
    why: str
    options: dict[str, Value]
    owns: Sequence[str] = ()
    contributes: Sequence[str] = ()

    def lines(self) -> list[str]:
        out = ["", *_comment(self.why), "[[source]]", f'kind = "{self.kind}"']
        out += [f"{key} = {_value(value)}" for key, value in self.options.items()]
        if self.contributes:
            out += _list("contributes", self.contributes)
        if self.owns:
            out += _list("owns", self.owns)
        return out


def _experiment(layout: Layout, nwb_file: str | None) -> tuple[str | None, list[str]]:
    """Return the experiment the packet covers, where the sorted asset covers more than one."""
    if len(layout.experiments) < 2:
        return None, []
    named = [e for e in layout.experiments if nwb_file and f"_{e}_" in Path(nwb_file).name]
    experiment = named[0] if named else min(layout.experiments)
    why = "the NWB's" if named else "the first, since no NWB names one"
    return experiment, [
        (
            f"The sorted asset covers {', '.join(layout.experiments)}; the packet covers {experiment}, {why}. Every "
            "source scoped by experiment names the same one, or the units the sorter and the analyzer read "
            "do not join."
        )
    ]


def sources(choice: Choice, layout: Layout, *, local_videos: Path | None) -> tuple[list[_Source], list[str]]:
    """Return the recipe's sources, and a line for each one left out and why."""
    sorted_uri, raw_uri = choice.sorted.uri, choice.raw.uri
    # `assets.choose` chooses only public assets, and a public asset has a location.
    assert sorted_uri is not None and raw_uri is not None
    nwb = layout.nwb_file
    left_out: list[str] = []
    experiment, scoped_why = _experiment(layout, nwb)
    scoped = {"experiment": experiment} if experiment else {}
    found: list[_Source] = [
        _Source(
            "session",
            "session.json and subject.json: each stream's observation window, and the probe clocks.",
            {"root": sorted_uri, "zone": ZONE, "in_process": True},
            owns=[
                CORE_EVENT_STREAM_OBSERVATION_INTERVALS,
                CORE_SUBJECTS,
                CORE_CALIBRATIONS,
                CORE_CALIBRATION_DEVICES,
                CORE_CALIBRATION_POINTS,
            ],
        ),
        _Source(
            "sync",
            "TTL events from the raw asset: the anchors relating each probe clock to harp.",
            {"root": f"{raw_uri}/ecephys"},
            contributes=[CORE_CLOCKS, CORE_CLOCK_ANCHORS, CORE_CLOCK_OBSERVATION_INTERVALS],
            owns=[CORE_CLOCK_PHASE_STEPS],
        ),
        _Source(
            "sorter",
            "\n".join(["spikes.npy carries sample indices, so the spike times need no fitting.", *scoped_why]),
            {"root": sorted_uri, **scoped, "parent_clock_id": "harp"},
            contributes=[CORE_CLOCKS, CORE_PROCESSING_RUNS, CORE_CLOCK_OBSERVATION_INTERVALS],
            owns=[
                CORE_UNITS,
                CORE_SPIKE_EVENTS,
                CORE_SORTING_RUNS,
                CORE_SORTING_RUN_CHANNELS,
                CORE_CURATION_VERSIONS,
                CORE_UNIT_QUALITY_LABELS,
            ],
        ),
        _Source(
            "waveforms",
            "The analyzer's templates, which say which electrodes each unit sits on.",
            {"root": sorted_uri, **scoped, "sd": True},
            owns=[CORE_UNIT_ELECTRODES],
            contributes=[CORE_ARRAY_ASSETS, CORE_ARRAY_DIMENSIONS, CORE_ARRAY_LABELS],
        ),
        _Source(
            "aind_unit_qc",
            "The pipeline's per-unit quality metrics, from the same analyzer.",
            {"root": sorted_uri, **scoped, **({"nwb": nwb} if nwb else {}), "in_process": True},
            owns=[AIND_UNIT_QC_METRICS, AIND_UNIT_QC_WAVEFORM_METRICS, AIND_UNIT_QC_SYNCHRONY],
        ),
    ]
    if layout.clipped:
        found.append(
            _Source(
                "openephys",
                "The acquisition chain behind the probes: basestation, connect board and headstage.",
                {"root": f"{raw_uri}/ecephys/ecephys_clipped"},
                contributes=[CORE_DEVICES],
            )
        )
    else:
        left_out.append("openephys: the raw asset holds no ecephys/ecephys_clipped")
    ephys_nwb = next((n for n in layout.ephys_nwbs if f"_{experiment or 'experiment1'}_" in Path(n).name), None)
    read = nwb or ephys_nwb
    if read is not None:
        nwb_options: dict[str, Value] = {
            "root": read,
            "zone": ZONE,
            # Whether a stream is a signal is a fact about the instrument, which no catalogue states.
            "signals": [],
            "emit_clock": False,
            "in_process": True,
        }
        if nwb is not None:
            nwb_options["interval_kind"] = "dynamic_foraging.trials"
        if layout.clipped:
            nwb_options["attachments"] = f"{raw_uri}/ecephys/ecephys_clipped"
        why = (
            "The NWB's probes, electrodes, events and trials. signals is empty and interval_kind names the\n"
            "dynamic-foraging task: GUESS, since no catalogue states either."
            if nwb is not None
            else "The sorted asset's own NWB, for its probes and electrodes. It holds no behaviour, so the packet\n"
            "has no events or trials; signals is empty: GUESS, since no catalogue states it."
        )
        found.append(
            _Source(
                "aind_nwb",
                why,
                nwb_options,
                contributes=[
                    CORE_CLOCKS,
                    CORE_CLOCK_ANCHORS,
                    CORE_ARRAY_ASSETS,
                    CORE_ARRAY_DIMENSIONS,
                    CORE_DEVICES,
                ],
                owns=[
                    CORE_ELECTRODE_COORDINATES,
                    CORE_ELECTRODES,
                    CORE_EVENT_STREAMS,
                    CORE_EVENTS,
                    CORE_PROBES,
                    CORE_INTERVALS,
                    CORE_UNIT_COORDINATES,
                    CORE_COORDINATE_FRAMES,
                    CORE_COORDINATE_FRAME_AXES,
                    CORE_ELECTRODE_COORDINATE_VALUES,
                    CORE_UNIT_COORDINATE_VALUES,
                ],
            )
        )
        found.append(
            _Source(
                "lfp",
                "The NWB's LFP series, referenced rather than copied.",
                {"root": read},
                owns=[CORE_ARRAY_CHANNELS],
                contributes=[CORE_ARRAY_ASSETS, CORE_ARRAY_DIMENSIONS, CORE_ARRAY_LABELS],
            )
        )
    else:
        left_out.append("aind_nwb and lfp: no NWB is public, so the packet has no probes or electrodes")
    if nwb is not None:
        left_out.append(
            "dynamic_foraging: the task's trials, blocks and session parameters need an extraction no "
            "installed adapter performs"
        )
    elif ephys_nwb is not None:
        left_out.append(
            "the behaviour: no NWB of this sorting carrying it is in a public bucket, so the sorted asset's "
            "ephys-only NWB is read"
        )
    if layout.videos is not None and local_videos is not None:
        found.append(
            _Source(
                "video",
                "Frame times for the behaviour videos, read from a local copy and addressed where they are published.",
                {"root": str(local_videos), "uri_base": layout.videos, "in_process": True},
                owns=[CORE_MEDIA_ASSETS, CORE_MEDIA_FRAMES],
            )
        )
    elif layout.videos is not None:
        left_out.append(f"video: ffprobe reads a local file, so it needs a copy of {layout.videos} (--videos)")
    else:
        left_out.append("video: the raw asset holds no behavior-videos")
    return found, left_out


def render(
    choice: Choice,
    layout: Layout,
    *,
    session: Mapping[str, str],
    subject: Mapping[str, str],
    notes: Sequence[str],
    packet_id: str,
    out: str,
    registry: str,
    extensions: Mapping[str, str],
    local_videos: Path | None = None,
) -> tuple[str, list[str]]:
    """Render the recipe, and return it with the extension IDs its sources need but `extensions` lacks."""
    found, left_out = sources(choice, layout, local_videos=local_videos)
    needed = sorted(
        {EXTENSION_OF[s.kind] for s in found if s.kind in EXTENSION_OF}
        | {str(s.options["interval_kind"]).split(".", 1)[0] for s in found if "interval_kind" in s.options}
    )
    missing = [extension for extension in needed if extension not in extensions]
    lines = [
        "# Drafted by `escapewheel-aind-recipe` from DocDB and Code Ocean, reading only public assets:",
        f"#   raw     {choice.raw.uri}",
        f"#   sorted  {choice.sorted.uri}",
        f"#   nwb     {choice.nwb.uri if choice.nwb else 'none public'}",
        *(["# Review every line marked GUESS before building."] if any("GUESS" in s.why for s in found) else []),
        *(f"# {note}" for note in [*choice.notes, *layout.notes]),
        "",
        "[packet]",
        f"id = {_value(packet_id)}",
        f"out = {_value(out)}",
        f"registry = {_value(registry)}",
        *_list("extensions", [extensions[e] for e in needed if e in extensions]),
        "",
        "# From the raw asset's DocDB v2 record. Times are UTC.",
        *(f"# {note}" for note in notes),
        "[session]",
        *(f"{key} = {_value(value)}" for key, value in session.items()),
        "",
        "[subject]",
        *(f"{key} = {_value(value)}" for key, value in subject.items()),
        "",
        "# The behaviour clock, a HARP counter at 31,250 Hz on every AIND ecephys rig.",
        "[[clock]]",
        'clock_id = "harp"',
        'name = "harp"',
        "tick_rate_num = 31250",
        'origin = "harp_counter"',
    ]
    for source in found:
        lines += source.lines()
    if left_out:
        lines += ["", "# Left out:", *(f"#   {line}" for line in left_out)]
    return "\n".join(lines) + "\n", missing


__all__ = ["EXTENSION_OF", "ZONE", "Layout", "render", "sources"]
