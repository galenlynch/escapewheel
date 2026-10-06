"""A packet's dense arrays as xarray objects, each axis carrying its coordinates (Part 02 §12.11).

- :class:`EscapewheelBackend` -- the ``escapewheel`` engine of :func:`xarray.open_dataset` and
  :func:`xarray.open_datatree`.
- :class:`TickIndex` -- selects positions on a tick axis by tick, exactly.
- :class:`Ticks` -- the tick at each position of a tick axis, computed rather than stored.
- :class:`ReferenceIndex` -- selects them by reference tick or second, exactly.
- :class:`OnReference` -- each position's reference tick and second, computed through the anchors.
- :class:`Reference` -- how a tick axis's clock reaches the reference clock and the time origin.

Opening reads the packet's tables and no values; a selection reads only the chunks it touches.
Needs the ``xarray`` extra.
"""

from __future__ import annotations

import functools
import math
import os
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from fractions import Fraction
from numbers import Integral
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr
from numpy.typing import NDArray
from xarray.backends import BackendArray, BackendEntrypoint
from xarray.core import indexing
from xarray.core.indexing import IndexSelResult
from xarray.indexes import CoordinateTransform, CoordinateTransformIndex

from .axes import ArrayDescription, IrregularAxis, LabelledAxis, NumericAxis, TickAxis, describe
from .clocks import ClockGraph, clock_graph, declared_bound, origin, reference_clock, stored_intervals
from .errors import NotAligned, NoTimeOrigin
from .location import Location
from .manifest import MANIFEST_FILENAME
from .packet import Packet, open_packet
from .protocols import PacketLike
from .resources import ArrayResource

#: A tick, or a bound of a tick window; a float is taken at its exact binary value.
Tick = int | float | Fraction

#: Each axis tuple, and the mask over those axes marking positions that hold no value.
Padding = list[tuple[tuple[int, ...], NDArray[np.bool_]]]


class Ticks(CoordinateTransform):
    """Position *k* of `dim` is tick ``origin + k * step``: int64 where both are whole, float64 otherwise."""

    def __init__(self, name: str, dim: str, size: int, origin: Fraction, step: Fraction) -> None:
        """Map `size` positions of `dim` to the coordinate `name`."""
        whole = origin.denominator == 1 and step.denominator == 1
        super().__init__([name], {dim: size}, dtype=np.dtype(np.int64 if whole else np.float64))
        self.name, self.dim, self.size, self.origin, self.step = name, dim, size, origin, step

    def forward(self, dim_positions: dict[str, Any]) -> dict[Hashable, Any]:
        """Return the tick at each position."""
        positions = np.asarray(dim_positions[self.dim])
        if self.dtype == np.int64:
            return {self.name: int(self.origin) + positions.astype(np.int64) * int(self.step)}
        return {self.name: float(self.origin) + positions * float(self.step)}

    def reverse(self, coord_labels: dict[Hashable, Any]) -> dict[str, Any]:
        """Return the fractional position of each tick."""
        return {self.dim: (np.asarray(coord_labels[self.name]) - float(self.origin)) / float(self.step)}

    def equals(self, other: CoordinateTransform, **_: Any) -> bool:
        """Two tick axes are equal where every position has the same tick."""
        fields = ("name", "dim", "size", "origin", "step")
        return isinstance(other, Ticks) and all(getattr(self, f) == getattr(other, f) for f in fields)

    def window(self, start: Tick | None, stop: Tick | None) -> slice:
        """Return the positions whose tick lies in the closed window, in exact arithmetic."""
        lo = 0 if start is None else max(0, math.ceil((Fraction(start) - self.origin) / self.step))
        hi = self.size if stop is None else min(self.size, math.floor((Fraction(stop) - self.origin) / self.step) + 1)
        return slice(lo, max(lo, hi))

    def sliced(self, key: Any) -> Ticks | None:
        """Return the ticks a forward positional slice keeps, or None for any other selection."""
        if not isinstance(key, slice):
            return None
        start, stop, stride = key.indices(self.size)
        if stride < 1:
            return None
        size = len(range(start, stop, stride))
        return Ticks(self.name, self.dim, size, self.origin + start * self.step, self.step * stride)

    def nearest(self, tick: Tick, tolerance: Tick | None = None) -> int:
        """Return the position whose tick is nearest `tick`, within `tolerance` ticks where given."""
        offset = (Fraction(tick) - self.origin) / self.step
        found = min(max(round(offset), 0), self.size - 1)
        if self.size == 0 or (tolerance is not None and abs(found - offset) * self.step > Fraction(tolerance)):
            raise KeyError(f"no position of {self.dim!r} is within {tolerance} ticks of {tick}")
        return found


