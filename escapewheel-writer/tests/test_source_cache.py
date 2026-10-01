"""The source cache (Part 12 §10), read through a store double that reports an entity tag.

A double rather than a bucket: the obligations are about what the store reports and when it is
asked, which a test can only observe from the store's side.
"""

import hashlib
import json
from pathlib import Path
from typing import ClassVar

import fsspec
import pytest
from escapewheel_validator import Level
from fsspec.implementations.memory import MemoryFileSystem
from upath.implementations.memory import MemoryPath
from upath.registry import register_implementation

from escapewheel_writer import declaration, kinds
from escapewheel_writer.errors import RecipeFault, SourceDefect
from escapewheel_writer.notes import NoteCode, codes
from escapewheel_writer.recipe import TERMS, Recipe
from escapewheel_writer.sources.store import STORAGE_FORMAT, prune_kept, source_root
from tests import sorterfixture
from tests.conftest import REGISTRY
from tests.test_build_end_to_end import STREAMS, _recipe, _sources


class TaggedStore(MemoryFileSystem):
    """A store whose `info` reports an entity tag that changes with its bytes, logging each read."""

    protocol = "tagged"
    store: ClassVar[dict] = {}
    pseudo_dirs: ClassVar[list[str]] = [""]
    #: Every path opened for reading, which is every fetch a reader made.
    read: ClassVar[list[str]] = []
    #: Off, the store reports no entity tag, checksum or version.
    tagging = True
    #: On, every request fails as an unreachable store's would.
    unreachable = False

    @classmethod
    def _strip_protocol(cls, path):
        path = str(path)
        return super()._strip_protocol(path.removeprefix("tagged://"))

    def info(self, path, **kwargs):
        if self.unreachable:
            raise ConnectionError(path)
        found = super().info(path, **kwargs)
        if self.tagging and found["type"] == "file":
            found["ETag"] = hashlib.md5(self.store[self._strip_protocol(path)].getvalue()).hexdigest()
        return found

    def _open(self, path, mode="rb", **kwargs):
        if self.unreachable:
            raise ConnectionError(path)
        if "r" in mode:
            type(self).read.append(self._strip_protocol(path))
        return super()._open(path, mode, **kwargs)


@pytest.fixture
def double(monkeypatch):
    fsspec.register_implementation("tagged", TaggedStore, clobber=True)
    register_implementation("tagged", MemoryPath, clobber=True)
    TaggedStore.store.clear()
    TaggedStore.pseudo_dirs[:] = [""]
    TaggedStore.read.clear()
    monkeypatch.setattr(TaggedStore, "tagging", True)
    monkeypatch.setattr(TaggedStore, "unreachable", False)
    return fsspec.filesystem("tagged")


def _kept(location: Path) -> list[Path]:
    """Every entry a later run could read: what is published, not what is in flight."""
    return [p for p in (location / STORAGE_FORMAT).rglob("*") if p.is_file() and "partial" not in p.parts]


# -- the declaration ---------------------------------------------------------------------


def _document(**names):
    return {"kind": "cached", "produces": [], "contributes": [], "states": [], "consumes": [], **names}


def test_accepts_may_name_source_cache():
    """The one term `accepts` may name, since a build supplies it only where it has a location."""
    document = _document(needs=["root"], accepts=["source_cache"])
    assert declaration.refusals(document, tables={}, options=(), terms=TERMS) == []


def test_needs_naming_source_cache_is_refused_naming_the_adapter(tmp_path):
    document = _document(needs=["root", "source_cache"], accepts=[])
    ((code, _),) = declaration.refusals(document, tables={}, options=(), terms=TERMS)
    assert code is RecipeFault.NEEDS_SOURCE_CACHE
    (tmp_path / "cached.json").write_text(json.dumps({**document, "protocols": ["stream-v0.1"]}))
    (tmp_path / "session.toml").write_text(f"""
[packet]
id = "s1"
[session]
session_id = "s1"
[[source]]
kind = "cached"
root = "{tmp_path}"
delivery = {{ command = ["true"], declaration = "cached.json" }}
""")
    problems = Recipe.load(tmp_path / "session.toml").check(REGISTRY)
    (refused,) = [p for p in problems if p.code is RecipeFault.NEEDS_SOURCE_CACHE]
    assert refused.message.startswith("cached needs source_cache")


