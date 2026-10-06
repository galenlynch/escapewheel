"""Arrays a packet writes or references reach it with their catalog rows bound."""

import json

import pyarrow.parquet as pq
import pytest
from escapewheel_validator import Level, check_table

from escapewheel_writer import CommitRefused, PacketWriter
from escapewheel_writer.errors import (
    UsageError,
    UsageFault,
)
from tests.builders import array_asset_tables, waveform_values


def test_an_array_is_written_as_zarr_v3(tmp_path, registry, minimal):
    from escapewheel_writer.bindings import StagedArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    for resource_id, records in array_asset_tables().items():
        writer.add(resource_id, records)
    values = waveform_values()
    writer.add_array(
        "core.waveform_means",
        StagedArray(
            values=values,
            resource_id="core.waveform_means",
            declaration_id="core.array_asset_instances",
            array_asset_id="wf",
            chunks=(1, 4, 10),
            shard=(4, 4, 10),
        ),
    )
    report = writer.commit(root)
    assert report.passed
    entry = next(
        r
        for r in json.loads((root / "packet.json").read_text())["resources"]
        if r["resource_id"] == "core.waveform_means"
    )
    assert entry["declaration_id"] == "core.array_asset_instances"
    assert "physical_profile" not in entry
    assert "codecs" not in entry
    assert (root / "arrays" / "core" / "waveform_means.zarr").is_dir()


def test_the_array_reads_back_identically(tmp_path, registry, minimal):
    import numpy as np
    import zarr

    from escapewheel_writer.bindings import StagedArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    for resource_id, records in array_asset_tables().items():
        writer.add(resource_id, records)
    values = waveform_values()
    writer.add_array(
        "core.waveform_means",
        StagedArray(
            values=values,
            resource_id="core.waveform_means",
            declaration_id="core.array_asset_instances",
            array_asset_id="wf",
            chunks=(1, 4, 10),
            shard=(4, 4, 10),
        ),
    )
    writer.commit(root)
    back = zarr.open_array(str(root / "arrays" / "core" / "waveform_means.zarr"), mode="r")
    assert np.array_equal(np.asarray(back[:]), values)


def test_a_written_array_carries_its_axes_names(tmp_path, registry, minimal):
    """Part 03 §6.4: the names come from `core.array_dimensions`, so no source has to repeat them."""
    import zarr

    from escapewheel_writer.bindings import StagedArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in {**minimal, **array_asset_tables()}.items():
        writer.add(resource_id, records)
    writer.add_array(
        "core.waveform_means",
        StagedArray(
            values=waveform_values(),
            resource_id="core.waveform_means",
            declaration_id="core.array_asset_instances",
            array_asset_id="wf",
            chunks=(1, 4, 10),
            shard=(4, 4, 10),
        ),
    )
    writer.commit(root)
    back = zarr.open_array(str(root / "arrays" / "core" / "waveform_means.zarr"), mode="r")
    assert back.metadata.dimension_names == ("unit", "channel", "sample")


#: Each unit position's contacts, by name; a unit with fewer contacts than the axis is long pads.
CONTACTS = {0: ("e2", "e3", None), 1: ("e1", None, None)}


def _labelled_writer(registry, minimal, contacts=CONTACTS, electrodes=("e1", "e2", "e3")):
    """A writer holding an array whose channel axis depends on its unit axis (Part 02 §12.11)."""
    import numpy as np

    from escapewheel_writer.bindings import StagedArray

    tables = array_asset_tables()
    axes = tables["core.array_dimensions"]
    for axis in ("origin_value", "step_value", "coordinate_unit"):
        del axes[1][axis]
    axes[1] |= {"coordinate_resource": "core.electrodes", "depends_on_axis_index": 0}
    tables["core.electrodes"] = [{"session_id": "s001", "electrode_id": e} for e in electrodes]
    tables["core.array_labels"] = [
        {
            "session_id": "s001",
            "array_asset_id": "wf",
            "axis_index": 1,
            "depends_on_position_index": unit,
            "position_index": position,
            "label_id": name,
        }
        for unit, names in contacts.items()
        for position, name in enumerate(names)
    ]
    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in {**minimal, **tables}.items():
        writer.add(resource_id, records)
    values = np.zeros((len(contacts), 3, 4), dtype="int16")
    writer.add_array(
        "core.waveform_means",
        StagedArray(
            values=values,
            resource_id="core.waveform_means",
            declaration_id="core.array_asset_instances",
            array_asset_id="wf",
            chunks=(1, 3, 4),
            shard=(2, 3, 4),
        ),
    )
    return writer


def test_a_label_is_numbered_as_the_row_its_axis_names_and_padding_stays_null(tmp_path, registry, minimal):
    """A label holds the electrode's name, so it takes the number `core.electrodes` gives that name."""
    root = tmp_path / "s001"
    report = _labelled_writer(registry, minimal).commit(root)
    assert report.passed
    electrodes = pq.read_table(root / "tables/core/electrodes.parquet").to_pylist()
    number = {row["electrode_name"]: row["electrode_id"] for row in electrodes}
    labels = pq.read_table(root / "tables/core/array_labels.parquet").to_pylist()
    got = {(r["depends_on_position_index"], r["position_index"]): r["label_id"] for r in labels}
    assert got == {
        (unit, position): None if name is None else number[name]
        for unit, names in CONTACTS.items()
        for position, name in enumerate(names)
    }


