"""The shape `reading` requires of a resource document a delivery carries."""

import pytest

from escapewheel_writer.reading import _refuses


@pytest.mark.parametrize(
    "extra",
    [
        pytest.param({"validation_state": "passed"}, id="validation_state"),
        pytest.param({"derived_from": ["core.sessions"]}, id="derived_from"),
        pytest.param({"processing_run_id": "run"}, id="processing_run_id"),
        pytest.param({"verified_at": "yesterday"}, id="malformed_date_time"),
    ],
)
def test_a_delivered_entry_carries_no_build_supplied_member(extra):
    """Part 12 §5: the delivered entry is the manifest entry less what the build supplies."""
    entry = {
        "resource_id": "core.lfp",
        "declaration_id": "core.array_asset_instances",
        "uri": "s3://bucket/lfp.zarr",
        "external": True,
    }
    assert _refuses({"resources": [entry]}) is None
    assert _refuses({"resources": [{**entry, **extra}]}) is not None
