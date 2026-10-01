"""The boundary a build reaches a source through: a declaration, a command, and three protocols.

Every test here runs the adapter in a process of its own, because that is the thing being tested:
what crosses is one JSON object and what comes back is rows, and neither may depend on the two
halves sharing an interpreter.
"""

import inspect
import io
import json
import sys
from dataclasses import replace

import pytest

from escapewheel_writer import declaration, delivery
from escapewheel_writer.clock import HARP_TICK_RATE_HZ, Clock
from escapewheel_writer.encoding import STREAMED_BATCH_ROWS
from escapewheel_writer.errors import DeliveryFailed, RecipeFault, SourceDefect, SourceFault, UsageError, UsageFault
from escapewheel_writer.notes import NoteCode, codes
from escapewheel_writer.recipe import TERMS
from escapewheel_writer.sources import ADAPTERS
from escapewheel_writer.sources.nwb import NWBSource
from tests import nwbfixture

SESSION = "mini_2025-04-09"
ZONE = "America/Los_Angeles"
KIND = "task.trials"

#: How a test runs the writer's own delivering command. `-m` rather than the console script, so
#: nothing here depends on which directory is on PATH.
ESCAPEWHEEL = (sys.executable, "-m", "escapewheel_reader.scripts.cli")


@pytest.fixture
def harp():
    return Clock("harp", session_id=SESSION, name="HARP", tick_rate_num=HARP_TICK_RATE_HZ, origin="HARP epoch")


@pytest.fixture
def nwb(tmp_path):
    return nwbfixture.build(tmp_path)


@pytest.fixture
def supplied(nwb, harp):
    """What a build hands the NWB adapter: the terms it declared, and the recipe's options."""
    return {
        "root": str(nwb),
        "session_id": SESSION,
        "reference_clock": harp.record(),
        "units": [],
        "options": {"zone": ZONE, "interval_kind": KIND},
    }


# -- the declaration ----------------------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(ADAPTERS))
def test_every_shipped_adapter_generates_a_valid_document(kind):
    """Generated rather than maintained (Part 12 §7), so this is what an author starts from."""
    jsonschema = pytest.importorskip("jsonschema")
    document = declaration.document_of(ADAPTERS[kind], kind, ["stream-v0.1"])
    assert not list(jsonschema.Draft202012Validator(declaration.schema()).iter_errors(document))
    assert document["kind"] == kind


def test_a_generated_document_carries_what_the_adapter_accepts():
    """An option with a default is declarable only here, so `sample` crosses as the adapter's."""
    document = declaration.document_of(ADAPTERS["sorter"], "sorter", ["stream-v0.1"])
    assert "sample" in document["accepts"]
    assert "sample" not in document["needs"]


@pytest.mark.parametrize("kind", sorted(ADAPTERS))
def test_every_option_an_adapter_reads_is_declared(kind):
    """The declared list is checked against the constructor, so it cannot go stale.

    A parameter holding a default is an option a recipe may set, and one a recipe may set and no
    declaration names is refused (Part 12 §4) -- so an option added here without being declared
    would refuse every recipe setting it. `store` is the exception: a handle a recipe cannot
    carry, supplied where the class accepts one rather than declared (Part 12 §4). `source_cache`
    is a term and declared anyway, the one `accepts` may name.
    """
    adapter = ADAPTERS[kind]
    parameters = list(inspect.signature(adapter.__init__).parameters.values())[1:]
    optional = {
        p.name
        for p in parameters
        if p.default is not inspect.Parameter.empty
        and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
        and p.name not in adapter.NEEDS
        and (p.name not in TERMS or p.name == "source_cache")
        and p.name != "store"
    }
    assert optional == set(getattr(adapter, "ACCEPTS", ()))


def test_ownership_from_the_documents_is_ownership_from_the_classes():
    """The two forms are one declaration, so what a build settles from them cannot differ."""
    from_document = {
        resource: kind
        for kind in sorted(ADAPTERS)
        for resource in declaration.document_of(ADAPTERS[kind], kind, ["stream-v0.1"])["produces"]
    }
    from_class = {resource: kind for kind in sorted(ADAPTERS) for resource in sorted(ADAPTERS[kind].PRODUCES)}
    assert from_document == from_class


def test_a_document_round_trips_through_a_file(tmp_path):
    written = tmp_path / "nwb.json"
    document = declaration.document_of(ADAPTERS["nwb"], "nwb", ["flight-v0.1"])
    written.write_text(json.dumps(document))
    assert declaration.load(written) == document


def test_a_shipped_class_generates_no_protocol_unless_given_one():
    """Only a shipped adapter may state none (Part 12 §3), and its document then fails the schema."""
    bare = declaration.document_of(ADAPTERS["nwb"], "nwb")
    assert "protocols" not in bare
    assert declaration.shape_problems(bare) == ["declaration: 'protocols' is a required property"]
    assert declaration.shape_problems(bare, shipped=True) == []


