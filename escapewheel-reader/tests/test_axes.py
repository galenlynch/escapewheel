"""Describing a dense array's axes and scaling from the packet's tables (Part 02 §12.11)."""

from fractions import Fraction

import numpy as np
import pytest
from packet_fixture import CLOCK_PROBE, SESSION

from escapewheel_reader.axes import LabelledAxis, NumericAxis, Scaling, TickAxis, describe
from escapewheel_reader.errors import AxisFault, UnresolvableAxis

from .conftest import LFP, WAVE


def _axis(rows, resource_id, axis):
    (row,) = [r for r in rows[resource_id] if r["array_asset_id"] == WAVE and r["axis_index"] == axis]
    return row


# -- labels --------------------------------------------------------------------------------


def test_a_dependent_axis_names_each_units_own_contacts(array_packet):
    """Channel position 1 is the first unit's contact 102 and the second's 101."""
    channel = describe(array_packet(), "core.waveform_mean").axes[1].coordinates
    assert isinstance(channel, LabelledAxis)
    assert (channel.resource_id, channel.key, channel.depends_on, channel.shape) == (
        "core.electrodes",
        "electrode_id",
        0,
        (2, 3),
    )
    assert channel.rows["depends_on_position_index"].to_pylist() == [0, 0, 0, 1, 1, 1]
    assert channel.rows["electrode_name"].to_pylist() == ["e102", "e100", "e103", "e101", "e103", None]


def test_padding_is_masked_and_not_filled(array_packet):
    """Any fill is a label like the others, so only the mask says the last position is no contact."""
    channel = describe(array_packet(), "core.waveform_mean").axes[1].coordinates
    assert isinstance(channel, LabelledAxis)
    labels = channel.labels()
    assert labels.tolist() == [[102, 100, 103], [101, 103, None]]
    assert labels.mask.tolist() == [[False, False, False], [False, False, True]]


def test_an_independent_axis_reads_its_own_array_in_position_order(array_packet):
    """The LFP's labels are stored reversed among the waveform's, which name the same electrodes."""
    channel = describe(array_packet(), "core.lfp").axes[1].coordinates
    assert isinstance(channel, LabelledAxis)
    assert channel.depends_on is None and channel.shape == (3,)
    assert channel.rows.column_names[:2] == ["position_index", "electrode_id"]
    assert channel.labels().tolist() == [100, 101, 102]


def test_an_analysis_array_numbered_like_a_core_one_reads_its_own_labels(array_packet):
    """`analysis.unit_rates` and `core.lfp` are both array 31, and each keeps its labels in its own table."""
    packet = array_packet()
    unit = describe(packet, "analysis.unit_rates").axes[0].coordinates
    assert isinstance(unit, LabelledAxis)
    assert (unit.resource_id, unit.key, unit.labels().tolist()) == ("core.units", "unit_id", [12, 11])
    channel = describe(packet, "core.lfp").axes[1].coordinates
    assert isinstance(channel, LabelledAxis)
    assert channel.labels().tolist() == [100, 101, 102]


def test_a_missing_label_is_refused(array_packet):
    """Padding is a row with a null label, so a position with no row at all is a gap, not padding."""

    def drop_padding(rows):
        rows["core.array_labels"] = [r for r in rows["core.array_labels"] if r["label_id"] is not None]

    with pytest.raises(UnresolvableAxis) as refused:
        describe(array_packet(drop_padding), "core.waveform_mean")
    assert refused.value.reason is AxisFault.LABEL_COUNT


def test_a_label_naming_no_row_is_refused(array_packet):
    def unknown_contact(rows):
        (row,) = [r for r in rows["core.array_labels"] if r["array_asset_id"] == WAVE and r["label_id"] == 101]
        row["label_id"] = 999

    with pytest.raises(UnresolvableAxis) as refused:
        describe(array_packet(unknown_contact), "core.waveform_mean")
    assert refused.value.reason is AxisFault.LABEL_UNMATCHED


def test_a_dependency_on_a_dependent_axis_is_refused(array_packet):
    """The unit axis depending on the channel axis leaves neither to decide the other's labels."""

    def mutual(rows):
        _axis(rows, "core.array_dimensions", 0)["depends_on_axis_index"] = 1

    with pytest.raises(UnresolvableAxis) as refused:
        describe(array_packet(mutual), "core.waveform_mean")
    assert refused.value.reason is AxisFault.DEPENDENCY_CHAIN


# -- regular axes and forms ----------------------------------------------------------------


def test_a_rational_step_is_not_rounded(array_packet):
    """937.5 ticks per sample puts every other sample between ticks."""
    time = describe(array_packet(), "core.lfp").axes[0].coordinates
    assert isinstance(time, TickAxis)
    assert time.clock_id == CLOCK_PROBE
    assert time.ticks(np.arange(4)).tolist() == [1000, 1937.5, 2875, 3812.5]


def test_a_whole_step_gives_integer_ticks():
    """A tick is an integer wherever the step allows, so an adapter can index by it exactly."""
    ticks = TickAxis(clock_id=0, origin_tick=-500, step=Fraction(24)).ticks(np.arange(3))
    assert ticks.dtype == np.int64
    assert ticks.tolist() == [-500, -476, -452]


