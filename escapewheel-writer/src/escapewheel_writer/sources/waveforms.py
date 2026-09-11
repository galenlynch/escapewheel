"""Read a unit's mean waveform out of an NWB and describe it as a packet array asset.

What the source stores and what a packet should store differ in three ways, each measured in
`conformance/zarr-probe/waveforms.py` against 6,781 real units.

**It is sparse, densified.** SpikeInterface computes a waveform on the contacts a unit sits
near -- 26 of 384 here, fewer at a probe's edge -- and the NWB pads the rest with zeros so it
need not record which contacts those were. 93.3% of the rectangle is padding. A packet records
the support instead, in `core.unit_electrodes`, which R28 added for the link and whose
`channel_index` is the position along the array's channel axis. R20 §2's labelled form on
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

`waveform_sd` is the same array of a different quantity and is stored the same way, on the
mean's support rather than on its own. Measured over 6,781 units the two live-channel masks
disagree on 52 of 2,603,904 (unit, channel) cells, every one of them live in the mean and zero
in the deviation and none the other way -- so the mean's support is a superset, cutting the
deviation on it loses nothing, and one `core.unit_electrodes` describes both channel axes.
Letting each array find its own support is what would make a position mean different contacts
in the two.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from numpy.typing import NDArray

from .nwb import SourceDefect
from .store import SourceStore, source_root

#: Samples either side of the window used to estimate what the average left behind. Only for
#: reporting; the scale comes from the range, not from this.
EDGE = 20


def _uri(asset_id: str) -> str:
    """Where the writer puts a packet-owned array, which `core.array_assets.uri` must match."""
    return f"arrays/core/{asset_id}.zarr"


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
        Identifier for the mean array.
    sd : bool
        Also read `waveform_sd` and store it as a second array. Off by default: it doubles what
        the read holds and costs a second pass over 3.1 GB, and a packet that wants only the
        template should not pay for it.
    sd_asset_id : str
        Identifier for the deviation array, when `sd` is set.
    compressed_per_chunk : float
        Expected compressed bytes per chunk, which is what `arrays.shard_for` sizes a shard
        against.
    prefix : str
        Prepended to identifiers this adapter mints.
    """

    #: `05` §3.4: what this adapter can supply, whatever a given root happens to hold.
    #: Static, so a recipe check reads it with nothing open -- `offers` counts rows and
    #: therefore needs the data.
    PRODUCES = frozenset(
        {
            "core.array_assets",
            "core.array_dimensions",
            "core.unit_electrodes",
        }
    )

    #: `05` §3.4: recipe fields this adapter states, to the attribute holding each. Declared
    #: empty rather than omitted, because a build refuses a source it cannot ask.
    STATES: ClassVar[dict[str, str]] = {}

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        units: dict[tuple[str, str], dict[str, str]],
        electrodes: dict[int, str] | None = None,
        array_asset_id: str = "waveform_mean",
        sd: bool = False,
        sd_asset_id: str = "waveform_sd",
        compressed_per_chunk: float = 3850.0,
        prefix: str = "",
        store: Any = None,
    ) -> None:
        self.root = source_root(root)
        self.store = store if store is not None else SourceStore(self.root)
        self.session_id = session_id
        self.units = dict(units)
        self.electrodes = dict(electrodes or {})
        self.array_asset_id = f"{prefix}{array_asset_id}"
        self.sd = sd
        self.sd_asset_id = f"{prefix}{sd_asset_id}"
        self.compressed_per_chunk = compressed_per_chunk
        self.prefix = prefix
        self.notes: list[str] = []
        self._built: dict[str, Any] | None = None

    # -- reading ------------------------------------------------------------------------

    def _scan(
        self, array: Any, device: Any, ks: Any, spread: Any = None
    ) -> tuple[
        list[int],
        list[dict[str, str]],
        list[NDArray[np.int64]],
        list[int],
        list[NDArray[np.float64]],
        float,
        list[NDArray[np.float64]],
        float,
    ]:
        """Walk the source a chunk row at a time, keeping only each unit's own contacts.

        The block is the source's own chunk along the unit axis, so every chunk is read exactly
        once and none is read twice. What survives a block is the slabs, which are two orders
        smaller than the block that produced them. They stay float64: the arithmetic that follows
        is a division and a round, and in float32 fourteen values in twenty-six million land on
        the other side of a tie.

        `spread` is cut on the mean's live mask rather than on its own, which is what keeps one
        `core.unit_electrodes` describing both arrays.

        The peak contact is taken here rather than from `extremum_channel_index`, which indexes
        the channels the sorting kept while every other channel axis in the file is the probe's
        full contact list. It is the most negative sample, not the largest absolute one: measured
        against the retained lists over 6,781 units, the negative peak reproduces the source's
        index in 6,781 and the absolute peak in 6,346.
        """
        total = array.shape[0]
        block = int(array.chunks[0]) or total
        keep: list[int] = []
        identity: list[dict[str, str]] = []
        support: list[NDArray[np.int64]] = []
        primary: list[int] = []
        slabs: list[NDArray[np.float64]] = []
        sd_slabs: list[NDArray[np.float64]] = []
        peak = sd_peak = 0.0
        for start in range(0, total, block):
            dense = np.asarray(array[start : start + block])
            deviation = np.asarray(spread[start : start + block]) if spread is not None else None
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
                primary.append(int(slab.min(axis=1).argmin()))
                slabs.append(slab)
                if deviation is not None:
                    sd_slab = deviation[offset][:, live].T.copy()
                    sd_peak = max(sd_peak, float(np.abs(sd_slab).max()))
                    sd_slabs.append(sd_slab)
            del dense, deviation
        return keep, identity, support, primary, slabs, peak, sd_slabs, sd_peak

    @staticmethod
    def _quantise(
        slabs: list[NDArray[np.float64]], peak: float, width: int, samples: int
    ) -> tuple[NDArray[np.int16], float]:
        """Scale float64 slabs onto int16, the peak landing on the last code.

        The quantisation this leaves is well under the standard error of the means themselves --
        measured at 0.052 uV for the best-resolved tenth, against a step of peak/32767. The
        deviation is non-negative and still stored signed, spending a bit it never uses: unsigned
        would buy one bit of resolution on a quantity whose own sampling error is far larger, at
        the cost of a second convention for reading these arrays.
        """
        scale = peak / 32767.0
        values = np.zeros((len(slabs), width, samples), dtype=np.int16)
        for position, slab in enumerate(slabs):
            values[position, : slab.shape[0]] = np.rint(slab / scale).astype(np.int16)
        return values, scale

    def _read(self) -> dict[str, Any]:
        """Pack the array once, and remember what packing it revealed.

        Read a chunk row at a time rather than whole. The source is `(units, samples,
        channels)` float64 chunked `(424, 19, 48)`, so materialising it costs 3.1 GB while one
        chunk row is 195 MB, and a unit's own slab -- the contacts it actually has signal on --
        is 31 KB. Keeping the slabs and discarding each block holds about 0.4 GB, and reads
        every chunk exactly once: the peak the scale needs is accumulated as the blocks go by
        rather than found in a second pass over an array held for the purpose. Asking for the
        deviation doubles both, since it is the same shape read the same way.
        """
        if self._built is not None:
            return self._built
        import zarr

        group = self.root / "units"
        array = zarr.open_array(str(group / "waveform_mean"), mode="r", zarr_format=2)
        spread = None
        if self.sd:
            try:
                # Broad, because which error an absent array raises is the store's business.
                spread = zarr.open_array(str(group / "waveform_sd"), mode="r", zarr_format=2)
            except Exception as absent:
                raise SourceDefect(f"sd was asked for and {group / 'waveform_sd'} does not open") from absent
            if spread.shape != array.shape:
                raise SourceDefect(f"waveform_sd is {spread.shape} where waveform_mean is {array.shape}")
        device = self.store.array(group / "device_name")
        ks = self.store.array(group / "ks_unit_id")
        electrode_rows = self.store.array(group / "electrodes")
        bounds = self.store.array(group / "electrodes_index")

        total, samples = array.shape[0], array.shape[1]
        keep, identity, support, primary, slabs, peak, sd_slabs, sd_peak = self._scan(array, device, ks, spread)

        if not keep:
            self.notes.append("units: no NWB row matches a unit in the packet's sorting")
            raise SourceDefect("no unit in waveform_mean matches the packet's sorting")
        if len(keep) < total:
            self.notes.append(f"units: {total - len(keep)} NWB row(s) match no unit or are all zero; skipped")
        width = max(s.size for s in support)
        if not peak:
            raise SourceDefect("waveform_mean is entirely zero, so no unit has a channel support")

        values, scale = self._quantise(slabs, peak, width, samples)
        self._built = {
            "primary": primary,
            "values": values,
            "scale": scale,
            "identity": identity,
            "support": support,
            "rows": keep,
            "electrode_rows": electrode_rows,
            "bounds": bounds,
            "samples": samples,
        }
        if self.sd:
            if not sd_peak:
                raise SourceDefect("waveform_sd is entirely zero over the mean's support")
            sd_values, sd_scale = self._quantise(sd_slabs, sd_peak, width, samples)
            self._built |= {"sd_values": sd_values, "sd_scale": sd_scale}
        return self._built

    # -- what the packet stores ----------------------------------------------------------

    @property
    def values(self) -> NDArray[np.int16]:
        """The array itself: `(unit, channel, sample)`, int16."""
        built = self._read()
        return built["values"]  # type: ignore[no-any-return]

    def _asset(
        self, asset_id: str, semantic_type: str, name: str, scale: float, uri: str, clock_id: str | None
    ) -> dict[str, Any]:
        """One `core.array_assets` row.

        No `dtype` or `shape`: the Zarr array declares both, and `02` §6 forbids a table from
        restating what the data already says. `conversion` is the one thing the array cannot
        say, so it is the one thing recorded here.
        """
        return {
            "array_asset_id": asset_id,
            "session_id": self.session_id,
            "semantic_type": semantic_type,
            "array_asset_name": name,
            "uri": uri,
            "format": "zarr_v3",
            "clock_id": clock_id,
            "sample_rate_hz": 30000.0,
            "unit": "uV",
            "conversion": scale,
            "offset": 0.0,
            "metadata": {"quantisation": "int16, scale = peak / 32767"},
        }

    def array_assets(self, uri: str | None = None, clock_id: str | None = None) -> list[dict[str, Any]]:
        """`core.array_assets`, one row per array this source stores.

        The deviation gets its own row and its own `conversion`, because it is quantised against
        its own peak; sharing the mean's scale would spend resolution on a range it never
        reaches. Everything else about the two is identical, the deviation being the mean's
        shape on the mean's contacts.
        """
        built = self._read()
        rows = [
            self._asset(
                self.array_asset_id,
                "waveform_mean",
                "mean waveform per unit",
                built["scale"],
                uri or _uri(self.array_asset_id),
                clock_id,
            )
        ]
        if self.sd:
            rows.append(
                self._asset(
                    self.sd_asset_id,
                    "waveform_sd",
                    "waveform standard deviation per unit",
                    built["sd_scale"],
                    _uri(self.sd_asset_id),
                    clock_id,
                )
            )
        return rows

    def _axes(self, asset_id: str, clock_id: str | None, origin: int | None) -> list[dict[str, Any]]:
        """One array's three axes, in stored order (R3 §5)."""
        built = self._read()
        start = origin if origin is not None else -(built["samples"] // 2)
        sample_axis: dict[str, Any] = {
            "array_asset_id": asset_id,
            "axis_index": 2,
            "dimension_name": "sample",
        }
        if clock_id is None:
            sample_axis |= {"origin_value": float(start), "step_value": 1.0, "coordinate_unit": "sample"}
        else:
            sample_axis |= {"clock_id": clock_id, "origin_tick": start, "step_tick_num": 1}
        return [
            {"array_asset_id": asset_id, "axis_index": 0, "dimension_name": "unit"},
            {
                "array_asset_id": asset_id,
                "axis_index": 1,
                "dimension_name": "channel",
                "coordinate_resource": "core.unit_electrodes",
                "coordinate_position_column": "channel_index",
            },
            sample_axis,
        ]

    def array_dimensions(self, clock_id: str | None = None, origin: int | None = None) -> list[dict[str, Any]]:
        """`core.array_dimensions`, one row per axis of each array, in stored order (R3 §5).

        The channel axis takes R20 §2's labelled form, pointing at `core.unit_electrodes`,
        because which contact a position means is per unit and no coordinate array can say it.
        Both arrays point at the same rows: the deviation is cut on the mean's support, so a
        position means the same contact in each.

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
        axes = self._axes(self.array_asset_id, clock_id, origin)
        if self.sd:
            axes += self._axes(self.sd_asset_id, clock_id, origin)
        return axes

    def unit_electrodes(self) -> list[dict[str, Any]]:
        """`core.unit_electrodes`, one row per unit per contact it has signal on (R28).

        This is the array's channel axis written down. Without it the array's second axis is
        an offset into nothing, which is exactly the state the NWB is in -- it pads to 384 so
        that it never has to say which contacts a unit was computed on.

        Supersedes `NWBSource.unit_electrodes`, which emits nothing because the peak contact
        is not resolvable from the file's own columns. One relation, one emitter: a packet with
        waveforms takes the support from here, and the peak is marked among it rather than
        standing as a separate row that would collide on the key.

        `is_primary` is the template's own negative peak, taken in `_scan`. Reading
        `extremum_channel_index` as a contact position names the wrong electrode whenever the
        sorting dropped a channel below it -- 5,071 of 6,781 units on the measured session, of
        which 609 were marked on no contact at all because the index landed outside the unit's
        support and the other 4,462 were marked on a contact that is not the peak.

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
                        "channel_index": ordinal,
                        "is_primary": ordinal == built["primary"][position],
                    }
                )
        return rows

    def staged_arrays(self) -> list[Any]:
        """Return the arrays themselves, sized for the store they will live in.

        The chunk is one unit, which is the unit of the question, and `shard_for` keeps that
        from becoming one object per chunk (`conformance/zarr-probe/waveforms.py`).
        """
        from ..arrays import shard_for
        from ..writer import StagedArray

        built = self._read()
        wanted = [(self.array_asset_id, built["values"])]
        if self.sd:
            wanted.append((self.sd_asset_id, built["sd_values"]))
        staged = []
        for asset_id, values in wanted:
            chunks = (1, *values.shape[1:])
            staged.append(
                StagedArray(
                    values=values,
                    array_asset_id=asset_id,
                    chunks=chunks,
                    shard=shard_for(values.shape, chunks, self.compressed_per_chunk),
                )
            )
        return staged

    def records(self, *, uri: str | None = None, clock_id: str | None = None) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records, keyed by resource ID.

        The arrays themselves are not among them: they are bytes, staged through
        `PacketWriter.add_array` from `staged_arrays`.
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