class TickIndex(CoordinateTransformIndex):
    """An index over a tick axis that selects by exact tick.

    A slice is a closed window of ticks, as a label slice is elsewhere in xarray, and a tick or an
    array of them must each land on a position; ``method="nearest"`` selects the nearest instead,
    and no other method applies. Whole ticks compare as integers; a fractional tick compares as its
    float64 coordinate shows it, so a value copied from the coordinate selects its position.
    """

    def __init__(self, transform: Ticks) -> None:
        """Index the tick axis `transform` computes."""
        super().__init__(transform)
        self.ticks = transform

    def sel(self, labels: dict[Any, Any], method: str | None = None, tolerance: Any = None) -> IndexSelResult:
        """Select positions by tick, or with ``method="nearest"`` by the nearest within `tolerance` ticks."""
        if method not in (None, "nearest"):
            raise ValueError(f"a tick axis selects exactly or by nearest, not by {method!r}")
        ((name, key),) = labels.items()
        ticks = self.ticks
        if method is not None and not isinstance(key, slice):
            nearest = functools.partial(ticks.nearest, tolerance=tolerance)
            found = np.vectorize(nearest, otypes=[np.int64])(np.asarray(getattr(key, "values", key), dtype=object))
            return IndexSelResult({ticks.dim: found if found.ndim else int(found)})

        def window(start: Tick | None, stop: Tick | None) -> slice | NDArray[np.int64]:
            if ticks.dtype == np.int64:
                return ticks.window(start, stop)
            widened = ticks.window(*_widened(start, stop, 1))
            return _shown(widened, lambda k: ticks.forward({ticks.dim: k})[ticks.name], start, stop)

        return _select(name, key, ticks.dim, window)

    def isel(self, indexers: Mapping[Any, Any]) -> TickIndex | None:
        """Keep the index through a forward positional slice; any other selection leaves the ticks unindexed."""
        sliced = self.ticks.sliced(indexers.get(self.ticks.dim))
        return None if sliced is None else TickIndex(sliced)


class Reference:
    """How a tick axis's clock reaches the session's reference clock, and where the session's seconds start.

    `origin` and `rate` are None where the packet declares no time origin, so there are no seconds.
    """

    def __init__(
        self,
        graph: ClockGraph,
        clock_id: int,
        reference_clock_id: int,
        bound: float,
        origin: int | None = None,
        rate: Fraction | None = None,
    ) -> None:
        """Map `clock_id`'s ticks up its parent chain to `reference_clock_id`, placing those within `bound`.

        `rate` is the reference clock's ticks per second.

        Raises
        ------
        NotAligned, Unanchored
            As :meth:`ClockGraph.path` does, where the clock does not reach the reference.
        """
        self.graph, self.clock_id, self.reference_clock_id, self.bound = graph, clock_id, reference_clock_id, bound
        self.origin, self.rate = origin, rate
        self.path = None if clock_id == reference_clock_id else graph.path(clock_id, reference_clock_id, bound)

    def __eq__(self, other: object) -> bool:
        """Two references are equal where they map one clock graph the same way."""
        fields = ("clock_id", "reference_clock_id", "bound", "origin", "rate")
        return (
            isinstance(other, Reference)
            and self.graph is other.graph
            and all(getattr(self, f) == getattr(other, f) for f in fields)
        )

    def __hash__(self) -> int:
        """Hash consistently with equality."""
        return hash((id(self.graph), self.clock_id, self.reference_clock_id, self.bound))

    def mapped(self, ticks: NDArray[Any]) -> NDArray[np.float64]:
        """Return each tick on the reference clock, NaN where the mapping does not place it.

        A tick between two of its clock's ticks maps by the same piecewise-linear rule as one on them.
        """
        if self.path is None:
            return np.asarray(ticks, dtype=np.float64)
        stored = np.asarray(ticks)
        stored = stored.astype(np.int64 if np.issubdtype(stored.dtype, np.integer) else np.float64)
        reference, placed = self.path(stored.ravel())
        return np.where(placed, reference, np.nan).reshape(stored.shape)

    def tick_window(self, seconds: tuple[Tick | None, Tick | None]) -> tuple[Fraction | None, Fraction | None]:
        """Return the closed window of reference ticks a closed window of seconds is."""
        if self.origin is None or self.rate is None:
            raise KeyError("the packet declares no time origin, so its axes have no seconds")
        return (
            None if seconds[0] is None else self.origin + Fraction(seconds[0]) * self.rate,
            None if seconds[1] is None else self.origin + Fraction(seconds[1]) * self.rate,
        )


