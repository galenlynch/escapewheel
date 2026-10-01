"""What more than one test module builds: packets, recipes, and the rows and documents they hold."""

from __future__ import annotations

import json
from pathlib import Path

from escapewheel_writer import PacketWriter
from escapewheel_writer.recipe import Recipe
from tests import sorterfixture, syncfixture


def commit_tables(root, registry, tables, **kwargs):
    writer = PacketWriter(registry, packet_id=root.name, **kwargs)
    for resource_id, records in tables.items():
        writer.add(resource_id, records)
    return writer.commit(root)


def import_runs(**overrides):
    """A materialization activity (Part 06 §5), which is what an amendment normally carries."""
    return [
        {
            "processing_run_id": "run1",
            # Part 02 §7.1: a run is session-scoped, and an amendment names the session it is for
            # rather than inheriting one -- the packet it amends may hold more than one.
            "session_id": "s001",
            "activity_type": "materialization",
            "software_name": "escapewheel_writer",
            "software_version": "0.0.0",
            "status": "succeeded",
            **overrides,
        }
    ]


def waveform_values(units=8, channels=4, samples=10):
    """A small stand-in with the shape a waveform array has: units, channels, samples."""
    import numpy as np

    rng = np.random.default_rng(0)
    return (rng.normal(0, 100, (units, channels, samples))).astype("int16")


def array_asset_tables(asset_id: str = "wf") -> dict[str, list[dict]]:
    """The rows an array must be accompanied by: every axis named, and counted in steps of 1 (Part 03 §6.3)."""
    return {
        "core.array_assets": [
            {
                "array_asset_id": asset_id,
                "session_id": "s001",
                "semantic_type": "waveform_mean",
                "array_asset_name": "mean waveform per unit",
            }
        ],
        "core.array_dimensions": [
            {
                "array_asset_id": asset_id,
                "axis_index": i,
                "dimension_name": n,
                "origin_value": 0.0,
                "step_value": 1.0,
                "coordinate_unit": "1",
            }
            for i, n in enumerate(("unit", "channel", "sample"))
        ],
    }


RECIPE_BASE = """
[packet]
id = "s001"
registry = "reg.json"

[session]
session_id = "s001"
reference_clock_id = "harp"

[subject]
subject_id = "m001"

[[clock]]
clock_id = "harp"
name = "HARP"
tick_rate_num = 31250
origin = "HARP epoch"
"""


def write_recipe(tmp_path, body, name="session.toml"):
    """Write a recipe and return its path."""
    path = tmp_path / name
    path.write_text(RECIPE_BASE + body)
    return path


def problems_coded(problems, code, level=None):
    """The problems carrying one code, at one level where given."""
    return [p for p in problems if p.code is code and level in (None, p.level)]


#: The NWB states a probe's type and manufacturer where the sorter knows only the stream, so a
#: recipe listing both prefers it.
PREFER_NWB = """
[preference."core.probes"]
source = "nwb"
reason = "the NWB states a probe's type and manufacturer; the sorter knows only the stream"
"""


def contested_recipe(tmp_path):
    """A recipe preferring the NWB for `core.probes`, which the sorter also produces."""
    return Recipe.load(
        write_recipe(
            tmp_path,
            '\n[[source]]\nkind = "nwb"\nroot = "n"\n'
            'owns = ["core.probes"]\n'
            '\n[[source]]\nkind = "sorter"\nroot = "s"\n'
            'owns = ["core.units"]\n' + PREFER_NWB,
        )
    )


TWO_DEFAULTED = '\n[[source]]\nkind = "sorter"\nroot = "s"\n\n[[source]]\nkind = "nwb"\nroot = "n"\nzone = "UTC"\n'


NWB_OWNING_PROBES = '\n[[source]]\nkind = "nwb"\nroot = "s"\nzone = "UTC"\nowns = ["core.probes"]\n'


def declaration_for(tmp_path, **fields):
    """Write an adapter's declaration document and return its path, relative to the recipe."""

    document = {
        "kind": "thermistor",
        "protocols": ["stream-v0.1"],
        "produces": ["core.devices"],
        "contributes": [],
        "states": [],
        "needs": ["root", "session_id", "sample_rate_hz"],
        "accepts": [],
        "consumes": [],
        **fields,
    }
    (tmp_path / "thermistor.json").write_text(json.dumps(document))
    return "thermistor.json"


