import copy

from escapewheel_reader.profile import (
    check_physical_profile,
    interface_for,
    physical_profile,
    physical_profile_schema,
    variant_for_zarr_format,
)


def test_bundled_profile_derives_every_logical_interface():
    assert interface_for("table") == "parquet"
    assert interface_for("dense_array") == "zarr"
    assert interface_for("opaque") is None


def test_bundled_profile_is_checked_once_and_selects_variants():
    assert physical_profile() is physical_profile()
    assert variant_for_zarr_format(3)["ownership"] == ["packet", "external"]
    assert variant_for_zarr_format(2)["ownership"] == ["external"]


def test_generic_checker_rejects_cross_member_drift():
    descriptor = copy.deepcopy(physical_profile())
    descriptor["kind_interfaces"]["table"] = "missing"
    errors = check_physical_profile(
        descriptor,
        physical_profile_schema(),
        logical_kinds={"table", "dense_array", "opaque"},
        logical_standard="escapewheel-logical-v0.1",
    )
    assert any("undeclared interface" in error for error in errors)
    assert any("not referenced" in error for error in errors)


_V3_FLOOR = "interfaces/zarr/variants/v3/reader_floor"


def _check(descriptor):
    return check_physical_profile(descriptor, physical_profile_schema())


def _v3_floor(descriptor):
    return descriptor["interfaces"]["zarr"]["variants"]["v3"]["reader_floor"]


def test_the_schema_accepts_the_v3_floor_of_patterns_and_sharding():
    """Part 03 §6.4 states the descriptor's v3 floor exactly."""
    floor = _v3_floor(physical_profile())
    assert floor["codec_sequences"][-1] == [{"name": "bytes"}, {"name": "blosc", "configuration": {"cname": "zstd"}}]
    assert floor["sharding"]["index_location"] == "end"
    assert physical_profile()["$schema"] == physical_profile_schema()["$id"]
    assert physical_profile_schema()["$id"].endswith("/physical-profile/0.2.0")
    assert _check(copy.deepcopy(physical_profile())) == ()


def test_the_schema_admits_configuration_only_on_blosc():
    descriptor = copy.deepcopy(physical_profile())
    _v3_floor(descriptor)["codec_sequences"][2][1]["configuration"] = {"cname": "zstd"}
    assert any(error.startswith(_V3_FLOOR) for error in _check(descriptor))


def test_the_schema_rejects_an_unknown_pattern_member():
    descriptor = copy.deepcopy(physical_profile())
    _v3_floor(descriptor)["codec_sequences"][0][0]["endian"] = "little"
    assert any(error.startswith(_V3_FLOOR) for error in _check(descriptor))


def test_the_checker_rejects_a_descriptor_naming_the_old_schema():
    descriptor = copy.deepcopy(physical_profile())
    descriptor["$schema"] = "https://escapewheel.org/schemas/physical-profile/0.1.0"
    errors = _check(descriptor)
    assert "$schema does not name the supplied physical-profile schema" in errors