class OnReference(CoordinateTransform):
    """A tick axis's positions on the reference clock and in seconds from the session's origin.

    Both float64, NaN where the clock mapping places no tick. Either name may be None, for a
    coordinate the axis does not carry.
    """

    def __init__(self, ticks: Ticks, reference: Reference, tick_name: str | None, second_name: str | None) -> None:
        """Compute `tick_name` and `second_name` for each position of `ticks`."""
        names = [name for name in (tick_name, second_name) if name is not None]
        super().__init__(names, {ticks.dim: ticks.size}, dtype=np.dtype(np.float64))
        self.ticks, self.reference, self.tick_name, self.second_name = ticks, reference, tick_name, second_name

    def forward(self, dim_positions: dict[str, Any]) -> dict[Hashable, Any]:
        """Return each position's reference tick and second."""
        stored = self.ticks.forward(dim_positions)[self.ticks.name]
        reference = self.reference.mapped(stored)
        found: dict[Hashable, Any] = {}
        if self.tick_name is not None:
            found[self.tick_name] = reference
        if self.second_name is not None:
            assert self.reference.origin is not None and self.reference.rate is not None
            found[self.second_name] = (reference - self.reference.origin) / float(self.reference.rate)
        return found

    def reverse(self, coord_labels: dict[Hashable, Any]) -> dict[str, Any]:
        """Refuse: a reference tick reaches a position only through :meth:`positions`."""
        raise NotImplementedError("select a reference tick or second through the index, exactly")

    def equals(self, other: CoordinateTransform, **_: Any) -> bool:
        """Two are equal where their axes' ticks, the mapping and the names agree."""
        return (
            isinstance(other, OnReference)
            and self.ticks.equals(other.ticks)
            and self.reference == other.reference
            and (self.tick_name, self.second_name) == (other.tick_name, other.second_name)
        )

    def sliced(self, key: Any) -> OnReference | None:
        """Return the coordinates a forward positional slice keeps, or None for any other selection."""
        ticks = self.ticks.sliced(key)
        return None if ticks is None else OnReference(ticks, self.reference, self.tick_name, self.second_name)

    def positions(self, start: Tick | None, stop: Tick | None) -> slice | NDArray[np.int64]:
        """Return the positions whose reference tick lies in the closed window, exactly.

        A slice where they are contiguous, and an array where the mapping leaves a hole.
        """
        ticks, reference = self.ticks, self.reference
        if reference.path is None:
            return ticks.window(start, stop)
        first = -(2**62) if start is None else math.ceil(Fraction(start))
        last = 2**62 if stop is None else math.floor(Fraction(stop))
        starts, stops = stored_intervals(
            reference.graph, reference.clock_id, reference.reference_clock_id, (first, last), reference.bound
        )
        runs = []
        for low, high in zip(starts.tolist(), stops.tolist(), strict=True):
            # The inverse is exact on stored ticks; a position between two of them is checked against
            # the mapping itself within one tick of each end, and every position inside maps within.
            candidates = ticks.window(low - 1, high + 1)
            head = range(candidates.start, min(candidates.stop, ticks.window(low - 1, low + 1).stop))
            tail = range(max(head.stop, ticks.window(high - 1, high + 1).start), candidates.stop)
            edges = np.concatenate([np.arange(head.start, head.stop), np.arange(tail.start, tail.stop)])
            inside = edges[self._within(edges, first, last)].tolist()
            if head.stop < tail.start:
                inside += [head.stop, tail.start - 1]
            if inside:
                runs.append((min(inside), max(inside) + 1))
        if not runs:
            return slice(0, 0)
        if len(runs) == 1:
            return slice(*runs[0])
        return np.concatenate([np.arange(begin, end) for begin, end in runs]).astype(np.int64)

    def _within(self, positions: NDArray[np.int64], first: int, last: int) -> NDArray[np.bool_]:
        """Return whether each position's reference tick is placed and within ``[first, last]``."""
        reference = self.reference.mapped(self.ticks.forward({self.ticks.dim: positions})[self.ticks.name])
        with np.errstate(invalid="ignore"):
            return np.asarray((reference >= first) & (reference <= last))