def test_a_recipe_setting_a_term_is_refused(tmp_path):
    """A term resolves before an option, so a value the recipe sets for one would never arrive."""
    sorted_root, raw = _sources(tmp_path)
    path = _recipe(tmp_path, sorted_root, raw)
    path.write_text(path.read_text().replace('kind = "sorter"', f'kind = "sorter"\nsource_cache = "{tmp_path}"'))
    (refused,) = [p for p in Recipe.load(path).check(REGISTRY) if p.code is RecipeFault.OPTION_IS_TERM]
    assert refused.message.startswith("source sorter sets 'source_cache'")


# -- what a build supplies -----------------------------------------------------------------


def _context(recipe, location):
    from escapewheel_writer.session import Context
    from escapewheel_writer.sourcing import resolved_source_cache

    context = Context(session_id="s1", workspace=Path(f"{recipe.out}.deliveries"))
    context.source_cache = resolved_source_cache(location, recipe.out, context)
    return context


def test_an_accepting_adapter_is_supplied_the_location_and_no_other_is(tmp_path, monkeypatch):
    """In its input object, with no environment variable set, and to no adapter that did not ask."""
    from escapewheel_writer.sourcing import supplied_to

    for variable in ("ESCAPEWHEEL_SOURCE_CACHE", "TMPDIR"):
        monkeypatch.delenv(variable, raising=False)
    sorted_root, raw = _sources(tmp_path)
    recipe = Recipe.load(_recipe(tmp_path, sorted_root, raw))
    context = _context(recipe, tmp_path / "cache")
    sorter = next(spec for spec in recipe.sources if spec.kind == "sorter")
    assert supplied_to(sorter, recipe, context)["source_cache"] == str((tmp_path / "cache").resolve())

    declining = type("Declining", (), {"NEEDS": ("root", "session_id"), "ACCEPTS": ()})
    monkeypatch.setattr(kinds, "adapter_for", lambda kind: declining)
    assert "source_cache" not in supplied_to(sorter, recipe, context)


@pytest.mark.parametrize("inside", ["packet", "packet.deliveries/sorter", "packet/.staging"])
def test_a_location_inside_the_packet_or_a_delivery_is_supplied_to_no_adapter(tmp_path, inside):
    from escapewheel_writer.sourcing import supplied_to

    sorted_root, raw = _sources(tmp_path)
    recipe = Recipe.load(_recipe(tmp_path, sorted_root, raw))
    context = _context(recipe, tmp_path / inside)
    assert context.source_cache is None
    assert NoteCode.NO_SOURCE_CACHE in codes(context.notes)
    sorter = next(spec for spec in recipe.sources if spec.kind == "sorter")
    assert "source_cache" not in supplied_to(sorter, recipe, context)


def test_a_delivered_adapter_is_handed_the_location_only_where_it_accepts_it(tmp_path):
    from escapewheel_writer.delivery import construct

    sorted_root, _ = _sources(tmp_path)
    source = construct(
        "sorter", {"root": str(sorted_root), "session_id": "s1", "source_cache": str(tmp_path / "cache"), "options": {}}
    )
    assert source.root.exists()


# -- what an adapter keeps -----------------------------------------------------------------


def test_an_object_whose_tag_changed_is_fetched_again(double, tmp_path):
    double.pipe("/bucket/obj", b"old")
    assert (source_root("tagged://bucket", cache=tmp_path) / "obj").read_bytes() == b"old"
    double.pipe("/bucket/obj", b"new")
    assert (source_root("tagged://bucket", cache=tmp_path) / "obj").read_bytes() == b"new"


def test_an_object_changed_while_it_was_fetched_is_not_kept_under_the_old_tag(double, tmp_path, monkeypatch):
    """What arrived is the new object, so filing it under the tag asked about would misname it."""
    double.pipe("/bucket/obj", b"old")
    fetch = MemoryFileSystem.get_file

    def overtaken(self, rpath, lpath, **kwargs):
        self.pipe("/bucket/obj", b"new")
        fetch(self, rpath, lpath, **kwargs)

    with monkeypatch.context() as patched:
        patched.setattr(TaggedStore, "get_file", overtaken)
        assert (source_root("tagged://bucket", cache=tmp_path) / "obj").read_bytes() == b"new"
    assert list((tmp_path / STORAGE_FORMAT / "objects").glob("*")) == []