DELIVERED = """
[[source]]
kind = "thermistor"
root = "."
sample_rate_hz = 1000

[source.delivery]
declaration = "{declaration}"
command = ["thermistor-adapter", "--verbose"]
report_path = "reports/thermistor.json"
"""


def prefixed(**by_kind):
    """Source entries of these kinds, each setting `prefix` to its value or leaving it unset for None."""
    return "".join(
        f'\n[[source]]\nkind = "{kind}"\nroot = "."\nowns = []\n' + ("" if value is None else f'prefix = "{value}"\n')
        for kind, value in by_kind.items()
    )


#: The two streams the recipe sorts. `sorterfixture.build` would add the same probe sorted in a
#: second experiment, which Part 05 §12 refuses as an alternative the packet does not choose between.
STREAMS = (
    "experiment1_Record Node 109#Neuropix-PXI-100.50720-1_recording1",
    "experiment1_Record Node 109#Neuropix-PXI-100.50720-2_recording1",
)

#: Each stream's first raw sample, which is what makes its counter recording-relative.
FIRST_SAMPLE = {"Neuropix-PXI-100.50720-1": 44_259_994, "Neuropix-PXI-100.50720-2": 44_251_369}

#: What the recipe spells the reference clock, and so what `core.clocks.clock_name` must hold:
#: a name is what its identifier stands for (Part 02 §8.2), never a human label.
CLOCK_NAME = "harp"


def session_sources(root: Path) -> tuple[Path, Path]:
    """Write a sorted asset and the raw tree whose pulses anchor its probe clocks."""
    sorted_root = root / "sorted"
    for name in STREAMS:
        sorterfixture.stream(sorted_root, name, spikes=sorterfixture.SPIKES)

    raw = root / "raw"
    recording = raw / "Record Node 109" / "experiment1" / "recording1"
    for name, first in FIRST_SAMPLE.items():
        syncfixture.stream(
            recording / "events",
            name,
            first_sample=first,
            aligned=True,
            continuous=recording / "continuous",
        )
    (raw / "structure.json").write_text(json.dumps({"note": "fixture"}))
    return sorted_root, raw


def session_recipe(root: Path, sorted_root: Path, raw: Path) -> Path:
    """A recipe of the shape a real one has: sync anchors the clocks, the sorter owns the units."""
    path = root / "session.toml"
    path.write_text(f"""
[packet]
id = "s1"
out = "{root}/packet"

[session]
session_id = "s1"
subject_id = "m001"
reference_clock_id = "{CLOCK_NAME}"
session_start_time = "2026-08-27T00:00:00Z"

[subject]
subject_id = "m001"
species = "Mus musculus"
sex = "male"
date_of_birth = "2025-01-01"

[[clock]]
clock_id = "{CLOCK_NAME}"
name = "HARP"
tick_rate_num = 31250
origin = "harp epoch"

[[source]]
kind = "sync"
root = "{raw}"
contributes = ["core.clocks", "core.clock_anchors", "core.clock_observation_intervals"]

[[source]]
kind = "sorter"
root = "{sorted_root}"
parent_clock_id = "{CLOCK_NAME}"
contributes = ["core.clocks", "core.clock_observation_intervals", "core.processing_runs"]
owns = [
  "core.probes",
  "core.units",
  "core.spike_events",
  "core.sorting_runs",
  "core.curation_versions",
  "core.unit_quality_labels",
]
""")
    return path


def amending_recipe(root: Path, sorted_root: Path, *, amends: str = "0.1.0", extra: str = "") -> Path:
    """A recipe adding a second curation of the packet's sortings, and nothing it holds."""
    path = root / "amend.toml"
    path.write_text(f"""
[packet]
id = "s1"
out = "{root}/packet"
amends = "{amends}"

[session]
session_id = "s1"

[[source]]
kind = "sorter"
root = "{sorted_root}"
parent_clock_id = "{CLOCK_NAME}"
curation = "recurated"
contributes = ["core.processing_runs"]
owns = ["core.units", "core.spike_events", "core.curation_versions", "core.unit_quality_labels"]
{extra}""")
    return path