class ReferenceIndex(CoordinateTransformIndex):
    """An index selecting a tick axis's positions by reference tick or by second, exactly.

    A slice is a closed window and a value must be the coordinate of one position. A reference tick
    is a whole tick and compares as one; a second compares as its float64 coordinate shows it, so a
    value copied from the coordinate selects its position.
    """

    def __init__(self, transform: OnReference) -> None:
        """Index the coordinates `transform` computes."""
        super().__init__(transform)
        self.on_reference = transform

    def sel(self, labels: dict[Any, Any], method: str | None = None, tolerance: Any = None) -> IndexSelResult:
        """Select positions by reference tick or second."""
        if method is not None:
            raise ValueError("a reference tick or second selects exactly; select a window instead of the nearest")
        if len(labels) != 1:
            raise ValueError("select by a reference tick or by a second, not both at once")
        ((name, key),) = labels.items()
        transform = self.on_reference
        in_seconds = name == transform.second_name

        def window(start: Tick | None, stop: Tick | None) -> slice | NDArray[np.int64]:
            if not in_seconds:
                return transform.positions(start, stop)
            widened = transform.positions(*_widened(*transform.reference.tick_window((start, stop)), 1))
            dim = transform.ticks.dim
            return _shown(widened, lambda k: transform.forward({dim: k})[transform.second_name], start, stop)

        return _select(name, key, transform.ticks.dim, window)

    def isel(self, indexers: Mapping[Any, Any]) -> ReferenceIndex | None:
        """Keep the index through a forward positional slice; any other selection leaves the coordinates unindexed."""
        sliced = self.on_reference.sliced(indexers.get(self.on_reference.ticks.dim))
        return None if sliced is None else ReferenceIndex(sliced)


def _widened(start: Tick | None, stop: Tick | None, margin: int) -> tuple[Tick | None, Tick | None]:
    """Return the window widened by `margin` at each bounded end."""
    return (None if start is None else start - margin, None if stop is None else stop + margin)


def _shown(
    found: slice | NDArray[np.int64], values: Any, start: Tick | None, stop: Tick | None
) -> slice | NDArray[np.int64]:
    """Trim positions, in coordinate order, to those whose coordinate as `values` gives it lies in the window.

    `found` must hold every such position; only its ends are tested, since the coordinate ascends.
    """

    def inside(position: int) -> bool:
        (value,) = values(np.array([position]))
        return bool(not np.isnan(value) and (start is None or value >= start) and (stop is None or value <= stop))

    every = range(found.start, found.stop) if isinstance(found, slice) else found
    lo, hi = 0, len(every)
    while lo < hi and not inside(int(every[lo])):
        lo += 1
    while hi > lo and not inside(int(every[hi - 1])):
        hi -= 1
    if isinstance(found, slice):
        return slice(found.start + lo, found.start + hi)
    return found[lo:hi]


def _select(
    name: Hashable, key: Any, dim: str, window: Callable[[Tick | None, Tick | None], slice | NDArray[np.int64]]
) -> IndexSelResult:
    """Select by a closed window, or by values each the coordinate of exactly one position."""
    if isinstance(key, slice):
        if key.step is not None:
            raise ValueError("a window takes no step")
        return IndexSelResult({dim: window(key.start, key.stop)})

    def one(value: Tick) -> int:
        found = window(value, value)
        positions = range(found.start, found.stop) if isinstance(found, slice) else found
        if len(positions) != 1:
            raise KeyError(f"{len(positions)} positions of {dim!r} have {name} {value}, not one")
        return int(positions[0])

    values = np.asarray(getattr(key, "values", key), dtype=object)
    found = np.vectorize(one, otypes=[np.int64])(values)
    return IndexSelResult({dim: found if found.ndim else int(found)})


