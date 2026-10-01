from escapewheel_reader.profile import (
    PROFILE_ID,
    interface_for,
    physical_profile,
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


def test_the_profile_id_is_the_one_the_bundled_descriptor_declares():
    """The descriptor is found by the ID and states it, so the two cannot name different profiles."""
    assert physical_profile()["id"] == PROFILE_ID
