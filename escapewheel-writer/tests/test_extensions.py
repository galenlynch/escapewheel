"""A packet carries an extension's table the same way it carries a core one (R17)."""

import json
from pathlib import Path

import pyarrow as pa
import pytest
from escapewheel_reader import open_packet
from escapewheel_validator import validate

from escapewheel_writer import PacketWriter

EXTENSION = {
    "registry_version": "0.1.0",
    "logical_standard_version": "0.1",
    "extension_id": "task",
    "extends": "escapewheel-logical-v0.1",
    "tables": {
        "task.trials": {
            "columns": [
                {
                    "name": "session_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "assigned",
                },
                {
                    "name": "interval_kind",
                    "type": "string",
                    "presence": "required",
                    "role": "discriminator",
                    "resolves": "required",
                },
                {
                    "name": "trial_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "carried",
                },
                {"name": "choice", "type": "string", "presence": "nullable", "role": "data", "enum": ["left", "right"]},
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
        }
    },
}


TRIALS = [
    {"session_id": "s001", "interval_kind": "task.trials", "interval_id": 0, "clock_id": "harp_s001", "start_tick": 0, "stop_tick": 99},
    {"session_id": "s001", "interval_kind": "task.trials", "interval_id": 1, "clock_id": "harp_s001", "start_tick": 200, "stop_tick": 299},
]


def _commit(root, registry, minimal, *, choice="left"):
    writer = PacketWriter(registry, packet_id=root.name, extensions=[EXTENSION])
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    writer.add("core.intervals", TRIALS)
    writer.add(
        "task.trials", [{"session_id": t["session_id"], "interval_kind": "task.trials", "trial_id": t["interval_id"], "choice": choice} for t in TRIALS]
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
    assert manifest["extensions"] == {"task": {"version": "0.1.0", "registry": "extensions/task.json"}}
    assert (root / "extensions" / "task.json").is_file()
    assert open_packet(root).extensions()["task"]["extension_id"] == "task"


def test_the_entry_says_which_extension_owns_it(tmp_path, registry, minimal):
    """`05` §5.4: a reader knows what it holds without parsing the extension's registry."""
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    entry = next(
        r for r in json.loads((root / "packet.json").read_text())["resources"] if r["resource_id"] == "task.trials"
    )
    assert (entry["layer"], entry["extension_id"]) == ("extension", "task")


def test_the_extension_is_validated_and_reported_apart(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal, choice="sideways")
    report = validate(open_packet(root))
    assert report.passed, "core conformance is unchanged by an extension's finding (`05` §5.4)"
    assert not report.extension_passed("task")
    assert "task.trials.choice.in_vocabulary" in {f.check for f in report.findings}


def test_a_core_table_cannot_be_redefined(registry):
    stray = {**EXTENSION, "tables": {"core.intervals": EXTENSION["tables"]["task.trials"]}}
    with pytest.raises(ValueError, match="not namespaced"):
        PacketWriter(registry, packet_id="s001", extensions=[stray])


def test_an_unnamespaced_table_is_refused(registry):
    stray = {**EXTENSION, "tables": {"elsewhere.trials": EXTENSION["tables"]["task.trials"]}}
    with pytest.raises(ValueError, match="not namespaced"):
        PacketWriter(registry, packet_id="s001", extensions=[stray])


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
    from escapewheel_writer.session import _KINDS

    monkeypatch.setattr("escapewheel_writer.sources.discovered", lambda: {"sorter": _Registered})
    assert "sorter" in _KINDS, "the built-ins are consulted first, so this never reaches discovered()"


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
    columns = {c["name"]: c for c in drafted.document["tables"]["vrf.sites"]["columns"]}
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

    meta = json.loads(Path("../registry/registry.schema.json").read_text())
    drafted = draft("vrf", {"sites": _sites(tmp_path)})
    errors = list(jsonschema.Draft202012Validator(meta).iter_errors(drafted.document))
    assert errors, "a draft that validated would be a draft nobody finishes"


def test_the_namespace_is_the_extension_id(tmp_path):
    from escapewheel_writer.scaffold import draft

    drafted = draft("vrf", {"sites": _sites(tmp_path), "patches": _sites(tmp_path)})
    assert set(drafted.document["tables"]) == {"vrf.sites", "vrf.patches"}


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
        document["extension_id"] = extension_id
        document["tables"] = {f"{extension_id}.{table}": document["tables"]["task.trials"]}
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
        "registry_version": "0.1.0",
        "logical_standard_version": "0.1",
        "extension_id": "vrf",
        "extends": "escapewheel-logical-v0.1",
        "tables": {
            "vrf.sites": {
                "columns": [
                    {
                        "name": "session_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                    },
                    {
                        "name": "site_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "carried",
                    },
                    {"name": "odor", "type": "string", "presence": "nullable", "role": "data"},
                ],
                "primary_key": ["session_id", "site_id"],
                "references": [
                    {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]}
                ],
                "rules": [],
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

    # The file carried a name; the packet holds the number the writer assigned (`05` §8).
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
        root, session_id="s001", tables={"vrf.sites": "sites.parquet"}, command=f"{sys.executable} export.py"
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
        command=f"{sys.executable} -c 'raise SystemExit(3)'",
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
        root, session_id="s001", tables={"vrf.sites": "sites.parquet"}, command=f"{sys.executable} -c 'pass'"
    )
    with pytest.raises(SourceDefect, match="no file at the declared path after running"):
        source.offers()