class _Values(BackendArray):
    """An array's stored values, read per selection, and decoded where asked.

    Decoding applies the scaling and marks padding as NaN, so it yields float64.
    """

    def __init__(self, resource: ArrayResource, scaling: Any, padding: Padding) -> None:
        """Read `resource`, applying `scaling` and setting each position `padding` masks to NaN."""
        self.resource, self.scaling, self.padding = resource, scaling, padding
        self.shape = tuple(resource.shape)
        decoded = scaling is not None or bool(padding)
        self.dtype = np.dtype(np.float64) if decoded else np.dtype(resource.dtype)

    def __getitem__(self, key: indexing.ExplicitIndexer) -> Any:
        """Read the selection, the outer indexing Zarr supports, with xarray decomposing the rest."""
        return indexing.explicit_indexing_adapter(key, self.shape, indexing.IndexingSupport.OUTER, self._read)

    def _read(self, key: tuple[Any, ...]) -> NDArray[Any]:
        """Read and decode one outer selection."""
        stored = np.asarray(self.resource.open().oindex[key])
        if self.dtype != np.float64 or (self.scaling is None and not self.padding):
            return stored
        values = stored.astype(np.float64)
        if self.scaling is not None:
            along: tuple[int, ...] = () if self.scaling.axis is None else (self.scaling.axis,)
            values = values * _outer(self.scaling.conversion, along, key) + _outer(self.scaling.offset, along, key)
        for axes, mask in self.padding:
            values = np.where(_outer(mask, axes, key), np.nan, values)
        return values


def _outer(values: Any, axes: tuple[int, ...], key: tuple[Any, ...]) -> Any:
    """Select `values`, whose dimensions are the array's `axes` in order, as `key` selects the array.

    The result broadcasts against the selection: an integer in `key` drops its axis, as Zarr's
    outer indexing does, and each axis `values` lacks has length 1.
    """
    if not axes:
        return values
    order = sorted(range(len(axes)), key=axes.__getitem__)
    selected = np.transpose(np.asarray(values), order)
    ascending = [axes[i] for i in order]
    for dim in reversed(range(len(ascending))):
        part = key[ascending[dim]]
        selected = selected[(slice(None),) * dim + (part,)] if isinstance(part, slice) else selected.take(part, dim)
    kept = [axis for axis, part in enumerate(key) if not isinstance(part, Integral)]
    shape = [1] * len(kept)
    for axis, size in zip((a for a in ascending if a in kept), selected.shape, strict=True):
        shape[kept.index(axis)] = size
    return selected.reshape(shape)


def _names(description: ArrayDescription) -> dict[int, str]:
    """Name each axis's coordinate: the key a labelled axis holds, ``tick``, or the dimension's own name.

    A name two axes would share, or that is another axis's dimension, takes its dimension as a prefix.
    """
    dims = [axis.name for axis in description.axes]
    wanted = [
        axis.coordinates.key
        if isinstance(axis.coordinates, LabelledAxis)
        else "tick"
        if isinstance(axis.coordinates, TickAxis)
        else axis.name
        for axis in description.axes
    ]
    return {
        index: name
        if name == dims[index] or (wanted.count(name) == 1 and name not in dims)
        else f"{dims[index]}_{name}"
        for index, name in enumerate(wanted)
    }


def _irregular(packet: PacketLike, form: IrregularAxis, mask_and_scale: bool) -> tuple[Any, dict[str, Any]]:
    """Return an irregular axis's values unread, and their unit; unindexed, since an index reads them all."""
    scaling = describe(packet, form.resource_id).scaling
    values = _Values(packet.array_resource(form.resource_id), scaling if mask_and_scale else None, [])
    lazy = indexing.LazilyIndexedArray(values)
    if scaling is None:
        return lazy, {}
    attrs = {} if scaling.unit is None else {"units": scaling.unit}
    if mask_and_scale:
        return lazy, attrs
    return lazy, {**attrs, "scale_factor": scaling.conversion, "add_offset": scaling.offset}


def _reference(packet: PacketLike, clock_id: int) -> Reference | None:
    """Return how a clock reaches the packet's reference clock and seconds, or None where it reaches neither."""
    try:
        target = reference_clock(packet)
    except NotAligned:
        return None
    try:
        start, num, den = origin(packet)
        seconds: tuple[int | None, Fraction | None] = (start, Fraction(num, den))
    except (NoTimeOrigin, NotAligned):
        seconds = (None, None)
    if clock_id == target and seconds[0] is None:
        return None
    try:
        return Reference(clock_graph(packet), clock_id, target, declared_bound(packet), *seconds)
    except ValueError:  # NotAligned and Unanchored: the clock does not reach the reference
        return None


