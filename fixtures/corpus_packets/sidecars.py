"""Packets listing sidecars: catalog rows, scope rows, and the payloads and references they bind."""

from pathlib import Path

from .opaque import owned_opaque
from .record import Build, Expected, Packet
from .registry import EXTENSION
from .session import content
from .subsets import without_extracellular
from .writing import edit_manifest, write_packet

INSTANCES = "core.sidecar_instances"

#: A fixture-local extension whose one table a scope can name: its key is one string column, which
#: a scope's value matches as it stands (Part 02 §8.3).
LAB_RECORDS = {
    "$schema": EXTENSION["$schema"],
    "registry_id": "lab_records",
    "registry_version": "0.1.0",
    "logical_standard_version": EXTENSION["logical_standard_version"],
    "rule_language": EXTENSION["rule_language"],
    "extension_id": "lab_records",
    "resources": {
        "lab_records.surgeries": {
            "content_class": "extension",
            "kind": "table",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "optional",
            "table": {
                "columns": [
                    {
                        "name": "surgery_name",
                        "type": "string",
                        "presence": "required",
                        "role": "data",
                        "vocabulary": "free",
                        "description": "The lab's name for the surgery.",
                    },
                    {
                        "name": "procedure",
                        "type": "string",
                        "presence": "nullable",
                        "role": "data",
                        "vocabulary": "free",
                        "description": "What was done.",
                    },
                ],
                "primary_key": ["surgery_name"],
                "references": [],
                "rules": [],
                "amendment_groups": [],
            },
        }
    },
}
PROTOCOL = "https://protocols.example.org/surgery.pdf"

#: One row each: a null type and media type, a registered media type, and a type and media type
#: that no list holds.
LISTED = [
    {"resource_id": "core.readme", "sidecar_type": None, "media_type": None, "description": None, "metadata": None},
    {
        "resource_id": "core.viewer_state",
        "sidecar_type": None,
        "media_type": "application/json",
        "description": "Saved state of a viewer",
        "metadata": None,
    },
    {
        "resource_id": "core.surgery_protocol",
        "sidecar_type": "surgery_protocol",
        "media_type": "application/vnd.example.unlisted",
        "description": "Surgery protocol",
        "metadata": None,
    },
]

#: The README is about nothing in particular, the viewer state about the subject, and the protocol
#: about both sessions and a surgery the lab's extension records.
SCOPES = [
    {"resource_id": "core.viewer_state", "scope_kind": "core.subjects", "scope": "m001"},
    {"resource_id": "core.surgery_protocol", "scope_kind": "core.sessions", "scope": "s001"},
    {"resource_id": "core.surgery_protocol", "scope_kind": "core.sessions", "scope": "s002"},
    {"resource_id": "core.surgery_protocol", "scope_kind": "lab_records.surgeries", "scope": "implant"},
]

#: The second session the protocol is about; it records nothing else.
SECOND_SESSION = {
    "session_id": "s002",
    "subject_id": "m001",
    "session_start_time": None,
    "reference_clock_id": None,
}


def referenced(resource_id: str) -> dict:
    """A referenced sidecar's entry: nothing reached, so no digest or size (Part 04 §5.2)."""
    return {
        "resource_id": resource_id,
        "declaration_id": INSTANCES,
        "uri": PROTOCOL,
        "validation_state": "not_run",
        "external": True,
    }


