"""The boundary a build reaches a source through: a declaration, a command, and three protocols.

Every test here runs the adapter in a process of its own, because that is the thing being tested:
what crosses is one JSON object and what comes back is rows, and neither may depend on the two
halves sharing an interpreter.
"""

import json
import sys
from dataclasses import replace

import pytest

from escapewheel_writer import Clock, declaration, delivery
from escapewheel_writer.clock import HARP_TICK_RATE_HZ
from escapewheel_writer.recipe import TERMS
from escapewheel_writer.sources import ADAPTERS, NWBSource, SourceDefect
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
    """Generated rather than maintained (Part 03 §11.5), so this is what an author starts from."""
    jsonschema = pytest.importorskip("jsonschema")
    document = declaration.of(ADAPTERS[kind], kind, "stream-v0.1")
    assert not list(jsonschema.Draft202012Validator(declaration.schema()).iter_errors(document))
    assert document["kind"] == kind


def test_ownership_from_the_documents_is_ownership_from_the_classes():
    """The two forms are one declaration, so what a build settles from them cannot differ."""
    from_document = {
        resource: kind
        for kind in sorted(ADAPTERS)
        for resource in declaration.of(ADAPTERS[kind], kind, "stream-v0.1")["produces"]
    }
    from_class = {resource: kind for kind in sorted(ADAPTERS) for resource in sorted(ADAPTERS[kind].PRODUCES)}
    assert from_document == from_class


def test_a_document_round_trips_through_a_file(tmp_path):
    written = tmp_path / "nwb.json"
    document = declaration.of(ADAPTERS["nwb"], "nwb", "flight-v0.1")
    written.write_text(json.dumps(document))
    assert declaration.load(written) == document


@pytest.mark.parametrize(
    ("broken", "expected"),
    [
        ({"protocol": "carrier-pigeon-v1"}, "in no group"),
        ({"produces": ["core.tirals"]}, "no loaded registry declares"),
        ({"states": ["subject.sbuject_id"]}, "is no column of"),
        ({"needs": ["open_store"]}, "neither a term nor an option"),
        ({"needs": ["socket"]}, "a protocol supplies"),
    ],
)
def test_a_build_refuses_what_it_can_check_without_the_adapter(broken, expected, registry):
    """Part 03 §11.5's checks, each firing on its own and naming what is wrong."""
    sound = declaration.of(ADAPTERS["nwb"], "nwb", "stream-v0.1")
    found = declaration.refusals(
        {**sound, **broken},
        tables=registry["tables"],
        options={"zone", "interval_kind"},
        terms=TERMS,
    )
    assert any(expected in refusal for refusal in found), found


def test_a_sound_declaration_is_refused_for_nothing(registry):
    sound = declaration.of(ADAPTERS["nwb"], "nwb", "stream-v0.1")
    assert (
        declaration.refusals(
            sound, tables=registry["tables"], options={"zone", "interval_kind"}, terms=TERMS
        )
        == []
    )


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
    delivered = got.batches()
    for resource in wanted:
        arrived = [row for batch in delivered[resource] for row in batch.to_pylist()]
        assert arrived == delivery.as_table(here.get(resource, [])).to_pylist(), resource


def test_stage_one_agrees_with_what_arrived(supplied, tmp_path):
    got = delivery.fetch(
        "nwb",
        [*ESCAPEWHEEL, "deliver", "nwb"],
        supplied,
        protocol="stream-v0.1",
        wanted=sorted(NWBSource.PRODUCES),
        workspace=tmp_path / "work",
    )
    counted = {r: sum(b.num_rows for b in batches) for r, batches in got.batches().items()}
    assert got.offers() == counted


