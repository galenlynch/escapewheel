"""A packet carries an extension's table the same way it carries a core one (R17)."""

import copy
import json
from pathlib import Path

import pyarrow as pa
import pytest
from escapewheel_reader import open_packet
from escapewheel_validator import RegistryRejected

from escapewheel_writer import PacketWriter
from escapewheel_writer.errors import (
    CommitRefused,
    ExtensionNotFound,
    RecipeFault,
    RecipeUnsound,
    UnknownSourceKind,
)

EXTENSION = {
    "$schema": "https://escapewheel.org/schemas/registry/0.11.0",
    "registry_id": "task",
    "registry_version": "0.1.0",
    "logical_standard_version": "escapewheel-logical-v0.1",
    "rule_language": "escapewheel-rule-sql-v0.2",
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
                        "name": "trial_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "The trial, and the interval it occupies in core.",
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
                "primary_key": ["trial_id"],
                "amendment_groups": [["trial_id"]],
                "references": [
                    {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]},
                    {
                        "columns": ["trial_id"],
                        "resource": "core.intervals",
                        "resource_columns": ["interval_id"],
                        "specialises": "core.intervals.interval_kind",
                    },
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
        "interval_id": "s001/task.trials/0",
        "local_interval_label": "0",
        "clock_id": "harp_s001",
        "start_tick": 0,
        "stop_tick": 99,
    },
    {
        "session_id": "s001",
        "interval_kind": "task.trials",
        "interval_id": "s001/task.trials/1",
        "local_interval_label": "1",
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
    from escapewheel_writer.session import Context, _build_source

    monkeypatch.setattr("escapewheel_writer.sources.discovered", lambda: {"tasklog": _Registered})
    spec = SourceSpec(kind="nonesuch", root=tmp_path, owns=())
    with pytest.raises(UnknownSourceKind) as refused:
        _build_source(spec, None, Context(session_id="s001"))
    assert refused.value.kind == "nonesuch"
    assert "tasklog" in refused.value.known


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

    meta = json.loads((Path(__file__).resolve().parents[2] / "spec/artifacts/registry.schema.json").read_text())
    drafted = draft("vrf", {"sites": _sites(tmp_path)})
    errors = list(jsonschema.Draft202012Validator(meta).iter_errors(drafted.document))
    assert errors, "a draft that validated would be a draft nobody finishes"


def test_a_finished_draft_with_float_columns_passes_the_registry_check(tmp_path):
    """Part 02 §5.4 requires `finite` on every float column, so the draft writes one and reports
    it; supplying only the reported decisions leaves a document the registry check accepts."""
    import pyarrow.parquet as pq
    from escapewheel_validator import check_registry_context

    from escapewheel_writer.scaffold import draft

    from .conftest import REGISTRY, REGISTRY_CONTEXT

    path = tmp_path / "doses.parquet"
    pq.write_table(
        pa.table(
            {
                "dose_id": pa.array([0, 1], type=pa.int32()),
                "volume": pa.array([0.5, None]),
                "rate": pa.array([1.0, float("nan")], type=pa.float32()),
            }
        ),
        path,
    )
    drafted = draft("vrf", {"doses": path})
    table = drafted.document["resources"]["vrf.doses"]["table"]
    columns = {c["name"]: c for c in table["columns"]}
    assert (columns["volume"]["finite"], columns["rate"]["finite"]) == (False, False)
    assert "finite" not in columns["dose_id"]
    reported = " ".join(drafted.decisions)
    assert "vrf.doses.volume: finite is false" in reported
    assert "vrf.doses.rate: finite is false" in reported and "this data holds 1 non-finite" in reported

    columns["dose_id"].update(role="identifier", identity="carried")
    for column in table["columns"]:
        column.setdefault("role", "data")
        column["description"] = f"The {column['name']}."
    table["primary_key"] = ["dose_id"]
    table["columns"].append(
        next(c for c in REGISTRY["resources"]["core.units"]["table"]["columns"] if c["name"] == "metadata")
    )
    result = check_registry_context(drafted.document, core=REGISTRY_CONTEXT).result
    assert result.state == "valid", [(o.id, o.instance) for p in result.phases for o in p.outcomes]


def test_a_string_column_is_reported_as_needing_a_vocabulary(tmp_path):
    """Part 02 §9.3: a string column with a role needs one, so the report says so and lists the
    values a closed enum could start from."""
    import pyarrow.parquet as pq

    from escapewheel_writer.scaffold import draft

    path = tmp_path / "doses.parquet"
    pq.write_table(pa.table({"route": ["oral", "iv", "oral", None]}), path)
    drafted = draft("vrf", {"doses": path})
    columns = {c["name"]: c for c in drafted.document["resources"]["vrf.doses"]["table"]["columns"]}
    assert "vocabulary" not in columns["route"], "no default, as for role"
    reported = " ".join(drafted.decisions)
    assert "vrf.doses.route: needs a vocabulary" in reported
    assert "this data holds 2 distinct value(s): iv, oral" in reported


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
    with pytest.raises(ExtensionNotFound, match="opto_tagging, unit_qc"):
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

    def interval(extension_id, table, t):
        return f"s001/{extension_id}.{table}/{t['local_interval_label']}"

    # Each source numbers its own kind from 0, so site 0 and pulse 0 are two intervals labelled
    # "0", and the packet numbers them apart (Part 02 §12.9).
    writer.add(
        "core.intervals",
        [
            {**t, "interval_kind": f"{e}.{table}", "interval_id": interval(e, table, t)}
            for e, table in kinds
            for t in TRIALS
        ],
    )
    for extension_id, table in kinds:
        writer.add(
            f"{extension_id}.{table}",
            [
                {"session_id": t["session_id"], "trial_id": interval(extension_id, table, t), "choice": "left"}
                for t in TRIALS
            ],
        )
    root = tmp_path / "s001"
    assert writer.commit(root).passed

    packet = open_packet(root)
    assert set(packet.extensions()) == {"vr_foraging", "opto_tagging", "unit_qc"}
    assert packet.table("vr_foraging.sites").num_rows == 2
    assert packet.table("unit_qc.metrics").num_rows == 2
    intervals = packet.table("core.intervals")
    # Kinds follow one another in Unicode order, each numbered consecutively from where the last ended.
    assert intervals.column("interval_id").to_pylist() == list(range(6))
    assert intervals.column("interval_kind").to_pylist() == [
        kind for kind in ("opto_tagging.pulses", "unit_qc.metrics", "vr_foraging.sites") for _ in TRIALS
    ]
    assert intervals.column("local_interval_label").to_pylist() == ["0", "1"] * 3
    assert packet.table("vr_foraging.sites").column("trial_id").to_pylist() == [4, 5]


# -- a recipe names each extension once (Part 05 §3.1) ----------------------------------------


def _task_version(version):
    """The task extension at `version`, 0.2.0 admitting one more choice so the two are not the same bytes."""
    document = copy.deepcopy(EXTENSION)
    document["registry_version"] = version
    if version != EXTENSION["registry_version"]:
        choice = next(c for c in document["resources"]["task.trials"]["table"]["columns"] if c["name"] == "choice")
        choice["enum"] = [*choice["enum"], "none"]
    return document


def _named(extension_id):
    """The task extension renamed, so a recipe can list two distinct extensions."""
    document = json.loads(json.dumps(EXTENSION).replace('"task', f'"{extension_id}'))
    document["extension_id"] = document["registry_id"] = extension_id
    return document


def _extensions_recipe(tmp_path, entries, documents, source=""):
    """A recipe listing `entries` under `[packet].extensions`, with `documents` written beside it."""
    for name, document in documents.items():
        (tmp_path / name).write_text(json.dumps(document))
    path = tmp_path / "session.toml"
    path.write_text(
        f'[packet]\nid = "s001"\nextensions = {json.dumps(entries)}\n'
        '[session]\nsession_id = "s001"\nsubject_id = "m001"\nsession_start_time = "2026-08-27T00:00:00Z"\n'
        '[subject]\nsubject_id = "m001"\nspecies = "Mus musculus"\nsex = "male"\n'
        '[[clock]]\nclock_id = "harp"\nname = "harp"\ntick_rate_num = 31250\norigin = "harp_epoch"\n' + source
    )
    return path


#: A source the build would open were the recipe not refused first.
SORTER = (
    '[[source]]\nkind = "sorter"\nroot = "sorted"\n'
    'owns = ["core.units", "core.clocks", "core.curation_versions", "core.sorting_runs"]\n'
)


def _build_refuses(recipe, registry, monkeypatch):
    """Build `recipe`, requiring a refusal before any source is opened, and return the refusal."""
    from escapewheel_writer import session

    def opened(*_args, **_kwargs):
        raise AssertionError("a source was opened")

    monkeypatch.setattr(session, "_build_source", opened)
    with pytest.raises(RecipeUnsound) as refused:
        session.build(recipe, registry)
    assert not (recipe.out / "staging").exists(), "refused before anything was prepared"
    return refused.value


@pytest.mark.parametrize(
    ("entries", "documents", "installed"),
    [
        (["task.json", "task.json"], {"task.json": EXTENSION}, {}),
        (
            ["task-0.1.0.json", "task-0.2.0.json"],
            {"task-0.1.0.json": EXTENSION, "task-0.2.0.json": _task_version("0.2.0")},
            {},
        ),
        (["task.json", "task"], {"task.json": EXTENSION}, {"task": EXTENSION}),
    ],
    ids=["repeated-path", "two-versions", "path-and-installed-id"],
)
def test_a_recipe_listing_one_extension_twice_is_refused(
    tmp_path, registry, monkeypatch, entries, documents, installed
):
    """Part 05 §3.1: entries list one extension when their documents carry one `extension_id`, however
    each entry names it, and the build refuses before it opens a source rather than keeping the last."""
    from escapewheel_writer import extensions as ext
    from escapewheel_writer.recipe import Recipe

    monkeypatch.setattr(ext, "installed", lambda: installed)
    recipe = Recipe.load(_extensions_recipe(tmp_path, entries, documents, SORTER))
    refusal = _build_refuses(recipe, registry, monkeypatch)
    named = ", ".join(repr(entry) for entry in entries)
    (problem,) = refusal.problems
    assert problem.code is RecipeFault.REPEATED_EXTENSION
    assert f"extension task is listed in 2 entries ({named})" in problem.message


def test_the_check_command_refuses_one_extension_listed_twice(tmp_path, capsys):
    """`import --check` reaches the same refusal, from the recipe and the registries alone."""
    from escapewheel_reader.scripts.cli import main

    registry = Path(__file__).resolve().parents[2] / "spec" / "artifacts" / "logical_schemas.json"
    path = _extensions_recipe(
        tmp_path,
        ["task-0.1.0.json", "task-0.2.0.json"],
        {"task-0.1.0.json": EXTENSION, "task-0.2.0.json": _task_version("0.2.0")},
    )
    assert main(["import", str(path), "--registry", str(registry), "--check"]) == 2
    assert "extension task is listed in 2 entries ('task-0.1.0.json', 'task-0.2.0.json')" in capsys.readouterr().err


def test_a_recipe_listing_two_extensions_builds_and_binds_both(tmp_path, registry):
    """Distinct `extension_id` values are two extensions, each bound (Part 05 §3.1, Part 09 §5.3)."""
    from escapewheel_writer.recipe import Recipe
    from escapewheel_writer.session import build

    recipe = Recipe.load(
        _extensions_recipe(tmp_path, ["task.json", "cue.json"], {"task.json": EXTENSION, "cue.json": _named("cue")})
    )
    problems = recipe.check(registry.document, [EXTENSION, _named("cue")])
    assert not [p for p in problems if p.code is RecipeFault.REPEATED_EXTENSION]
    writer = build(recipe, registry)
    assert writer.commit(recipe.out).passed
    bound = json.loads((recipe.out / "packet.json").read_text())["registries"]
    assert {registry_id: bound[registry_id]["role"] for registry_id in ("task", "cue")} == {
        "task": "extension",
        "cue": "extension",
    }


def test_two_registries_for_one_extension_are_refused_given_directly(registry):
    """A writer given the documents rather than a recipe refuses too, instead of keeping the later."""
    with pytest.raises(ValueError, match=r"two registries for extension 'task' \(versions 0.1.0 and 0.2.0\)"):
        PacketWriter(registry, packet_id="s001", extensions=[EXTENSION, _task_version("0.2.0")])


# -- an extension that is entirely data ------------------------------------------------------


def _vrf_registry():
    return {
        "$schema": "https://escapewheel.org/schemas/registry/0.11.0",
        "registry_id": "vrf",
        "registry_version": "0.1.0",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "rule_language": "escapewheel-rule-sql-v0.2",
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
                    "amendment_groups": [["session_id", "site_id"]],
                    "references": [
                        {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]}
                    ],
                    "rules": [],
                },
            }
        },
    }


