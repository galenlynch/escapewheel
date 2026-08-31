"""Read a unit's mean waveform out of an NWB and describe it as a packet array asset.

What the source stores and what a packet should store differ in three ways, each measured in
`conformance/zarr-probe/waveforms.py` against 6,781 real units.

**It is sparse, densified.** SpikeInterface computes a waveform on the contacts a unit sits
near -- 26 of 384 here, fewer at a probe's edge -- and the NWB pads the rest with zeros so it
need not record which contacts those were. 93.3% of the rectangle is padding. A packet records
the support instead, in `core.unit_electrodes`, which R28 added for the link and whose
`channel_ordinal` is the position along the array's channel axis. R20 §2's labelled form on
that axis is what ties the two together.

**It is float64 over int16 samples.** Every value round-trips through float32 with zero error,
and the samples averaged were 10-bit ADC counts. Stored as int16 with a scale on
`core.array_assets.conversion` -- the form an `ElectricalSeries` already uses -- the array is
a quarter of the width and the packet says what the scale is.

**Time is not the fastest axis.** The source stores (unit, sample, channel), mirroring a
recording. A template is not a recording: one channel's trace is a smooth curve and adjacent
channels are independent noise, so (unit, channel, sample) both compresses better and matches
how a trace is read -- 11% smaller and a trace 3.8x faster. R3 §5 makes the stored order the
packet's to declare.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .nwb import SourceDefect
from .store import SourceStore

#: Samples either side of the window used to estimate what the average left behind. Only for
#: reporting; the scale comes from the range, not from this.
EDGE = 20


def _support(dense: NDArray[Any], width: int) -> list[NDArray[np.int64]]:
    """Which channel each unit actually has signal on, in the source's channel order."""
    live = (dense != 0).any(axis=1)
    return [np.flatnonzero(row)[:width] for row in live]