class _Builder:
    """One array's coordinates, collected axis by axis."""

    def __init__(self, resource_id: str) -> None:
        """Start an empty set of coordinates for `resource_id`."""
        self.resource_id = resource_id
        self.coords: dict[str, xr.Variable] = {}
        self.indexed: list[str] = []
        self.ticks: list[tuple[TickIndex, int]] = []
        self.references: list[ReferenceIndex] = []
        self.padding: Padding = []

    def add(self, name: str, dims: tuple[str, ...], values: Any, attrs: Mapping[str, Any] | None = None) -> None:
        """Add a coordinate, refusing a second of one name."""
        if name in self.coords:
            raise ValueError(f"{self.resource_id}: two coordinates would be named {name!r}")
        self.coords[name] = xr.Variable(dims, values, attrs)

    def labelled(self, axis: int, name: str, form: LabelledAxis, dims: list[str], columns: Sequence[str]) -> None:
        """Add a labelled axis's labels, where it pads, and the columns of its rows asked for."""
        along = (dims[axis],) if form.depends_on is None else (dims[form.depends_on], dims[axis])
        labels = form.labels()
        mask = np.ma.getmaskarray(labels)
        self.add(name, along, labels.data, {"resource": form.resource_id})
        if mask.any():
            self.add(f"{dims[axis]}_present", along, ~mask)
            self.padding.append(((axis,) if form.depends_on is None else (form.depends_on, axis), mask))
        elif form.depends_on is None and len(np.unique(labels.data)) == labels.size:
            self.indexed.append(name)
        for column in columns:
            if column not in form.rows.column_names:
                raise ValueError(f"{form.resource_id} has no column {column!r} to label {dims[axis]!r} with")
            self.add(column, along, form.rows.column(column).to_numpy(zero_copy_only=False).reshape(form.shape))

    def scaling(self, description: ArrayDescription, dims: list[str], mask_and_scale: bool) -> dict[str, Any]:
        """Return the values' attributes, adding a coordinate for what varies along an axis."""
        scaling = description.scaling
        if scaling is None:
            return {}
        attrs: dict[str, Any] = {}
        unit = scaling.unit
        if isinstance(unit, tuple) and len(set(unit)) == 1:
            unit = unit[0]
        if isinstance(unit, str):
            attrs["units"] = unit
        elif unit is not None and scaling.axis is not None:
            self.add("units", (dims[scaling.axis],), np.asarray(unit))
        if mask_and_scale:
            return attrs
        if scaling.axis is None:
            return {**attrs, "scale_factor": scaling.conversion, "add_offset": scaling.offset}
        self.add("conversion", (dims[scaling.axis],), scaling.conversion)
        self.add("offset", (dims[scaling.axis],), scaling.offset)
        return attrs


def _dataset(
    packet: PacketLike, resource_id: str, *, mask_and_scale: bool, columns: Mapping[str, Sequence[str]], strict: bool
) -> xr.Dataset:
    """Build one array's Dataset, its values unread; `strict` refuses columns for a dimension it lacks."""
    description = describe(packet, resource_id)
    dims = [axis.name for axis in description.axes]
    if strict and (unknown := set(columns) - set(dims)):
        raise ValueError(f"{resource_id} has no dimension {', '.join(sorted(unknown))}; its dimensions are {dims}")
    names, built = _names(description), _Builder(resource_id)
    for axis in description.axes:
        form, name = axis.coordinates, names[axis.index]
        if isinstance(form, LabelledAxis):
            built.labelled(axis.index, name, form, dims, columns.get(axis.name, ()))
            continue
        if columns.get(axis.name):
            raise ValueError(f"{resource_id}: {axis.name!r} is not a labelled axis, so it has no columns")
        if isinstance(form, NumericAxis):
            built.add(name, (axis.name,), form.origin + np.arange(axis.length) * form.step, {"units": form.unit})
            built.indexed.append(name)
        elif isinstance(form, IrregularAxis):
            built.add(name, (axis.name,), *_irregular(packet, form, mask_and_scale))
        else:
            ticks = Ticks(name, axis.name, axis.length, Fraction(form.origin_tick), form.step)
            built.ticks.append((TickIndex(ticks), form.clock_id))
            if (reference := _reference(packet, form.clock_id)) is not None:
                prefix = name.removesuffix("tick")
                tick_name = None if reference.path is None else f"{prefix}reference_tick"
                second_name = None if reference.origin is None else f"{prefix}second"
                built.references.append(ReferenceIndex(OnReference(ticks, reference, tick_name, second_name)))
    attrs = {"resource_id": resource_id, **built.scaling(description, dims, mask_and_scale)}
    resource = packet.array_resource(resource_id)
    values = _Values(resource, description.scaling if mask_and_scale else None, built.padding if mask_and_scale else [])
    data = xr.Variable(dims, indexing.LazilyIndexedArray(values), attrs)
    unit_of_read = resource.shards or resource.chunks
    data.encoding = {"preferred_chunks": dict(zip(dims, unit_of_read, strict=True)), "chunks": unit_of_read}
    # No default index: one on an irregular axis would read its coordinate array whole.
    dataset = xr.Dataset({_variable_name(resource_id): data}, coords=xr.Coordinates(built.coords, indexes={}))
    for index, clock_id in built.ticks:
        dataset = dataset.assign_coords(xr.Coordinates.from_xindex(index))
        dataset[index.ticks.name].attrs["clock_id"] = clock_id
    for on_reference in built.references:
        dataset = dataset.assign_coords(xr.Coordinates.from_xindex(on_reference))
        transform = on_reference.on_reference
        if transform.tick_name is not None:
            dataset[transform.tick_name].attrs["clock_id"] = transform.reference.reference_clock_id
        if transform.second_name is not None:
            dataset[transform.second_name].attrs["units"] = "s"
    for name in built.indexed:
        dataset = dataset.set_xindex(name)
    return dataset