def test_a_label_naming_no_row_refuses_the_commit(tmp_path, registry, minimal):
    """The name is numbered all the same, so only the generated anti-join can see it names nothing."""
    writer = _labelled_writer(registry, minimal, electrodes=("e1", "e2"))
    with pytest.raises(CommitRefused) as caught:
        writer.commit(tmp_path / "s001")
    failed = {f.check for f in caught.value.report.findings if f.level == Level.ERROR}
    assert failed == {
        check_table.paired_value_resolves("core.array_dimensions", "coordinate_resource", "core.electrodes").id
    }


def test_a_dependent_position_with_no_label_row_refuses_the_commit(tmp_path, registry, minimal):
    """Padding is a row whose label is null; a missing row leaves the position undeclared."""
    writer = _labelled_writer(registry, minimal, contacts={0: ("e2", "e3", None), 1: ("e1",)})
    with pytest.raises(CommitRefused) as caught:
        writer.commit(tmp_path / "s001")
    failed = {f.check for f in caught.value.report.findings if f.level == Level.ERROR}
    assert failed == {check_table.ARRAY_LABEL_MISSING.id}


def test_a_shard_that_is_not_whole_chunks_is_refused(tmp_path, registry, minimal):
    """A partial shard is not a regular chunk grid, which Part 03 §6.1 requires."""
    from escapewheel_writer.bindings import StagedArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    for resource_id, records in array_asset_tables().items():
        writer.add(resource_id, records)
    writer.add_array(
        "core.waveform_means",
        StagedArray(
            values=waveform_values(),
            resource_id="core.waveform_means",
            declaration_id="core.array_asset_instances",
            array_asset_id="wf",
            chunks=(3, 4, 10),
            shard=(4, 4, 10),
        ),
    )
    with pytest.raises(UsageError) as refused:
        writer.commit(root)
    assert refused.value.code is UsageFault.SHARD_MISFIT


def test_a_referenced_array_is_declared_external_and_copied_nowhere(tmp_path, registry, minimal):
    """Part 04 §5.1: the bytes stay where they are and the packet says where that is."""
    from escapewheel_writer.bindings import ExternalArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    for resource_id, records in array_asset_tables("probe.lfp").items():
        writer.add(resource_id, records)
    writer.reference_array(
        "core.probe.lfp",
        ExternalArray(
            array_asset_id="probe.lfp",
            declaration_id="core.array_asset_instances",
            uri="s3://bucket/lfp",
            physical_profile="zarr_v2",
            codecs=("blosc",),
            size_bytes=17,
        ),
    )
    assert writer.commit(root).passed
    entry = next(
        r for r in json.loads((root / "packet.json").read_text())["resources"] if r["resource_id"] == "core.probe.lfp"
    )
    assert entry["external"] is True
    assert "physical_profile" not in entry
    assert "codecs" not in entry
    assert entry["uri"] == "s3://bucket/lfp"
    assert entry["size_bytes"] == 17
    assert not (root / "arrays").exists(), "nothing was copied"


@pytest.mark.parametrize("uri", ["../lfp", "arrays/l fp", "arrays%2Flfp"])
def test_a_reference_neither_absolute_nor_relative_is_refused(tmp_path, registry, uri):
    """Part 03 §4: a uri without a scheme is a relative reference, and one no reader could decode is refused."""
    from escapewheel_writer.bindings import ExternalArray

    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in array_asset_tables("probe.lfp").items():
        writer.add(resource_id, records)
    with pytest.raises(UsageError) as refused:
        writer.reference_array(
            "core.probe.lfp",
            ExternalArray(array_asset_id="probe.lfp", declaration_id="core.array_asset_instances", uri=uri),
        )
    assert refused.value.code is UsageFault.URI_UNRESOLVABLE
    assert refused.value.where == "core.probe.lfp"


def test_an_external_reference_may_resolve_under_the_packet_root(tmp_path, registry):
    """Part 04 §5.1: external says who owns the bytes, not where they resolve, so a relative uri is kept."""
    from escapewheel_writer.bindings import ExternalArray

    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in array_asset_tables("probe.lfp").items():
        writer.add(resource_id, records)
    writer.reference_array(
        "core.probe.lfp",
        ExternalArray(array_asset_id="probe.lfp", declaration_id="core.array_asset_instances", uri="beside/l%c3%a9"),
    )
    assert writer._attachments.arrays["core.probe.lfp"].uri == "beside/l%C3%A9"


def test_a_referenced_codec_is_not_projected_into_the_manifest(tmp_path, registry, minimal):
    from escapewheel_writer.bindings import ExternalArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    for resource_id, records in array_asset_tables("probe.lfp").items():
        writer.add(resource_id, records)
    writer.reference_array(
        "core.probe.lfp",
        ExternalArray(
            array_asset_id="probe.lfp",
            declaration_id="core.array_asset_instances",
            uri="s3://bucket/lfp",
            physical_profile="zarr_v2",
            codecs=("blosc",),
        ),
    )
    writer.commit(root)
    manifest = json.loads((root / "packet.json").read_text())
    entry = next(r for r in manifest["resources"] if r["resource_id"] == "core.probe.lfp")
    assert "required_codecs" not in manifest
    assert "codecs" not in entry
