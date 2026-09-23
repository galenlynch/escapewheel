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
