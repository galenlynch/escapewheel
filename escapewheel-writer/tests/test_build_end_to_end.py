"""A recipe driven through `session.build` and committed, which no other test does.

The conformance corpus proves that an implementation agrees about the **format**: `fixtures/build.py`
calls `pq.write_table` directly and constructs no `PacketWriter`, so every rule about how a packet is
*written* -- encodings, assigned identifiers, the session fill, physical order -- is enforced on a
path the corpus does not take. Twenty-one revisions of writer drift accumulated behind that, and the
rebuild of 2026-09-12 found five defects at once, each an accepted revision implemented on one code
path and not the other.

So this builds a packet the way a person does: synthetic sources on disk, a recipe naming them,
`build` and then `commit`. What it asserts is what the corpus cannot -- that the bytes a writer
emits obey the rules the writer is supposed to apply, and that its two staging paths agree.

Kept small deliberately: ten spikes and two probes take under a second, and the defects this catches
were interface mismatches between modules that each passed their own tests, not anything that needed
scale to appear.
"""

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from escapewheel_validator import Level

from tests import sorterfixture, syncfixture
from tests.conftest import REGISTRY

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


def _sources(root: Path) -> tuple[Path, Path]:
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


def _recipe(root: Path, sorted_root: Path, raw: Path) -> Path:
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


@pytest.fixture(scope="module")
def committed(tmp_path_factory):
    """Build and commit one packet, and hand back its root and the report.

    Module-scoped because every assertion below reads the same committed bytes, and building it
    once is what keeps an end-to-end test cheap enough to keep.
    """
    from escapewheel_writer import Recipe, import_packet

    root = tmp_path_factory.mktemp("e2e")
    sorted_root, raw = _sources(root)
    recipe = Recipe.load(_recipe(root, sorted_root, raw))
    return recipe.out, import_packet(recipe, REGISTRY)


def _table(root: Path, resource_id: str) -> pa.Table:
    """Read a committed table through the manifest, as a consumer would."""
    from escapewheel_reader import open_packet

    return open_packet(root).table(resource_id)


def test_a_recipe_builds_and_commits(committed):
    """The assertion the corpus cannot make: a packet the writer produced end to end validates.

    Every one of the five defects the 2026-09-12 rebuild found stopped a build or refused a
    commit, and none of them was visible to a test that writes Parquet directly.
    """
    root, report = committed
    assert report.errors == 0, [f"{f.check}: {f.message}" for f in report.findings if f.level == Level.ERROR]
    assert (root / "packet.json").exists()


def _inputs(root: Path) -> list[str]:
    """The `core.source_files` URIs published as inputs of the import run."""
    files = {r["source_file_id"]: r["uri"] for r in _table(root, "core.source_files").to_pylist()}
    runs = {r["processing_run_id"]: r["processing_run_name"] for r in _table(root, "core.processing_runs").to_pylist()}
    links = _table(root, "core.processing_run_inputs").to_pylist()
    assert len(links) == len(files)
    assert {runs[r["processing_run_id"]].split(".")[0] for r in links} == {"import"}
    return sorted(files[r["source_file_id"]] for r in links)


def test_each_source_root_is_an_input_of_the_import(committed):
    """Part 05 §7: one `core.source_files` row per distinct root, linked to the import run."""
    root, _ = committed
    assert _inputs(root) == sorted([str(root.parent / "raw"), str(root.parent / "sorted")])


def test_a_relative_root_is_recorded_as_the_recipe_writes_it(tmp_path):
    """Resolved against the recipe's directory to read it, and recorded unresolved (Part 05 §11)."""
    from escapewheel_writer.recipe import Recipe
    from escapewheel_writer.session import build

    sorted_root, raw = _sources(tmp_path)
    recipe = Recipe.load(_recipe(tmp_path, sorted_root.relative_to(tmp_path), raw.relative_to(tmp_path)))
    build(recipe, REGISTRY).commit(recipe.out)
    assert _inputs(recipe.out) == ["raw", "sorted"]


def test_sources_sharing_a_root_record_it_once():
    """A source stating no root states none to record."""
    from types import SimpleNamespace

    from escapewheel_writer.provenance import source_roots

    document = {"source": [{"kind": "sync", "root": "raw"}, {"kind": "harp", "root": "raw"}, {"kind": "thermistor"}]}
    assert source_roots(SimpleNamespace(document=document)) == ["raw"]


def test_a_clock_name_is_what_its_identifier_stands_for(committed):
    """Part 02 §8.2. `Clock.record` wrote the human label, so no recipe spelling resolved to a clock."""
    root, _ = committed
    names = _table(root, "core.clocks").column("clock_name").to_pylist()
    assert CLOCK_NAME in names, names


def test_every_session_scoped_table_names_its_session(committed):
    """Part 02 §7.1, on the streaming path as much as the records one.

    The fill was applied in `add` and never in `add_batches`, so `core.spike_events` committed
    with a null `session_id` and only a rule firing against a different table said so.
    """
    root, _ = committed
    from escapewheel_reader import open_packet

    packet = open_packet(root)
    held = {r.resource_id for r in packet.resources(kind="table")}
    checked = []
    for resource_id, declaration in REGISTRY["resources"].items():
        if declaration["kind"] != "table":
            continue
        spec = declaration["table"]
        if resource_id not in held:
            continue
        if not any(c["name"] == "session_id" for c in spec["columns"]):
            continue
        column = packet.table(resource_id, columns=["session_id"]).column("session_id")
        assert column.null_count == 0, f"{resource_id} holds {column.null_count} null session_id"
        checked.append(resource_id)
    assert "core.spike_events" in checked, "the streamed table is the one this exists for"


