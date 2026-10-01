"""Every built-in adapter reports an array it will not decode as a defect of its source.

A build catches a `SourceDefect` and names the source it lay in, so an adapter letting any other
exception out ends the build with a traceback. Each kind that reads Zarr runs here on its own
fixture with one array it needs declared pickled.
"""

from __future__ import annotations

import sys

import nwbfixture
import pytest
from adapter_columns import emitted

from escapewheel_writer.errors import SourceDefect, SourceFault, UnsupportedEncoding
from escapewheel_writer.sources import ADAPTERS
from tests import sorterfixture
from tests.test_adapter_columns import BUILDERS
from tests.test_waveforms import STREAM

#: The arrays each kind needs and its fixture holds, relative to the fixture's root; none for a
#: kind that reads no Zarr.
NEEDED: dict[str, tuple[str, ...]] = {
    "harp": (),
    "openephys": (),
    "sync": (),
    "sorter": (f"postprocessed/{sorterfixture.NAMES[0]}.zarr/extensions/spike_amplitudes/amplitudes",),
    "nwb": ("mini.nwb/acquisition/sniff/timestamps",),
    "waveforms": (f"postprocessed/{STREAM}/sorting/unit_ids", f"postprocessed/{STREAM}/extensions/templates/average"),
    "lfp": ("s.nwb/processing/ecephys/LFP/ElectricalSeries45883-1-LFP/electrodes",),
}

#: What a module binds if it decodes Zarr.
READERS = {"SourceStore", "read_array", "DenseV2"}


def test_every_built_in_kind_is_checked():
    assert set(NEEDED) == set(ADAPTERS)


def test_an_unsupported_encoding_is_a_source_defect():
    assert issubclass(UnsupportedEncoding, SourceDefect)


@pytest.mark.parametrize(
    ("kind", "array"), [(kind, array) for kind, arrays in sorted(NEEDED.items()) for array in arrays]
)
def test_an_adapter_reports_an_array_it_will_not_decode_as_a_defect(kind, array, tmp_path):
    source = BUILDERS[kind](tmp_path)
    unreadable = nwbfixture.pickled(tmp_path / array)
    with pytest.raises(SourceDefect) as refused:
        emitted(source)
    assert refused.value.code is SourceFault.PICKLED
    assert refused.value.where == str(unreadable)


@pytest.mark.parametrize("kind", sorted(kind for kind, arrays in NEEDED.items() if not arrays))
def test_a_kind_with_no_array_here_decodes_no_zarr(kind):
    """Which is what leaves it with no encoding to refuse."""
    assert READERS.isdisjoint(vars(sys.modules[ADAPTERS[kind].__module__]))
