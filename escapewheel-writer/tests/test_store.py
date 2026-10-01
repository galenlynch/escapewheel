"""One source root, read once and shared."""

import numpy as np
import nwbfixture
import pytest

from escapewheel_writer.errors import UnsupportedEncoding
from escapewheel_writer.sources.store import SourceStore, store_for

#: One clock's `core.clocks` row, which is the shape the `clocks` term takes.
PROBE_CLOCK = {"clock_id": "probe.45883-1.samples", "tick_rate_num": 30000, "tick_rate_den": 1}


@pytest.fixture
def store(tmp_path):
    return SourceStore(nwbfixture.build(tmp_path))


def test_an_array_is_parsed_once(store, monkeypatch):
    """The point of the store: two readers of the same bytes cannot disagree."""
    from escapewheel_writer.sources import store as module

    calls = []
    real = module.read_array
    monkeypatch.setattr(module, "read_array", lambda p: calls.append(p) or real(p))
    first = store.array("intervals/trials/start_time")
    second = store.array("intervals/trials/start_time")
    assert len(calls) == 1
    assert np.array_equal(first, second)


def test_an_absolute_path_is_the_same_key_as_a_relative_one(store):
    from escapewheel_writer.sources import store as module

    calls = []
    real = module.read_array
    store.array("intervals/trials/start_time")
    module.read_array = lambda p: calls.append(p) or real(p)
    try:
        store.array(store.root / "intervals/trials/start_time")
    finally:
        module.read_array = real
    assert calls == [], "an absolute path must hit the cache the relative one filled"


def test_a_failure_is_not_cached(tmp_path):
    """A caller that handles UnsupportedEncoding and one that does not must both see it."""
    store = SourceStore(nwbfixture.build(tmp_path))
    for _ in range(2):
        with pytest.raises(UnsupportedEncoding):
            store.array("general/extracellular_ephys/electrodes/group")


def test_head_reads_only_the_chunks_it_needs(tmp_path):
    """64 MB decoded and retained per LFP series, to use two values, is what this avoids."""
    from tests.test_zarr_compat import _rechunk

    values = np.arange(10, dtype=np.float64)
    path = nwbfixture.array(tmp_path / "a", values)
    _rechunk(path, values, stride=4)
    (path / "2").unlink()
    assert SourceStore(tmp_path).head("a", 2).tolist() == [0.0, 1.0]


def test_head_is_memoized_per_count(store, monkeypatch):
    from escapewheel_writer.sources import store as module

    calls = []
    real = module.read_array
    monkeypatch.setattr(module, "read_array", lambda p, **kw: calls.append(kw) or real(p, **kw))
    store.head("intervals/trials/start_time", 1)
    store.head("intervals/trials/start_time", 1)
    assert calls == [{"limit": 1}]


def test_head_is_served_from_a_full_read_already_made(store, monkeypatch):
    """Whichever call comes first, the bytes are decoded once."""
    from escapewheel_writer.sources import store as module

    store.array("intervals/trials/start_time")
    monkeypatch.setattr(module, "read_array", lambda *a, **k: pytest.fail("read again"))
    assert store.head("intervals/trials/start_time", 1).tolist() == [1.0]


def test_members_and_attrs_are_memoized(store):
    assert store.members("acquisition") == store.members("acquisition")
    assert store.attrs("") == store.attrs("")


def test_is_array_distinguishes_a_group_from_an_array(store):
    assert store.is_array("intervals/trials/start_time")
    assert not store.is_array("intervals/trials")
    assert not store.is_array("nowhere/at/all")


def test_store_for_hands_back_the_same_store_for_one_root(tmp_path):
    root = nwbfixture.build(tmp_path)
    shared = {}
    assert store_for(root, shared) is store_for(root, shared)
    # The same tree named differently is still one store.
    assert store_for(str(root) + "/.", shared) is store_for(root, shared)


def test_an_adapter_built_alone_gets_its_own_store(tmp_path):
    """Nothing about sharing leaks into how an adapter is written or tested."""
    root = nwbfixture.build(tmp_path)
    assert store_for(root, None) is not store_for(root, None)


def test_the_adapters_that_share_a_root_share_its_store(tmp_path, registry):
    """Two adapters read the same .nwb, and both read the electrode table.

    The waveform adapter used to be a third. It reads the analyzer that computed the templates
    now, which is a different root, so it shares nothing with these two and needs no store of
    theirs.
    """
    from escapewheel_writer.recipe import Recipe
    from escapewheel_writer.session import Context
    from escapewheel_writer.sourcing import build_source

    root = nwbfixture.build(tmp_path)
    text = f"""
[packet]
id = "s1"
registry = "r"
[session]
session_id = "s1"
reference_clock_id = "harp"
[[clock]]
clock_id = "harp"
name = "HARP"
tick_rate_num = 31250
origin = "e"
[[source]]
kind = "nwb"
root = "{root}"
owns = ["core.electrodes"]
zone = "America/Los_Angeles"
[[source]]
kind = "lfp"
root = "{root}"
owns = ["core.array_channels"]
"""
    path = tmp_path / "session.toml"
    path.write_text(text)
    recipe = Recipe.load(path)
    # Both declare `units` and `clocks`, which a build fills from the sorter's output and
    # refuses to pass empty (Part 12 §4), so the context carries both as it would by the time any
    # of them is built.
    context = Context(
        session_id="s1",
        units=[{"device_name": "probeA", "local_unit_label": "0", "unit_id": 1}],
        clocks={PROBE_CLOCK["clock_id"]: PROBE_CLOCK},
    )
    built = [build_source(spec, recipe, context) for spec in recipe.sources]
    assert built[0].store is built[1].store
    assert len(context.stores) == 1