def test_a_confirmed_object_is_read_from_the_location(double, tmp_path):
    """Confirmed once per run by asking the store, and fetched only the first time."""
    double.pipe("/bucket/obj", b"x" * 100)
    for _ in range(2):
        assert (source_root("tagged://bucket", cache=tmp_path) / "obj").read_bytes() == b"x" * 100
    assert TaggedStore.read == ["/bucket/obj"]


def test_an_object_with_no_confirming_value_is_read_in_every_run(double, tmp_path, monkeypatch):
    monkeypatch.setattr(TaggedStore, "tagging", False)
    double.pipe("/bucket/obj", b"x")
    for _ in range(2):
        root = source_root("tagged://bucket", cache=tmp_path)
        assert (root / "obj").read_bytes() == b"x"
        assert (root / "obj").read_bytes() == b"x"
    assert TaggedStore.read == ["/bucket/obj", "/bucket/obj"]


def test_a_version_pinned_object_is_used_again_with_the_store_unreachable(double, tmp_path, monkeypatch):
    monkeypatch.setattr(TaggedStore, "tagging", False)
    double.pipe("/bucket/obj?versionId=3", b"v3")
    assert source_root("tagged://bucket/obj?versionId=3", cache=tmp_path).read_bytes() == b"v3"
    monkeypatch.setattr(TaggedStore, "unreachable", True)
    assert source_root("tagged://bucket/obj?versionId=3", cache=tmp_path).read_bytes() == b"v3"


def test_a_kept_object_of_the_wrong_size_is_not_used(double, tmp_path):
    double.pipe("/bucket/obj", b"whole")
    (source_root("tagged://bucket", cache=tmp_path) / "obj").read_bytes()
    (entry,) = _kept(tmp_path)
    entry.write_bytes(b"who")
    assert (source_root("tagged://bucket", cache=tmp_path) / "obj").read_bytes() == b"whole"


def test_everything_is_kept_under_the_writers_own_subdirectory(double, tmp_path):
    beside = tmp_path / "another-format" / "entry"
    beside.parent.mkdir()
    beside.write_bytes(b"theirs")
    double.pipe("/bucket/obj", b"ours")
    (source_root("tagged://bucket", cache=tmp_path) / "obj").read_bytes()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["another-format", STORAGE_FORMAT]
    assert beside.read_bytes() == b"theirs"


@pytest.mark.parametrize("route", ["open", "cat", "cat_file", "cat_ranges"])
def test_a_killed_fetch_leaves_nothing_readable(double, tmp_path, monkeypatch, route):
    """Whole or absent on every route, so an interrupted fetch is fetched again, never read short."""
    double.pipe("/bucket/obj", b"x" * 1000)

    def killed(self, rpath, lpath, **kwargs):
        Path(lpath).write_bytes(b"x" * 10)
        raise KeyboardInterrupt

    reads = {
        "open": lambda root: (root / "obj").read_bytes(),
        "cat": lambda root: root.fs.cat("/bucket/obj"),
        "cat_file": lambda root: root.fs.cat_file("/bucket/obj"),
        "cat_ranges": lambda root: root.fs.cat_ranges(["/bucket/obj"], [0], [1000])[0],
    }
    with monkeypatch.context() as patched:
        patched.setattr(TaggedStore, "get_file", killed)
        with pytest.raises(KeyboardInterrupt):
            reads[route](source_root("tagged://bucket", cache=tmp_path))
    assert _kept(tmp_path) == []
    assert list((tmp_path / STORAGE_FORMAT / "partial").iterdir()) == []
    assert reads[route](source_root("tagged://bucket", cache=tmp_path)) == b"x" * 1000


def test_prune_removes_only_what_this_writer_keeps(double, tmp_path):
    beside = tmp_path / "another-format" / "entry"
    beside.parent.mkdir()
    beside.write_bytes(b"theirs")
    double.pipe("/bucket/obj", b"ours")
    (source_root("tagged://bucket", cache=tmp_path) / "obj").read_bytes()
    assert prune_kept(tmp_path, older_than=1) == []
    assert [size for _, size in prune_kept(tmp_path)] == [4]
    assert _kept(tmp_path) != []
    prune_kept(tmp_path, apply=True)
    assert _kept(tmp_path) == []
    assert beside.read_bytes() == b"theirs"


# -- builds --------------------------------------------------------------------------------


