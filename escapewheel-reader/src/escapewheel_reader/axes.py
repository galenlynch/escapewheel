"""What a dense array's axes and values mean, read from the packet's tables (Part 03 §6.3).

- :func:`describe` -- an array's :class:`ArrayDescription`, reading no values.
- :class:`ArrayDescription` -- one :class:`Axis` per dimension, and any :class:`Scaling`.
- :class:`TickAxis`, :class:`NumericAxis`, :class:`IrregularAxis`, :class:`LabelledAxis` -- the
  four forms an axis's coordinates take.

Nothing here needs Zarr or an array library, so an adapter to one can build on it.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, cast

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from numpy.typing import NDArray

from .discriminators import Discriminator, _one, _paired_target, registries
from .errors import AxisFault, UnresolvableAxis
from .protocols import PacketLike
from .resource_ids import CORE_ARRAY_CHANNELS

#: The column whose value declares each coordinate form; an axis declares one.
FORMS = ("origin_tick", "origin_value", "coordinate_array_asset_id", "coordinate_resource")


@dataclass(frozen=True)
class TickAxis:
    """A regular axis on a clock: position *k* is tick ``origin_tick + k * step``."""

    clock_id: int
    origin_tick: int
    step: Fraction

    def ticks(self, positions: NDArray[np.int64]) -> NDArray[Any]:
        """Return the tick at each position: int64 where the step is whole, float64 otherwise.

        A fractional step lands between ticks, so an integer result would be a rounding the
        caller did not ask for.
        """
        positions = np.asarray(positions, dtype=np.int64)
        if self.step.denominator == 1:
            return self.origin_tick + positions * self.step.numerator
        return self.origin_tick + positions * (self.step.numerator / self.step.denominator)


@dataclass(frozen=True)
class NumericAxis:
    """A regular axis in a physical unit: position *k* is ``origin + k * step``.

    An axis carrying only its positions' order is one of these, with step 1 and unit ``1``.
    """

    origin: float
    step: float
    unit: str


@dataclass(frozen=True)
class IrregularAxis:
    """An axis whose values are a 1-D array, one per position."""

    array_asset_id: int
    resource_id: str


@dataclass(frozen=True)
class LabelledAxis:
    """An axis whose positions stand for rows of `resource_id`, each named by a label.

    `rows` has one row per position in position order: the label, in a column named `key` after
    the key it holds, by_position to the named row's columns. On a dependent axis the labels change
    along axis `depends_on`, so `rows` has one row per position for each position of that axis,
    ordered by it first and saying which in `depends_on_position_index`. A null label is padding:
    the position stands for no row, and the by_position columns are null with it.
    """

    resource_id: str
    key: str
    depends_on: int | None
    shape: tuple[int, ...]
    rows: pa.Table

    def labels(self) -> np.ma.MaskedArray[Any, np.dtype[Any]]:
        """Return the labels shaped `shape`, ``(length,)`` or ``(depends-on length, length)``, masked at padding.

        Masked rather than filled, since every integer is a possible label and no fill can mean none.
        """
        labels = self.rows.column(self.key).to_pylist()
        values = np.array([0 if label is None else label for label in labels], dtype=np.int64)
        mask = np.array([label is None for label in labels], dtype=bool)
        return np.ma.MaskedArray(values.reshape(self.shape), mask=mask.reshape(self.shape))


Coordinates = TickAxis | NumericAxis | IrregularAxis | LabelledAxis


@dataclass(frozen=True)
class Axis:
    """One axis in stored order (Part 03 §6.2), and the one coordinate form it declares."""

    index: int
    name: str
    length: int
    coordinates: Coordinates


@dataclass(frozen=True)
class Scaling:
    """``physical = stored * conversion + offset``, declared once for the array or per position of one axis.

    `axis` is None for the array level, where `conversion` and `offset` are scalars; otherwise
    they are float64 arrays along that axis. An array declaring a unit and no conversion stores
    physical values, so its conversion is 1; one declaring a conversion and no unit has `unit` None.
    """

    unit: str | tuple[str, ...] | None
    conversion: float | NDArray[np.float64]
    offset: float | NDArray[np.float64]
    axis: int | None = None


@dataclass(frozen=True)
class ArrayDescription:
    """What a catalogued dense array's axes and values mean, without its values."""

    resource_id: str
    array_asset_id: int
    shape: tuple[int, ...]
    axes: tuple[Axis, ...]
    scaling: Scaling | None


