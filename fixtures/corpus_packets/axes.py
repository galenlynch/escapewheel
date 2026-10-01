"""Packets about what each position of an array axis is."""

from .arrays import LABELLED_SHAPE, ORDER_ONLY, with_waveform
from .record import Expected, Packet


def labels(c, axis, outer):
    return [r for r in c["core.array_labels"] if (r["axis_index"], r["depends_on_position_index"]) == (axis, outer)]


def axis_without_form(c):
    for field in ORDER_ONLY:
        del c["core.array_dimensions"][2][field]


def axis_with_two_forms(c):
    c["core.array_dimensions"][2] |= {"clock_id": "imec_ap_s001", "origin_tick": 0, "step_tick_num": 1}


def label_naming_no_row(c):
    # A real name, numbered like any other, so only the per-kind anti-join sees it names nothing.
    labels(c, 1, 0)[0]["label_id"] = "elec_009"


def label_on_unlabelled_axis(c):
    c["core.array_labels"].append({**labels(c, 1, 0)[0], "axis_index": 2})


def label_missing(c):
    # The padding row goes, not the label: a null label still declares its position.
    c["core.array_labels"].remove(labels(c, 1, 1)[-1])


def chained_dependency(c):
    # Its labels repeat at each of the sample axis's positions, so completeness still holds.
    c["core.array_dimensions"][0]["depends_on_axis_index"] = 2
    units = labels(c, 0, 0)
    c["core.array_labels"] += [
        {**r, "depends_on_position_index": k} for k in range(1, LABELLED_SHAPE[2]) for r in units
    ]


def independent_label_off_zero(c):
    c["core.array_labels"].append({**labels(c, 0, 0)[0], "depends_on_position_index": 1})


def one_row_two_positions(c):
    first, second, *_ = labels(c, 1, 0)
    second["label_id"] = first["label_id"]


def label_beyond_axis(c):
    c["core.array_labels"].append({**labels(c, 1, 1)[-1], "position_index": LABELLED_SHAPE[1]})


def dependent_axis_unlabelled(c):
    c["core.array_dimensions"][2]["depends_on_axis_index"] = 0


def label_outside_core(c):
    # Null labels name no row, so nothing but the resource's class is wrong.
    c["core.array_dimensions"][0]["coordinate_resource"] = "analysis.array_assets"
    for r in labels(c, 0, 0):
        r["label_id"] = None


#: Part 03 §6.3's labelled axes: one packet that pads, and one per rule a label or axis breaks.
AXIS_PACKETS = (
    Packet("padded_labels", with_waveform()),
    Packet(
        "axis_without_form",
        with_waveform(axis_without_form),
        Expected("error", "core.array_dimensions.one_coordinate_form"),
    ),
    Packet(
        "axis_with_two_forms",
        with_waveform(axis_with_two_forms),
        Expected("error", "core.array_dimensions.one_coordinate_form"),
    ),
    Packet(
        "label_naming_no_row",
        with_waveform(label_naming_no_row),
        Expected("error", "core.array_dimensions.coordinate_resource.core_electrodes_resolves"),
    ),
    Packet(
        "label_on_unlabelled_axis",
        with_waveform(label_on_unlabelled_axis),
        Expected("error", "core.array_dimensions.coordinate_resource.specialised_row_has_kind"),
    ),
    Packet("label_missing", with_waveform(label_missing), Expected("error", "array.label_missing")),
    Packet(
        "chained_dependency",
        with_waveform(chained_dependency),
        Expected("error", "core.array_dimensions.dependency_not_chained"),
    ),
    Packet(
        "independent_label_off_zero",
        with_waveform(independent_label_off_zero),
        Expected("error", "core.array_labels.independent_depends_on_position_zero"),
    ),
    Packet(
        "one_row_two_positions",
        with_waveform(one_row_two_positions),
        Expected("error", "core.array_labels.one_position_per_row"),
    ),
    Packet(
        "label_beyond_axis",
        with_waveform(label_beyond_axis),
        Expected("error", "array.label_position_out_of_range"),
    ),
    Packet(
        "dependent_axis_unlabelled",
        with_waveform(dependent_axis_unlabelled),
        Expected("error", "core.array_dimensions.dependent_axis_labelled"),
    ),
    Packet(
        "label_outside_core",
        with_waveform(label_outside_core),
        Expected("error", "core.array_dimensions.coordinate_resource_is_core"),
    ),
    Packet(
        "array_without_dimension_names",
        with_waveform(dimension_names=None),
        Expected("error", "array.dimension_names"),
    ),
)
