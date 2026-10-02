"""A delivery states its adapter's compensations in a table a build records and never stages (Part 12 §5).

Each case runs the adapter in a process of its own under every protocol, since the table crosses as
any table of the delivery does and a build reads each protocol by a different means.
"""

import json
import sys
from pathlib import Path

import pytest
from escapewheel_reader import open_packet

from escapewheel_writer import declaration, reading, serving
from escapewheel_writer.errors import DeliveryFailed, SourceFault
from escapewheel_writer.sources.compensations import describe, recordable
from tests import compensatingfixture
from tests.compensatingfixture import APPLIED

PROTOCOLS = ["files-v0.1", "stream-v0.1", "flight-v0.1"]
ROUTES = ["in-process", *PROTOCOLS]

#: An adapter delivering one row of `core.sessions` and, where `stated` names one, a table under
#: the reserved identifier, by whichever protocol the build reached it over.
STATING = """import json, sys
from pathlib import Path
import pyarrow as pa
from escapewheel_writer import serving
supplied = json.loads(sys.stdin.buffer.read())
delivery = [("core.sessions", pa.table({{"session_id": ["s1"]}})){stated}]
protocol = serving.infers(supplied)
if protocol == "stream-v0.1":
    serving._serve_stream(delivery, sys.stdout.buffer)
elif protocol == "files-v0.1":
    serving._serve_files(delivery, Path(supplied["delivery_root"]))
else:
    serving._serve_flight(delivery, supplied["socket"])
"""

#: How a delivered `Keeping` runs: its own process, handed what a build supplies on standard input.
SERVE = """import json, sys
sys.path.insert(0, {here!r})
from escapewheel_writer import serving
from tests.compensatingfixture import Keeping
supplied = json.loads(sys.stdin.buffer.read())
serving.serve(Keeping(supplied["root"], session_id=supplied["session_id"]), supplied, serving.infers(supplied))
"""

HERE = str(Path(__file__).resolve().parents[1])

KEPT = {"id": "x.offset_kept", "defect": "the offset is local mean time", "action": "kept as stored"}


def _table(*rows, **columns):
    """Source text building a table of these rows, each column a string column unless `columns` gives it."""
    names = list(dict.fromkeys(name for row in rows for name in row))
    held = {name: f"pa.array({[row.get(name) for row in rows]!r}, pa.string())" for name in names}
    held.update(columns)
    return "pa.table({" + ", ".join(f"{name!r}: {value}" for name, value in held.items()) + "})"


def _fetch(tmp_path, protocol, stated, kind="thermistor"):
    """Run an adapter delivering `stated` under `compensations`, or no such table where it is None."""
    if protocol == "flight-v0.1":
        pytest.importorskip("pyarrow.flight")
    script = tmp_path / f"{kind}.py"
    script.write_text(STATING.format(stated="" if stated is None else f', ("compensations", {stated})'))
    return reading.fetch(
        kind,
        [sys.executable, str(script)],
        {"root": str(tmp_path), "session_id": "s1"},
        protocol=protocol,
        wanted=["core.sessions"],
        workspace=tmp_path / f"work-{kind}",
    )


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_a_delivered_adapter_states_what_it_states_in_process(protocol, tmp_path):
    """Part 05 §4.3: an adapter reached by a protocol states each compensation it applied in the table."""
    if protocol == "flight-v0.1":
        pytest.importorskip("pyarrow.flight")
    script = tmp_path / "serve.py"
    script.write_text(SERVE.format(here=HERE))
    got = reading.fetch(
        "keeping",
        [sys.executable, str(script)],
        {"root": str(tmp_path), "session_id": "s1"},
        protocol=protocol,
        wanted=["core.media_assets"],
        workspace=tmp_path / "work",
    )
    assert got.compensated == describe([APPLIED])
    assert all(got.compensated[0][text] for text in ("id", "defect", "action", "evidence"))


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize(
    "stated",
    [None, _table(**{name: "pa.array([], pa.string())" for name in KEPT})],
    ids=["no table", "an empty table"],
)
def test_an_absent_table_and_an_empty_one_each_state_none(protocol, stated, tmp_path):
    assert _fetch(tmp_path, protocol, stated).compensated == []


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize(
    "stated",
    [
        _table(KEPT),
        _table({**KEPT, "evidence": None}),
        _table(KEPT, evidence="pa.nulls(1)"),
    ],
    ids=["no evidence column", "a null evidence", "an evidence column of the null type"],
)
def test_a_compensation_stating_no_evidence_is_recorded_without_one(protocol, stated, tmp_path):
    got = _fetch(tmp_path, protocol, stated)
    assert got.compensated == [{**KEPT, "evidence": None}]
    assert recordable(got.compensated) == [KEPT]


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize(
    ("stated", "said"),
    [
        (_table({"defect": "d", "action": "a"}), "lacks the required column id"),
        (_table({"id": "x.y", "action": "a"}), "lacks the required column defect"),
        (_table({"id": "x.y", "defect": "d"}), "lacks the required column action"),
        (_table(KEPT, {**KEPT, "id": None}), "is null or empty in id at row 2"),
        (_table({**KEPT, "defect": ""}), "is null or empty in defect at row 1"),
        (_table({**KEPT, "action": None}, KEPT), "is null or empty in action at row 1"),
        (_table(KEPT, id="pa.array([7])"), "holds id as int64, which is not a string type"),
        (_table(), "lacks the required column id"),
    ],
    ids=[
        "no id column",
        "no defect column",
        "no action column",
        "a null id",
        "an empty defect",
        "a null action",
        "an id that is no string",
        "an empty table of no columns",
    ],
)
def test_a_table_lacking_required_text_is_refused_naming_the_source(protocol, stated, said, tmp_path):
    """An empty table is read as stating none only where it has the columns the section gives it."""
    with pytest.raises(DeliveryFailed) as refused:
        _fetch(tmp_path, protocol, stated)
    assert {failure.code for failure in refused.value.failures} == {SourceFault.COMPENSATIONS_SHAPE}
    assert {failure.where for failure in refused.value.failures} == {serving.COMPENSATIONS}
    assert str(refused.value).startswith("thermistor: the compensations table ")
    assert said in str(refused.value)


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_a_column_the_table_is_not_given_is_ignored(protocol, tmp_path):
    got = _fetch(tmp_path, protocol, _table({**KEPT, "evidence": "one file", "severity": "low"}))
    assert got.compensated == [{**KEPT, "evidence": "one file"}]


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_two_sources_stating_one_identifier_are_one_only_where_every_text_agrees(protocol, tmp_path):
    """Part 05 §4.3: two sharing an identifier and differing in any other text are both recorded."""
    first = _fetch(tmp_path, protocol, _table(KEPT), "first")
    same = _fetch(tmp_path, protocol, _table(KEPT), "same")
    other = {**KEPT, "action": "replaced with the session's zone"}
    differing = _fetch(tmp_path, protocol, _table(other), "differing")
    assert recordable([*first.compensated, *same.compensated]) == [KEPT]
    assert recordable([*first.compensated, *differing.compensated]) == [KEPT, other]


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_the_table_is_no_resource_the_source_was_left_owning(protocol, tmp_path):
    """Neither counted nor offered for staging: `wanted` names one resource and one is what arrived."""
    got = _fetch(tmp_path, protocol, _table(KEPT))
    assert sorted(got.tables) == ["core.sessions"]
    assert got.offers() == {"core.sessions": 1}


