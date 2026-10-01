"""Packets about a device's detail table."""

from .record import Expected, Packet
from .registry import EXTENSION
from .session import variant

#: A fixture-local extension declaring a detail table of `core.devices.device_kind`, which core
#: may not declare (Part 02 §8.3).
RIG_EXTENSION = {
    "$schema": EXTENSION["$schema"],
    "registry_id": "rig",
    "registry_version": "0.1.0",
    "logical_standard_version": EXTENSION["logical_standard_version"],
    "rule_language": EXTENSION["rule_language"],
    "extension_id": "rig",
    "resources": {
        "rig.neuropixels": {
            "content_class": "extension",
            "kind": "table",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "optional",
            "table": {
                "columns": [
                    {
                        "name": "session_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "Session ID.",
                    },
                    {
                        "name": "device_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "The probe this row describes.",
                    },
                ],
                "primary_key": ["device_id"],
                "references": [
                    {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]},
                    {
                        "columns": ["device_id"],
                        "resource": "core.devices",
                        "resource_columns": ["device_id"],
                        "specialises": "core.devices.device_kind",
                    },
                ],
                "rules": [],
                "amendment_groups": [["device_id"]],
            },
        }
    },
}


def probe_of_kind(kind: str | None):
    """Name `kind` as the probe's `device_kind`, and describe the probe in `rig.neuropixels`."""

    def mutate(c):
        c["core.devices"][0]["device_kind"] = kind
        c["rig.neuropixels"] = [{"session_id": "s001", "device_id": "imec0"}]

    return mutate


RIG = (RIG_EXTENSION,)

#: Part 02 §8.3's kind check on a detail table whose discriminator resolves `optional`.
DEVICE_PACKETS = (
    Packet("device_detail", variant(probe_of_kind("rig.neuropixels"), extensions=RIG)),
    Packet(
        "device_detail_unkinded",
        variant(probe_of_kind(None), extensions=RIG),
        Expected("error", "rig.neuropixels.device_id.names_a_row_of_its_kind", registry="rig"),
    ),
    Packet(
        "device_detail_other_kind",
        variant(probe_of_kind("core.probes"), extensions=RIG),
        Expected("error", "rig.neuropixels.device_id.names_a_row_of_its_kind", registry="rig"),
    ),
)