@pytest.mark.parametrize(
    "protocols", [[], ["flight-v0.1"], ["files-v0.1", "flight-v0.1"]], ids=["default", "one", "several"]
)
def test_declare_writes_a_document_the_schema_accepts(tmp_path, capsys, protocols):
    from escapewheel_reader.scripts.cli import main

    out = tmp_path / "nwb.json"
    flags = [flag for protocol in protocols for flag in ("--protocol", protocol)]
    assert main(["declare", "nwb", *flags, "--out", str(out)]) == 0
    document = json.loads(out.read_text())
    assert declaration.shape_problems(document) == []
    assert document["protocols"] == (protocols or ["stream-v0.1"])


def test_declare_refuses_a_protocol_for_a_class_stating_its_own(monkeypatch, capsys):
    from escapewheel_reader.scripts.cli import main

    from escapewheel_writer import sources

    stating = type("Stating", (NWBSource,), {"PROTOCOLS": ("files-v0.1",)})
    monkeypatch.setattr(sources, "discovered", lambda: {"stating": stating})
    assert main(["declare", "stating", "--protocol", "flight-v0.1"]) == 2
    assert "declares its own protocols" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("broken", "expected"),
    [
        ({"protocols": ["carrier-pigeon-v1"]}, RecipeFault.PROTOCOL_UNKNOWN),
        ({"produces": ["core.tirals"]}, RecipeFault.PRODUCES_UNDECLARED),
        ({"states": ["subject.sbuject_id"]}, RecipeFault.STATES_UNRESOLVED),
        ({"needs": ["open_store"]}, RecipeFault.NEEDS_UNFILLED),
        ({"needs": ["socket"]}, RecipeFault.NEEDS_PROTOCOL_TERM),
        ({"accepts": ["units"]}, RecipeFault.ACCEPTS_TERM),
        ({"accepts": ["socket"]}, RecipeFault.ACCEPTS_TERM),
        ({"accepts": ["zone"]}, RecipeFault.ACCEPTS_NEEDED),
    ],
)
def test_a_build_refuses_what_it_can_check_without_the_adapter(broken, expected, registry):
    """Part 12 §7's checks, each firing on its own and naming what is wrong."""
    sound = declaration.document_of(ADAPTERS["nwb"], "nwb", ["stream-v0.1"])
    found = declaration.refusals(
        {**sound, **broken},
        tables={
            name: declaration["table"]
            for name, declaration in registry["resources"].items()
            if declaration["kind"] == "table"
        },
        options={"zone", "interval_kind"},
        terms=TERMS,
    )
    assert expected in [code for code, _ in found], found


def test_a_sound_declaration_is_refused_for_nothing(registry):
    sound = declaration.document_of(ADAPTERS["nwb"], "nwb", ["stream-v0.1"])
    tables = {
        name: resource["table"] for name, resource in registry["resources"].items() if resource["kind"] == "table"
    }
    assert declaration.refusals(sound, tables=tables, options={"zone", "interval_kind"}, terms=TERMS) == []


# -- what crosses -------------------------------------------------------------------------


def test_everything_a_build_supplies_writes_down(supplied):
    """A term that cannot be written down cannot cross, whatever it means in this process."""
    assert json.loads(json.dumps(supplied)) == supplied


@pytest.mark.parametrize("protocol", ["stream-v0.1", "files-v0.1", "flight-v0.1"])
def test_the_rows_are_the_rows_the_adapter_produced(protocol, supplied, nwb, harp, tmp_path):
    """The boundary's own property: what a source produced is what a build receives."""
    if protocol == "flight-v0.1":
        pytest.importorskip("pyarrow.flight")
    here = NWBSource(nwb, reference_clock=harp.record(), zone=ZONE, interval_kind=KIND, units=[]).records()
    wanted = sorted(NWBSource.PRODUCES)
    got = delivery.fetch(
        "nwb",
        [*ESCAPEWHEEL, "deliver", "nwb"],
        supplied,
        protocol=protocol,
        wanted=wanted,
        workspace=tmp_path / "work",
    )
    assert sorted(got.tables) == wanted, "a resource with no rows arrives empty rather than not arriving"
    for resource in wanted:
        assert got.rows(resource) == delivery.as_table(here.get(resource, [])).to_pylist(), resource


def test_a_workspace_path_longer_than_a_socket_address_still_delivers(supplied, tmp_path):
    """A Unix socket's address holds about a hundred bytes, and a packet's path is not bounded by it."""
    pytest.importorskip("pyarrow.flight")
    workspace = tmp_path / ("d" * 60) / ("e" * 60) / "work"
    wanted = ["core.electrodes", "core.probes"]
    got = delivery.fetch(
        "nwb",
        [*ESCAPEWHEEL, "deliver", "nwb"],
        {**supplied, "wanted": wanted},
        protocol="flight-v0.1",
        wanted=wanted,
        workspace=workspace,
    )
    assert sorted(got.tables) == wanted


def test_stage_one_agrees_with_what_arrived(supplied, tmp_path):
    got = delivery.fetch(
        "nwb",
        [*ESCAPEWHEEL, "deliver", "nwb"],
        supplied,
        protocol="stream-v0.1",
        wanted=sorted(NWBSource.PRODUCES),
        workspace=tmp_path / "work",
    )
    counted = {resource: len(got.rows(resource)) for resource in got.tables}
    assert got.offers() == counted