SESSION = """
[session]
session_id = "s001"
subject_id = "m001"
session_start_time = "2026-08-27T00:00:00Z"

[subject]
subject_id = "m001"
species = "Mus musculus"
sex = "male"

[[clock]]
clock_id = "harp"
name = "harp"
tick_rate_num = 31250
origin = "harp_epoch"
"""


def _built(tmp_path, registry, monkeypatch, route):
    """Commit a packet whose one source is `Keeping`, reached by `route`, and return its root."""
    from escapewheel_writer.recipe import Recipe
    from escapewheel_writer.session import build

    if route == "flight-v0.1":
        pytest.importorskip("pyarrow.flight")
    monkeypatch.setattr("escapewheel_writer.sources.discovered", lambda: {"keeping": compensatingfixture.Keeping})
    source = f'\n[[source]]\nkind = "keeping"\nroot = "{tmp_path}"\nowns = ["core.media_assets"]\n'
    if route == "in-process":
        source += "in_process = true\n"
    else:
        script = tmp_path / "serve.py"
        script.write_text(SERVE.format(here=HERE))
        (tmp_path / "keeping.json").write_text(
            json.dumps(declaration.document_of(compensatingfixture.Keeping, "keeping"))
        )
        command = json.dumps([sys.executable, str(script)])
        source += f'\n[source.delivery]\ndeclaration = "keeping.json"\nprotocol = "{route}"\ncommand = {command}\n'
    path = tmp_path / "session.toml"
    path.write_text(f'[packet]\nid = "s001"\nout = "{tmp_path / "packet"}"\n' + SESSION + source)
    recipe = Recipe.load(path)
    report = build(recipe, registry).commit(recipe.out)
    assert report.passed, [(f.check, f.message) for f in report.findings]
    return recipe.out


@pytest.mark.parametrize("route", ROUTES)
def test_the_import_run_records_a_compensation_whatever_the_route(tmp_path, registry, monkeypatch, route):
    """Part 05 §4.3: the record a packet keeps is the one the adapter leaves run in the writer's process."""
    root = _built(tmp_path, registry, monkeypatch, route)
    (run,) = [
        row for row in open_packet(root).table("core.processing_runs").to_pylist() if row["activity_type"] == "import"
    ]
    assert json.loads(run["parameters"])["compensations"] == describe([APPLIED])


@pytest.mark.parametrize("route", PROTOCOLS)
def test_the_table_reaches_neither_the_packet_nor_its_manifest(tmp_path, registry, monkeypatch, route):
    """Part 12 §5: a build stages no such table and resolves no declaration for it."""
    root = _built(tmp_path, registry, monkeypatch, route)
    manifest = json.loads((root / "packet.json").read_text())
    assert serving.COMPENSATIONS not in {entry["resource_id"] for entry in manifest["resources"]}
    assert not [path for path in root.rglob("*") if serving.COMPENSATIONS in path.name]
