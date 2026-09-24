"""A packet carries an extension's table the same way it carries a core one (R17)."""

import copy
import json
from pathlib import Path

import pyarrow as pa
import pytest
from escapewheel_reader import open_packet
from escapewheel_validator import RegistryRejected

from escapewheel_writer import PacketWriter
from escapewheel_writer.writer import CommitRefused

EXTENSION = {
    "$schema": "https://escapewheel.org/schemas/registry/0.6.0",
    "registry_id": "task",
    "registry_version": "0.1.0",
    "logical_standard_version": "escapewheel-logical-v0.1",
    "rule_language": "escapewheel-rule-sql-v0.1",
    "extension_id": "task",
    "resources": {
        "task.trials": {
            "content_class": "extension",
            "kind": "table",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "optional",
            "table": {
                "columns": [
                    {
                        "name": "session_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "Session identity.",
                    },
                    {
                        "name": "interval_kind",
                        "type": "string",
                        "presence": "required",
                        "role": "discriminator",
                        "resolves": "required",
                        "description": "Interval kind declaration.",
                    },
                    {
                        "name": "trial_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "carried",
                        "description": "Source trial identity.",
                    },
                    {
                        "name": "choice",
                        "type": "string",
                        "presence": "nullable",
                        "role": "data",
                        "vocabulary": "closed",
                        "enum": ["left", "right"],
                        "description": "Choice.",
                    },
                ],
                "primary_key": ["session_id", "trial_id"],
                "references": [
                    {
                        "columns": ["session_id", "interval_kind", "trial_id"],
                        "resource": "core.intervals",
                        "resource_columns": ["session_id", "interval_kind", "interval_id"],
                    }
                ],
                "rules": [],
            },
        }
    },
}


TRIALS = [
    {
        "session_id": "s001",
        "interval_kind": "task.trials",
        "interval_id": 0,
        "clock_id": "harp_s001",
        "start_tick": 0,
        "stop_tick": 99,
    },
    {
        "session_id": "s001",
        "interval_kind": "task.trials",
        "interval_id": 1,
        "clock_id": "harp_s001",
        "start_tick": 200,
        "stop_tick": 299,
    },
]


def _commit(root, registry, minimal, *, choice="left", extension=EXTENSION):
    writer = PacketWriter(registry, packet_id=root.name, extensions=[extension])
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    writer.add("core.intervals", TRIALS)
    writer.add(
        "task.trials",
        [
            {
                "session_id": t["session_id"],
                "interval_kind": "task.trials",
                "trial_id": t["interval_id"],
                "choice": choice,
            }
            for t in TRIALS
        ],
    )
    return writer.commit(root)


