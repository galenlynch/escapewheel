"""Build a miniature AIND-written NWB-Zarr: base NWB plus the columns this pipeline adds.

The base shape and the Zarr-writing helpers are the shared `nwbfixture` both suites import. Every
column added here is one `inventory/nwb-adapter-base-and-dialect.md` measured as belonging to one
producer rather than to the schema.
"""

from pathlib import Path

import numpy as np
import nwbfixture as base
from nwbfixture import array, group, pickled, text

__all__ = ["array", "build", "group", "pickled", "text", "units"]


def build(root: Path, **options) -> Path:
    """Build the base session, as `nwbfixture.build` takes its options, and add this producer's columns."""
    nwb = base.build(root, **options)
    # Every attribute core 2.9.0 declares for a model or a serial is left unset, and both facts
    # are packed into the description instead. Measured at 0 of 10 devices on one real session.
    group(
        nwb / "general/devices/probeA",
        neurodata_type="Device",
        manufacturer="IMEC",
        description="Model: Neuropixels 2.0 - Quad Base - Serial number: 12345",
    )
    electrodes = nwb / "general/extracellular_ephys/electrodes"
    text(electrodes / "electrode_name", ["e0", "e0"])  # repeats, as the real file's does
    # The four this exporter adds. R59 §2 promoted the first two to columns of
    # core.electrode_coordinates and declined the other two, which is the split Part 02 §8.6 turns
    # on: only what no column holds may travel in the bag.
    array(electrodes / "ccf_id", np.array([382, 0], dtype=np.int64))
    text(electrodes / "ccf_acronym", ["CA1", "root"])
    text(electrodes / "ccf_name", ["Field CA1", "root"])
    text(electrodes / "ccf_structure_id_path", ["/997/8/567/", "/997/"])
    array(electrodes / "ccf_ml", np.array([100.0, np.nan]))
    array(electrodes / "ccf_ap", np.array([200.0, np.nan]))
    array(electrodes / "ccf_dv", np.array([300.0, np.nan]))

    trials = nwb / "intervals/trials"
    array(trials / "animal_response", np.array([1.0]))
    array(trials / "rewarded_historyL", np.array([False]))
    array(trials / "rewarded_historyR", np.array([True]))
    array(trials / "goCue_start_time", np.array([1.2]))
    array(trials / "reward_outcome_time", np.array([1.5]))
    return nwb


def units(nwb: Path, *, refuses: bool = True) -> list[dict[str, object]]:
    """Add a units table carrying this pipeline's unit identity, and return the build's own rows.

    `refuses` writes `spike_times` in an encoding this package will not decode, so that reading it
    would leave a note -- which is how a test sees that the ragged column was skipped.
    """
    table = group(nwb / "units", neurodata_type="Units", colnames=["spike_times"])
    array(table / "id", np.array([0], dtype=np.int64))
    array(table / "ks_unit_id", np.array([7], dtype=np.int64))
    text(table / "device_name", ["probeA"])
    for axis in ("ccf_ml", "ccf_ap", "ccf_dv"):
        array(table / axis, np.array([100.0]))
    if refuses:
        array(table / "spike_times", ["<ref>"], filter_id="pickle")
    else:
        array(table / "spike_times", np.array([0.1, 0.2, 0.3]))
    array(table / "spike_times_index", np.array([3], dtype=np.int64))
    return [{"device_name": "probeA", "local_unit_label": "7", "unit_id": 1}]