def test_a_build_asks_for_only_what_the_recipe_leaves_it_owning(supplied, tmp_path):
    """`wanted` is a term a build supplies and an adapter may act on (Part 12 §4)."""
    wanted = ["core.electrodes", "core.probes"]
    got = delivery.fetch(
        "nwb",
        [*ESCAPEWHEEL, "deliver", "nwb"],
        {**supplied, "wanted": wanted},
        protocol="files-v0.1",
        wanted=wanted,
        workspace=tmp_path / "work",
    )
    assert sorted(got.tables) == wanted


# -- the report ---------------------------------------------------------------------------


def test_the_values_behind_states_come_back_in_the_report(supplied, tmp_path):
    """No static document can carry them, because each needs the source read (Part 12 §9)."""
    report = tmp_path / "report.json"
    got = delivery.fetch(
        "nwb",
        [*ESCAPEWHEEL, "deliver", "nwb"],
        supplied,
        protocol="stream-v0.1",
        wanted=sorted(NWBSource.PRODUCES),
        states=sorted(NWBSource.STATES),
        report_path=report,
        workspace=tmp_path / "work",
    )
    assert report.is_file()
    assert got.stated_subject_subject_id == "m001"
    assert got.STATES["subject.subject_id"] == "stated_subject_subject_id"


def test_a_stale_report_is_not_read_as_this_runs(supplied, tmp_path):
    """A file at a path the recipe names outlives the run that wrote it (Part 12 §9)."""
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"problems": [{"level": "error", "message": "last week"}]}))
    got = delivery.fetch(
        "nwb",
        [*ESCAPEWHEEL, "deliver", "nwb"],
        supplied,
        protocol="files-v0.1",
        wanted=sorted(NWBSource.PRODUCES),
        report_path=report,
        workspace=tmp_path / "work",
    )
    assert not [note for note in got.notes if "last week" in note]


def test_what_the_report_says_is_reported(supplied, tmp_path):
    report = tmp_path / "report.json"
    got = delivery.fetch(
        "nwb",
        [*ESCAPEWHEEL, "deliver", "nwb"],
        supplied,
        protocol="stream-v0.1",
        wanted=sorted(NWBSource.PRODUCES),
        report_path=report,
        workspace=tmp_path / "work",
    )
    assert got.notes, "the adapter's own notes travel in its report"
    assert set(codes(got.notes)) == {NoteCode.REPORTED}


def test_a_report_is_not_required(supplied, tmp_path):
    """A build must not require one, and must read a field absent from it as unstated."""
    got = delivery.fetch(
        "nwb",
        [*ESCAPEWHEEL, "deliver", "nwb"],
        supplied,
        protocol="stream-v0.1",
        wanted=sorted(NWBSource.PRODUCES),
        states=sorted(NWBSource.STATES),
        workspace=tmp_path / "work",
    )
    assert got.notes == []
    assert got.stated_subject_subject_id is None


# -- when a delivery is not complete ------------------------------------------------------


def test_a_resource_that_never_arrived_is_a_failure(supplied, tmp_path):
    """Part 05 §4.4: an absent resource is the run having failed, never nothing to say."""
    with pytest.raises(DeliveryFailed) as refused:
        delivery.fetch(
            "nwb",
            [*ESCAPEWHEEL, "deliver", "nwb"],
            {**supplied, "wanted": ["core.electrodes"]},
            protocol="stream-v0.1",
            wanted=["core.electrodes", "core.units"],
            workspace=tmp_path / "work",
        )
    assert [failure.code for failure in refused.value.failures] == [SourceFault.NEVER_ARRIVED]
    assert refused.value.failures[0].where == "core.units"


def test_a_non_zero_exit_is_a_failure_whatever_arrived(supplied, tmp_path):
    """An adapter saying it failed is not overruled by its own output (Part 05 §4.4)."""
    with pytest.raises(DeliveryFailed) as refused:
        delivery.fetch(
            "nwb",
            [*ESCAPEWHEEL, "deliver", "nosuchkind"],
            supplied,
            protocol="stream-v0.1",
            wanted=[],
            workspace=tmp_path / "work",
        )
    assert SourceFault.COMMAND_EXITED in [f.code for f in refused.value.failures]


def test_an_adapter_still_ending_the_sentinel_is_not_cut_off(tmp_path):
    """The sentinel's schema arrives before its batch and end-of-stream marker are written."""
    script = tmp_path / "slow.py"
    script.write_text(
        "import sys, time\n"
        "import pyarrow as pa\n"
        "out = sys.stdout.buffer\n"
        "t = pa.table({'session_id': ['s1']}).replace_schema_metadata({'resource_id': 'core.sessions'})\n"
        "with pa.ipc.new_stream(out, t.schema) as w:\n"
        "    w.write_table(t)\n"
        "end = pa.table({}).replace_schema_metadata({'resource_id': 'end'})\n"
        "with pa.ipc.new_stream(out, end.schema) as w:\n"
        "    w.write_batch(pa.RecordBatch.from_pylist([], schema=end.schema))\n"
        "    out.flush()\n"
        "    time.sleep(0.5)\n"
        "out.flush()\n"
    )
    got = delivery.fetch(
        "slow",
        [sys.executable, str(script)],
        {"root": str(tmp_path)},
        protocol="stream-v0.1",
        wanted=["core.sessions"],
        workspace=tmp_path / "work",
    )
    assert got.tables["core.sessions"].num_rows == 1


