"""A build opens sources concurrently and still writes the packet a one-at-a-time build writes."""

import io
import json
import re
import shutil
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pyarrow.parquet as pq
import pytest

from escapewheel_writer import session
from escapewheel_writer.errors import SourceDefect
from escapewheel_writer.recipe import Recipe
from escapewheel_writer.sourcing import waits_for
from tests.builders import session_recipe, session_sources
from tests.conftest import REGISTRY

RUNS = "tables/core/processing_runs.parquet"


def _built(root: Path, workers: int) -> tuple[dict[str, bytes], list[str]]:
    """Import the session recipe under `root` and return its files' bytes and what the build said."""
    sorted_root, raw = session_sources(root)
    recipe = Recipe.load(session_recipe(root, sorted_root, raw))
    said: list[str] = []
    session.import_packet(recipe, REGISTRY, say=said.append, workers=workers)
    files = {str(p.relative_to(recipe.out)): p.read_bytes() for p in sorted(recipe.out.rglob("*")) if p.is_file()}
    return files, [re.sub(r"[\d.]+ s\b", "_ s", line) for line in said]


def _timeless(files: dict[str, bytes]) -> dict[str, Any]:
    """The packet less when it was built: the run's start, the manifest's dates and its digest of the runs."""
    kept: dict[str, Any] = dict(files)
    kept[RUNS] = pq.read_table(io.BytesIO(files[RUNS])).drop_columns(["started_at"])
    manifest = json.loads(files["packet.json"])
    del manifest["created_at"], manifest["validation"]["validated_at"]
    for resource in manifest["resources"]:
        if resource["uri"] == RUNS:
            del resource["digest"]
    kept["packet.json"] = manifest
    return kept


def test_a_concurrent_build_writes_the_packet_a_serial_one_does(tmp_path):
    """Same bytes but for when it was built, same log: only opening overlaps, and sources are handled in order."""
    one, one_said = _built(tmp_path / "a", 1)
    # Built at the same path, since a packet records where its sources were read from.
    shutil.move(tmp_path / "a", tmp_path / "kept")
    many, many_said = _built(tmp_path / "a", 8)
    one, many = _timeless(one), _timeless(many)
    assert sorted(many) == sorted(one)
    assert [name for name in one if many[name] != one[name]] == []
    assert many_said == one_said


def _spec(kind: str) -> SimpleNamespace:
    return SimpleNamespace(kind=kind)


def _opening(monkeypatch, specs, waits, opened):
    """An `_Opening` over stand-in specs, `waits` naming which kind waits for which."""
    monkeypatch.setattr(session, "waits_for", lambda earlier, later: earlier.kind in waits.get(later.kind, ()))
    monkeypatch.setattr(session, "_open", opened)
    return session._Opening(specs, None, None, workers=4)


def test_sources_waiting_for_nothing_open_together(monkeypatch):
    """Two sources that wait for nothing are both opening before either finishes."""
    both = threading.Barrier(2, timeout=10)

    def opened(spec, recipe, context):
        both.wait()
        return spec.kind

    opening = _opening(monkeypatch, [_spec("a"), _spec("b")], {}, opened)
    try:
        assert [opening.take(0), opening.take(1)] == ["a", "b"]
    finally:
        opening.close()


def test_a_source_opens_only_once_what_it_waits_for_is_harvested(monkeypatch):
    """`b` waits for `a`, so it is not opened until the build has harvested `a`."""
    started: list[str] = []

    def opened(spec, recipe, context):
        started.append(spec.kind)
        return spec.kind

    opening = _opening(monkeypatch, [_spec("a"), _spec("b")], {"b": ("a",)}, opened)
    try:
        assert opening.take(0) == "a"
        assert started == ["a"]
        opening.harvested(0)
        assert opening.take(1) == "b"
        assert started == ["a", "b"]
    finally:
        opening.close()


def test_a_source_that_fails_to_open_fails_the_build_and_publishes_nothing(tmp_path, monkeypatch):
    """The failure surfaces at its source's turn, as it would one at a time, and no packet is committed."""
    from escapewheel_writer.sources.sorter import SorterSource

    def failing(self):
        raise SourceDefect("unreadable")

    monkeypatch.setattr(SorterSource, "records", failing)
    sorted_root, raw = session_sources(tmp_path)
    recipe = Recipe.load(session_recipe(tmp_path, sorted_root, raw))
    with pytest.raises(SourceDefect, match="unreadable"):
        session.import_packet(recipe, REGISTRY, workers=4)
    assert not (recipe.out / "packet.json").exists()
    assert not [thread for thread in threading.enumerate() if thread.name.startswith("source")]


@pytest.mark.parametrize(
    ("earlier", "later", "waits"),
    [
        ("sorter", "sync", True),
        ("sorter", "waveforms", True),
        ("sorter", "lfp", True),
        ("sync", "lfp", True),
        ("sync", "sorter", False),
        ("openephys", "sorter", False),
        ("openephys", "waveforms", False),
    ],
)
def test_a_source_waits_for_what_it_consumes_and_for_what_supplies_its_terms(earlier, later, waits):
    """`lfp` needs `clocks`, which `sync` states, so it waits for `sync` without consuming it."""
    assert waits_for(SimpleNamespace(kind=earlier, delivery=None), SimpleNamespace(kind=later, delivery=None)) is waits