def test_a_build_asks_for_only_what_the_recipe_leaves_it_owning(supplied, tmp_path):
    """`wanted` is a term a build supplies and an adapter may act on (Part 03 §11.2)."""
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
    """No static document can carry them, because each needs the source read (Part 09 §5.8)."""
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
    """A file at a path the recipe names outlives the run that wrote it (Part 09 §5.8)."""
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
    assert all(note.startswith("nwb reports ") for note in got.notes)


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
    with pytest.raises(SourceDefect, match="never arrived"):
        delivery.fetch(
            "nwb",
            [*ESCAPEWHEEL, "deliver", "nwb"],
            {**supplied, "wanted": ["core.electrodes"]},
            protocol="stream-v0.1",
            wanted=["core.electrodes", "core.units"],
            workspace=tmp_path / "work",
        )


def test_a_non_zero_exit_is_a_failure_whatever_arrived(supplied, tmp_path):
    """An adapter saying it failed is not overruled by its own output (Part 05 §4.4)."""
    with pytest.raises(SourceDefect, match="exited"):
        delivery.fetch(
            "nwb",
            [*ESCAPEWHEEL, "deliver", "nosuchkind"],
            supplied,
            protocol="stream-v0.1",
            wanted=[],
            workspace=tmp_path / "work",
        )


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
    with pytest.raises(SourceDefect, match="did not end with the sentinel"):
        delivery.fetch(
            "half",
            [sys.executable, str(script)],
            {"root": str(tmp_path)},
            protocol="stream-v0.1",
            wanted=["core.sessions"],
            workspace=tmp_path / "work",
        )


def test_what_the_adapter_said_is_reported(tmp_path):
    """Standard error is what `files-v0.1` and `stream-v0.1` carry a failure on (Part 05 §4.4)."""
    script = tmp_path / "loud.py"
    script.write_text("import sys\nprint('the source is half written', file=sys.stderr)\nraise SystemExit(3)\n")
    with pytest.raises(SourceDefect, match="half written"):
        delivery.fetch(
            "loud",
            [sys.executable, str(script)],
            {"root": str(tmp_path)},
            protocol="stream-v0.1",
            wanted=[],
            workspace=tmp_path / "work",
        )


def test_a_command_that_is_a_string_is_refused(tmp_path):
    """A parse is a quoting convention no recipe declared (Part 05 §3.7)."""
    with pytest.raises(SourceDefect, match="argument list"):
        delivery.fetch(
            "nwb",
            "escapewheel deliver nwb",
            {"root": str(tmp_path)},
            protocol="stream-v0.1",
            wanted=[],
            workspace=tmp_path / "work",
        )


def test_a_source_that_stages_an_array_is_refused_rather_than_half_delivered(tmp_path):
    """A dense array crosses as a reference to a location a build supplies (Part 03 §11.3)."""

    class Stages:
        def records(self):
            return {"core.units": [{"unit_id": "7"}]}

        def staged_arrays(self):
            return [object()]

    with pytest.raises(SourceDefect, match="crosses as a reference"):
        delivery.serve(Stages(), {}, "stream-v0.1")


def test_an_unknown_kind_names_what_this_build_ships():
    with pytest.raises(SourceDefect, match="unknown source kind"):
        delivery.construct("tasklog", {"root": "."})


def test_the_protocol_is_read_from_the_term_that_asked_for_it():
    """A build supplies whichever terms its adapter's protocol requires (Part 03 §11.2)."""
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
    from escapewheel_writer.session import _build_source

    context = _context(reference=harp, workspace=tmp_path / "work")
    built = _build_source(_spec(tmp_path, nwb), None, context)
    assert isinstance(built, delivery.Delivered)
    assert sorted(built.offers()) == sorted(NWBSource.PRODUCES)
    assert built.offers()["core.electrodes"] == 2
    assert built.records() == {}, "a delivered resource travels as batches, as a file's rows do"


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
    from escapewheel_writer.session import _build_source, _compare_declared_facts

    spec = _spec(tmp_path, nwb, report_path=tmp_path / "report.json")
    context = _context(reference=harp, workspace=tmp_path / "work")
    built = _build_source(spec, None, context)
    recipe = _recipe_declaring(tmp_path, spec, subject_id="786867")
    with pytest.raises(SourceDefect, match="786867"):
        _compare_declared_facts(spec, built, context, recipe)