def test_a_delivery_cut_short_is_named_by_where_it_stopped(tmp_path):
    """A reader treats end of file as end of stream, so the sentinel is what tells them apart."""
    script = tmp_path / "half.py"
    script.write_text(
        "import sys\n"
        "import pyarrow as pa\n"
        "t = pa.table({'session_id': ['s1']}).replace_schema_metadata({'resource_id': 'core.sessions'})\n"
        "with pa.ipc.new_stream(sys.stdout.buffer, t.schema) as w:\n"
        "    w.write_table(t)\n"
        "sys.stdout.buffer.flush()\n"
    )
    with pytest.raises(DeliveryFailed) as refused:
        delivery.fetch(
            "half",
            [sys.executable, str(script)],
            {"root": str(tmp_path)},
            protocol="stream-v0.1",
            wanted=["core.sessions"],
            workspace=tmp_path / "work",
        )
    assert [failure.code for failure in refused.value.failures] == [SourceFault.NO_SENTINEL]


def test_what_the_adapter_said_is_reported(tmp_path):
    """Standard error is what `files-v0.1` and `stream-v0.1` carry a failure on (Part 05 §4.4)."""
    script = tmp_path / "loud.py"
    script.write_text("import sys\nprint('the source is half written', file=sys.stderr)\nraise SystemExit(3)\n")
    with pytest.raises(DeliveryFailed) as refused:
        delivery.fetch(
            "loud",
            [sys.executable, str(script)],
            {"root": str(tmp_path)},
            protocol="stream-v0.1",
            wanted=[],
            workspace=tmp_path / "work",
        )
    assert [failure.code for failure in refused.value.failures] == [SourceFault.COMMAND_EXITED, SourceFault.NO_SENTINEL]
    assert "half written" in str(refused.value.failures[0])


def test_a_command_that_is_a_string_is_refused(tmp_path):
    """A parse is a quoting convention no recipe declared (Part 05 §3.7)."""
    with pytest.raises(SourceDefect) as refused:
        delivery.fetch(
            "nwb",
            "escapewheel deliver nwb",
            {"root": str(tmp_path)},
            protocol="stream-v0.1",
            wanted=[],
            workspace=tmp_path / "work",
        )
    assert refused.value.code is SourceFault.COMMAND_NOT_A_LIST


def test_an_array_with_nowhere_to_go_is_refused_rather_than_half_delivered(tmp_path):
    """A dense array crosses as bytes under a location a build supplies (Part 12 §5)."""

    class Stages:
        def records(self):
            return {"core.units": [{"unit_id": "7"}]}

        def staged_arrays(self):
            return [object()]

    with pytest.raises(SourceDefect) as refused:
        delivery.serve(Stages(), {}, "stream-v0.1")
    assert refused.value.code is SourceFault.NO_ARRAY_LOCATION


def test_an_array_crosses_as_the_bytes_the_adapter_wrote(tmp_path):
    """The adapter writes it where it was told, named by its resource, which is all a build reads."""
    import numpy as np

    from escapewheel_writer.bindings import StagedArray

    class Stages:
        def records(self):
            return {}

        def staged_arrays(self):
            return [
                StagedArray(
                    values=np.arange(24, dtype="int16").reshape(2, 3, 4),
                    resource_id="core.waveform_mean",
                    declaration_id="core.array_asset_instances",
                    array_asset_id="waveform_mean",
                    chunks=(1, 3, 4),
                )
            ]

    location = tmp_path / "arrays"
    written = io.BytesIO()
    delivery.serve(Stages(), {"array_location": str(location)}, "stream-v0.1", out=written)
    assert (location / "core.waveform_mean.zarr/zarr.json").is_file()
    assert sorted(p.name for p in location.iterdir()) == ["core.waveform_mean.zarr"]

    got = delivery.Delivered("waveforms", {}, arrays=location)
    (staged,) = got.staged_arrays()
    assert (staged.resource_id, staged.declaration_id) == ("core.waveform_mean", "")
    assert staged.values is None and staged.written == location / "core.waveform_mean.zarr"