@pytest.fixture
def remote(double, tmp_path):
    """A recipe whose sorted asset is in the double, and a build of it into a named packet."""
    from escapewheel_writer.session import build

    sorted_root, raw = _sources(tmp_path / "local")
    double.put(str(sorted_root), "/bucket/sorted", recursive=True)
    path = _recipe(tmp_path / "local", "tagged://bucket/sorted", raw)

    def built(out: Path, location: Path | None):
        recipe = Recipe.load(path, out=out)
        report = build(recipe, REGISTRY, source_cache=location).commit(out)
        assert report.errors == 0, [f"{f.check}: {f.message}" for f in report.findings if f.level == Level.ERROR]
        return out

    return built


def _rows(root: Path) -> dict[str, list[dict]]:
    """Every table's rows, less the import run's `started_at`, which is when the build ran."""
    from escapewheel_reader import open_packet

    from escapewheel_writer import compare

    packet = open_packet(root)
    rows = {resource: packet.table(resource).to_pylist() for resource in sorted(compare.resources(root))}
    for run in rows["core.processing_runs"]:
        if run["activity_type"] == "import":
            del run["started_at"]
    return rows


def test_a_warm_and_a_cold_location_build_the_same_rows(remote, tmp_path):
    cold = remote(tmp_path / "cold", tmp_path / "cold-cache")
    warm = remote(tmp_path / "warm", tmp_path / "cold-cache")
    assert _rows(warm) == _rows(cold)
    assert "tagged://bucket/sorted" in {row["uri"] for row in _rows(cold)["core.source_files"]}


def test_a_packet_carries_the_bytes_the_store_holds_now(remote, double, tmp_path):
    """A kept object whose tag changed is fetched again, so the packet is the store's, not the cache's."""
    first = remote(tmp_path / "first", tmp_path / "cache")
    shifted = [(unit, sample + 1) for unit, sample in sorterfixture.SPIKES]
    sorterfixture.stream(tmp_path / "shifted", STREAMS[0], spikes=shifted)
    spikes = f"curated/{STREAMS[0]}/spikes.npy"
    double.pipe(f"/bucket/sorted/{spikes}", (tmp_path / "shifted" / spikes).read_bytes())
    again = remote(tmp_path / "again", tmp_path / "cache")
    cold = remote(tmp_path / "cold", None)
    assert _rows(again)["core.spike_events"] != _rows(first)["core.spike_events"]
    assert _rows(again)["core.spike_events"] == _rows(cold)["core.spike_events"]


def test_the_location_survives_a_published_build_and_a_refused_one(remote, tmp_path, monkeypatch):
    from escapewheel_writer.sources import sorter

    location = tmp_path / "cache"
    mine = location / "operator-note.txt"
    remote(tmp_path / "published", location)
    location.joinpath("operator-note.txt").write_text("keep")
    kept = sorted(_kept(location))
    assert kept

    def refused(self, *args, **kwargs):
        raise SourceDefect("refused")

    monkeypatch.setattr(sorter.SorterSource, "records", refused)
    with pytest.raises(SourceDefect):
        remote(tmp_path / "refused", location)
    assert sorted(_kept(location)) == kept
    assert mine.read_text() == "keep"


def test_a_build_with_no_location_fetches_every_object_every_time(remote, tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path / "tmp"))
    remote(tmp_path / "first", None)
    first = sorted(TaggedStore.read)
    TaggedStore.read.clear()
    remote(tmp_path / "second", None)
    assert first
    assert sorted(TaggedStore.read) == first
    assert not (tmp_path / "tmp").exists()


def test_import_keeps_the_location_beside_the_packet_unless_told_otherwise(tmp_path):
    """On the packet's disk rather than under `TMPDIR`, which is RAM wherever `/tmp` is a tmpfs."""
    from argparse import Namespace

    from escapewheel_writer.scripts.cli import import_source_cache

    out = tmp_path / "packets" / "786867-packet"
    assert import_source_cache(Namespace(source_cache=None, no_source_cache=False), out) == (
        tmp_path / "packets" / ".escapewheel-source-cache"
    )
    assert (
        import_source_cache(Namespace(source_cache=tmp_path / "named", no_source_cache=False), out)
        == tmp_path / "named"
    )
    assert import_source_cache(Namespace(source_cache=None, no_source_cache=True), out) is None