def test_the_writer_applies_its_own_encoding_rules(committed):
    """Part 03 §5.5, read off the committed bytes rather than off the writer's intent.

    Asserted against `encoding.encodings` rather than against a restatement of the rule, so this
    catches the writer failing to apply what it decided and not a disagreement about the decision.
    `fixtures/build.py` takes none of this path: `core.spike_events.t_tick` is `RLE_DICTIONARY` in
    every corpus packet, which is what §5.5 tells a writer not to do.
    """
    root, _ = committed
    from escapewheel_reader import open_packet

    from escapewheel_writer.encoding import encodings

    packet = open_packet(root)
    asserted = 0
    for resource in packet.resources(kind="table"):
        declaration = REGISTRY["resources"].get(resource.resource_id)
        spec = None if declaration is None or declaration["kind"] != "table" else declaration["table"]
        if spec is None:
            continue
        parquet = pq.ParquetFile(packet.path(resource.resource_id))
        if parquet.metadata.num_rows == 0:
            continue
        # The writer counted the table it wrote, or its first batch, which is this row group.
        delta, plain = encodings(resource.resource_id, spec, parquet.schema_arrow, sample=parquet.read_row_group(0))
        used = {}
        for group in range(parquet.metadata.num_row_groups):
            for i in range(parquet.metadata.num_columns):
                column = parquet.metadata.row_group(group).column(i)
                used.setdefault(column.path_in_schema, set()).update(column.encodings)
        for name in delta:
            assert "DELTA_BINARY_PACKED" in used.get(name, set()), (
                f"{resource.resource_id}.{name} took {used.get(name)} where the rule asks for delta"
            )
            asserted += 1
        for name in delta + plain:
            assert "RLE_DICTIONARY" not in used.get(name, set()), (
                f"{resource.resource_id}.{name} is dictionary-encoded against the rule"
            )
            asserted += 1
    assert asserted, "no column exercised a rule, so this asserted nothing"


#: The smallest packet that validates with a non-reference clock in it, which anchors need: a
#: clock with a parent, and an observation window per clock for anything on them to inherit.
TWO_CLOCKS = {
    "core.subjects": [{"subject_id": "m001", "species": "Mus musculus", "sex": "male"}],
    "core.sessions": [
        {
            "session_id": "s001",
            "subject_id": "m001",
            "reference_clock_id": "harp",
            "session_start_time": "2026-08-27T00:00:00Z",
            "t_zero_tick": 0,
        }
    ],
    "core.clocks": [
        {
            "clock_id": "harp",
            "session_id": "s001",
            "clock_name": "harp",
            "tick_rate_num": 31250,
            "tick_rate_den": 1,
            "origin": "harp epoch",
        },
        {
            "clock_id": "probe",
            "session_id": "s001",
            "clock_name": "probe",
            "parent_clock_id": "harp",
            "tick_rate_num": 30000,
            "tick_rate_den": 1,
            "origin": "sample 0",
        },
    ],
    "core.clock_observation_intervals": [
        {"session_id": "s001", "clock_id": "harp", "start_tick": 0, "stop_tick": 500_000},
        {"session_id": "s001", "clock_id": "probe", "start_tick": 0, "stop_tick": 5_000},
    ],
}

#: Anchors in the declared sort order, which `add_batches` requires of its caller and `add` does not.
ANCHORS = [
    {
        "session_id": "s001",
        "clock_id": "probe",
        "anchor_index": i,
        "t_tick": i * 1000,
        "parent_tick": i * 1000 * 31250 // 30000,
    }
    for i in range(6)
]


def test_the_records_path_and_the_streaming_path_agree(tmp_path):
    """The pair where a rule gets implemented once and forgotten once.

    Two of the five defects the rebuild found were `add` against `add_batches`, and nothing
    compared them: the same rows down each path have to reach Parquet identical, including what
    the writer fills in on the way. The streamed rows carry no `session_id` at all, because
    Part 02 §7.1's fill is the writer's job and is exactly what `add_batches` was not doing.
    """
    from escapewheel_writer.writer import PacketWriter

    def commit(where: Path, *, stream: bool) -> pa.Table:
        writer = PacketWriter(REGISTRY, packet_id="p", session="s001")
        for resource_id, records in TWO_CLOCKS.items():
            writer.add(resource_id, records)
        if stream:
            rows = [{k: v for k, v in row.items() if k != "session_id"} for row in ANCHORS]
            writer.add_batches("core.clock_anchors", pa.Table.from_pylist(rows).to_batches(max_chunksize=2))
        else:
            writer.add("core.clock_anchors", ANCHORS)
        assert writer.commit(where).passed
        return _table(where, "core.clock_anchors")

    staged = commit(tmp_path / "records", stream=False)
    streamed = commit(tmp_path / "batches", stream=True)
    assert staged.schema == streamed.schema
    assert staged.to_pylist() == streamed.to_pylist()
    # Named rather than left to the equality above, since a fill missing from both would pass it.
    assert streamed.column("session_id").null_count == 0
    assert streamed.column("session_id").to_pylist() == [0] * len(ANCHORS)