def test_a_written_array_is_moved_into_staging_and_read_for_what_it_declares(tmp_path, registry):
    """Every field of its manifest entry is in the array or in the build (Part 12 §5)."""
    import numpy as np

    from escapewheel_writer.bindings import StagedArray
    from escapewheel_writer.writer import PacketWriter

    delivered = tmp_path / "delivered"
    delivered.mkdir()
    from escapewheel_writer.arrays import write_zarr

    write_zarr(
        delivered / "waveform_mean.zarr",
        StagedArray(
            values=np.arange(24, dtype="int16").reshape(2, 3, 4),
            resource_id="core.waveform_mean",
            declaration_id="core.array_asset_instances",
            array_asset_id="waveform_mean",
            chunks=(1, 3, 4),
            shard=(2, 3, 4),
            dimension_names=("unit", "channel", "sample"),
        ),
    )
    writer = PacketWriter(registry, packet_id="s001", session="s001")
    writer.add("core.subjects", [{"subject_id": "m001", "species": "Mus musculus", "sex": "male"}])
    writer.add(
        "core.sessions",
        [{"session_id": "s001", "subject_id": "m001", "session_start_time": "2026-01-01T00:00:00Z"}],
    )
    writer.add(
        "core.array_assets",
        [
            {
                "session_id": "s001",
                "array_asset_id": "waveform_mean",
                "array_asset_name": "waveform_mean",
            }
        ],
    )
    writer.add(
        "core.array_dimensions",
        [
            {
                "session_id": "s001",
                "array_asset_id": "waveform_mean",
                "axis_index": axis,
                "dimension_name": name,
                "origin_value": 0.0,
                "step_value": 1.0,
                "coordinate_unit": "1",
            }
            for axis, name in enumerate(("unit", "channel", "sample"))
        ],
    )
    writer.add_array(
        "core.waveform_mean",
        StagedArray(
            values=None,
            resource_id="core.waveform_mean",
            declaration_id="core.array_asset_instances",
            array_asset_id="waveform_mean",
            written=delivered / "waveform_mean.zarr",
        ),
    )
    report = writer.commit(tmp_path / "packet")
    assert report.errors == 0

    entry = next(
        r
        for r in json.loads((tmp_path / "packet/packet.json").read_text())["resources"]
        if r["resource_id"] == "core.waveform_mean"
    )
    assert "physical_profile" not in entry
    assert "codecs" not in entry
    assert entry["size_bytes"] > 0 and entry["digest"]["algorithm"] == "sha256"
    assert not (delivered / "waveform_mean.zarr").exists(), "staging moved it rather than copying"


def _array_writer(registry, rows):
    from escapewheel_writer.writer import PacketWriter

    writer = PacketWriter(registry, packet_id="s001", session="s001")
    writer.add("core.array_assets", rows)
    return writer


def test_a_delivered_array_binds_to_the_catalog_row_carrying_its_name(registry, tmp_path):
    """The directory's name is the row's `resource_id`, and the row supplies the rest (Part 12 §5)."""
    from escapewheel_writer.bindings import StagedArray

    writer = _array_writer(
        registry, [{"session_id": "s001", "array_asset_id": "mean", "resource_id": "core.waveform_mean"}]
    )
    delivered = StagedArray(
        values=None,
        resource_id="core.waveform_mean",
        declaration_id="",
        array_asset_id="",
        written=tmp_path / "core.waveform_mean.zarr",
    )
    writer.add_array("core.waveform_mean", delivered)
    bound = writer._staged_arrays["core.waveform_mean"]
    assert (bound.declaration_id, bound.array_asset_id) == ("core.array_asset_instances", "mean")


def test_a_delivered_array_no_catalog_row_names_is_refused(registry, tmp_path):
    from escapewheel_writer.bindings import StagedArray

    writer = _array_writer(registry, [{"session_id": "s001", "array_asset_id": "mean"}])
    delivered = StagedArray(
        values=None, resource_id="core.waveform_mean", declaration_id="", array_asset_id="", written=tmp_path
    )
    with pytest.raises(UsageError) as refused:
        writer.add_array("core.waveform_mean", delivered)
    assert refused.value.code is UsageFault.CATALOG_ROW_UNBOUND
    assert refused.value.where == "core.waveform_mean"
    assert "binds 0 catalog rows" in str(refused.value)


def test_an_unknown_kind_names_what_this_build_ships():
    with pytest.raises(SourceDefect) as refused:
        delivery.construct("tasklog", {"root": "."})
    assert refused.value.code is SourceFault.UNKNOWN_KIND
    assert refused.value.where == "tasklog"


def test_a_table_too_large_to_hold_arrives_as_the_stream_it_was_sent_as():
    """The one case the streaming path exists for, and the one where the order is the adapter's."""
    import pyarrow as pa

    small = pa.table({"unit_id": ["1", "2"]})
    big = pa.table({"t_tick": list(range(STREAMED_BATCH_ROWS + 1))})
    got = delivery.Delivered("sorter", {"core.units": small, "core.spike_events": big})
    assert got.held("core.units") and not got.held("core.spike_events")
    assert sorted(got.records()) == ["core.units"]
    assert sorted(got.batches()) == ["core.spike_events"]


def test_a_shared_resource_is_held_however_large_it_is():
    """A writer takes one table from one path, since two streams cannot be sorted across a seam."""
    import pyarrow as pa

    big = pa.table({"clock_id": ["harp"] * (STREAMED_BATCH_ROWS + 1)})
    got = delivery.Delivered("sync", {"core.clocks": big}, merged=("core.clocks",))
    assert got.held("core.clocks")
    assert got.batches() == {}


