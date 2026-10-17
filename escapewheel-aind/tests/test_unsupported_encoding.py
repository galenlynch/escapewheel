"""Every adapter registered here reports an array it will not decode as a defect of its source.

A build catches a `SourceDefect` and names the source it lay in, so an adapter letting any other
exception out ends the build with a traceback. Each kind that reads Zarr runs here on its own
fixture with one array it needs declared pickled.
"""

from __future__ import annotations

import sys
from importlib.metadata import entry_points

import pytest
from adapter_columns import emitted
from escapewheel_writer.adapter import SOURCE_GROUP, SourceDefect, SourceFault

from escapewheel_aind.errors import AindFault
from escapewheel_aind.unit_qc import UnitQCSource
from tests import nwbfixture
from tests.test_adapter_columns import BUILDERS
from tests.test_unit_qc import UNITS, nwb_units

ANALYZER = "sorted/postprocessed/experiment1_Record Node 109#Neuropix-PXI-100.A_recording1.zarr"

#: The arrays each kind needs and its fixture holds, relative to the fixture's root, each with the
#: code the defect carries; none for a kind that reads no Zarr.
NEEDED: dict[str, tuple[tuple[str, str], ...]] = {
    "session": (),
    "video": (),
    "dynamic_foraging": (),
    "aind_nwb": (("mini.nwb/acquisition/sniff/timestamps", SourceFault.PICKLED),),
    # A column the analyzer holds in another encoding is not a metric, so the adapter skips it and
    # reports what the table then lacks.
    "aind_unit_qc": ((f"{ANALYZER}/extensions/quality_metrics/metrics/index", AindFault.NO_UNIT_INDEX),),
}

#: What a module binds if it decodes Zarr.
READERS = {"SourceStore", "read_array", "DenseV2"}


def test_every_registered_kind_is_checked():
    registered = {e.name for e in entry_points(group=SOURCE_GROUP) if e.dist and e.dist.name == "escapewheel-aind"}
    assert set(NEEDED) == registered


@pytest.mark.parametrize(
    ("kind", "array", "code"), [(kind, *needed) for kind, arrays in sorted(NEEDED.items()) for needed in arrays]
)
def test_an_adapter_reports_an_array_it_will_not_decode_as_a_defect(kind, array, code, tmp_path, monkeypatch):
    source = BUILDERS[kind](tmp_path, monkeypatch)
    nwbfixture.pickled(tmp_path / array)
    with pytest.raises(SourceDefect) as refused:
        emitted(source)
    assert refused.value.code is code


def test_the_unit_names_an_nwb_states_pickled_are_a_defect(tmp_path, monkeypatch):
    """The second store the unit-QC adapter reads, which names the units it fills from."""
    BUILDERS["aind_unit_qc"](tmp_path, monkeypatch)
    nwb = nwb_units(tmp_path)
    names = nwbfixture.pickled(nwb / "units/device_name")
    with pytest.raises(SourceDefect) as refused:
        UnitQCSource(tmp_path / "sorted", session_id="s1", units=UNITS, nwb=nwb).records()
    assert refused.value.code is SourceFault.PICKLED
    assert refused.value.where == str(names)


@pytest.mark.parametrize("kind", sorted(kind for kind, arrays in NEEDED.items() if not arrays))
def test_a_kind_with_no_array_here_decodes_no_zarr(kind):
    """Which is what leaves it with no encoding to refuse."""
    adapter = {e.name: e for e in entry_points(group=SOURCE_GROUP)}[kind].load()
    assert READERS.isdisjoint(vars(sys.modules[adapter.__module__]))