def test_an_extension_table_is_written_and_validates(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    report = _commit(root, registry, minimal)
    assert report.passed, [f.check for f in report.findings]
    assert (root / "tables" / "task" / "trials.parquet").is_file()


def test_the_packet_declares_the_extension_and_carries_its_registry(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    manifest = json.loads((root / "packet.json").read_text())
    descriptor = manifest["registries"]["task"]
    assert {k: descriptor[k] for k in ("role", "version", "path")} == {
        "role": "extension",
        "version": "0.1.0",
        "path": "registries/task/0.1.0.json.gz",
    }
    assert (root / descriptor["path"]).is_file()
    assert open_packet(root).extensions()["task"]["extension_id"] == "task"


def test_the_entry_binds_the_extension_declaration(tmp_path, registry, minimal):
    """The declaration binding selects the sole owning extension registry."""
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    entry = next(
        r for r in json.loads((root / "packet.json").read_text())["resources"] if r["resource_id"] == "task.trials"
    )
    assert entry["declaration_id"] == "task.trials"


def test_a_failing_extension_refuses_the_commit(tmp_path, registry, minimal):
    """Part 05 §9.2: a packet is published only whole, so an extension's failure refuses it."""
    root = tmp_path / "s001"
    with pytest.raises(CommitRefused) as refused:
        _commit(root, registry, minimal, choice="sideways")
    report = refused.value.report
    assert (report.verdict(), report.verdict("core"), report.verdict("task")) == ("failed", "passed", "failed")
    assert "task.trials.choice.in_vocabulary" in {f.check for f in report.findings if f.registry == "task"}
    assert not (root / "packet.json").exists()


def test_an_incomplete_verdict_refuses_the_commit(tmp_path, registry, minimal):
    """Part 05 §9.2: an unjudged packet is not a passing one, so the writer publishes nothing."""
    overflowing = copy.deepcopy(EXTENSION)
    overflowing["resources"]["task.trials"]["table"]["rules"].append(
        {
            "id": "task.trials.overflow",
            "level": "error",
            "message": "an evaluation that cannot complete",
            "sql": "SELECT CAST(trial_id + 1000 AS DECIMAL(38,0)) * 99999999999999999999999999999999999999 AS x "
            "FROM task.trials",
        }
    )
    root = tmp_path / "s001"
    with pytest.raises(CommitRefused) as refused:
        _commit(root, registry, minimal, extension=overflowing)
    report = refused.value.report
    assert (report.verdict(), report.verdict("task")) == ("incomplete", "incomplete")
    assert report.errors == 0
    assert not (root / "packet.json").exists()


def test_a_core_table_cannot_be_redefined(registry):
    stray = {**EXTENSION, "resources": {"core.intervals": EXTENSION["resources"]["task.trials"]}}
    with pytest.raises(RegistryRejected) as caught:
        PacketWriter(registry, packet_id="s001", extensions=[stray])
    assert caught.value.result.state == "invalid"


def test_an_unnamespaced_table_is_refused(registry):
    stray = {**EXTENSION, "resources": {"elsewhere.trials": EXTENSION["resources"]["task.trials"]}}
    with pytest.raises(RegistryRejected) as caught:
        PacketWriter(registry, packet_id="s001", extensions=[stray])
    assert caught.value.result.state == "invalid"


# -- a source adapter may come from another distribution ------------------------------------


class _Registered:
    """An adapter a third-party distribution might register, in the shape a built-in has."""

    def __init__(self, root, *, session_id, **options):
        self.root, self.session_id, self.options = root, session_id, options

    def offers(self):
        return {"task.trials": 2}


def test_a_registered_source_kind_is_built(tmp_path, monkeypatch):
    """R17's problem one layer down: an extension's table needs an adapter that knows a raw
    format this package never will, and editing the writer to add one is the gradient that
    leaves NWB's own mechanism unused."""
    from escapewheel_writer import session as session_module
    from escapewheel_writer.recipe import SourceSpec
    from escapewheel_writer.session import Context, _build_source

    monkeypatch.setattr("escapewheel_writer.sources.discovered", lambda: {"tasklog": _Registered})
    spec = SourceSpec(kind="tasklog", root=tmp_path, owns=("task.trials",), options={"zone": "utc"})
    built = _build_source(spec, None, Context(session_id="s001"))
    assert isinstance(built, _Registered)
    assert built.session_id == "s001" and built.options == {"zone": "utc"}
    assert session_module is not None


def test_a_builtin_kind_cannot_be_shadowed(tmp_path, monkeypatch):
    """A recipe naming `sorter` always means this package's sorter."""
    from escapewheel_writer.sources import ADAPTERS

    monkeypatch.setattr("escapewheel_writer.sources.discovered", lambda: {"sorter": _Registered})
    assert "sorter" in ADAPTERS, "the built-ins are consulted first, so this never reaches discovered()"


def test_an_unknown_kind_names_what_is_known(tmp_path, monkeypatch):
    from escapewheel_writer.recipe import SourceSpec
    from escapewheel_writer.session import Context, RecipeError, _build_source

    monkeypatch.setattr("escapewheel_writer.sources.discovered", lambda: {"tasklog": _Registered})
    spec = SourceSpec(kind="nonesuch", root=tmp_path, owns=())
    with pytest.raises(RecipeError, match="known kinds are .*tasklog"):
        _build_source(spec, None, Context(session_id="s001"))


def test_a_broken_plugin_is_skipped_not_raised(monkeypatch):
    """One broken third-party package must not make every other source unavailable."""
    import warnings as warnings_module

    from escapewheel_writer import sources

    class _Bad:
        name = "broken"

        def load(self):
            raise ImportError("no such module")

    monkeypatch.setattr(sources, "entry_points", lambda group: [_Bad()])
    with warnings_module.catch_warnings(record=True) as caught:
        warnings_module.simplefilter("always")
        assert sources.discovered() == {}
    assert "broken" in str(caught[0].message)


# -- scaffolding a draft ---------------------------------------------------------------------


def _sites(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    path = tmp_path / "sites.parquet"
    pq.write_table(
        pa.table(
            {
                "session_id": pa.array(["s1", "s1"]),
                "site_id": pa.array([0, 1], type=pa.int32()),
                "start_tick": pa.array([0, 100], type=pa.int64()),
                "odor_concentration": pa.array([0.5, None]),
                "patch_index": pa.array([0, 0], type=pa.int32()),
            }
        ),
        path,
    )
    return path


def test_a_draft_reads_what_the_data_shows(tmp_path):
    from escapewheel_writer.scaffold import draft

    drafted = draft("vrf", {"sites": _sites(tmp_path)})
    columns = {c["name"]: c for c in drafted.document["resources"]["vrf.sites"]["table"]["columns"]}
    assert columns["site_id"]["type"] == "int32"
    assert columns["start_tick"]["type"] == "int64"
    # Presence is read off this data and only true of it, which is why it is reported.
    assert columns["session_id"]["presence"] == "required"
    assert columns["odor_concentration"]["presence"] == "nullable"


def test_every_guess_is_reported(tmp_path):
    """R48 §2.2 refuses a default because a forgotten classification would look deliberate, and a
    generated file is exactly where a forgotten one hides."""
    from escapewheel_writer.scaffold import draft

    drafted = draft("vrf", {"sites": _sites(tmp_path)})
    reported = " ".join(drafted.decisions)
    for column in ("session_id", "site_id", "start_tick", "odor_concentration", "patch_index"):
        assert f"vrf.sites.{column}" in reported, column
    assert "primary_key is null" in reported
    assert "no references" in reported


def test_a_draft_does_not_validate_until_finished(tmp_path):
    """The draft is deliberately incomplete: R7 needs a key or an explicit null with a reason."""
    import json

    import jsonschema

    from escapewheel_writer.scaffold import draft

    meta = json.loads((Path(__file__).resolve().parents[2] / "registry/registry.schema.json").read_text())
    drafted = draft("vrf", {"sites": _sites(tmp_path)})
    errors = list(jsonschema.Draft202012Validator(meta).iter_errors(drafted.document))
    assert errors, "a draft that validated would be a draft nobody finishes"


def test_the_namespace_is_the_extension_id(tmp_path):
    from escapewheel_writer.scaffold import draft

    drafted = draft("vrf", {"sites": _sites(tmp_path), "patches": _sites(tmp_path)})
    assert set(drafted.document["resources"]) == {"vrf.sites", "vrf.patches"}


# -- an extension may arrive from an installed distribution ---------------------------------


def test_a_recipe_may_name_a_path_or_an_installed_id(tmp_path, monkeypatch):
    """Two situations, two answers: a document being drafted is a file beside the recipe, and one
    someone else maintains arrives in a distribution, which has no path a recipe could name."""
    from escapewheel_writer import extensions as ext

    beside = tmp_path / "task.json"
    beside.write_text(json.dumps(EXTENSION))
    assert ext.load("task.json", base=tmp_path)["extension_id"] == "task"

    monkeypatch.setattr(ext, "installed", lambda: {"vr_foraging": {"extension_id": "vr_foraging"}})
    assert ext.load("vr_foraging")["extension_id"] == "vr_foraging"


def test_an_unknown_extension_says_what_is_installed(monkeypatch):
    from escapewheel_writer import extensions as ext

    monkeypatch.setattr(ext, "installed", lambda: {"opto_tagging": {}, "unit_qc": {}})
    with pytest.raises(ext.ExtensionNotFound, match="opto_tagging, unit_qc"):
        ext.load("nonesuch")


def test_a_broken_extension_package_is_skipped(monkeypatch):
    import warnings as warnings_module

    from escapewheel_writer import extensions as ext

    class _Bad:
        name = "rotten"

        def load(self):
            raise ImportError("its author moved on")

    monkeypatch.setattr(ext, "entry_points", lambda group: [_Bad()])
    with warnings_module.catch_warnings(record=True) as caught:
        warnings_module.simplefilter("always")
        assert ext.installed() == {}
    assert "rotten" in str(caught[0].message)


def test_three_extensions_at_once(tmp_path, registry, minimal):
    """Nothing about carrying one is special-cased, so carrying three is carrying one thrice."""

    def named(extension_id, table):
        document = json.loads(json.dumps(EXTENSION))
        document["extension_id"] = document["registry_id"] = extension_id
        document["resources"] = {f"{extension_id}.{table}": document["resources"]["task.trials"]}
        return document

    writer = PacketWriter(
        registry,
        packet_id="s001",
        extensions=[
            named("vr_foraging", "sites"),
            named("opto_tagging", "pulses"),
            named("unit_qc", "metrics"),
        ],
    )
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    kinds = (("vr_foraging", "sites"), ("opto_tagging", "pulses"), ("unit_qc", "metrics"))
    # Each kind numbers its own intervals, which is what putting the kind in the key buys
    # (R54 §2.2): site 0 and pulse 0 are different rows of `core.intervals`.
    writer.add(
        "core.intervals",
        [{**t, "interval_kind": f"{e}.{table}"} for e, table in kinds for t in TRIALS],
    )
    for extension_id, table in kinds:
        writer.add(
            f"{extension_id}.{table}",
            [
                {
                    "session_id": t["session_id"],
                    "interval_kind": f"{extension_id}.{table}",
                    "trial_id": t["interval_id"],
                    "choice": "left",
                }
                for t in TRIALS
            ],
        )
    root = tmp_path / "s001"
    assert writer.commit(root).passed

    packet = open_packet(root)
    assert set(packet.extensions()) == {"vr_foraging", "opto_tagging", "unit_qc"}
    assert packet.table("vr_foraging.sites").num_rows == 2
    assert packet.table("unit_qc.metrics").num_rows == 2


# -- an extension that is entirely data ------------------------------------------------------


def _vrf_registry():
    return {
        "$schema": "https://escapewheel.org/schemas/registry/0.6.0",
        "registry_id": "vrf",
        "registry_version": "0.1.0",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "rule_language": "escapewheel-rule-sql-v0.1",
        "extension_id": "vrf",
        "resources": {
            "vrf.sites": {
                "content_class": "extension",
                "kind": "table",
                "instances": {"mode": "singleton", "presence": "optional"},
                "requires": [],
                "lineage": "optional",
                "table": {
                    "columns": [
                        {
                            "name": "session_id",
                            "type": "int32",
                            "presence": "required",
                            "role": "identifier",
                            "identity": "assigned",
                            "description": "Session identity.",
                        },
                        {
                            "name": "site_id",
                            "type": "int32",
                            "presence": "required",
                            "role": "identifier",
                            "identity": "carried",
                            "description": "Source site identity.",
                        },
                        {
                            "name": "odor",
                            "type": "string",
                            "presence": "nullable",
                            "role": "data",
                            "vocabulary": "open",
                            "description": "Odor label reported by the source.",
                        },
                        {
                            "name": "metadata",
                            "type": "json_string",
                            "presence": "optional",
                            "role": "data",
                            "description": "What the source stated about this row that the standard does not model, "
                            "carried in the source's own vocabulary and read by no rule.",
                        },
                    ],
                    "primary_key": ["session_id", "site_id"],
                    "references": [
                        {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]}
                    ],
                    "rules": [],
                },
            }
        },
    }


def _export(root, *, rows=2):
    import pyarrow as pa
    import pyarrow.parquet as pq

    root.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table(
            {
                "session_id": pa.array(["s001"] * rows),
                "site_id": pa.array(list(range(rows)), type=pa.int32()),
                "odor": pa.array(["a", "b"][:rows]),
            }
        ),
        root / "sites.parquet",
    )
    return root


def test_a_file_source_needs_no_python_of_ours(tmp_path, registry, minimal):
    """The whole point: a registry document and some Parquet, nothing installed, nothing to rot."""
    from escapewheel_writer.sources import TablesSource

    export = _export(tmp_path / "export")
    source = TablesSource(export, session_id="s001", tables={"vrf.sites": "sites.parquet"})
    assert source.offers() == {"vrf.sites": 2}

    writer = PacketWriter(registry, packet_id="s001", extensions=[_vrf_registry()])
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    for resource_id, batches in source.batches().items():
        writer.add_batches(resource_id, batches)
    root = tmp_path / "p"
    assert writer.commit(root).passed

    # The file carried a name; the packet holds the number the writer assigned (Part 05 §8).
    table = open_packet(root).table("vrf.sites")
    assert table.schema.field("session_id").type == pa.int32()
    assert table.column("site_id").to_pylist() == [0, 1]


def test_a_command_runs_first_and_is_not_a_shell(tmp_path):
    """`uv run …`, `python -m …` and `/opt/venv/bin/python …` are all just commands, so isolating
    an adapter's dependencies is the recipe author's choice and not a tool we require."""
    import sys

    from escapewheel_writer.sources import TablesSource

    root = tmp_path / "raw"
    root.mkdir()
    script = root / "export.py"
    script.write_text(
        "import pyarrow as pa, pyarrow.parquet as pq\n"
        "pq.write_table(pa.table({'session_id': pa.array(['s001']),"
        " 'site_id': pa.array([0], type=pa.int32()), 'odor': pa.array(['a'])}), 'sites.parquet')\n"
    )
    source = TablesSource(
        root,
        session_id="s001",
        tables={"vrf.sites": "sites.parquet"},
        command=[sys.executable, "export.py"],
    )
    assert source.offers() == {"vrf.sites": 1}
    assert any("export.py" in note for note in source.notes)


def test_a_failing_command_is_a_source_defect(tmp_path):
    import sys

    from escapewheel_writer.sources import TablesSource
    from escapewheel_writer.sources.nwb import SourceDefect

    root = tmp_path / "raw"
    root.mkdir()
    source = TablesSource(
        root,
        session_id="s001",
        tables={"vrf.sites": "sites.parquet"},
        command=[sys.executable, "-c", "raise SystemExit(3)"],
    )
    with pytest.raises(SourceDefect, match="failed"):
        source.offers()


def test_a_command_that_does_not_produce_what_it_claimed_says_so(tmp_path):
    import sys

    from escapewheel_writer.sources import TablesSource
    from escapewheel_writer.sources.nwb import SourceDefect

    root = tmp_path / "raw"
    root.mkdir()
    source = TablesSource(
        root,
        session_id="s001",
        tables={"vrf.sites": "sites.parquet"},
        command=[sys.executable, "-c", "pass"],
    )
    with pytest.raises(SourceDefect, match="no file at the declared path after running"):
        source.offers()


def test_a_command_given_as_a_string_is_refused(tmp_path):
    r"""Part 05 §3.7: splitting one applies a quoting convention the recipe never declared, and
    POSIX rules eat a backslash on every host, so `C:\Python\python.exe` loses its separators."""
    from escapewheel_writer.sources import TablesSource
    from escapewheel_writer.sources.nwb import SourceDefect

    root = tmp_path / "raw"
    root.mkdir()
    with pytest.raises(SourceDefect, match="argument list"):
        TablesSource(
            root,
            session_id="s001",
            tables={"vrf.sites": "sites.parquet"},
            command="python export.py",
        )


#: Where the reference registry and the extensions this repository ships live, for the checks that
#: go through the command rather than the function.
_REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "logical_schemas.json"
_EXTENSIONS = Path(__file__).resolve().parents[2] / "registry" / "extensions"


def test_the_check_command_passes_a_shipped_extension(capsys):
    """Through `main`, so a pass proves the entry-point wiring and not just the handler."""
    from escapewheel_reader.scripts.cli import main

    document = _EXTENSIONS / "vr_foraging.json"
    assert main(["extension", "check", str(document), "--registry", str(_REGISTRY)]) == 0
    assert "sound" in capsys.readouterr().out


def test_the_check_command_refuses_a_document_with_a_dangling_reference(tmp_path, capsys):
    """The half of authoring that never shipped: an author learns now rather than at a build."""
    from escapewheel_reader.scripts.cli import main

    document = json.loads((_EXTENSIONS / "vr_foraging.json").read_text())
    table = next(
        declaration["table"] for declaration in document["resources"].values() if declaration["kind"] == "table"
    )
    table["references"].append(
        {"columns": [table["primary_key"][0]], "resource": "core.absent", "resource_columns": ["x"]}
    )
    path = tmp_path / "vr_foraging.json"
    path.write_text(json.dumps(document))
    assert main(["extension", "check", str(path), "--registry", str(_REGISTRY)]) == 1
    assert "registry.reference.resolves" in capsys.readouterr().out


def test_the_check_command_reads_the_registry_a_packet_binds(tmp_path, capsys, registry, minimal):
    """Part 04 §8 makes the packet's bound copy the authority, and it is what an author has to hand."""
    from escapewheel_reader.scripts.cli import main

    writer = PacketWriter(registry, packet_id="p")
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    root = tmp_path / "packet"
    assert writer.commit(root).passed

    document = _EXTENSIONS / "aind_opto.json"
    assert main(["extension", "check", str(document), "--packet", str(root)]) == 0
    assert "sound" in capsys.readouterr().out