def test_the_protocol_is_read_from_the_term_that_asked_for_it():
    """A build supplies whichever terms its adapter's protocol requires (Part 12 §4)."""
    assert delivery.infers({"socket": "/tmp/a.sock"}) == "flight-v0.1"
    assert delivery.infers({"delivery_root": "/tmp/d"}) == "files-v0.1"
    assert delivery.infers({"root": "/data"}) == "stream-v0.1"


# -- what a build does with one --------------------------------------------------------------


def _spec(tmp_path, nwb, **delivery_fields):
    """A source entry the recipe would carry for a delivered NWB."""
    from escapewheel_writer.recipe import DeliverySpec, SourceSpec

    fields = {"command": (*ESCAPEWHEEL, "deliver", "nwb"), "protocol": "stream-v0.1", **delivery_fields}
    return SourceSpec(
        kind="nwb",
        root=nwb,
        owns=("core.electrodes", "core.probes"),
        options={"zone": ZONE, "interval_kind": KIND},
        delivery=DeliverySpec(**fields),
    )


def _context(session_id=SESSION, **fields):
    """The build's context by the time the NWB source runs: the sorter has minted its units."""
    from escapewheel_writer.session import Context

    fields.setdefault("units", [{"device_name": "probeA", "local_unit_label": "7", "unit_id": 1}])
    return Context(session_id=session_id, **fields)


def test_a_build_reaches_a_delivered_source_through_the_same_construction(tmp_path, nwb, harp):
    """Which route a source took reaches nothing downstream: what comes back is adapter-shaped."""
    from escapewheel_writer.session import build_source

    context = _context(reference=harp, workspace=tmp_path / "work")
    built = build_source(_spec(tmp_path, nwb), None, context)
    assert isinstance(built, delivery.Delivered)
    assert sorted(built.offers()) == sorted(NWBSource.PRODUCES)
    assert built.offers()["core.electrodes"] == 2
    # Held rather than streamed: a table this size is one the writer sorts, and the streaming
    # path writes through untouched.
    assert all(built.held(resource) for resource in built.tables)
    assert built.batches() == {}
    assert sorted(built.records()) == sorted(NWBSource.PRODUCES)


def test_a_shipped_adapter_whose_entry_names_no_protocol_is_served_over_one(tmp_path, nwb, harp):
    """Part 12 §3: a delivery table takes an adapter this build ships out of process."""
    from escapewheel_writer.session import build_source

    said = []
    context = _context(reference=harp, workspace=tmp_path / "work", say=said.append)
    built = build_source(_spec(tmp_path, nwb, protocol=""), None, context)
    assert isinstance(built, delivery.Delivered)
    assert any("over stream-v0.1" in line for line in said), said


