"""Build a miniature NWB-Zarr on disk, including the parts zarr-python cannot open.

The real file this adapter was written against is 8.49 GB and not in any repository, so the
tests build their own. It reproduces both faults measured in
`inventory/nwb-zarr-776259-2025-04-09.md` §1 -- vlen-bytes scalars with a numeric fill value,
and a pickled object-reference column -- because those are what the adapter exists to survive.
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
    group(
        general / "devices" / "probeA",
        neurodata_type="Device",
        manufacturer="IMEC",
        description="Model: Neuropixels 2.0 - Quad Base - Serial number: 12345",
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
    text(electrodes / "electrode_name", ["e0", "e0"])  # repeats, as the real file's does
    text(electrodes / "location", ["CA1", "unknown"])
    # The four the AIND exporter adds. R59 §2 promoted the first two to columns of
    # core.electrode_coordinates and declined the other two, which is the split `02` §8.6
    # turns on: only what no column holds may travel in the bag.
    array(electrodes / "ccf_id", np.array([382, 0], dtype=np.int64))
    text(electrodes / "ccf_acronym", ["CA1", "root"])
    text(electrodes / "ccf_name", ["Field CA1", "root"])
    text(electrodes / "ccf_structure_id_path", ["/997/8/567/", "/997/"])
    array(electrodes / "rel_x", np.array([0.0, 32.0]))
    array(electrodes / "rel_y", np.array([0.0, 0.0]))
    array(electrodes / "ccf_ml", np.array([100.0, np.nan]))
    array(electrodes / "ccf_ap", np.array([200.0, np.nan]))
    array(electrodes / "ccf_dv", np.array([300.0, np.nan]))
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
    array(trials / "animal_response", np.array([1.0]))
    array(trials / "rewarded_historyL", np.array([False]))
    array(trials / "rewarded_historyR", np.array([True]))
    array(trials / "reward_probabilityL", np.array([0.4]))
    array(trials / "goCue_start_time", np.array([1.2]))
    array(trials / "reward_outcome_time", np.array([1.5]))
    array(trials / "laser_on_trial", np.array([0], dtype=np.int64))
    array(trials / "auto_train_engaged", np.array([False]))
    text(trials / "auto_train_stage", ["None"])
    return nwb
