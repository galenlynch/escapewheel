"""The manifest and the source document say what a commit put in place."""

import json

import pytest
from escapewheel_reader import check_sources

from escapewheel_writer import CommitRefused, PacketWriter
from tests.builders import array_asset_tables, commit_tables


def test_no_manifest_names_a_resource_that_is_not_in_place(tmp_path, registry, minimal):
    """Part 05 §6: a reader sees the previous manifest or the new one, never a partial one.

    The invariant is about visibility, not about the mechanism: whatever primitive publishes the
    manifest, every resource it names must already be at its final location. Checked by reading
    the committed manifest and demanding every packet-owned URI resolve.
    """
    root = tmp_path / "packet"
    writer = PacketWriter(registry, packet_id="p")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    writer.commit(root)

    manifest = json.loads((root / "packet.json").read_text())
    absent = [r["uri"] for r in manifest["resources"] if not r.get("external") and not (root / r["uri"]).exists()]
    assert not absent, f"the manifest names {absent}, which are not in place"


def test_a_refused_commit_publishes_no_manifest(tmp_path, registry, minimal):
    """Part 05 §6 again, from the other side: a failed commit leaves the previous state visible.

    Here there is no previous state, so nothing at all may be published -- a manifest naming
    resources that failed validation is the thing the ordering exists to prevent.
    """
    root = tmp_path / "packet"
    writer = PacketWriter(registry, packet_id="p")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    # A clock that names a parent it does not have: refused by the generated foreign key.
    writer.add(
        "core.clocks",
        [
            {
                "clock_id": "orphan",
                "session_id": "s1",
                "clock_name": "x",
                "origin": "sample 0",
                "parent_clock_id": "nowhere",
            }
        ],
    )
    with pytest.raises(CommitRefused):
        writer.commit(root)
    assert not (root / "packet.json").exists()


def test_a_referenced_source_reaches_the_default_document(tmp_path, registry, minimal):
    """Part 04 §5.5: written at the packet root, and not declared as a resource."""
    from escapewheel_writer.bindings import ExternalArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    for resource_id, records in array_asset_tables("lfp0").items():
        writer.add(resource_id, records)
    writer.declare_source("raw_nwb", "file:///mnt/Data/ephys/session.nwb")
    writer.reference_array(
        "core.probe0.lfp",
        ExternalArray(
            array_asset_id="lfp0",
            declaration_id="core.array_asset_instances",
            uri="processing/ecephys/LFP/data",
            source="raw_nwb",
            physical_profile="zarr_v2",
        ),
    )
    writer.commit(root)

    document = json.loads((root / "sources.json").read_text())
    assert not check_sources(document)
    assert document["sources_standard_version"] == "escapewheel-sources-v0.1"
    assert document["sources"]["raw_nwb"]["uri"] == "file:///mnt/Data/ephys/session.nwb"

    manifest = json.loads((root / "packet.json").read_text())
    entry = next(r for r in manifest["resources"] if r["resource_id"] == "core.probe0.lfp")
    assert entry["source"] == "raw_nwb"
    assert entry["uri"] == "processing/ecephys/LFP/data"
    # Not a packet resource: nothing in the manifest names it, which is what keeps Part 04 §5.1's
    # immutability off it and lets a moved mirror be corrected in place.
    assert not any(r.get("uri") == "sources.json" for r in manifest["resources"])


def test_no_source_means_no_document(tmp_path, registry, minimal):
    """A document locating nothing is worse than none: it answers a lookup it should not."""
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    assert not (root / "sources.json").exists()


def _referencing(writer, array_asset_id, source, uri):
    """Reference `array_asset_id`'s data within `source`, read at `uri`, with the rows it needs."""
    from escapewheel_writer.bindings import ExternalArray

    tables = array_asset_tables(array_asset_id)
    tables["core.array_assets"][0]["array_asset_name"] = array_asset_id
    for resource_id, records in tables.items():
        writer.add(resource_id, [{"session_id": "s001", **record} for record in records])
    writer.declare_source(source, uri)
    writer.reference_array(
        f"core.{array_asset_id}.lfp",
        ExternalArray(
            array_asset_id=array_asset_id,
            declaration_id="core.array_asset_instances",
            uri="processing/ecephys/LFP/data",
            source=source,
            physical_profile="zarr_v2",
        ),
    )


def test_an_amendment_writes_the_default_document(tmp_path, registry, minimal):
    """Part 04 §5.5: an amendment that first references a source locates it as a build would."""
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    writer = PacketWriter(registry, packet_id=root.name)
    _referencing(writer, "lfp0", "raw_nwb", "file:///mnt/Data/ephys/session.nwb")
    assert writer.amend(root).passed
    document = json.loads((root / "sources.json").read_text())
    assert not check_sources(document)
    assert document["sources"] == {"raw_nwb": {"uri": "file:///mnt/Data/ephys/session.nwb"}}


def test_an_amendment_leaves_the_document_the_root_holds(tmp_path, registry, minimal):
    """Part 05 §6 refuses a promotion onto a path that exists, so the document is not rewritten."""
    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    _referencing(writer, "lfp0", "raw_nwb", "file:///mnt/Data/ephys/session.nwb")
    writer.commit(root)
    before = (root / "sources.json").read_bytes()
    amending = PacketWriter(registry, packet_id=root.name)
    _referencing(amending, "lfp1", "other_nwb", "file:///mnt/Data/ephys/other.nwb")
    assert amending.amend(root).passed
    assert (root / "sources.json").read_bytes() == before
