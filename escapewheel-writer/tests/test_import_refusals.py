"""`escapewheel import` prints a refusal and exits with a status; it raises none."""

from pathlib import Path

import pytest
from escapewheel_reader.scripts.cli import main

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

CORE = Path(__file__).resolve().parents[2] / "spec" / "artifacts" / "logical_schemas.json"

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
