"""Build a miniature SpikeInterface curated tree, with the traps the real one carries.

The asset this adapter was written against is 79 GB and not in any repository, so the tests
build their own. What it reproduces deliberately:

- **`unit_ids` with a gap.** Kilosort leaves gaps where clusters merged, so `unit_index` --
  a dense offset -- and the unit id diverge after the first gap. A fixture with contiguous
  ids would pass whether or not the adapter resolves the offset.
- **A quad-base probe**, sorted as shank streams that share a serial.
- **Labels no closed vocabulary covers**: `non_soma` from bombcell, and the four sources
  disagreeing with each other.
- **A naive sorter timestamp**, which has no zone to be localized to.
"""

import json
from pathlib import Path

import numpy as np
from nwbfixture import array

#: Ids 0..5 with 3 and 4 missing, so offset 3 is unit 5. A fixture without a gap would not
#: distinguish an adapter that resolves `unit_index` from one that stores it.
UNIT_IDS = [0, 1, 2, 5, 12, 40]

#: One label per unit per source. bombcell alone emits `non_soma`, which Part 02 §9.3 projects to
#: null rather than forcing into `noise`.
LABELS = {
    "KSLabel": ["good", "mua", "good", "mua", "good", "mua"],
    "bombcell_label": ["good", "noise", "non_soma", "mua", "good", "noise"],
    "decoder_label": ["sua", "noise", "mua", "mua", "sua", "noise"],
    "unitrefine_label": ["sua", "noise", "sua", "mua", "sua", "noise"],
}


#: How long the recording behind a stream ran, in its own samples. Comfortably past the last
#: spike, as a real one is: a sorter cannot centre a template at the very end.
N_SAMPLES = (100,)

#: What the analyzer says it ran on: four contacts of a five-contact probe, `CH2` dropped, so a
#: channel index and a contact position part company at index 2.
CHANNEL_IDS = ("CH0", "CH1", "CH3", "CH4")


def stream(
    root: Path,
    name: str,
    *,
    spikes,
    unit_ids=UNIT_IDS,
    analyzer=True,
    return_in_uv=True,
    n_samples=N_SAMPLES,
    channel_ids=CHANNEL_IDS,
):
    """Write one curated stream, and optionally its SortingAnalyzer.

    Parameters
    ----------
    spikes : sequence of (unit_index, sample_index)
        In the source's own order, which is time order and not the packet's.
    """
    folder = root / "curated" / name
    (folder / "properties").mkdir(parents=True, exist_ok=True)

    table = np.array(
        [(t, u, 0) for u, t in spikes],
        dtype=[("sample_index", "<i8"), ("unit_index", "<i8"), ("segment_index", "<i8")],
    )
    np.save(folder / "spikes.npy", table)
    (folder / "numpysorting_info.json").write_text(
        json.dumps({"sampling_frequency": 30000.0, "unit_ids": list(unit_ids), "num_segments": 1})
    )
    (folder / "curation.json").write_text(
        json.dumps(
            {
                "format_version": "2",
                "unit_ids": list(unit_ids),
                "label_definitions": {"quality": {"name": "quality", "label_options": ["good", "MUA", "noise"]}},
                "manual_labels": [{"unit_id": unit_ids[1], "labels": {"quality": ["noise"]}}],
                "removed": [unit_ids[1]],
                "merges": [{"unit_ids": [unit_ids[0], unit_ids[2]], "new_unit_id": None}],
                "splits": [],
            }
        )
    )
    (folder / "si_folder.json").write_text(
        json.dumps(
            {
                "class": "spikeinterface.core.sortingfolder.NumpyFolderSorting",
                "version": "0.104.7",
                "annotations": {
                    "__sorting_info__": {
                        "log": {
                            "sorter_name": "kilosort4",
                            "sorter_version": "4.1.7",
                            # No offset, and its machine's zone is not recorded anywhere.
                            "datetime": "2026-08-26T23:25:57.061395",
                            "run_time": 1234.5,
                        },
                        "params": {"sorter_name": "kilosort4", "sorter_params": {"Th_universal": 9}},
                    }
                },
            }
        )
    )
    for name_, values in LABELS.items():
        np.save(folder / "properties" / f"{name_}.npy", np.array(values[: len(unit_ids)]))
    np.save(folder / "properties" / "decoder_probability.npy", np.linspace(0.5, 0.95, len(unit_ids)))
    np.save(folder / "properties" / "unitrefine_probability.npy", np.linspace(0.6, 0.9, len(unit_ids)))
    np.save(folder / "properties" / "original_cluster_id.npy", np.array(unit_ids, dtype=np.int64))

    if analyzer:
        zarr = root / "postprocessed" / f"{name}.zarr"
        zarr.mkdir(parents=True, exist_ok=True)
        (zarr / ".zgroup").write_text(json.dumps({"zarr_format": 2}))
        (zarr / ".zattrs").write_text(json.dumps({"settings": {"return_in_uV": return_in_uv}}))
        # `recording_info` lives only in the consolidated metadata, as SpikeInterface writes
        # it, and carries the recording length that is a sample clock's window.
        recording = {"recording_attributes": {"sampling_frequency": 30000.0}}
        if n_samples is not None:
            recording["recording_attributes"]["num_samples"] = list(n_samples)
        if channel_ids is not None:
            recording["recording_attributes"]["channel_ids"] = list(channel_ids)
        (zarr / ".zmetadata").write_text(json.dumps({"metadata": {"recording_info/.zattrs": recording}}))
        array(
            zarr / "extensions" / "spike_amplitudes" / "amplitudes",
            np.arange(len(spikes), dtype=np.float32) * -1.0,
        )
    return folder


#: Two shanks of one quad-base probe, so `core.probes` has to collapse them.
NAMES = (
    "experiment1_Record Node 109#Neuropix-PXI-100.50720-1_recording1",
    "experiment1_Record Node 109#Neuropix-PXI-100.50720-2_recording1",
    "experiment2_Record Node 109#Neuropix-PXI-100.50720-1_recording1",
)

#: Time-ordered, as the source is; units interleave, so the adapter has to sort.
SPIKES = [(0, 10), (3, 11), (1, 12), (5, 20), (0, 25), (3, 26), (2, 30), (0, 41), (4, 55), (5, 60)]


def build(root: Path, *, analyzer=True, n_samples=N_SAMPLES) -> Path:
    """Write the whole asset: three streams across two experiments."""
    for name in NAMES:
        stream(root, name, spikes=SPIKES, analyzer=analyzer, n_samples=n_samples)
    return root
