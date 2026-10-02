"""A sidecar is listed by `core.sidecars` and resolved by its resource ID, as any catalogued resource is."""

import copy
import json

import pyarrow as pa
from packet_fixture import CORE_REGISTRY, UNREAD_DIGEST, install_registry, read_registry, resource_entry, write_table

from escapewheel_reader import open_packet

SIDECARS = ("core.sidecars", "core.sidecar_scopes", "core.sidecar_instances")
PROTOCOL = "https://example.org/protocols/surgery.pdf"


def _with_sidecars(root):
    """Bind core's sidecar declarations, list a packet-owned README and a referenced protocol, scope one."""
    full = json.loads(CORE_REGISTRY.read_text())
    registry = read_registry(root)
    for resource_id in SIDECARS:
        registry["resources"][resource_id] = copy.deepcopy(full["resources"][resource_id])
    install_registry(root, registry)
    listed = pa.table(
        {
            "resource_id": ["core.protocol", "core.readme"],
            "sidecar_type": [None, None],
            "media_type": [None, "text/markdown"],
            "description": ["Surgery protocol", None],
            "metadata": pa.array([None, None], type=pa.string()),
        }
    )
    scopes = pa.table({"resource_id": ["core.protocol"], "scope_kind": ["core.sessions"], "scope": ["1"]})
    readme = root / "opaque" / "core.readme" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# session\n")
    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"] += [
        resource_entry("core.sidecars", write_table(root, "sidecars", listed)),
        resource_entry("core.sidecar_scopes", write_table(root, "sidecar_scopes", scopes)),
        {
            **resource_entry("core.readme", "opaque/core.readme/README.md", digest=UNREAD_DIGEST),
            "declaration_id": "core.sidecar_instances",
        },
        {**resource_entry("core.protocol", PROTOCOL, external=True), "declaration_id": "core.sidecar_instances"},
    ]
    (root / "packet.json").write_text(json.dumps(manifest))
    return open_packet(root)


def test_the_reader_lists_both_tables_and_resolves_each_sidecar(packet_root):
    packet = _with_sidecars(packet_root)
    listed = {row["resource_id"]: row for row in packet.table("core.sidecars").to_pylist()}
    assert sorted(listed) == ["core.protocol", "core.readme"]
    assert packet.table("core.sidecar_scopes").to_pylist() == [
        {"resource_id": "core.protocol", "scope_kind": "core.sessions", "scope": "1"}
    ]
    for resource_id in listed:
        resource = packet.resource(resource_id)
        assert (resource.kind, resource.declaration_id) == ("opaque", "core.sidecar_instances")
    assert packet.path("core.readme").read_text() == "# session\n"
    assert packet.resource("core.protocol").entry["external"] is True
