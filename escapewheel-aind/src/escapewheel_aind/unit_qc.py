"""The quality pipeline's per-unit metrics, read from the analyzer that computed them.

`aind_unit_qc` holds the SpikeInterface metrics an AIND pipeline computes for every unit. They are
read from the `SortingAnalyzer` beside the curated sorting, as `waveforms` reads its templates, and
not from the NWB exported afterwards: the analyzer names each row by the sorter's own unit label, so
a unit is resolved through the build's `units` term by `(device_name, local_unit_label)` and
carried as the name the sorter minted. The packet numbers it, so this adapter never needs a
committed packet to learn an integer.

Each metric keeps the name the pipeline gives it, which is the vocabulary people search by. The
one rename is `num_spikes`, which becomes `num_spikes_used` so it cannot be read as core's
`n_spikes`. The synchrony metric arrives as one column per size, `sync_spike_<size>`, and becomes
one row per size, so a fourth size is a row rather than a schema change.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from escapewheel_writer.declaration import FILES, FLIGHT, STREAM
from escapewheel_writer.sources.defect import SourceDefect
from escapewheel_writer.sources.sorter import STREAM as STREAM_NAME
from escapewheel_writer.sources.sorter import SortedStream
from escapewheel_writer.sources.store import SourceStore, source_root
from escapewheel_writer.sources.waveforms import ANALYZERS
from escapewheel_writer.sources.zarr_compat import UnsupportedEncoding
from numpy.typing import NDArray

#: The analyzer extensions holding each table's metrics, as a data frame of one array per column.
QUALITY = "extensions/quality_metrics/metrics"
TEMPLATE = "extensions/template_metrics/metrics"

#: `aind_unit_qc.metrics` column to the analyzer's `quality_metrics` column it is read from.
METRICS = {
    "num_spikes_used": "num_spikes",
    "presence_ratio": "presence_ratio",
    "firing_range": "firing_range",
    "snr": "snr",
    "isi_violations_ratio": "isi_violations_ratio",
    "isi_violations_count": "isi_violations_count",
    "rp_contamination": "rp_contamination",
    "rp_violations": "rp_violations",
    "sliding_rp_violation": "sliding_rp_violation",
    "amplitude_cutoff": "amplitude_cutoff",
    "amplitude_median": "amplitude_median",
    "amplitude_cv_median": "amplitude_cv_median",
    "amplitude_cv_range": "amplitude_cv_range",
    "isolation_distance": "isolation_distance",
    "l_ratio": "l_ratio",
    "d_prime": "d_prime",
    "silhouette": "silhouette",
    "nn_hit_rate": "nn_hit_rate",
    "nn_miss_rate": "nn_miss_rate",
    "drift_ptp": "drift_ptp",
    "drift_std": "drift_std",
    "drift_mad": "drift_mad",
}

#: `aind_unit_qc.waveform_metrics` column to the analyzer's `template_metrics` column. A column the
#: analyzer does not carry is left absent, which says the source stated no value for it.
WAVEFORM_METRICS = {
    name: name
    for name in (
        "peak_to_valley",
        "peak_trough_ratio",
        "half_width",
        "repolarization_slope",
        "recovery_slope",
        "num_positive_peaks",
        "num_negative_peaks",
        "exp_decay",
        "spread",
        "velocity_above",
        "velocity_below",
    )
}

#: A synchrony column, and the size it counts.
SYNCHRONY = re.compile(r"^sync_spike_(?P<size>\d+)$")


class UnitQCSource:
    """`aind_unit_qc.metrics`, `waveform_metrics` and `synchrony`, from a SpikeInterface analyzer.

    Parameters
    ----------
    root : str or Path
        The `postprocessed` directory, or an asset directory containing one.
    session_id : str
        The session these units belong to.
    units : sequence of Mapping
        One record per unit, as the build supplies it: `device_name` and `local_unit_label`, the
        stream's probe and the sorter's own label, and the `unit_id` assigned. An analyzer unit
        matching none is skipped, since the packet's sorting does not hold it.
    experiment : str, optional
        Restrict to one experiment, as the sorter is. Streams of two experiments share their probe
        names, so without it a unit of one would match a unit of the other.
    """

    #: Part 03 §11.1: released apart from the writer, so it declares its protocols.
    PROTOCOLS: ClassVar[tuple[str, ...]] = (STREAM, FILES, FLIGHT)

    #: Part 05 §3.4: what this adapter can supply, whatever a given root happens to hold.
    PRODUCES = frozenset({"aind_unit_qc.metrics", "aind_unit_qc.waveform_metrics", "aind_unit_qc.synchrony"})

    #: Part 05 §3.4: recipe fields this adapter states. Declared empty rather than omitted, because a
    #: build refuses a source it cannot ask.
    STATES: ClassVar[dict[str, str]] = {}

    #: Part 05 §3.4: what a build must supply (Part 03 §11.2).
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id", "units")

    #: Part 05 §3.4: options this adapter reads and can run without. `store` is absent because it
    #: is a handle, which a recipe cannot carry and a declaration may not name.
    ACCEPTS: ClassVar[tuple[str, ...]] = ("experiment",)

    #: Part 05 §3.4: the kinds whose output this adapter reads. `units` is the sorter's.
    CONSUMES: ClassVar[tuple[str, ...]] = ("sorter",)

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        units: Sequence[Mapping[str, Any]],
        experiment: str | None = None,
        store: Any = None,
    ) -> None:
        path = source_root(root)
        self.root = path if path.name == ANALYZERS else path / ANALYZERS
        if not self.root.is_dir():
            raise SourceDefect(f"{path} holds no {ANALYZERS}/ directory")
        self.store = store if store is not None else SourceStore(self.root)
        self.session_id = session_id
        self.experiment = experiment
        # A mapping keyed by a pair does not cross a boundary (Part 03 §11.2), so the build hands
        # over rows and this keys them.
        self.units = {(str(row["device_name"]), str(row["local_unit_label"])): row["unit_id"] for row in units}
        self.notes: list[str] = []
        self._built: dict[str, list[dict[str, Any]]] | None = None

    def streams(self) -> list[SortedStream]:
        """Every analyzer in the tree, named as the curated sorting names its streams."""
        found = []
        for child in sorted(self.root.iterdir()):
            if not child.is_dir() or child.suffix != ".zarr":
                continue
            if matched := STREAM_NAME.match(child.stem):
                found.append(SortedStream(path=child, **matched.groupdict()))
        if self.experiment is not None:
            found = [s for s in found if s.experiment == self.experiment]
        if not found:
            raise SourceDefect(f"{self.root} holds no analyzer for experiment {self.experiment!r}")
        return found

    def _frame(self, stream: SortedStream, group: str) -> dict[str, NDArray[Any]] | None:
        """Read one extension's data frame as columns, keyed by name, or None where it is absent.

        `index` is the unit labels; every other column is read only where it is numeric, since a
        metric is a number and a column of another encoding is not one of them.
        """
        where = stream.path / group
        if not where.is_dir():
            self.notes.append(f"{stream.key}: the analyzer holds no {group}; its units contribute no rows to it")
            return None
        columns: dict[str, NDArray[Any]] = {}
        for name in self.store.members(where):
            try:
                values = self.store.array(where / name)
            except UnsupportedEncoding:
                continue
            if name == "index" or values.dtype.kind in "iufb":
                columns[name] = values
        if "index" not in columns:
            raise SourceDefect(f"{stream.key}: {group} names no unit for its rows")
        return columns

    def _rows(self, stream: SortedStream, frame: Mapping[str, NDArray[Any]]) -> tuple[list[int], list[Any]]:
        """Return the frame's row offsets whose unit the packet holds, and each one's `unit_id`."""
        kept, identity = [], []
        for offset, label in enumerate(frame["index"]):
            found = self.units.get((stream.device, _label(label)))
            if found is not None:
                kept.append(offset)
                identity.append(found)
        return kept, identity

    def _read(self) -> dict[str, list[dict[str, Any]]]:
        """Build all three tables in one pass over the streams."""
        if self._built is not None:
            return self._built
        built: dict[str, list[dict[str, Any]]] = {resource: [] for resource in sorted(self.PRODUCES)}
        seen: dict[Any, str] = {}
        missed = 0
        for stream in self.streams():
            quality = self._frame(stream, QUALITY)
            if quality is not None:
                kept, identity = self._rows(stream, quality)
                missed += len(quality["index"]) - len(kept)
                for unit in identity:
                    if unit in seen:
                        raise SourceDefect(
                            f"unit {unit} matches rows of both {seen[unit]} and {stream.key}; "
                            "set `experiment` to the one the sorter reads"
                        )
                    seen[unit] = stream.key
                built["aind_unit_qc.metrics"] += self._table(quality, METRICS, kept, identity)
                built["aind_unit_qc.synchrony"] += self._synchrony(quality, kept, identity)
            template = self._frame(stream, TEMPLATE)
            if template is not None:
                kept, identity = self._rows(stream, template)
                built["aind_unit_qc.waveform_metrics"] += self._table(template, WAVEFORM_METRICS, kept, identity)
        if not seen:
            raise SourceDefect("no unit in the analyzer's quality metrics matches the packet's sorting")
        if missed:
            self.notes.append(f"units: {missed} analyzer unit(s) match no unit in the packet's sorting; skipped")
        self._built = built
        return built

    def _table(
        self,
        frame: Mapping[str, NDArray[Any]],
        columns: Mapping[str, str],
        kept: Sequence[int],
        identity: Sequence[Any],
    ) -> list[dict[str, Any]]:
        """One row per kept unit, carrying every mapped column the frame holds."""
        held = {target: _values(frame[source][kept]) for target, source in columns.items() if source in frame}
        return [
            {"session_id": self.session_id, "unit_id": unit, **{name: values[i] for name, values in held.items()}}
            for i, unit in enumerate(identity)
        ]

    def _synchrony(
        self, frame: Mapping[str, NDArray[Any]], kept: Sequence[int], identity: Sequence[Any]
    ) -> list[dict[str, Any]]:
        """One row per kept unit per synchrony size the frame carries a column for."""
        sizes = sorted((int(m.group("size")), name) for name in frame if (m := SYNCHRONY.match(name)))
        rows = []
        for size, name in sizes:
            values = _values(frame[name][kept])
            rows += [
                {"session_id": self.session_id, "unit_id": unit, "synchrony_size": size, "sync_spike": values[i]}
                for i, unit in enumerate(identity)
            ]
        return rows

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds, keyed by resource ID, each present even where empty."""
        return dict(self._read())

    def offers(self) -> dict[str, int]:
        """Which resources this source supplies from its root, and how many rows (Part 05 §4.1)."""
        return {resource: len(rows) for resource, rows in self._read().items()}


def _label(value: Any) -> str:
    """Return a unit label as the sorter's `local_unit_label` spells it."""
    return str(int(value)) if isinstance(value, (int, np.integer)) else str(value)


def _values(column: NDArray[Any]) -> list[Any]:
    """Return a column as Python values, a non-finite float as None, since NaN is not a measurement."""
    if column.dtype.kind == "f":
        return [v if np.isfinite(v) else None for v in column.tolist()]
    return list(column.tolist())


__all__ = ["METRICS", "WAVEFORM_METRICS", "UnitQCSource"]