def test_a_rerun_reads_nothing_an_earlier_run_left(tmp_path, supplied):
    """Part 05 §2: a build supplies each location empty, so a leftover cannot pass for a delivery."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    leftover = tmp_path / "work" / "delivery"
    leftover.mkdir(parents=True)
    pq.write_table(pa.table({"trial_id": [1]}), leftover / "core.trials.parquet")
    got = delivery.fetch(
        "quiet",
        [sys.executable, "-c", "import sys; sys.stdin.read()"],
        supplied,
        protocol="files-v0.1",
        wanted=[],
        workspace=tmp_path / "work",
    )
    assert got.tables == {}


def test_a_file_written_outside_the_delivery_root_is_not_a_delivery(tmp_path, supplied):
    """Part 05 §2: a build reads a delivery from nowhere but the locations it supplied."""
    script = tmp_path / "astray.py"
    script.write_text(
        "import sys, pyarrow as pa, pyarrow.parquet as pq\nsys.stdin.read()\n"
        f"pq.write_table(pa.table({{'trial_id': [1]}}), {str(tmp_path / 'core.trials.parquet')!r})\n"
    )
    with pytest.raises(DeliveryFailed) as refused:
        delivery.fetch(
            "astray",
            [sys.executable, str(script)],
            supplied,
            protocol="files-v0.1",
            wanted=["core.trials"],
            workspace=tmp_path / "work",
        )
    assert [failure.code for failure in refused.value.failures] == [SourceFault.NEVER_ARRIVED]
    assert refused.value.failures[0].where == "core.trials"


def test_an_array_location_is_under_staging_and_supplied_empty(tmp_path):
    """So an array moves into the packet by rename (Part 12 §5), and no leftover binds."""
    from escapewheel_writer.recipe import SourceSpec
    from escapewheel_writer.session import filled_terms

    context = _context(staging=tmp_path / "packet" / "staging")
    stale = context.staging / "deliveries" / "waveforms" / "core.waveform_mean.zarr"
    stale.mkdir(parents=True)
    spec = SourceSpec(kind="waveforms", root=tmp_path, owns=())
    location = filled_terms(spec, None, context, ["array_location"])["array_location"]
    assert location == str(context.staging / "deliveries" / "waveforms")
    assert not stale.exists() and not stale.parent.exists()


def _recipe_declaring(tmp_path, spec, *, subject_id):
    """A recipe carrying one delivered source and a subject to compare it against."""
    from escapewheel_writer.recipe import Recipe

    path = tmp_path / "session.toml"
    path.write_text(
        f'[packet]\nid = "s001"\nregistry = "reg.json"\n\n[session]\nsession_id = "{SESSION}"\n'
        f'\n[subject]\nsubject_id = "{subject_id}"\n'
    )
    return replace(Recipe.load(path), sources=(spec,))


def test_a_delivered_source_still_has_its_facts_compared(tmp_path, nwb, harp):
    """Part 05 §3.6's comparison runs on the report's `stated` as it runs on an attribute."""
    from escapewheel_writer.session import build_source, compare_declared_facts

    spec = _spec(tmp_path, nwb, report_path=tmp_path / "report.json")
    context = _context(reference=harp, workspace=tmp_path / "work")
    built = build_source(spec, None, context)
    recipe = _recipe_declaring(tmp_path, spec, subject_id="786867")
    with pytest.raises(SourceDefect) as refused:
        compare_declared_facts(spec, built, context, recipe)
    assert refused.value.code is SourceFault.FACT_DIFFERS
    assert refused.value.where == "subject.subject_id"


def test_the_harvest_reads_a_delivered_source_s_rows(tmp_path, nwb, harp):
    """What the sources after it consume comes from the rows, not from the object that made them.

    Which is what lets a source be delivered at all: by the time a build harvests, the process
    that produced the rows has exited.
    """
    from escapewheel_writer.session import build_source, harvest, rows_reader

    spec = _spec(tmp_path, nwb)
    context = _context(reference=harp, workspace=tmp_path / "work")
    built = build_source(spec, None, context)
    harvest(
        spec, built, context, _recipe_declaring(tmp_path, spec, subject_id="m001"), rows_reader(built, built.records())
    )
    assert context.event_streams, "the NWB declares the streams a later source's windows cover"
    assert [row["clock_id"] for row in context.clocks.values()] == ["harp"]


# -- the channel what a build supplies crosses by --------------------------------------------


def test_what_a_build_supplies_crosses_on_standard_input(tmp_path, supplied):
    """Part 12 §4: on standard input, with no argument added to the command the recipe wrote."""
    script = tmp_path / "echo.py"
    script.write_text(
        "import json, sys\n"
        "seen = {'argv': sys.argv[1:], 'stdin': json.loads(sys.stdin.buffer.read())}\n"
        "open(sys.argv[1], 'w').write(json.dumps(seen))\n"
        "raise SystemExit(7)\n"
    )
    seen = tmp_path / "seen.json"
    with pytest.raises(DeliveryFailed) as refused:
        delivery.fetch(
            "echo",
            [sys.executable, str(script), str(seen)],
            supplied,
            protocol="stream-v0.1",
            wanted=[],
            workspace=tmp_path / "work",
        )
    assert SourceFault.COMMAND_EXITED in [f.code for f in refused.value.failures]
    crossed = json.loads(seen.read_text())
    assert crossed["argv"] == [str(seen)], "the command is what the recipe wrote, and nothing more"
    assert crossed["stdin"]["root"] == supplied["root"]
    assert crossed["stdin"]["options"] == supplied["options"]


def test_a_term_larger_than_an_argument_crosses(tmp_path, supplied):
    """The failure this channel replaces: Linux caps one argument at 32 pages, 131,072 bytes."""
    units = [{"device_name": "probeA", "local_unit_label": str(n), "unit_id": n} for n in range(4_505)]
    crossing = json.dumps({**supplied, "units": units})
    assert len(crossing) > 131_072, "the object has to be past the limit for this to test anything"

    script = tmp_path / "count.py"
    script.write_text(
        "import json, sys\nopen(sys.argv[1], 'w').write(str(len(json.loads(sys.stdin.buffer.read())['units'])))\n"
    )
    counted = tmp_path / "counted"
    got = delivery.fetch(
        "count",
        [sys.executable, str(script), str(counted)],
        {**supplied, "units": units},
        protocol="files-v0.1",
        wanted=[],
        workspace=tmp_path / "work",
    )
    assert counted.read_text() == "4505"
    assert got.tables == {}


# -- what a delivery says about what it references ------------------------------------------


class Referencing:
    """A source whose resources are a store's, as the LFP and video adapters' are."""

    PRODUCES = frozenset({"core.array_assets", "core.media_assets"})

    def records(self):
        return {
            "core.array_assets": [{"array_asset_id": "46101.lfp", "array_asset_name": "46101.lfp"}],
            "core.media_assets": [{"media_asset_id": "bottom_camera", "media_asset_name": "bottom_camera"}],
        }

    def external_arrays(self):
        from escapewheel_writer.bindings import ExternalArray

        return {
            "core.46101.lfp": ExternalArray(
                array_asset_id="46101.lfp",
                declaration_id="core.array_asset_instances",
                uri="s3://bucket/ElectricalSeries46101-LFP/data",
                physical_profile="zarr_v2",
                codecs=("blosc",),
                size_bytes=582991872,
            )
        }

    def external_media(self):
        from escapewheel_writer.bindings import ExternalMedia

        return {
            "core.bottom_camera": ExternalMedia(
                media_asset_id="bottom_camera",
                declaration_id="core.media_asset_instances",
                uri="s3://bucket/bottom_camera.mp4",
                format="mp4",
                size_bytes=2884901888,
            )
        }


@pytest.mark.parametrize("protocol", ["stream-v0.1", "files-v0.1"])
def test_what_a_source_references_crosses_with_its_rows(protocol, tmp_path):
    """The half of a manifest no row holds and no build may go looking for (Part 12 §5)."""
    script = tmp_path / "serve.py"
    script.write_text(
        "import json, sys\n"
        "from escapewheel_writer import delivery\n"
        f"{inspect.getsource(Referencing)}\n"
        "delivery.serve(Referencing(), json.loads(sys.stdin.buffer.read()), "
        f"{protocol!r})\n"
    )
    got = delivery.fetch(
        "lfp",
        [sys.executable, str(script)],
        {"root": str(tmp_path), "session_id": "s1"},
        protocol=protocol,
        wanted=["core.array_assets", "core.media_assets"],
        workspace=tmp_path / "work",
    )
    assert delivery.RESOURCES not in got.tables, "the document is not one of the resources asked for"
    (array,) = got.external_arrays().values()
    assert array.uri == "s3://bucket/ElectricalSeries46101-LFP/data"
    (media,) = got.external_media().values()
    assert (media.uri, media.size_bytes) == ("s3://bucket/bottom_camera.mp4", 2884901888)


def test_a_malformed_resource_document_is_refused(tmp_path, supplied):
    """Refused rather than reported: a bad entry merged into a manifest misdescribes the packet."""
    script = tmp_path / "bad.py"
    script.write_text(
        "import json, sys\n"
        "import pyarrow as pa\n"
        "from escapewheel_writer import delivery\n"
        "json.loads(sys.stdin.buffer.read())\n"
        "out = sys.stdout.buffer\n"
        "doc = json.dumps({'resources': [{'uri': 'file:///x'}]})\n"
        "delivery._write(out, delivery.RESOURCES, delivery.as_table([{'document': doc}]))\n"
        "delivery._write(out, delivery.SENTINEL, pa.table({}))\n"
        "out.flush()\n"
    )
    with pytest.raises(DeliveryFailed) as refused:
        delivery.fetch(
            "bad",
            [sys.executable, str(script)],
            supplied,
            protocol="stream-v0.1",
            wanted=[],
            workspace=tmp_path / "work",
        )
    assert [failure.code for failure in refused.value.failures] == [SourceFault.DOCUMENT_SHAPE]


def test_a_referenced_resource_no_row_declares_is_refused(tmp_path, supplied):
    """Part 12 §5: a build rejects an entry that does not resolve rather than dropping it."""
    script = tmp_path / "stray.py"
    script.write_text(
        "import json, sys\n"
        "import pyarrow as pa\n"
        "from escapewheel_writer import delivery\n"
        "json.loads(sys.stdin.buffer.read())\n"
        "out = sys.stdout.buffer\n"
        "entry = {'resource_id': 'core.nowhere', 'declaration_id': 'core.media_asset_instances',\n"
        "         'uri': 's3://bucket/nowhere.mp4', 'external': True}\n"
        "doc = json.dumps({'resources': [entry]})\n"
        "delivery._write(out, delivery.RESOURCES, delivery.as_table([{'document': doc}]))\n"
        "delivery._write(out, delivery.SENTINEL, pa.table({}))\n"
        "out.flush()\n"
    )
    with pytest.raises(SourceDefect) as refused:
        delivery.fetch(
            "stray",
            [sys.executable, str(script)],
            supplied,
            protocol="stream-v0.1",
            wanted=[],
            workspace=tmp_path / "work",
        )
    assert refused.value.code is SourceFault.REFERENCE_UNBOUND
    assert refused.value.where == "core.nowhere"


@pytest.mark.parametrize(
    "extra",
    [
        pytest.param({"validation_state": "passed"}, id="validation_state"),
        pytest.param({"derived_from": ["core.sessions"]}, id="derived_from"),
        pytest.param({"processing_run_id": "run"}, id="processing_run_id"),
        pytest.param({"verified_at": "yesterday"}, id="malformed_date_time"),
    ],
)
def test_a_delivered_entry_carries_no_build_supplied_member(extra):
    """Part 12 §5: the delivered entry is the manifest entry less what the build supplies."""
    entry = {
        "resource_id": "core.lfp",
        "declaration_id": "core.array_asset_instances",
        "uri": "s3://bucket/lfp.zarr",
        "external": True,
    }
    assert delivery._refuses({"resources": [entry]}) is None
    assert delivery._refuses({"resources": [{**entry, **extra}]}) is not None
