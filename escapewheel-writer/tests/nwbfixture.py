"""Build a miniature NWB-Zarr on disk, including the parts zarr-python cannot open.

The real file this adapter was written against is 8.49 GB and not in any repository, so the
tests build their own. It reproduces both faults measured in
`inventory/nwb-zarr-776259-2025-04-09.md` §1 -- vlen-bytes scalars with a numeric fill value,
and a pickled object-reference column -- because those are what the adapter exists to survive.

What it writes is what core NWB 2.9.0 declares, plus `channel_name`, which the schema does not
and SpikeInterface reads out of files it did not write. A producer's own columns belong in the
fixture of whichever adapter reads them: `escapewheel-aind` builds on this shape and adds the
atlas triple, the packed device description and the task's trial columns.
"""

import json
import pickle
from pathlib import Path

import numcodecs
import numpy as np

BLOSC = {"id": "blosc", "cname": "lz4", "clevel": 5, "shuffle": 1, "blocksize": 0}


def group(path: Path, **attributes) -> Path:
    """Create a Zarr v2 group with attributes."""
    path.mkdir(parents=True, exist_ok=True)
    (path / ".zgroup").write_text(json.dumps({"zarr_format": 2}))
    if attributes:
        (path / ".zattrs").write_text(json.dumps(attributes))
    return path


def array(path: Path, values, *, filter_id: str | None = None, **attributes) -> Path:
    """Write a one-dimensional Zarr v2 array, in one chunk.

    `filter_id` selects the object encoding: ``vlen-utf8`` for text, ``vlen-bytes`` for the
    scalar datetimes hdmf-zarr writes that way, ``pickle`` for object references. A filtered
    array gets ``fill_value: 0`` exactly as hdmf-zarr writes it -- that combination is what
    zarr-python 3.3 rejects.
    """
    path.mkdir(parents=True, exist_ok=True)
    if filter_id is None:
        data = np.asarray(values)
        dtype, filters = data.dtype.str, []
        buffer = data.tobytes()
    else:
        data = np.empty(len(values), dtype=object)
        data[:] = list(values)
        dtype, filters = "|O", [{"id": filter_id}]
        if filter_id == "pickle":
            filters = [{"id": "pickle", "protocol": pickle.HIGHEST_PROTOCOL}]
        buffer = numcodecs.get_codec(filters[0]).encode(data)
    (path / "0").write_bytes(numcodecs.get_codec(BLOSC).encode(buffer))
    (path / ".zarray").write_text(
        json.dumps(
            {
                "zarr_format": 2,
                "shape": [len(values)],
                "chunks": [len(values)],
                "dtype": dtype,
                "compressor": BLOSC,
                "filters": filters or None,
                "fill_value": 0,
                "order": "C",
            }
        )
    )
    if attributes:
        (path / ".zattrs").write_text(json.dumps(attributes))
    return path


def text(path: Path, values, **attributes) -> Path:
    """Write a vlen-utf8 array."""
    return array(path, values, filter_id="vlen-utf8", **attributes)


def build(root: Path, *, seconds=(1.0, 2.0), trial_stop=None, session_offset="-07:00") -> Path:
    """Build a whole miniature session and return the ``.nwb`` directory.

    Times are on a 31,250 Hz grid so they quantize exactly, except where a test asks
    otherwise. One trial, two licks, two electrodes on one probe.
    """
    nwb = group(root / "mini.nwb", neurodata_type="NWBFile", nwb_version="2.10.0")
    text(nwb / "identifier", ["abc-123"])
    text(nwb / "session_description", ["a miniature session"])
    # vlen-bytes with a numeric fill value: the encoding zarr-python refuses
    array(nwb / "session_start_time", [f"2025-04-09T17:25:12{session_offset}".encode()], filter_id="vlen-bytes")

    general = group(nwb / "general")
    text(general / "session_id", ["mini_2025-04-09"])
    text(general / "institution", ["Allen Institute for Neural Dynamics"])
    subject = group(general / "subject")
    text(subject / "subject_id", ["m001"])
    text(subject / "species", ["Mus musculus"])
    text(subject / "sex", ["M"])
    text(subject / "genotype", ["wt"])
    # -07:53 is Pacific Local Mean Time, which is what the real file carries here
    array(subject / "date_of_birth", [b"2024-09-24T00:00:00-07:53"], filter_id="vlen-bytes")

    group(general / "devices")
    # The three attributes core 2.9.0 declares for a Device, each holding what it is for. A
    # producer that leaves them empty and packs the same facts into `description` is the case
    # `escapewheel-aind` tests.
    group(
        general / "devices" / "probeA",
        neurodata_type="Device",
        manufacturer="IMEC",
        model_number="Neuropixels 2.0 - Quad Base",
        serial_number="12345",
        description="a probe",
    )
    ephys = group(general / "extracellular_ephys")
    group(
        ephys / "probeA",
        neurodata_type="ElectrodeGroup",
        location="CA1",
        description="Recorded electrodes from probe probeA",
        zarr_link=[{"name": "device", "path": "/general/devices/probeA", "source": "."}],
    )
    electrodes = group(ephys / "electrodes", neurodata_type="ElectrodesTable", colnames=["location", "group"])
    array(electrodes / "id", np.array([0, 1], dtype=np.int64))
    text(electrodes / "group_name", ["probeA", "probeA"])
    text(electrodes / "channel_name", ["CH0", "CH1"])
    text(electrodes / "location", ["CA1", "unknown"])
    array(electrodes / "rel_x", np.array([0.0, 32.0]))
    array(electrodes / "rel_y", np.array([0.0, 0.0]))
    array(electrodes / "x", np.array([np.nan, np.nan]))
    array(electrodes / "imp", np.array([np.nan, np.nan]))
    # object references, pickled: unreadable and unnecessary, group_name says the same thing
    array(electrodes / "group", ["<ref>", "<ref>"], filter_id="pickle")

    acquisition = group(nwb / "acquisition")
    licks = group(acquisition / "left_lick_time", neurodata_type="TimeSeries", description="The time of left licks")
    array(licks / "timestamps", np.asarray(seconds, dtype=np.float64))
    array(licks / "data", np.ones(len(seconds)))
    absent = group(acquisition / "FIP_rising_time", neurodata_type="TimeSeries", description="placeholder")
    array(absent / "timestamps", np.array([np.nan]))
    array(absent / "data", np.array([1.0]))

    trials = group(nwb / "intervals/trials", neurodata_type="TimeIntervals", colnames=["start_time", "stop_time"])
    array(trials / "id", np.array([0], dtype=np.int64))
    array(trials / "start_time", np.array([1.0]))
    array(trials / "stop_time", np.array([2.0 if trial_stop is None else trial_stop]))
    # Columns `TimeIntervals` does not declare, which a base reader carries verbatim rather than
    # interpreting. They exercise the constant/varying split, not any task's shape.
    array(trials / "reward_probabilityL", np.array([0.4]))
    array(trials / "laser_on_trial", np.array([0], dtype=np.int64))
    array(trials / "auto_train_engaged", np.array([False]))
    text(trials / "auto_train_stage", ["None"])
    return nwb
