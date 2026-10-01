"""Reference an NWB's LFP series as external array assets, and describe their axes (Part 04 §5.1).

- :class:`LFPSource` -- the series as `ExternalArray` references, and the tables for their axes.
- :data:`GROUP` -- where an NWB keeps its LFP series.

The adapter does not read a series' stored timestamps as its axis. It declares the axis regular on
the probe's own sample clock, and records that choice as the `lfp.timestamps_distrusted`
compensation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import numpy as np

from .compensations import Compensates
from .defect import SourceDefect
from .nwb import contact_columns, contact_ids, ucum_code
from .store import SourceStore, source_root

#: Where an NWB keeps its LFP series.
GROUP = "processing/ecephys/LFP"

#: The array within a series that holds the samples. The asset's URI names the array, not the
#: group around it, because a dense array asset is one array.
DATA = "data"


class LFPSource(Compensates):
    """An NWB's LFP series, as external array assets plus the tables describing their axes.

    Parameters
    ----------
    root : str or Path
        The `.nwb` directory.
    session_id : str
        The session these series belong to.
    clocks : sequence of Mapping, optional
        The `core.clocks` row of every clock declared before this source runs. A series is
        placed on the one whose ID ends in `.<probe>.samples`, which is the probe's own sample
        clock, and that row is what states the rate an axis step in ticks is derived against.
    uri_base : str, optional
        Absolute base the referenced arrays live under, without a trailing slash, to which the
        series path is appended. Absent, the local path is used as a `file://` URI, which makes
        a packet that resolves only on this machine.
    prefix : str
        Prepended to the contact names this adapter composes. It MUST match what the adapter
        owning `core.electrodes` uses, since a name is what the writer numbers.
    source_cache : str, optional
        The build's source-cache location, which a store root is read through (Part 12 §10).
    verify : str, default "size"
        What to establish about the referenced bytes, each level including the one before it:

        - `none` records no claim.
        - `size` lists the store and records the total.
        - `members` also records Part 04 §5.4's per-member listing, carrying the entity tag the
          store handed over with it. Same request, so it costs what `size` costs; what it buys is
          a per-member check where the total hides two members changing in opposite directions,
          and `validate --store-digests` to see whether anything changed in place.
        - `sha256` also digests every byte, recording the prefix's SHA-256 `digest` and each
          member's own beside it (Part 04 §4.3).

        A remote base needs `escapewheel-validator[remote]` and a backend for its scheme;
        unreachable leaves the claim unmade rather than guessed.

        The default is `size` on cost and on manifest size. A listing is a request per prefix
        where a digest reads every referenced byte, so a digest is a publication-time cost that
        a build should not pay by default. `members` costs no further requests but a manifest
        entry per member, which is why it is not the default either. A packet recording neither
        is not silently treated as verified: `validate --checksums` and `--store-digests` each
        report what they had nothing to compare against.
    """

    #: Part 05 §3.4: what this adapter can supply, whatever a given root happens to hold.
    #: Static, so a recipe check reads it with nothing open -- `offers` counts rows and
    #: therefore needs the data.
    PRODUCES = frozenset(
        {
            "core.array_assets",
            "core.array_channels",
            "core.array_dimensions",
            "core.array_labels",
        }
    )

    #: Part 05 §3.4: what of `PRODUCES` this adapter supplies only part of, which a source entry
    #: without `owns` contributes rather than owns.
    CONTRIBUTES = frozenset(
        {
            "core.array_assets",
            "core.array_dimensions",
            "core.array_labels",
        }
    )

    #: Part 05 §3.4: recipe fields this adapter states, to the attribute holding each. Declared
    #: empty rather than omitted, because a build refuses a source it cannot ask.
    STATES: ClassVar[dict[str, str]] = {}

    #: Part 05 §3.4: what a build must supply, resolved against Part 12 §4's terms first and the
    #: recipe's options second. A name resolving to neither is refused before any source is opened.
    #:
    #: An option the adapter can run without is left out: a declared name a recipe does not set
    #: resolves to nothing, so declaring one makes it mandatory.
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id", "clocks")

    #: Part 05 §3.4: options this adapter reads and can run without, which a recipe may leave
    #: unset (Part 12 §4). `store` is absent because it is a handle, which a recipe cannot
    #: carry and a declaration may not name.
    ACCEPTS: ClassVar[tuple[str, ...]] = ("uri_base", "prefix", "verify", "source_cache")

    #: Part 05 §3.4: the kinds whose output this adapter reads, which is what orders a build.
    CONSUMES: ClassVar[tuple[str, ...]] = ("sorter",)

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        clocks: Any = (),
        uri_base: str | None = None,
        prefix: str = "",
        verify: str = "size",
        store: Any = None,
        source_cache: str | None = None,
    ) -> None:
        self.root = source_root(root, cache=source_cache)
        self.store = store if store is not None else SourceStore(self.root)
        self.session_id = session_id
        self.clocks = [dict(row) for row in clocks]
        self.prefix = prefix
        self.uri_base = uri_base.rstrip("/") if uri_base else None
        if verify not in {"none", "size", "members", "sha256"}:
            raise ValueError(f"verify must be none, size, members or sha256, not {verify!r}")
        self.verify = verify
        Compensates.__init__(self)
        self.notes: list[str] = []
        # Part 02 §12.4 makes the two rate forms exclusive, so a clock states one or the other
        # and this reads whichever it states. The rational is the common case; the float is what
        # a source that measured its rate rather than declaring it records.
        self._rates: dict[str, float] = {
            row["clock_id"]: (
                float(row["tick_rate_hz"])
                if row.get("tick_rate_hz") is not None
                else row["tick_rate_num"] / row["tick_rate_den"]
            )
            for row in self.clocks
        }
        self._probe: dict[str, str] = {}
        self._series = (
            sorted(p for p in (self.root / GROUP).iterdir() if p.is_dir()) if (self.root / GROUP).is_dir() else []
        )
        if not self._series:
            self.notes.append(f"{GROUP}: no series found, so no LFP is referenced")

    # -- identity ---------------------------------------------------------------------

    def probe_of(self, series: Path) -> str:
        """Return the probe a series records, from the contacts its own electrode region names.

        Derived rather than parsed out of the series name, which NWB does not constrain at all: an
        `ElectricalSeries` declares an electrode region, and the contacts in one belong to a single
        `ElectrodeGroup`.
        """
        if series.name not in self._probe:
            columns = contact_columns(self.store, self.root / "general/extracellular_ephys/electrodes")
            if "group_name" not in columns:
                raise SourceDefect("electrodes/group_name: absent, so no series can name its probe")
            group = columns["group_name"]
            found = {str(group[int(row)]) for row in self.store.array(series / "electrodes")}
            if len(found) != 1:
                raise SourceDefect(
                    f"{series.name}: its contacts span {len(found)} electrode groups, so it records no one probe"
                )
            self._probe[series.name] = found.pop()
        return self._probe[series.name]

    def array_asset_id(self, series: Path) -> str:
        """Return the asset ID for a series, which is its probe plus what it holds."""
        return f"{self.probe_of(series)}.lfp"

    def resource_id(self, series: Path) -> str:
        """Return the manifest resource ID for a series."""
        return f"core.{self.array_asset_id(series)}"

    def _clock(self, series: Path) -> str:
        """Return the probe's own sample clock, which is what the axis advances on."""
        probe = self.probe_of(series)
        matches = [row["clock_id"] for row in self.clocks if str(row["clock_id"]).endswith(f".{probe}.samples")]
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
        meta = self.store.zarray(path)
        if meta is None:
            raise SourceDefect(f"{path}: no .zarray, so it is not a Zarr v2 array")
        return meta

    def _zattrs(self, path: Path) -> dict[str, Any]:
        return self.store.attrs(path)

    @staticmethod
    def _codecs(meta: dict[str, Any]) -> tuple[str, ...]:
        """Name the codecs a v2 array's own metadata uses, its filters first (Part 03 §6.4)."""
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
        stamps = self.store.head(series / "timestamps", 2)
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
                declaration_id="core.array_asset_instances",
                uri=self._uri(series),
                physical_profile="zarr_v2",
                codecs=self._codecs(meta),
            )
            out[self.resource_id(series)] = self._verified(array)
        return out

    def _verified(self, array: Any) -> Any:
        """Record what looking at the referenced bytes established, or nothing (Part 03 §8).

        Resolves the URI the manifest will carry, not the local copy beside it: bytes next to
        the writer are not the bytes the URI names, however likely they are to be identical.
        A store it cannot reach leaves the claim unmade, which is a packet saying less rather
        than saying something untrue (Part 04 §5.2).

        `size_bytes` is the whole prefix, metadata documents included, because a dense array
        asset is a prefix of many objects and its `.zarray` is part of what it is (Part 04 §5.4).
        """
        from escapewheel_validator.stores import StoreUnreachable, digest_resource, listing

        from ..writer import ExternalArray

        if self.verify == "none":
            return array
        try:
            # A prefix's digest reads every byte, which is why it is asked for separately. Its
            # members' values are kept, so a consumer can check one chunk.
            digested = digest_resource(array.uri) if self.verify == "sha256" else None
            found = listing(array.uri) if digested is None else digested.found
        except StoreUnreachable as exc:
            self.notes.append(f"{array.array_asset_id}: nothing verified, {exc}")
            return array
        members = None
        if self.verify in {"members", "sha256"}:
            values = digested.members if digested is not None else (None,) * len(found.members)
            members = tuple(_member_entry(member, value) for member, value in zip(found.members, values, strict=True))
            if not found.digested_by_store:
                self.notes.append(
                    f"{array.array_asset_id}: the store offered no entity tag for any of its "
                    f"{len(found.members)} members, so none records a store digest"
                )
        return ExternalArray(
            array_asset_id=array.array_asset_id,
            declaration_id=array.declaration_id,
            uri=array.uri,
            physical_profile=array.physical_profile,
            codecs=array.codecs,
            digest=None if digested is None else {"algorithm": digested.algorithm, "value": digested.value},
            size_bytes=found.size_bytes,
            verified_at=datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            members=members,
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
                    # No `array_asset_name`: Part 02 §8.2's rule for a clock holds for an asset
                    # too -- the name is what the identifier stands for, and the numbering fills
                    # it from exactly that where a row leaves it unset (R53 §2.5). A source's own
                    # label here would leave the packet with no record of what the identifier
                    # was minted from, and nothing to join a row to its manifest entry by.
                    # The series name reaches the manifest entry's `uri` through `external_arrays`.
                    "band": "lfp",
                    "clock_id": self._clock(series),
                    # No sample_rate_hz: core.array_dimensions declares the step in ticks on a
                    # clock whose rate is declared, so a rate here would be a second, rounded
                    # statement of the same fact (Part 02 §6) -- and the rounded one is the one
                    # a source gets wrong.
                    "unit": ucum_code(attrs.get("unit")),
                    "conversion": attrs.get("conversion"),
                    "offset": attrs.get("offset"),
                }
            )
        return rows

    def array_dimensions(self) -> list[dict[str, Any]]:
        """`core.array_dimensions`: a regular tick axis, then a labelled channel axis (Part 03 §6.3)."""
        rows = []
        for series in self._series:
            clock_id = self._clock(series)
            meta = self._zarray(series / DATA)
            step = self._decimation(series, self._clock_rate(clock_id))
            self.compensate("lfp.timestamps_distrusted")
            rows.append(
                {
                    "array_asset_id": self.array_asset_id(series),
                    "axis_index": 0,
                    "dimension_name": "time",
                    "clock_id": clock_id,
                    # LFP sample 0 is taken as the probe's own sample 0. Stored t0 values that
                    # differ between series are the probes starting at different moments, not
                    # the LFP starting late on any of them.
                    "origin_tick": 0,
                    "step_tick_num": step,
                    "step_tick_den": 1,
                }
            )
            rows.append(
                {
                    "array_asset_id": self.array_asset_id(series),
                    "axis_index": 1,
                    "dimension_name": "channel",
                    "coordinate_resource": "core.electrodes",
                }
            )
            if len(meta["shape"]) != 2:
                raise SourceDefect(f"{series.name}: rank {len(meta['shape'])}, expected (time, channel)")
        return rows

    def _clock_rate(self, clock_id: str) -> float:
        """Return the declared tick rate of a clock, from the row the build supplied for it."""
        rate = self._rates.get(clock_id)
        if rate is None:
            raise SourceDefect(f"{clock_id}: no declared tick rate, so an axis step in ticks cannot be derived")
        return float(rate)

    def _electrodes(self) -> tuple[Path, dict[str, Any], list[str]]:
        """Return the electrode table, its columns and each source row's contact name."""
        table = self.root / "general/extracellular_ephys/electrodes"
        # One rule for naming a contact, shared with the adapter owning `core.electrodes`: a second
        # spelling here would mint a second electrode and leave this axis pointing at neither.
        columns = contact_columns(self.store, table)
        names, note = contact_ids(columns, self.prefix)
        if note is not None and note not in self.notes:
            self.notes.append(note)
        return table, columns, names

    def array_labels(self) -> list[dict[str, Any]]:
        """`core.array_labels`, the electrode at each channel position of every series (Part 03 §6.3).

        A label is the contact's name, which the writer numbers in `core.electrodes`' numbering.
        """
        if not self._series:
            return []
        _, _, names = self._electrodes()
        return [
            {
                "array_asset_id": self.array_asset_id(series),
                "axis_index": 1,
                "depends_on_position_index": 0,
                "position_index": index,
                "label_id": names[source_row],
            }
            for series in self._series
            for index, source_row in enumerate(int(r) for r in self.store.array(series / "electrodes"))
        ]

    def array_channels(self) -> list[dict[str, Any]]:
        """`core.array_channels`, one row per channel of every series (R19 §2)."""
        if not self._series:
            return []
        table, columns, _ = self._electrodes()
        channel = columns.get("channel_name")
        shift = self.store.array(table / "inter_sample_shift") if (table / "inter_sample_shift").is_dir() else None
        if shift is None:
            self.notes.append("electrodes/inter_sample_shift: absent, so array channels carry no acquisition offset")
        rows = []
        for series in self._series:
            region = self.store.array(series / "electrodes")
            for index, source_row in enumerate(int(r) for r in region):
                rows.append(
                    {
                        "array_asset_id": self.array_asset_id(series),
                        "axis_index": 1,
                        "channel_index": index,
                        "channel_label": str(channel[source_row]) if channel is not None else None,
                        "inter_sample_shift": float(shift[source_row]) if shift is not None else None,
                    }
                )
        return rows

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Return every table this source supplies."""
        return {
            "core.array_assets": self.array_assets(),
            "core.array_dimensions": self.array_dimensions(),
            "core.array_labels": self.array_labels(),
            "core.array_channels": self.array_channels(),
        }

    def offers(self) -> dict[str, int]:
        """Part 05 §4.1: how many rows of each resource this source can supply.

        `core.array_channels` and `core.array_labels` are counted from each series' electrode
        region, which is what both iterate.
        """
        channels = sum(len(self.store.array(series / "electrodes")) for series in self._series)
        return {
            "core.array_assets": len(self._series),
            "core.array_dimensions": 2 * len(self._series),
            "core.array_labels": channels,
            "core.array_channels": channels,
        }


def _member_entry(member: Any, digest: str | None = None) -> dict[str, Any]:
    """One Part 04 §5.4 member entry, omitting what was not established."""
    entry: dict[str, Any] = {"key": member.key, "size_bytes": member.size_bytes}
    if digest is not None:
        entry["digest"] = digest
    if member.store_digest is not None:
        entry["store_digest"] = {
            "algorithm": member.store_digest.algorithm,
            "value": member.store_digest.value,
        }
    return entry


__all__ = ["GROUP", "LFPSource"]