def _held(packet: PacketLike) -> set[str]:
    return {r.resource_id for r in packet.resources()}


def _catalog_row(packet: PacketLike, resource_id: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Return the array's declaration, its catalog row, and the catalog's resource ID."""
    declaration = packet.resource(resource_id).declaration
    if not declaration or declaration.get("kind") != "dense_array":
        raise UnresolvableAxis(AxisFault.NOT_AN_ARRAY, f"{resource_id} is not declared as a dense array")
    instances = declaration.get("instances", {})
    if instances.get("mode") != "catalog":
        raise UnresolvableAxis(
            AxisFault.UNCATALOGUED, f"{resource_id}: its declaration has no catalog, so no row names its axes"
        )
    catalog_id = instances["catalog_resource"]
    catalog = packet.table(catalog_id)
    rows = catalog.filter(pc.field(instances["resource_id_column"]) == resource_id).to_pylist()
    if len(rows) != 1:
        raise UnresolvableAxis(
            AxisFault.UNCATALOGUED, f"{resource_id}: {len(rows)} rows of {catalog_id} name it, not one"
        )
    return dict(declaration), rows[0], catalog_id


def _label_rows(packet: PacketLike, axes_id: str, array_asset_id: int) -> tuple[Discriminator, pa.Table]:
    """Return how the axes table's labels resolve, and this array's rows of its label table.

    The label table is the one `coordinate_resource`'s `discriminates_via` names, as a validator
    finds it (Part 05 §5.3), since a core and an analysis array keep their labels apart.
    """
    found = _one(packet, axes_id, "coordinate_resource")
    if found.specialised not in _held(packet):
        raise UnresolvableAxis(
            AxisFault.LABELS_ABSENT, f"{axes_id} labels an axis and the packet holds no {found.specialised}"
        )
    table = packet.table(found.specialised)
    return found, table.filter(pc.field("array_asset_id") == array_asset_id)


def _labelled(
    packet: PacketLike,
    row: dict[str, Any],
    rows: list[dict[str, Any]],
    shape: tuple[int, ...],
    found: Discriminator,
    labels: pa.Table,
) -> LabelledAxis:
    """Order one axis's labels by position and join each to the row it names."""
    axis, name, kind = row["axis_index"], row["dimension_name"], row["coordinate_resource"]
    depends_on = row["depends_on_axis_index"]
    if depends_on is None:
        extent = 1
    elif 0 <= depends_on < len(shape) and depends_on != axis and rows[depends_on]["depends_on_axis_index"] is None:
        extent = shape[depends_on]
    else:
        raise UnresolvableAxis(
            AxisFault.DEPENDENCY_CHAIN,
            f"axis {name!r} depends on axis {depends_on}, not on another independent axis",
        )
    length = shape[axis]
    order = ["depends_on_position_index", "position_index"]
    ours = labels.filter(pc.field("axis_index") == axis).sort_by([(c, "ascending") for c in order])
    expected = (np.repeat(np.arange(extent), length), np.tile(np.arange(length), extent))
    if ours.num_rows != extent * length or not all(
        np.array_equal(ours.column(c).to_numpy(), e) for c, e in zip(order, expected, strict=True)
    ):
        raise UnresolvableAxis(
            AxisFault.LABEL_COUNT,
            f"axis {name!r} has {ours.num_rows} label rows for its {extent * length} positions, not one at each",
        )
    if kind not in _held(packet):
        raise UnresolvableAxis(
            AxisFault.LABELS_ABSENT, f"axis {name!r} stands for rows of {kind}, which the packet does not hold"
        )
    key = _paired_target(packet, kind, found)
    named = packet.table(kind)
    ids = ours.column("label_id")
    # Taken by index, the named rows stay in position order, and padding takes a row of nulls.
    at = pc.index_in(ids, value_set=named.column(key).combine_chunks())
    unmatched = at.null_count - ids.null_count
    if unmatched:
        raise UnresolvableAxis(AxisFault.LABEL_UNMATCHED, f"axis {name!r}: {unmatched} labels name no row of {kind}")
    taken = named.select([key, *(c for c in named.column_names if c != key)]).take(at)
    kept = order[1:] if depends_on is None else order
    by_position = pa.Table.from_arrays(
        [*(ours.column(c) for c in kept), *taken.columns], names=[*kept, *taken.column_names]
    )
    return LabelledAxis(kind, key, depends_on, (length,) if depends_on is None else (extent, length), by_position)


def _irregular(packet: PacketLike, row: dict[str, Any], length: int, catalog: pa.Table) -> IrregularAxis:
    """Find the 1-D array holding an irregular axis's values, and check it has one per position."""
    target = row["coordinate_array_asset_id"]
    named = cast("list[str]", catalog.filter(pc.field("array_asset_id") == target)["resource_id"].to_pylist())
    if len(named) != 1:
        raise UnresolvableAxis(
            AxisFault.COORDINATE_ARRAY,
            f"axis {row['dimension_name']!r} names array asset {target}, which no row catalogues",
        )
    shape = packet.array_resource(named[0]).shape
    if shape != (length,):
        raise UnresolvableAxis(
            AxisFault.COORDINATE_ARRAY, f"axis {row['dimension_name']!r}: {named[0]} has shape {shape}, not ({length},)"
        )
    return IrregularAxis(target, str(named[0]))


def _coordinates(
    packet: PacketLike,
    row: dict[str, Any],
    rows: list[dict[str, Any]],
    shape: tuple[int, ...],
    catalog: pa.Table,
    labels: tuple[Discriminator, pa.Table] | None,
) -> Coordinates:
    """Return the one form an axis row declares."""
    name = row["dimension_name"]
    forms = [form for form in FORMS if row[form] is not None]
    if len(forms) != 1:
        raise UnresolvableAxis(AxisFault.FORM_COUNT, f"axis {name!r} declares {len(forms)} coordinate forms, not one")
    if forms[0] != "coordinate_resource" and row["depends_on_axis_index"] is not None:
        raise UnresolvableAxis(
            AxisFault.DEPENDENCY_UNLABELLED,
            f"axis {name!r} depends on another axis and has no labels to vary",
        )
    if forms[0] == "origin_tick":
        if row["step_tick_num"] is None or row["clock_id"] is None:
            raise UnresolvableAxis(AxisFault.FORM_INCOMPLETE, f"axis {name!r} has an origin tick and no step or clock")
        return TickAxis(row["clock_id"], row["origin_tick"], Fraction(row["step_tick_num"], row["step_tick_den"] or 1))
    if forms[0] == "origin_value":
        if row["step_value"] is None or row["coordinate_unit"] is None:
            raise UnresolvableAxis(AxisFault.FORM_INCOMPLETE, f"axis {name!r} has an origin value and no step or unit")
        return NumericAxis(row["origin_value"], row["step_value"], row["coordinate_unit"])
    if forms[0] == "coordinate_array_asset_id":
        return _irregular(packet, row, shape[row["axis_index"]], catalog)
    assert labels is not None
    return _labelled(packet, row, rows, shape, *labels)


def _channel_scaling(packet: PacketLike, array_asset_id: int, axes_id: str) -> pa.Table | None:
    """Return this array's channel rows declaring a conversion, or None where its channels have no table.

    A channel table belongs to the arrays of the axes table it references: an analysis array is
    numbered apart from a core one, and a channel row for a core array with its number is not its.
    """
    references = registries(packet).get(CORE_ARRAY_CHANNELS, {}).get("references", [])
    if CORE_ARRAY_CHANNELS not in _held(packet) or not any(r.get("resource") == axes_id for r in references):
        return None
    table: pa.Table = packet.table(CORE_ARRAY_CHANNELS)
    return table.filter((pc.field("array_asset_id") == array_asset_id) & pc.field("conversion").is_valid())


def _scaling(
    asset: dict[str, Any], channels: pa.Table | None, shape: tuple[int, ...], resource_id: str
) -> Scaling | None:
    """Return the one level scaling is declared at, or None where neither declares it."""
    per_channel = channels.sort_by("channel_index") if channels is not None and channels.num_rows else None
    unit, conversion = asset.get("unit"), asset.get("conversion")
    if conversion is not None and per_channel is not None:
        raise UnresolvableAxis(
            AxisFault.SCALING_LEVELS,
            f"{resource_id} declares scaling on the array and per channel (core.array_assets.one_scaling_level)",
        )
    if per_channel is None:
        if unit is None and conversion is None:
            return None
        return Scaling(unit, 1.0 if conversion is None else float(conversion), float(asset.get("offset") or 0.0))
    axes = sorted(set(np.asarray(per_channel.column("axis_index").to_numpy()).tolist()))
    if len(axes) != 1 or not 0 <= axes[0] < len(shape):
        raise UnresolvableAxis(
            AxisFault.SCALING_AXIS, f"{resource_id} scales channels on axes {axes}, not on one of its axes"
        )
    axis = axes[0]
    if per_channel.column("channel_index").to_pylist() != list(range(shape[axis])):
        raise UnresolvableAxis(
            AxisFault.SCALING_COVERAGE,
            f"{resource_id} scales {per_channel.num_rows} of the {shape[axis]} channels on axis {axis}, "
            f"so the others have no physical value",
        )
    units = per_channel.column("unit").to_pylist()
    if None in units:
        raise UnresolvableAxis(
            AxisFault.SCALING_UNIT_ABSENT,
            f"{resource_id} converts a channel into no unit (core.array_channels.scaling_pair_complete)",
        )
    channel_units = tuple(str(u) for u in units)
    if unit is not None and set(channel_units) != {unit}:
        raise UnresolvableAxis(
            AxisFault.SCALING_UNIT_DISAGREES,
            f"{resource_id} declares its values in {unit} and its channels in {sorted(set(channel_units))}",
        )
    return Scaling(
        channel_units,
        np.asarray(per_channel.column("conversion").to_numpy(), dtype=np.float64),
        np.array([offset or 0.0 for offset in per_channel.column("offset").to_pylist()], dtype=np.float64),
        axis,
    )


def describe(packet: PacketLike, resource_id: str) -> ArrayDescription:
    """Describe a catalogued dense array's axes and scaling, reading no values.

    Parameters
    ----------
    packet : Packet
        The packet declaring the array.
    resource_id : str
        The array's dotted resource ID.

    Returns
    -------
    ArrayDescription
        One `Axis` per stored axis, and the scaling that turns stored values into physical ones.

    Raises
    ------
    UnresolvableAxis
        Where the declared coordinates or scaling do not determine one answer.
    """
    declaration, asset, catalog_id = _catalog_row(packet, resource_id)
    shape = tuple(packet.array_resource(resource_id).shape)
    axes_id = declaration["array"]["axes_resource"]
    array_asset_id = asset["array_asset_id"]
    table = packet.table(axes_id)
    rows = table.filter(pc.field("array_asset_id") == array_asset_id).sort_by("axis_index").to_pylist()
    if [row["axis_index"] for row in rows] != list(range(len(shape))):
        raise UnresolvableAxis(
            AxisFault.AXES_UNDECLARED, f"{axes_id} does not declare each of {resource_id}'s {len(shape)} axes once"
        )
    labelled = any(row["coordinate_resource"] is not None for row in rows)
    labels = _label_rows(packet, axes_id, array_asset_id) if labelled else None
    catalog = packet.table(catalog_id)
    axes = tuple(
        Axis(row["axis_index"], row["dimension_name"], length, _coordinates(packet, row, rows, shape, catalog, labels))
        for row, length in zip(rows, shape, strict=True)
    )
    scaling = _scaling(asset, _channel_scaling(packet, array_asset_id, axes_id), shape, resource_id)
    return ArrayDescription(resource_id, array_asset_id, shape, axes, scaling)


__all__ = [
    "ArrayDescription",
    "Axis",
    "IrregularAxis",
    "LabelledAxis",
    "NumericAxis",
    "Scaling",
    "TickAxis",
    "describe",
]