def _variable_name(resource_id: str) -> str:
    """Name an array's variable after the last part of its resource ID, ``lfp`` for ``core.45883-1.lfp``."""
    return resource_id.rpartition(".")[2]


def _packet(filename_or_obj: Any) -> PacketLike:
    """Open a packet named by path or URI, or take an opened one as it is."""
    if isinstance(filename_or_obj, os.PathLike):
        return open_packet(Path(filename_or_obj))
    if isinstance(filename_or_obj, str | Location):
        return open_packet(filename_or_obj)
    return filename_or_obj  # type: ignore[no-any-return]


def _catalogued(packet: PacketLike) -> list[str]:
    """Return the packet's dense arrays a catalog row describes, in manifest order."""
    return [
        resource.resource_id
        for resource in packet.resources()
        if (resource.declaration or {}).get("kind") == "dense_array"
        and (resource.declaration or {}).get("instances", {}).get("mode") == "catalog"
    ]


def _named(resource_id: str | Sequence[str]) -> list[str]:
    """Return the named arrays, a lone ID as a list of one."""
    return [resource_id] if isinstance(resource_id, str) else list(resource_id)


def _resource_ids(resource_id: str | Sequence[str]) -> list[str]:
    """Return the named arrays, refusing two whose variables would share a name."""
    ids = _named(resource_id)
    names = [_variable_name(r) for r in ids]
    if len(set(names)) != len(names):
        raise ValueError(f"{ids} name two arrays one variable name; open them as a DataTree")
    return ids


def _columns(columns: Mapping[str, str | Sequence[str]] | None) -> dict[str, Sequence[str]]:
    """Return the columns asked for per dimension, a lone name as a list of one."""
    return {dim: [names] if isinstance(names, str) else names for dim, names in (columns or {}).items()}