def sidecars(mutate=None, *, edit=None, scopes=True, base=None) -> Build:
    """A build of the valid session listing `LISTED` and, where `scopes`, `SCOPES`.

    `mutate` edits the rows and `edit` the manifest; `base` edits the session's own rows first.
    """

    def build(out: Path) -> None:
        c = content()
        if base is not None:
            base(c)
        c["core.sessions"].append(dict(SECOND_SESSION, session_start_time=c["core.sessions"][0]["session_start_time"]))
        c["core.sidecars"] = [dict(row) for row in LISTED]
        c["lab_records.surgeries"] = [{"surgery_name": "implant", "procedure": "headbar and craniotomy"}]
        if scopes:
            c["core.sidecar_scopes"] = [dict(row) for row in SCOPES]
        if mutate is not None:
            mutate(c)
        write_packet(out, c, extensions=(LAB_RECORDS,))
        entries = [
            owned_opaque(out, "core.readme", "README.md", b"# s001\n", declaration_id=INSTANCES),
            owned_opaque(
                out, "core.viewer_state", "viewer", {"state.json": b'{"zoom": 2}\n'}, declaration_id=INSTANCES
            ),
            referenced("core.surgery_protocol"),
        ]
        edit_manifest(out, lambda m: m["resources"].extend(entries))
        if edit is not None:
            edit_manifest(out, edit)

    return build


def scoped(row: dict):
    """Add one scope row to the protocol's."""

    def mutate(c):
        c["core.sidecar_scopes"].append({"resource_id": "core.surgery_protocol", **row})

    return mutate


def listed_twice(c):
    c["core.sidecars"].append(dict(LISTED[0], description="another"))


def unbound_row(c):
    c["core.sidecars"].append(dict(LISTED[0], resource_id="core.notes"))


def unbound_entry(manifest):
    manifest["resources"].append(dict(referenced("core.notes"), uri="https://protocols.example.org/notes.pdf"))


def with_lineage(manifest):
    entry = next(e for e in manifest["resources"] if e["resource_id"] == "core.readme")
    entry["derived_from"] = ["core.sessions"]


def scope_unlisted(c):
    c["core.sidecar_scopes"].append({"resource_id": "core.notes", "scope_kind": "core.sessions", "scope": "s001"})


#: Sidecars (Part 02 §12.10): two packets that conform and one per rule a sidecar or scope breaks.
SIDECAR_PACKETS = (
    Packet("sidecars", sidecars(), checksums=True),
    Packet("sidecars_without_scopes", sidecars(scopes=False), checksums=True),
    Packet("sidecar_row_unbound", sidecars(unbound_row), Expected("error", "packet.resource.catalog_row_binding")),
    Packet(
        "sidecar_entry_unbound", sidecars(edit=unbound_entry), Expected("error", "packet.resource.catalog_row_binding")
    ),
    Packet("sidecar_listed_twice", sidecars(listed_twice), Expected("error", "core.sidecars.primary_key_unique")),
    Packet(
        "sidecar_scope_unlisted",
        sidecars(scope_unlisted),
        Expected("error", "core.sidecar_scopes.resource_id_resolves"),
    ),
    Packet(
        "sidecar_scope_undeclared_table",
        sidecars(scoped({"scope_kind": "lab.surgeries", "scope": "1"})),
        Expected("error", "core.sidecar_scopes.scope_kind.kind_declared"),
    ),
    Packet(
        "sidecar_scope_uncarried_table",
        sidecars(scoped({"scope_kind": "core.probes", "scope": "probe0"}), base=without_extracellular),
        Expected("error", "core.sidecar_scopes.scope_kind.kind_declared"),
    ),
    Packet(
        "sidecar_scope_composite_key",
        sidecars(scoped({"scope_kind": "core.coordinate_frames", "scope": "ccf"})),
        Expected("error", "core.sidecar_scopes.scope_kind.key_fits_paired_value"),
    ),
    Packet(
        "sidecar_scope_absent_row",
        sidecars(scoped({"scope_kind": "core.subjects", "scope": "m999"})),
        Expected("error", "core.sidecar_scopes.scope_kind.core_subjects_resolves"),
    ),
    Packet(
        "sidecar_scope_null",
        sidecars(scoped({"scope_kind": "core.sessions", "scope": None})),
        Expected("error", "core.sidecar_scopes.scope.not_null"),
    ),
    Packet(
        "sidecar_with_lineage", sidecars(edit=with_lineage), Expected("error", "packet.resource.derived_from_forbidden")
    ),
)
