"""The physical-profile descriptor checker (Part 03 §2.1) and the overriding-order conditions (Part 03 §5.4)."""

import copy
import json

import pytest

from checkers.artifacts import ARTIFACTS
from checkers.descriptor import check_physical_profile, override_errors

SCHEMA = json.loads((ARTIFACTS / "physical_profile.schema.json").read_text())
DESCRIPTOR = json.loads((ARTIFACTS / "physical_profiles/escapewheel-portable-v0.1.json").read_text())
_V3_FLOOR = "interfaces/zarr/variants/v3/reader_floor"
_V2_FLOOR = "interfaces/zarr/variants/v2/reader_floor"


def _descriptor():
    return copy.deepcopy(DESCRIPTOR)


def _check(descriptor):
    return check_physical_profile(descriptor, SCHEMA)


def _v3_floor(descriptor):
    return descriptor["interfaces"]["zarr"]["variants"]["v3"]["reader_floor"]


def _v2_floor(descriptor):
    return descriptor["interfaces"]["zarr"]["variants"]["v2"]["reader_floor"]


def test_generic_checker_rejects_cross_member_drift():
    descriptor = _descriptor()
    descriptor["kind_interfaces"]["table"] = "missing"
    errors = check_physical_profile(
        descriptor,
        SCHEMA,
        logical_kinds={"table", "dense_array", "opaque"},
        logical_standard="escapewheel-logical-v0.1",
    )
    assert any("undeclared interface" in error for error in errors)
    assert any("not referenced" in error for error in errors)


def test_the_schema_accepts_the_v3_floor_of_patterns_and_sharding():
    """Part 03 §6.3 states the descriptor's v3 floor exactly."""
    floor = _v3_floor(DESCRIPTOR)
    assert floor["codec_sequences"][-1] == [{"name": "bytes"}, {"name": "blosc", "configuration": {"cname": "zstd"}}]
    assert floor["sharding"]["index_location"] == "end"
    assert DESCRIPTOR["$schema"] == SCHEMA["$id"]
    assert _check(_descriptor()) == ()


def test_the_schema_admits_configuration_only_on_blosc():
    descriptor = _descriptor()
    _v3_floor(descriptor)["codec_sequences"][2][1]["configuration"] = {"cname": "zstd"}
    assert any(error.startswith(_V3_FLOOR) for error in _check(descriptor))


def test_the_schema_rejects_an_unknown_pattern_member():
    descriptor = _descriptor()
    _v3_floor(descriptor)["codec_sequences"][0][0]["endian"] = "little"
    assert any(error.startswith(_V3_FLOOR) for error in _check(descriptor))


def test_the_checker_rejects_a_descriptor_naming_the_old_schema():
    descriptor = _descriptor()
    descriptor["$schema"] = "https://escapewheel.org/schemas/physical-profile/0.1.0"
    assert "$schema does not name the supplied physical-profile schema" in _check(descriptor)


def test_the_schema_identifier_is_0_4_0_and_a_0_3_0_descriptor_fails():
    """Part 03 §2.1 states the identifier the descriptor's `$schema` must name."""
    assert SCHEMA["$id"] == "https://escapewheel.org/schemas/physical-profile/0.4.0"
    descriptor = _descriptor()
    descriptor["$schema"] = "https://escapewheel.org/schemas/physical-profile/0.3.0"
    assert "$schema does not name the supplied physical-profile schema" in _check(descriptor)


def test_the_schema_accepts_the_v2_floor_of_patterns_and_byte_orders():
    """Part 03 §6.3 states the descriptor's v2 floor exactly."""
    assert _v2_floor(DESCRIPTOR) == {
        "metadata_patterns": [
            {"filters": None, "compressor": None},
            {"filters": None, "compressor": {"id": "zstd"}},
            {"filters": None, "compressor": {"id": "blosc", "cname": "zstd"}},
        ],
        "dtype_byte_orders": ["<", "|"],
    }
    assert _check(_descriptor()) == ()


@pytest.mark.parametrize(
    "byte_orders",
    [None, [], ["<", "="], ["<", "<"]],
    ids=["absent", "empty", "unknown-character", "repeated"],
)
def test_the_schema_requires_a_v2_floor_to_list_byte_order_characters(byte_orders):
    """Part 03 §6.3: one or more distinct members of `<`, `>` and `|`, and never omitted."""
    descriptor = _descriptor()
    if byte_orders is None:
        del _v2_floor(descriptor)["dtype_byte_orders"]
    else:
        _v2_floor(descriptor)["dtype_byte_orders"] = byte_orders
    assert any(error.startswith(_V2_FLOOR) for error in _check(descriptor))


def test_the_schema_admits_every_byte_order_character():
    descriptor = _descriptor()
    _v2_floor(descriptor)["dtype_byte_orders"] = ["<", ">", "|"]
    assert _check(descriptor) == ()


def test_the_schema_refuses_byte_orders_on_the_v3_floor():
    """Part 03 §6.3: a v3 array's byte order is its `bytes` codec's, which the v3 floor does not bound."""
    descriptor = _descriptor()
    _v3_floor(descriptor)["dtype_byte_orders"] = ["<", "|"]
    assert any(error.startswith(_V3_FLOOR) for error in _check(descriptor))


def test_the_table_interface_declares_the_overriding_orders():
    """Part 03 §5.4: the portable descriptor's one override, which the schema admits."""
    parquet = DESCRIPTOR["interfaces"]["parquet"]
    assert parquet["overriding_orders"] == {
        "analysis.spike_events": ["session_id", "clock_id", "time_bucket_tick", "unit_id", "t_tick"]
    }
    assert "ew-overriding-orders" in parquet["anchors"]


def test_overriding_orders_on_an_interface_not_storing_tables_is_refused():
    descriptor = _descriptor()
    descriptor["interfaces"]["zarr"]["overriding_orders"] = {"core.array_assets": ["session_id"]}
    assert _check(descriptor) == ("interface 'zarr' declares overriding_orders but does not store tables",)


SPIKES = {
    "columns": [
        {"name": "session_id"},
        {"name": "unit_id"},
        {"name": "t_tick"},
        {"name": "amplitude"},
        {"name": "clock_id", "determined_by": ["session_id"]},
        {"name": "time_bucket_tick", "determined_by": ["t_tick"]},
    ],
    "primary_key": ["session_id", "unit_id", "t_tick"],
}
OVERRIDE = ["session_id", "clock_id", "time_bucket_tick", "unit_id", "t_tick"]


def test_the_portable_override_is_consistent():
    assert override_errors(OVERRIDE, SPIKES) == []


@pytest.mark.parametrize(
    ("order", "table", "error"),
    [
        (OVERRIDE, None, "the core registry declares no such table"),
        ([*OVERRIDE, "spike_count"], SPIKES, "'spike_count' is not a column of the table"),
        (OVERRIDE[:-1], SPIKES, "key column 't_tick' is absent"),
        (
            ["session_id", "amplitude", "unit_id", "t_tick"],
            SPIKES,
            "'amplitude' precedes a key column and is not determined by the key",
        ),
        (["session_id", "unit_id", "t_tick"], SPIKES, "the order is the table's primary key's order"),
    ],
    ids=["undeclared-table", "undeclared-column", "missing-key-column", "undetermined-column", "key-order"],
)
def test_an_inconsistent_override_is_refused(order, table, error):
    assert override_errors(order, table) == [error]