class EscapewheelBackend(BackendEntrypoint):
    """Open a packet's dense arrays as ``engine="escapewheel"``.

    ``xr.open_dataset(packet, engine="escapewheel", resource_id="core.waveform_mean")`` gives one
    variable per array, named after the last part of its resource ID, on dimensions named as the
    packet names its axes. Each axis carries its coordinates:

    - a labelled axis carries its labels as a coordinate named for the key they hold, such as
      ``unit_id``, indexed where it is independent and its labels are distinct. A dependent axis's
      labels vary along the axis it depends on, so the coordinate is 2-D. Where any position is
      padding, a boolean ``<dim>_present`` coordinate is false there and the label is meaningless.
      `columns` adds columns of the labelled rows, as ``{"unit": ["quality_label"]}``.
    - a numeric axis carries its values as an indexed coordinate named for the dimension, its unit
      in ``units``.
    - an irregular axis carries its coordinate array's values, unread and unindexed, named the same
      way; ``set_xindex`` reads them to select by value.
    - a tick axis carries a ``tick`` coordinate computed per position, under a :class:`TickIndex`,
      and its clock in ``clock_id``. Where its clock reaches the packet's reference clock, it also
      carries ``reference_tick``, NaN where the anchors place no tick, and where the packet declares
      a time origin ``second``, both under a :class:`ReferenceIndex`. An axis on the reference
      clock carries ``second`` alone.

    A coordinate name two axes would share takes its dimension as a prefix, as ``channel_tick``.

    With `mask_and_scale`, values are float64 in the declared unit and padding is NaN. Without it,
    they are as stored, with an array-level ``scale_factor`` and ``add_offset`` in the attributes
    or per-position ``conversion`` and ``offset`` coordinates.
    """

    description = "Read an Escapewheel packet's dense arrays, each axis carrying its coordinates"
    url = "https://github.com/galenlynch/escapewheel/"
    open_dataset_parameters = ("filename_or_obj", "drop_variables", "resource_id", "mask_and_scale", "columns")
    supports_groups = True

    def open_dataset(
        self,
        filename_or_obj: Any,
        *,
        drop_variables: str | Iterable[str] | None = None,
        resource_id: str | Sequence[str] | None = None,
        mask_and_scale: bool = True,
        columns: Mapping[str, str | Sequence[str]] | None = None,
    ) -> xr.Dataset:
        """Open one array, or several sharing their dimensions' coordinates exactly, as a Dataset.

        Parameters
        ----------
        filename_or_obj : PacketLike, str, Path or Location
            An opened packet, or a packet root to open.
        drop_variables : str or iterable of str, optional
            Variables or coordinates to leave out.
        resource_id : str or sequence of str
            The arrays to open, by dotted resource ID.
        mask_and_scale : bool, default True
            Whether to apply the declared scaling and make padding NaN.
        columns : mapping, optional
            Dimension name to the columns of its labelled rows to add as coordinates.

        Returns
        -------
        xarray.Dataset
            The arrays, their values unread.

        Raises
        ------
        ValueError
            Where no array is named, two would share a variable name, or their coordinates disagree.
        UnresolvableAxis
            Where an array's declared coordinates or scaling do not determine one answer.
        """
        packet = _packet(filename_or_obj)
        if resource_id is None:
            raise ValueError(f"name the arrays to open with resource_id: {', '.join(_catalogued(packet))}")
        asked = _columns(columns)
        parts = [
            _dataset(packet, r, mask_and_scale=mask_and_scale, columns=asked, strict=isinstance(resource_id, str))
            for r in _resource_ids(resource_id)
        ]
        merged = (
            parts[0]
            if len(parts) == 1
            else xr.merge(parts, join="exact", compat="equals", combine_attrs="drop_conflicts")
        )
        return merged.drop_vars(drop_variables or [], errors="ignore")

    def open_groups_as_dict(
        self,
        filename_or_obj: Any,
        *,
        drop_variables: str | Iterable[str] | None = None,
        resource_id: str | Sequence[str] | None = None,
        mask_and_scale: bool = True,
        columns: Mapping[str, str | Sequence[str]] | None = None,
    ) -> dict[str, xr.Dataset]:
        """Open each array as a group at its resource ID's path, ``/core/waveform_mean``.

        `resource_id` defaults to every array a catalog describes; the other parameters are
        :meth:`open_dataset`'s, `columns` applying to each array having the dimension.
        """
        packet = _packet(filename_or_obj)
        ids = _catalogued(packet) if resource_id is None else _named(resource_id)
        asked = _columns(columns)
        groups = {"/": xr.Dataset()}
        for r in ids:
            dataset = _dataset(packet, r, mask_and_scale=mask_and_scale, columns=asked, strict=False)
            groups["/" + r.replace(".", "/")] = dataset.drop_vars(drop_variables or [], errors="ignore")
        return groups

    def open_datatree(
        self,
        filename_or_obj: Any,
        *,
        drop_variables: str | Iterable[str] | None = None,
        resource_id: str | Sequence[str] | None = None,
        mask_and_scale: bool = True,
        columns: Mapping[str, str | Sequence[str]] | None = None,
    ) -> xr.DataTree:
        """Open each array as a node of a DataTree, as :meth:`open_groups_as_dict` arranges them."""
        groups = self.open_groups_as_dict(
            filename_or_obj,
            drop_variables=drop_variables,
            resource_id=resource_id,
            mask_and_scale=mask_and_scale,
            columns=columns,
        )
        return xr.DataTree.from_dict(groups)

    def guess_can_open(self, filename_or_obj: Any) -> bool:
        """Claim an opened packet, or a local directory holding a manifest; never reach a remote store."""
        if isinstance(filename_or_obj, Packet):
            return True
        if isinstance(filename_or_obj, str | os.PathLike) and "://" not in str(filename_or_obj):
            return (Path(filename_or_obj) / MANIFEST_FILENAME).is_file()
        return False


__all__ = ["EscapewheelBackend", "OnReference", "Reference", "ReferenceIndex", "TickIndex", "Ticks"]