def test_a_file_delivered_source_needs_no_python_of_ours(tmp_path, registry, minimal):
    """The whole point: a registry document and a script writing Parquet, nothing of ours imported."""
    import sys

    from escapewheel_writer import delivery

    script = tmp_path / "export.py"
    script.write_text(
        "import json, sys\n"
        "import pyarrow as pa, pyarrow.parquet as pq\n"
        "terms = json.load(sys.stdin)\n"
        "pq.write_table(pa.table({'session_id': pa.array([terms['session_id']] * 2),"
        " 'site_id': pa.array([0, 1], type=pa.int32()), 'odor': pa.array(['a', 'b'])}),"
        " f\"{terms['delivery_root']}/vrf.sites.parquet\")\n"
    )
    source = delivery.fetch(
        "vrf_sites",
        [sys.executable, str(script)],
        {"root": str(tmp_path), "session_id": "s001"},
        protocol="files-v0.1",
        wanted=["vrf.sites"],
        workspace=tmp_path / "work",
    )
    assert source.offers() == {"vrf.sites": 2}

    writer = PacketWriter(registry, packet_id="s001", extensions=[_vrf_registry()])
    for resource_id, records in {**minimal, **source.records()}.items():
        writer.add(resource_id, records)
    root = tmp_path / "p"
    assert writer.commit(root).passed

    # The file carried a name; the packet holds the number the writer assigned (Part 05 §4.3).
    table = open_packet(root).table("vrf.sites")
    assert table.schema.field("session_id").type == pa.int32()
    assert table.column("site_id").to_pylist() == [0, 1]


#: Where the reference registry and the extensions this repository ships live, for the checks that
#: go through the command rather than the function.
_REGISTRY = Path(__file__).resolve().parents[2] / "spec" / "artifacts" / "logical_schemas.json"
_EXTENSIONS = Path(__file__).resolve().parents[2] / "extensions"


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

    document = _EXTENSIONS.parent / "escapewheel-aind/extensions/aind_opto.json"
    assert main(["extension", "check", str(document), "--packet", str(root)]) == 0
    assert "sound" in capsys.readouterr().out