def test_a_numeric_axis_keeps_its_origin_step_and_unit(array_packet):
    sample = describe(array_packet(), "core.waveform_mean").axes[2].coordinates
    assert sample == NumericAxis(-1.0, 1.0, "{sample}")


@pytest.mark.parametrize(
    ("change", "forms"),
    [({"origin_value": None}, 0), ({"coordinate_resource": "core.units"}, 2)],
    ids=["none", "two"],
)
def test_an_axis_declaring_other_than_one_form_is_refused(array_packet, change, forms):
    """Nothing says which of two forms governs, and with none a position is only a number."""

    def reform(rows):
        _axis(rows, "core.array_dimensions", 2).update(change)

    with pytest.raises(UnresolvableAxis) as refused:
        describe(array_packet(reform), "core.waveform_mean")
    assert refused.value.reason is AxisFault.FORM_COUNT


def test_a_dependent_axis_without_labels_is_refused(array_packet):
    def sample_depends(rows):
        _axis(rows, "core.array_dimensions", 2)["depends_on_axis_index"] = 0

    with pytest.raises(UnresolvableAxis) as refused:
        describe(array_packet(sample_depends), "core.waveform_mean")
    assert refused.value.reason is AxisFault.DEPENDENCY_UNLABELLED


# -- scaling -------------------------------------------------------------------------------


def _per_channel(conversions, *, array_level=False):
    """Give the LFP's channels their own conversions, and drop its array-level one unless kept."""

    def edit(rows):
        rows["core.array_channels"] = [
            {
                "session_id": SESSION,
                "array_asset_id": LFP,
                "axis_index": 1,
                "channel_index": i,
                "unit": "uV",
                "conversion": c,
            }
            for i, c in conversions.items()
        ]
        if not array_level:
            (asset,) = [r for r in rows["core.array_assets"] if r["array_asset_id"] == LFP]
            asset.update(unit=None, conversion=None, offset=None)

    return edit


def test_scaling_declared_on_the_array_is_one_pair(array_packet):
    """Stored 3 becomes 3 * 2.0 + 0.5 uV at every position."""
    scaling = describe(array_packet(), "core.lfp").scaling
    assert scaling is not None
    assert (scaling.unit, scaling.conversion, scaling.offset, scaling.axis) == ("uV", 2.0, 0.5, None)


def test_scaling_declared_per_channel_runs_along_the_channel_axis(array_packet):
    """Each channel's own conversion in position order, an absent offset adding nothing, and none for the
    analysis array sharing the LFP's number."""
    packet = array_packet(_per_channel({2: 3.0, 0: 1.0, 1: 2.0}))
    scaling = describe(packet, "core.lfp").scaling
    assert scaling is not None
    assert scaling.axis == 1 and scaling.unit == ("uV", "uV", "uV")
    assert scaling.conversion.tolist() == [1.0, 2.0, 3.0]  # type: ignore[union-attr]
    assert scaling.offset.tolist() == [0.0, 0.0, 0.0]  # type: ignore[union-attr]
    assert describe(packet, "analysis.unit_rates").scaling is None


def test_no_declared_scaling_is_none(array_packet):
    """Nothing to apply, and no guess at a unit."""
    assert describe(array_packet(), "core.waveform_mean").scaling is None


def test_a_unit_without_a_conversion_is_already_physical(array_packet):
    """The unit still has to reach the caller, or rates in Hz read as unitless numbers."""

    def in_hertz(rows):
        rows["analysis.array_assets"][0]["unit"] = "Hz"

    scaling = describe(array_packet(in_hertz), "analysis.unit_rates").scaling
    assert scaling == Scaling("Hz", 1.0, 0.0)


def test_scaling_at_both_levels_is_refused(array_packet):
    """Two statements of one relation, and nothing says which governs."""
    packet = array_packet(_per_channel({0: 1.0, 1: 2.0, 2: 3.0}, array_level=True))
    with pytest.raises(UnresolvableAxis) as refused:
        describe(packet, "core.lfp")
    assert refused.value.reason is AxisFault.SCALING_LEVELS


def test_an_array_unit_disagreeing_with_its_channels_is_refused(array_packet):
    """Two statements of the values' unit, and nothing says which holds."""
    edit = _per_channel({0: 1.0, 1: 2.0, 2: 3.0})

    def in_millivolts(rows):
        edit(rows)
        (asset,) = [r for r in rows["core.array_assets"] if r["array_asset_id"] == LFP]
        asset["unit"] = "mV"

    with pytest.raises(UnresolvableAxis) as refused:
        describe(array_packet(in_millivolts), "core.lfp")
    assert refused.value.reason is AxisFault.SCALING_UNIT_DISAGREES


def test_scaling_some_channels_is_refused(array_packet):
    """The middle channel has no conversion, so its values have no physical unit."""
    with pytest.raises(UnresolvableAxis) as refused:
        describe(array_packet(_per_channel({0: 1.0, 2: 3.0})), "core.lfp")
    assert refused.value.reason is AxisFault.SCALING_COVERAGE
