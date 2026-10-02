"""`escapewheel import` prints a refusal and exits with a status; it raises none."""

import json
from pathlib import Path

import pytest
from escapewheel_reader.scripts.cli import main
from escapewheel_validator import RegistryRejected, check_registry_context_bytes
from jsonschema import Draft202012Validator

from escapewheel_writer.errors import (
    NotCommitted,
    PayloadFault,
    PayloadProblem,
    PayloadRefused,
    RecipeUnsound,
    SourceDefect,
    SourceFault,
    TermUnfilled,
)
from escapewheel_writer.scripts import cli
from escapewheel_writer.writer import PacketWriter
from tests.builders import amending_recipe, session_recipe, session_sources
from tests.test_extensions import EXTENSION, extensions_recipe

ARTIFACTS = Path(__file__).resolve().parents[2] / "spec" / "artifacts"
CORE = ARTIFACTS / "logical_schemas.json"
RESULT_SCHEMA = Draft202012Validator(json.loads((ARTIFACTS / "registry_result.schema.json").read_text()))

_VERSION = '"registry_version": "0.1.0"'
#: The task extension with `registry_version` repeated, which only a check of the bytes sees
#: (Part 02 §9.4).
REPEATED_MEMBER = json.dumps(EXTENSION).replace(_VERSION, f"{_VERSION}, {_VERSION}")
#: The task extension without a member its meta-schema requires, so it decodes and is not valid.
MISSING_MEMBER = json.dumps({member: value for member, value in EXTENSION.items() if member != "rule_language"})

BEFORE_THE_COMMIT = [
    RecipeUnsound("session.toml: refused, 1 error(s)", path=Path("session.toml"), problems=[]),
    TermUnfilled("sorter needs parent_clock_id", kind="sorter", name="parent_clock_id"),
    SourceDefect("probeA: two clocks belong to its probe", code=SourceFault.NO_ONE_CLOCK, where="probeA"),
]

IN_THE_COMMIT = [
    PayloadRefused(
        "clip.mp4 is a symbolic link (Part 12 §5)",
        problems=[PayloadProblem(PayloadFault.NOT_REGULAR, "clip.mp4 is a symbolic link")],
    ),
    NotCommitted("packet holds no committed packet.json; use commit() to create a packet"),
    SourceDefect("probeA: no clock belongs to its probe", code=SourceFault.NO_ONE_CLOCK, where="probeA"),
]


def _raising(refusal):
    def refuse(*args, **kwargs):
        raise refusal

    return refuse


def _printed(capsys, refusal) -> bool:
    """Whether the refusal was the last line printed, and nothing printed was a traceback."""
    printed = capsys.readouterr().err
    return printed.endswith(f"error: {refusal}\n") and "Traceback" not in printed


@pytest.fixture
def recipe(tmp_path):
    return session_recipe(tmp_path, *session_sources(tmp_path))


def test_an_unreadable_recipe_exits_2(tmp_path, capsys):
    path = tmp_path / "session.toml"
    path.write_text("[packet\n")
    assert main(["import", str(path)]) == 2
    printed = capsys.readouterr().err
    assert printed.startswith("error: ") and "Traceback" not in printed


@pytest.mark.parametrize(
    ("core", "extension", "printed", "failing_phase", "outcome"),
    [
        (b"{", json.dumps(EXTENSION), "core registry", "json", "registry.json.invalid_syntax"),
        (CORE.read_bytes(), "{", "extension registry", "json", "registry.json.invalid_syntax"),
        (CORE.read_bytes(), REPEATED_MEMBER, "extension registry task", "json", "registry.json.duplicate_member"),
        (CORE.read_bytes(), MISSING_MEMBER, "extension registry task", "shape", None),
    ],
    ids=["core", "undecodable-extension", "repeated-member", "missing-member"],
)
def test_a_rejected_registry_writes_its_complete_result(
    tmp_path, capsys, core, extension, printed, failing_phase, outcome
):
    """Part 05 §14.4: `--registry-result` holds the Part 02 §9.5 result of the registry that stopped
    the build, where the phase that fails says whose result it is. The line printed names an
    extension whose document decodes."""
    (tmp_path / "core.json").write_bytes(core)
    (tmp_path / "task.json").write_text(extension)
    recipe = extensions_recipe(tmp_path, ["task.json"], {})
    result = tmp_path / "result.json"

    status = main(["import", str(recipe), "--registry", str(tmp_path / "core.json"), "--registry-result", str(result)])

    assert status == 2
    assert capsys.readouterr().err == f"error: {printed} is invalid\n"
    written = json.loads(result.read_text())
    RESULT_SCHEMA.validate(written)
    assert written["state"] == "invalid"
    (failed,) = [phase for phase in written["phases"] if phase["state"] == "invalid"]
    assert failed["phase"] == failing_phase
    if outcome is not None:
        assert [found["id"] for found in failed["outcomes"]] == [outcome]


def test_a_registry_the_build_rejects_writes_its_result(recipe, monkeypatch):
    """Part 05 §14.4: a rejection raised by the build reaches `--registry-result` as the same result."""
    rejected = check_registry_context_bytes(b"{")
    monkeypatch.setattr(cli, "build", _raising(RegistryRejected("task", rejected)))
    result = recipe.parent / "result.json"

    assert main(["import", str(recipe), "--registry", str(CORE), "--registry-result", str(result)]) == 2

    assert json.loads(result.read_text()) == rejected.result.to_dict()


@pytest.mark.parametrize("refusal", BEFORE_THE_COMMIT, ids=lambda refusal: type(refusal).__name__)
def test_a_build_that_refuses_exits_2(recipe, monkeypatch, capsys, refusal):
    monkeypatch.setattr(cli, "build", _raising(refusal))
    assert main(["import", str(recipe), "--registry", str(CORE)]) == 2
    assert _printed(capsys, refusal)


@pytest.mark.parametrize("refusal", IN_THE_COMMIT, ids=lambda refusal: type(refusal).__name__)
def test_a_commit_that_refuses_exits_1(recipe, monkeypatch, capsys, refusal):
    monkeypatch.setattr(PacketWriter, "commit", _raising(refusal))
    assert main(["import", str(recipe), "--registry", str(CORE)]) == 1
    assert _printed(capsys, refusal)


def test_an_amendment_that_refuses_exits_1(packet, monkeypatch, capsys):
    root, sorted_root = packet
    refusal = NotCommitted(f"{root / 'packet'} holds no committed packet.json; use commit() to create a packet")
    monkeypatch.setattr(PacketWriter, "amend", _raising(refusal))
    assert main(["import", str(amending_recipe(root, sorted_root))]) == 1
    assert _printed(capsys, refusal)


def test_a_refusal_from_another_subcommand_exits_1(tmp_path, capsys):
    """`verify` handles no refusal itself, so the shared entry point prints it."""
    assert main(["verify", str(tmp_path)]) == 1
    printed = capsys.readouterr().err
    assert printed.startswith("error: ") and "Traceback" not in printed
