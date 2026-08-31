"""One source root, read once and shared."""

import numpy as np
import pytest

from nwb_lake_writer.sources.store import SourceStore, store_for
from nwb_lake_writer.sources.zarr_compat import UnsupportedEncoding
from tests import nwbfixture


@pytest.fixture
def store(tmp_path):
    return SourceStore(nwbfixture.build(tmp_path))


def test_an_array_is_parsed_once(store, monkeypatch):
    """The point of the store: two readers of the same bytes cannot disagree."""
    from nwb_lake_writer.sources import store as module

    calls = []
    real = module.read_array
    monkeypatch.setattr(module, "read_array", lambda p: calls.append(p) or real(p))
    first = store.array("intervals/trials/start_time")
    second = store.array("intervals/trials/start_time")
    assert len(calls) == 1
    assert np.array_equal(first, second)


def test_an_absolute_path_is_the_same_key_as_a_relative_one(store):
    from nwb_lake_writer.sources import store as module

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
    """Three adapters read the same .nwb, and two of them read the electrode table."""
    from nwb_lake_writer.recipe import Recipe
    from nwb_lake_writer.session import Context, _build_source

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
kind = "waveforms"
root = "{root}"
owns = ["core.unit_electrodes"]
[[source]]
kind = "lfp"
root = "{root}"
owns = ["core.array_channels"]
"""
    path = tmp_path / "session.toml"
    path.write_text(text)
    recipe = Recipe.load(path)
    context = Context(session_id="s1")
    built = [_build_source(spec, recipe, context) for spec in recipe.sources]
    assert built[0].store is built[1].store
    assert len(context.stores) == 1
