"""A packet's dense arrays as xarray objects, each axis carrying its coordinates (Part 03 §6.3).

- :class:`EscapewheelBackend` -- the ``escapewheel`` engine of :func:`xarray.open_dataset` and
  :func:`xarray.open_datatree`.
- :class:`TickIndex` -- selects positions on a tick axis by tick, exactly.
- :class:`Ticks` -- the tick at each position of a tick axis, computed rather than stored.

Opening reads the packet's tables and no values; a selection reads only the chunks it touches.
Needs the ``xarray`` extra.
"""

from __future__ import annotations

import functools
import math
import os
from collections.abc import Hashable, Iterable, Mapping, Sequence
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

    def position(self, tick: Tick) -> int:
        """Return the position whose tick is exactly `tick`."""
        offset = (Fraction(tick) - self.origin) / self.step
        if offset.denominator != 1 or not 0 <= offset < self.size:
            raise KeyError(f"no position of {self.dim!r} is at tick {tick}")
        return int(offset)

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
    and no other method applies.
    Bounds are compared as fractions, so a window never gains or loses an edge position to rounding
    however far the axis runs from its origin.
    """

    def __init__(self, transform: Ticks) -> None:
        """Index the tick axis `transform` computes."""
        super().__init__(transform)
        self.ticks = transform

    def sel(self, labels: dict[Any, Any], method: str | None = None, tolerance: Any = None) -> IndexSelResult:
        """Select positions by tick, or with ``method="nearest"`` by the nearest within `tolerance` ticks."""
        if method not in (None, "nearest"):
            raise ValueError(f"a tick axis selects exactly or by nearest, not by {method!r}")
        (key,) = labels.values()
        if isinstance(key, slice):
            if key.step is not None:
                raise ValueError("a tick window takes no step")
            return IndexSelResult({self.ticks.dim: self.ticks.window(key.start, key.stop)})
        if isinstance(key, xr.Variable | xr.DataArray):
            key = key.values
        find = self.ticks.position if method is None else functools.partial(self.ticks.nearest, tolerance=tolerance)
        found = np.vectorize(find, otypes=[np.int64])(np.asarray(key, dtype=object))
        return IndexSelResult({self.ticks.dim: found if found.ndim else int(found)})

    def isel(self, indexers: Mapping[Any, Any]) -> TickIndex | None:
        """Keep the index through a forward positional slice; any other selection leaves the ticks unindexed."""
        ticks, key = self.ticks, indexers.get(self.ticks.dim)
        if not isinstance(key, slice):
            return None
        start, stop, stride = key.indices(ticks.size)
        if stride < 1:
            return None
        size = len(range(start, stop, stride))
        return TickIndex(Ticks(ticks.name, ticks.dim, size, ticks.origin + start * ticks.step, ticks.step * stride))


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


def _irregular(packet: PacketLike, form: IrregularAxis, mask_and_scale: bool) -> tuple[NDArray[Any], dict[str, Any]]:
    """Read an irregular axis's values, and their unit; a coordinate array is 1-D and read whole."""
    values = np.asarray(packet.array_resource(form.resource_id).read())
    scaling = describe(packet, form.resource_id).scaling
    if scaling is None:
        return values, {}
    attrs = {} if scaling.unit is None else {"units": scaling.unit}
    if mask_and_scale:
        return values * scaling.conversion + scaling.offset, attrs
    return values, {**attrs, "scale_factor": scaling.conversion, "add_offset": scaling.offset}


class _Builder:
    """One array's coordinates, collected axis by axis."""

    def __init__(self, resource_id: str) -> None:
        """Start an empty set of coordinates for `resource_id`."""
        self.resource_id = resource_id
        self.coords: dict[str, xr.Variable] = {}
        self.indexed: list[str] = []
        self.ticks: list[tuple[TickIndex, int]] = []
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
        elif isinstance(form, IrregularAxis):
            built.add(name, (axis.name,), *_irregular(packet, form, mask_and_scale))
        else:
            ticks = Ticks(name, axis.name, axis.length, Fraction(form.origin_tick), form.step)
            built.ticks.append((TickIndex(ticks), form.clock_id))
    attrs = {"resource_id": resource_id, **built.scaling(description, dims, mask_and_scale)}
    resource = packet.array_resource(resource_id)
    values = _Values(resource, description.scaling if mask_and_scale else None, built.padding if mask_and_scale else [])
    data = xr.Variable(dims, indexing.LazilyIndexedArray(values), attrs)
    unit_of_read = resource.shards or resource.chunks
    data.encoding = {"preferred_chunks": dict(zip(dims, unit_of_read, strict=True)), "chunks": unit_of_read}
    dataset = xr.Dataset({_variable_name(resource_id): data}, coords=built.coords)
    for index, clock_id in built.ticks:
        dataset = dataset.assign_coords(xr.Coordinates.from_xindex(index))
        dataset[index.ticks.name].attrs["clock_id"] = clock_id
    for name in built.indexed:
        dataset = dataset.set_xindex(name)
    return dataset


def _variable_name(resource_id: str) -> str:
    """Name an array's variable after its resource, without the content class."""
    return resource_id.partition(".")[2]


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
    variable per array, named without its content class, on dimensions named as the packet names
    its axes. Each axis carries its coordinates:

    - a labelled axis carries its labels as a coordinate named for the key they hold, such as
      ``unit_id``, indexed where it is independent and its labels are distinct. A dependent axis's
      labels vary along the axis it depends on, so the coordinate is 2-D. Where any position is
      padding, a boolean ``<dim>_present`` coordinate is false there and the label is meaningless.
      `columns` adds columns of the labelled rows, as ``{"unit": ["quality_label"]}``.
    - a numeric axis carries its values as an indexed coordinate named for the dimension, its unit
      in ``units``.
    - an irregular axis carries its coordinate array's values, read whole, named the same way.
    - a tick axis carries a ``tick`` coordinate computed per position, under a :class:`TickIndex`,
      and its clock in ``clock_id``.

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


__all__ = ["EscapewheelBackend", "TickIndex", "Ticks"]