class WaveformSource:
    """`waveform_mean` from an NWB, as a sparse int16 array plus the tables describing it.

    Parameters
    ----------
    root : str or Path
        The `.nwb` directory.
    session_id : str
        The session these units belong to.
    units : Mapping
        `(device_name, ks_unit_id)` to the identifying triple, as `NWBSource` takes. The array
        rows follow the NWB's own unit order, and a unit the packet's sorting does not contain
        is skipped rather than stored as padding.
    electrodes : Mapping, optional
        Global electrode row index to `electrode_id`, so the support can name real electrodes.
        Without it `core.unit_electrodes` is not emitted and the channel axis carries no
        coordinate.
    array_asset_id : str
        Identifier for the array.
    prefix : str
        Prepended to identifiers this adapter mints.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        units: dict[tuple[str, str], dict[str, str]],
        electrodes: dict[int, str] | None = None,
        array_asset_id: str = "waveform_mean",
        prefix: str = "",
        store: Any = None,
    ) -> None:
        self.root = Path(root)
        self.store = store if store is not None else SourceStore(self.root)
        self.session_id = session_id
        self.units = dict(units)
        self.electrodes = dict(electrodes or {})
        self.array_asset_id = f"{prefix}{array_asset_id}"
        self.prefix = prefix
        self.notes: list[str] = []
        self._built: dict[str, Any] | None = None

    # -- reading ------------------------------------------------------------------------

    def _scan(
        self, array: Any, device: Any, ks: Any
    ) -> tuple[list[int], list[dict[str, str]], list[NDArray[np.int64]], list[NDArray[np.float64]], float]:
        """Walk the source a chunk row at a time, keeping only each unit's own contacts.

        The block is the source's own chunk along the unit axis, so every chunk is read exactly
        once and none is read twice. What survives a block is the slabs, which are two orders
        smaller than the block that produced them. They stay float64: the arithmetic that follows
        is a division and a round, and in float32 fourteen values in twenty-six million land on
        the other side of a tie.
        """
        total = array.shape[0]
        block = int(array.chunks[0]) or total
        keep: list[int] = []
        identity: list[dict[str, str]] = []
        support: list[NDArray[np.int64]] = []
        slabs: list[NDArray[np.float64]] = []
        peak = 0.0
        for start in range(0, total, block):
            dense = np.asarray(array[start : start + block])
            for offset in range(dense.shape[0]):
                found = self.units.get((str(device[start + offset]), str(int(ks[start + offset]))))
                if found is None:
                    continue
                live = np.flatnonzero((dense[offset] != 0).any(axis=0))
                if not live.size:
                    continue
                slab = dense[offset][:, live].T.copy()
                peak = max(peak, float(np.abs(slab).max()))
                keep.append(start + offset)
                identity.append(found)
                support.append(live)
                slabs.append(slab)
            del dense
        return keep, identity, support, slabs, peak

    def _read(self) -> dict[str, Any]:
        """Pack the array once, and remember what packing it revealed.

        Read a chunk row at a time rather than whole. The source is `(units, samples,
        channels)` float64 chunked `(424, 19, 48)`, so materialising it costs 3.1 GB while one
        chunk row is 195 MB, and a unit's own slab -- the contacts it actually has signal on --
        is 31 KB. Keeping the slabs and discarding each block holds about 0.4 GB, and reads
        every chunk exactly once: the peak the scale needs is accumulated as the blocks go by
        rather than found in a second pass over an array held for the purpose.
        """
        if self._built is not None:
            return self._built
        import zarr

        group = self.root / "units"
        array = zarr.open_array(str(group / "waveform_mean"), mode="r", zarr_format=2)
        device = self.store.array(group / "device_name")
        ks = self.store.array(group / "ks_unit_id")
        electrode_rows = self.store.array(group / "electrodes")
        bounds = self.store.array(group / "electrodes_index")
        extremum = self.store.array(group / "extremum_channel_index")

        total, samples = array.shape[0], array.shape[1]
        keep, identity, support, slabs, peak = self._scan(array, device, ks)

        if not keep:
            self.notes.append("units: no NWB row matches a unit in the packet's sorting")
            raise SourceDefect("no unit in waveform_mean matches the packet's sorting")
        if len(keep) < total:
            self.notes.append(f"units: {total - len(keep)} NWB row(s) match no unit or are all zero; skipped")
        width = max(s.size for s in support)
        if not peak:
            raise SourceDefect("waveform_mean is entirely zero, so no unit has a channel support")

        # int16 spans the range; the scale is what makes the peak land on the last code. The
        # quantisation this leaves is well under the standard error of the means themselves --
        # measured at 0.052 uV for the best-resolved tenth, against a step of peak/32767.
        scale = peak / 32767.0
        values = np.zeros((len(keep), width, samples), dtype=np.int16)
        for position, slab in enumerate(slabs):
            values[position, : slab.shape[0]] = np.rint(slab / scale).astype(np.int16)

        self._built = {
            "extremum": extremum,
            "values": values,
            "scale": scale,
            "identity": identity,
            "support": support,
            "rows": keep,
            "electrode_rows": electrode_rows,
            "bounds": bounds,
            "samples": samples,
        }
        return self._built
        import zarr

        group = self.root / "units"
        dense = np.asarray(zarr.open_array(str(group / "waveform_mean"), mode="r", zarr_format=2)[:])
        device = self.store.array(group / "device_name")
        ks = self.store.array(group / "ks_unit_id")
        electrode_rows = self.store.array(group / "electrodes")
        bounds = self.store.array(group / "electrodes_index")
        extremum = self.store.array(group / "extremum_channel_index")

        width = max((s.size for s in _support(dense, dense.shape[2])), default=0)
        if not width:
            raise SourceDefect("waveform_mean is entirely zero, so no unit has a channel support")

        keep, identity, support = [], [], []
        for row in range(dense.shape[0]):
            found = self.units.get((str(device[row]), str(int(ks[row]))))
            if found is None:
                continue
            keep.append(row)
            identity.append(found)
            support.append(np.flatnonzero((dense[row] != 0).any(axis=0))[:width])
        if not keep:
            self.notes.append("units: no NWB row matches a unit in the packet's sorting")
            raise SourceDefect("no unit in waveform_mean matches the packet's sorting")
        if len(keep) < dense.shape[0]:
            self.notes.append(f"units: {dense.shape[0] - len(keep)} NWB row(s) match no unit; skipped")

        peak = float(np.abs(dense[keep]).max())
        # int16 spans the range; the scale is what makes the peak land on the last code. The
        # quantisation this leaves is well under the standard error of the means themselves --
        # measured at 0.052 uV for the best-resolved tenth, against a step of peak/32767.
        scale = peak / 32767.0 if peak else 1.0
        values = np.zeros((len(keep), width, dense.shape[1]), dtype=np.int16)
        for position, (row, channels) in enumerate(zip(keep, support, strict=True)):
            values[position, : channels.size] = np.rint(dense[row][:, channels].T / scale).astype(np.int16)

        self._built = {
            "extremum": extremum,
            "values": values,
            "scale": scale,
            "identity": identity,
            "support": support,
            "rows": keep,
            "electrode_rows": electrode_rows,
            "bounds": bounds,
            "samples": dense.shape[1],
        }
        return self._built

    # -- what the packet stores ----------------------------------------------------------

    @property
    def values(self) -> NDArray[np.int16]:
        """The array itself: `(unit, channel, sample)`, int16."""
        built = self._read()
        return built["values"]  # type: ignore[no-any-return]

    def array_assets(self, uri: str, clock_id: str | None = None) -> list[dict[str, Any]]:
        """`core.array_assets`, one row.

        No `dtype` or `shape`: the Zarr array declares both, and R3 §3.0 forbids a table from
        restating what the data already says. `conversion` is the one thing the array cannot
        say, so it is the one thing recorded here.
        """
        built = self._read()
        return [
            {
                "array_asset_id": self.array_asset_id,
                "session_id": self.session_id,
                "semantic_type": "waveform_mean",
                "name": "mean waveform per unit",
                "kind": "dense_array_asset",
                "uri": uri,
                "format": "zarr_v3",
                "clock_id": clock_id,
                "sample_rate_hz": 30000.0,
                "unit": "uV",
                "conversion": built["scale"],
                "offset": 0.0,
                "metadata": {"quantisation": "int16, scale = peak / 32767"},
            }
        ]

    def array_dimensions(self, clock_id: str | None = None, origin: int | None = None) -> list[dict[str, Any]]:
        """`core.array_dimensions`, one row per axis, in stored order (R3 §5).

        The channel axis takes R20 §2's labelled form, pointing at `core.unit_electrodes`,
        because which contact a position means is per unit and no coordinate array can say it.

        The sample axis takes the **numeric** form, in samples, and not the tick form. A
        waveform window is not positioned on any session clock: position *k* is *k - origin*
        samples from the spike, and each unit's spike sits on the clock of the probe that
        recorded it -- twelve of them here, at slightly different true rates. Naming one would
        be wrong for eleven. Samples rather than seconds for the same reason: every waveform is
        150 consecutive samples of its own probe exactly, where seconds would be a nominal
        30 kHz that no probe quite runs at.

        Passing `clock_id` switches to the tick form, which is right only for an array whose
        units all sit on one clock.
        """
        built = self._read()
        start = origin if origin is not None else -(built["samples"] // 2)
        sample_axis: dict[str, Any] = {
            "array_asset_id": self.array_asset_id,
            "axis_index": 2,
            "dimension_name": "sample",
        }
        if clock_id is None:
            sample_axis |= {"origin_value": float(start), "step_value": 1.0, "coordinate_unit": "sample"}
        else:
            sample_axis |= {"clock_id": clock_id, "origin_tick": start, "step_ticks": 1}
        return [
            {"array_asset_id": self.array_asset_id, "axis_index": 0, "dimension_name": "unit"},
            {
                "array_asset_id": self.array_asset_id,
                "axis_index": 1,
                "dimension_name": "channel",
                "coordinate_resource": "core.unit_electrodes",
                "coordinate_position_column": "channel_ordinal",
            },
            sample_axis,
        ]

    def unit_electrodes(self) -> list[dict[str, Any]]:
        """`core.unit_electrodes`, one row per unit per contact it has signal on (R28).

        This is the array's channel axis written down. Without it the array's second axis is
        an offset into nothing, which is exactly the state the NWB is in -- it pads to 384 so
        that it never has to say which contacts a unit was computed on.

        Supersedes `NWBSource.unit_electrodes`, which emits only the peak contact because it
        reads the file without zarr and the support lives in a rank-3 array. One relation, one
        emitter: a packet with waveforms takes the support from here, and the peak is marked
        among it rather than standing as a separate row that would collide on the key.

        R28 `amplitude` is left null. The source measures one amplitude per unit, not per
        electrode, and it is not a reduction of the template either -- no peak, trough,
        absolute extremum or peak-to-trough of `waveform_mean` reproduces it. Filling the
        column would mean inventing a number the source disagrees with.
        """
        built = self._read()
        if not self.electrodes:
            self.notes.append("no electrode map given, so the channel support is not emitted")
            return []
        rows = []
        for position, (row, channels) in enumerate(zip(built["rows"], built["support"], strict=True)):
            start = 0 if row == 0 else int(built["bounds"][row - 1])
            identity = built["identity"][position]
            for ordinal, channel in enumerate(channels):
                electrode = self.electrodes.get(int(built["electrode_rows"][start + int(channel)]))
                if electrode is None:
                    continue
                rows.append(
                    {
                        "session_id": self.session_id,
                        **identity,
                        "electrode_id": electrode,
                        "channel_ordinal": ordinal,
                        "is_primary": int(channel) == int(built["extremum"][row]),
                    }
                )
        return rows

    def records(
        self, *, uri: str = "arrays/core/waveform_mean.zarr", clock_id: str | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records, keyed by resource ID.

        The array itself is not among them: it is bytes, staged through `PacketWriter.add_array`.
        """
        built = {
            "core.array_assets": self.array_assets(uri=uri),
            "core.array_dimensions": self.array_dimensions(clock_id=clock_id),
            "core.unit_electrodes": self.unit_electrodes(),
        }
        return {resource: rows for resource, rows in built.items() if rows}

    def offers(self) -> dict[str, int]:
        """Which resources this source supplies from its root, and how many rows (`05` §1)."""
        return {resource: len(rows) for resource, rows in self.records().items()}


__all__ = ["EDGE", "WaveformSource"]
