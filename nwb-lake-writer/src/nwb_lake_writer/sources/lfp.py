"""Reference an NWB's LFP series as external array assets, and describe their axes.

Five things about this data decide the shape of what follows, each measured against the twelve
series of `ecephys_776259_2025-04-09`.

**It is referenced, not copied.** 5.8 GB of compressed int16 across twelve probes. R14 §2.3
makes referencing the expected form for a resource this size: copying duplicates the bulk of a
dataset, and transcoding to the portable floor would discard the acquisition's own compression
for nothing. The bytes stay where they are and the packet says where that is.

**It is Zarr v2, which only an external resource may be** (R21 §3.2). A packet-owned array
must be v3. The version rides on `physical_profile`, not a new field, because a resource that
already says which profile it is should not say it twice.

**Its timestamps are unusable and unnecessary.** Every series stores 7,983,750 float64
timestamps -- 767 MB across twelve -- on a regenerated nominal grid, with the sign of `t0`
flipped so the array reads as 268 days before the spikes. None of it is needed: LFP sample 0
lands on AP tick -6.0 to -6.2 on every probe measured, so each series begins at its own
probe's sample 0 and advances exactly 24 AP ticks a sample. R20's regular-tick axis states
that in three integers, on the clock the spikes are already on, and both defects disappear
rather than being carried forward.

**The channel axis is a labelled one.** LFP keeps every fourth contact -- 96 of 384 -- so the
axis cannot be described by a range. `core.array_channels` names the electrode behind each
position and R20 §2's labelled form points the axis at it.

**`inter_sample_shift` is the per-channel quantity R19 was for.** It takes eight distinct
values within a series, because a Neuropixels ADC samples its channels in turn rather than at
once. `conversion` is *not*: it is one value per series here, so it stays on
`core.array_assets` rather than being repeated down 96 rows, which R3 §3.0 forbids.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .nwb import SourceDefect
from .zarr_compat import read_array

#: Where an NWB keeps its LFP series.
GROUP = "processing/ecephys/LFP"

#: The array within a series that holds the samples. R21 §3.2's URI names the array, not the
#: group around it, because a dense array asset is one array.
DATA = "data"


class LFPSource:
    """An NWB's LFP series, as external array assets plus the tables describing their axes.

    Parameters
    ----------
    root : str or Path
        The `.nwb` directory.
    session_id : str
        The session these series belong to.
    clocks : sequence of str, optional
        Clock IDs the packet declares. A series is placed on the one whose ID ends in
        `.<probe>.samples`, which is the probe's own sample clock.
    electrodes : Mapping, optional
        Global electrode row index to `electrode_id`, so a channel can name a real electrode.
    uri_base : str, optional
        Absolute base the referenced arrays live under, without a trailing slash, to which the
        series path is appended. Absent, the local path is used as a `file://` URI, which makes
        a packet that resolves only on this machine.
    verify : str, default "size"
        What to establish about the referenced bytes: `size` lists the store, `sha256` also
        digests it, `none` records no claim. A remote base needs `nwb-lake-reader[remote]` and
        a backend for its scheme; unreachable leaves the claim unmade rather than guessed.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        clocks: Any = (),
        electrodes: Any = None,
        uri_base: str | None = None,
        verify: str = "size",
    ) -> None:
        self.root = Path(root)
        self.session_id = session_id
        self.clocks = list(clocks)
        self.electrodes = dict(electrodes or {})
        self.uri_base = uri_base.rstrip("/") if uri_base else None
        if verify not in {"none", "size", "sha256"}:
            raise ValueError(f"verify must be none, size or sha256, not {verify!r}")
        self.verify = verify
        self.notes: list[str] = []
        self._rates: dict[str, float] = {}
        self._series = (
            sorted(p for p in (self.root / GROUP).iterdir() if p.is_dir()) if (self.root / GROUP).is_dir() else []
        )
        if not self._series:
            self.notes.append(f"{GROUP}: no series found, so no LFP is referenced")

    # -- identity ---------------------------------------------------------------------

    @staticmethod
    def probe_of(series: Path) -> str:
        """Return the probe a series belongs to, from the name NWB gives it."""
        return series.name.removeprefix("ElectricalSeries").removesuffix("-LFP")

    def array_asset_id(self, series: Path) -> str:
        """Return the asset ID for a series, which is its probe plus what it holds."""
        return f"{self.probe_of(series)}.lfp"

    def resource_id(self, series: Path) -> str:
        """Return the manifest resource ID for a series."""
        return f"core.{self.array_asset_id(series)}"

    def _clock(self, series: Path) -> str:
        """Return the probe's own sample clock, which is what the axis advances on."""
        probe = self.probe_of(series)
        matches = [c for c in self.clocks if c.endswith(f".{probe}.samples")]
        if len(matches) != 1:
            raise SourceDefect(
                f"{series.name}: {len(matches)} clocks end in '.{probe}.samples', so the time axis has no clock"
            )
        return str(matches[0])

    def _uri(self, series: Path) -> str:
        if self.uri_base:
            return f"{self.uri_base}/{GROUP}/{series.name}/{DATA}"
        return (series / DATA).resolve().as_uri()

    # -- what the store declares --------------------------------------------------------

    def _zarray(self, path: Path) -> dict[str, Any]:
        meta = path / ".zarray"
        if not meta.is_file():
            raise SourceDefect(f"{path}: no .zarray, so it is not a Zarr v2 array")
        parsed: dict[str, Any] = json.loads(meta.read_text())
        return parsed

    def _zattrs(self, path: Path) -> dict[str, Any]:
        meta = path / ".zattrs"
        parsed: dict[str, Any] = json.loads(meta.read_text()) if meta.is_file() else {}
        return parsed

    @staticmethod
    def _codecs(meta: dict[str, Any]) -> tuple[str, ...]:
        """Name the codecs an array uses, as R15 §2 requires the manifest to declare them."""
        names = [str(f["id"]) for f in meta.get("filters") or []]
        if compressor := meta.get("compressor"):
            names.append(str(compressor["id"]))
        return tuple(names)

    def _decimation(self, series: Path, clock_rate: float) -> int:
        """How many probe ticks one LFP sample advances.

        Taken from the interval between the first two timestamps rather than from their values.
        The interval survives the sign fault that ruins the values, and the ratio it gives is a
        small integer or this is not a decimation of the probe's stream at all.
        """
        stamps = read_array(series / "timestamps")[:2]
        if stamps.size < 2 or not np.isfinite(stamps).all() or stamps[1] == stamps[0]:
            raise SourceDefect(f"{series.name}: timestamps give no interval, so the axis step is unknown")
        exact = clock_rate * float(stamps[1] - stamps[0])
        step = round(exact)
        if step < 1 or abs(exact - step) > 1e-3:
            raise SourceDefect(
                f"{series.name}: {exact:.6f} probe ticks a sample is not an integer, so this is not a decimation"
            )
        return int(step)

    # -- records ------------------------------------------------------------------------

    def external_arrays(self) -> dict[str, Any]:
        """Return the `ExternalArray` to reference per series, keyed by resource ID."""
        from ..writer import ExternalArray

        out = {}
        for series in self._series:
            meta = self._zarray(series / DATA)
            if meta.get("zarr_format") != 2:
                raise SourceDefect(f"{series.name}: zarr_format {meta.get('zarr_format')}, expected 2")
            array = ExternalArray(
                array_asset_id=self.array_asset_id(series),
                uri=self._uri(series),
                physical_profile="zarr_v2",
                codecs=self._codecs(meta),
            )
            out[self.resource_id(series)] = self._verified(array)
        return out

    def _verified(self, array: Any) -> Any:
        """Record what looking at the referenced bytes established, or nothing (R14 §2.3.1).

        Resolves the URI the manifest will carry, not the local copy beside it: bytes next to
        the writer are not the bytes the URI names, however likely they are to be identical.
        A store it cannot reach leaves the claim unmade, which is a packet saying less rather
        than saying something untrue (R36 §2.4).

        `size_bytes` is the whole prefix, metadata documents included, because a dense array
        asset is a prefix of many objects and its `.zarray` is part of what it is (R36 §2.1).
        """
        from nwb_lake_reader.stores import StoreUnreachable, digest, listing

        from ..writer import ExternalArray

        if self.verify == "none":
            return array
        try:
            found = listing(array.uri)
            # A prefix has no natural digest, so R36 §2.2 defines one. It reads every byte --
            # 3.9 s an array here -- which is why it is asked for separately.
            checksum = digest(array.uri) if self.verify == "sha256" else None
        except StoreUnreachable as exc:
            self.notes.append(f"{array.array_asset_id}: nothing verified, {exc}")
            return array
        return ExternalArray(
            array_asset_id=array.array_asset_id,
            uri=array.uri,
            physical_profile=array.physical_profile,
            codecs=array.codecs,
            sha256=checksum,
            size_bytes=found.size_bytes,
            verified_at=datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        )

    def array_assets(self) -> list[dict[str, Any]]:
        """`core.array_assets`, one row per series."""
        rows = []
        for series in self._series:
            attrs = self._zattrs(series / DATA)
            rows.append(
                {
                    "array_asset_id": self.array_asset_id(series),
                    "session_id": self.session_id,
                    "semantic_type": "ElectricalSeries",
                    "name": series.name,
                    "kind": "lfp",
                    "uri": self._uri(series),
                    "format": "zarr_v2",
                    "clock_id": self._clock(series),
                    # No sample_rate_hz: core.array_dimensions declares the step in ticks on a
                    # clock whose rate is declared, so a rate here would be a second, rounded
                    # statement of the same fact (R3 §3.0) -- and the rounded one is the one
                    # this file gets wrong.
                    "unit": attrs.get("unit"),
                    "conversion": attrs.get("conversion"),
                    "offset": attrs.get("offset"),
                }
            )
        return rows

    def array_dimensions(self) -> list[dict[str, Any]]:
        """`core.array_dimensions`: a regular tick axis, then a labelled channel axis (R20 §2)."""
        rows = []
        for series in self._series:
            clock_id = self._clock(series)
            meta = self._zarray(series / DATA)
            step = self._decimation(series, self._clock_rate(clock_id))
            rows.append(
                {
                    "array_asset_id": self.array_asset_id(series),
                    "axis_index": 0,
                    "dimension_name": "time",
                    "clock_id": clock_id,
                    # Measured across four probes: LFP sample 0 lands within 0.2 ms of the
                    # probe's own sample 0, while the series' stored t0 values differ by
                    # 0.130 s -- that spread is the probes starting at different moments, not
                    # the LFP starting late on any of them.
                    "origin_tick": 0,
                    "step_ticks": step,
                    "step_tick_den": 1,
                }
            )
            rows.append(
                {
                    "array_asset_id": self.array_asset_id(series),
                    "axis_index": 1,
                    "dimension_name": "channel",
                    "coordinate_resource": "core.array_channels",
                    "coordinate_position_column": "channel_index",
                }
            )
            if len(meta["shape"]) != 2:
                raise SourceDefect(f"{series.name}: rank {len(meta['shape'])}, expected (time, channel)")
        return rows

    def _clock_rate(self, clock_id: str) -> float:
        """Return the declared tick rate of a clock, from whatever the recipe supplied."""
        rate = self._rates.get(clock_id)
        if rate is None:
            raise SourceDefect(f"{clock_id}: no declared tick rate, so an axis step in ticks cannot be derived")
        return float(rate)

    def array_channels(self) -> list[dict[str, Any]]:
        """`core.array_channels`, one row per channel of every series (R19 §2)."""
        table = self.root / "general/extracellular_ephys/electrodes"
        channel = read_array(table / "channel_name") if (table / "channel_name").is_dir() else None
        shift = read_array(table / "inter_sample_shift") if (table / "inter_sample_shift").is_dir() else None
        if shift is None:
            self.notes.append("electrodes/inter_sample_shift: absent, so array channels carry no acquisition offset")
        rows = []
        for series in self._series:
            region = read_array(series / "electrodes")
            for index, source_row in enumerate(int(r) for r in region):
                rows.append(
                    {
                        "array_asset_id": self.array_asset_id(series),
                        "axis_index": 1,
                        "channel_index": index,
                        "electrode_id": self.electrodes.get(source_row),
                        "channel_label": str(channel[source_row]) if channel is not None else None,
                        "inter_sample_shift": float(shift[source_row]) if shift is not None else None,
                    }
                )
            if not self.electrodes:
                self.notes.append("no electrode map given, so array channels name no electrode")
        return rows

    def records(self, *, rates: Any = None) -> dict[str, list[dict[str, Any]]]:
        """Return every table this source supplies.

        Parameters
        ----------
        rates : Mapping, optional
            Clock ID to declared tick rate, which the axis step in ticks is derived against.
        """
        self._rates = dict(rates or {})
        return {
            "core.array_assets": self.array_assets(),
            "core.array_dimensions": self.array_dimensions(),
            "core.array_channels": self.array_channels(),
        }

    def offers(self) -> dict[str, int]:
        """`05` Stage 1: how many rows of each resource this source can supply."""
        return {"core.array_assets": len(self._series), "core.array_dimensions": 2 * len(self._series)}


__all__ = ["GROUP", "LFPSource"]
