"""Build the example packet, and check that Part 08 shows its layout and manifest excerpt.

The packet is the conformance corpus's valid session written by the writer rather than by hand,
with every repository extension bound and one resource of each kind the corpus lacks: a
packet-owned array, an external array, a materialized analysis table, and a derived analysis
array. Part 08 carries its layout and excerpt as text, and this fails where they differ from what
the writer produces against the current registries, printing the text Part 08 should carry.

    python example.py
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
from escapewheel_writer import PacketWriter, materialize_spike_events
from escapewheel_writer.adapter import ExternalArray, StagedArray

ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "spec" / "parts" / "08_example_packet.md"
REGISTRY = json.loads((ROOT / "spec" / "artifacts" / "logical_schemas.json").read_text())
EXTENSIONS = {
    path.stem: json.loads(path.read_text())
    for path in sorted(
        [*(ROOT / "extensions").glob("*.json"), *(ROOT / "escapewheel-aind" / "extensions").glob("*.json")],
        key=lambda path: path.name,
    )
}

#: The session, as the corpus's valid packet carries it. Loaded by path because `fixtures/` is
#: not a package and its builder's module name says nothing outside that directory.
_spec = importlib.util.spec_from_file_location("corpus", ROOT / "fixtures" / "build.py")
assert _spec is not None and _spec.loader is not None
corpus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(corpus)

SESSION = "s001"

#: The array the packet owns, the one it references, and the one derived from its spikes.
OWNED, EXTERNAL, DERIVED = "core.waveform_mean", "core.probe0_lfp", "analysis.unit_rates"

#: The waveform array's channel axis, as long as the most contacts any unit has.
CHANNELS = 3

#: What the derived array and its catalog rows were computed from.
LINEAGE = ["core.spike_events", "core.units"]

#: The entries Part 08 §3 shows, one per kind of resource.
EXCERPT = ("core.units", OWNED, EXTERNAL, "analysis.spike_events", DERIVED)


def tables() -> dict[str, list[dict[str, Any]]]:
    """Every row the example adds, keyed by resource ID."""
    rows = corpus.content()
    rows["aind_unit_qc.metrics"] = [
        {"unit_id": 1, "num_spikes_used": 30, "presence_ratio": 0.98, "snr": 6.1, "isi_violations_ratio": 0.4},
        {"unit_id": 2, "num_spikes_used": 11, "presence_ratio": 0.81, "snr": 3.2, "isi_violations_ratio": 2.7},
    ]
    rows["core.array_assets"] = [
        {
            "array_asset_id": "waveform_mean",
            "array_asset_name": "mean waveform per unit",
            "semantic_type": "waveform_mean",
        },
        {
            "array_asset_id": "probe0_lfp",
            "array_asset_name": "probe0 LFP",
            "semantic_type": "extracellular_voltage",
            "band": "lfp",
        },
    ]
    wave, lfp = {"array_asset_id": "waveform_mean"}, {"array_asset_id": "probe0_lfp"}
    rows["core.array_dimensions"] = [
        {**wave, "axis_index": 0, "dimension_name": "unit", "coordinate_resource": "core.units"},
        {
            **wave,
            "axis_index": 1,
            "dimension_name": "channel",
            "coordinate_resource": "core.electrodes",
            "depends_on_axis_index": 0,
        },
        {
            **wave,
            "axis_index": 2,
            "dimension_name": "sample",
            "origin_value": -3.0,
            "step_value": 1.0,
            "coordinate_unit": "{sample}",
        },
        {
            **lfp,
            "axis_index": 0,
            "dimension_name": "time",
            "clock_id": "imec_ap_s001",
            "origin_tick": 0,
            "step_tick_num": 24,
        },
        {**lfp, "axis_index": 1, "dimension_name": "channel", "coordinate_resource": "core.electrodes"},
    ]
    # Each unit's contacts along the waveform's channel axis, padded with null to its length.
    contacts: dict[Any, list[Any]] = {}
    for link in rows["core.unit_electrodes"]:
        contacts.setdefault(link["unit_id"], []).append(link["electrode_id"])
    electrodes = [e["electrode_id"] for e in rows["core.electrodes"]]
    rows["core.array_labels"] = [
        *(
            {**wave, "axis_index": 0, "depends_on_position_index": 0, "position_index": k, "label_id": unit}
            for k, unit in enumerate(contacts)
        ),
        *(
            {**wave, "axis_index": 1, "depends_on_position_index": k, "position_index": j, "label_id": label}
            for k, held in enumerate(contacts.values())
            for j, label in enumerate(held + [None] * (CHANNELS - len(held)))
        ),
        *(
            {**lfp, "axis_index": 1, "depends_on_position_index": 0, "position_index": j, "label_id": e}
            for j, e in enumerate(electrodes)
        ),
    ]
    rows["analysis.array_assets"] = [
        {
            "array_asset_id": "unit_rates",
            "array_asset_name": "firing rate per unit per bin",
            "semantic_type": "binned_rate",
            "unit": "Hz",
        },
    ]
    rates = {"array_asset_id": "unit_rates"}
    rows["analysis.array_dimensions"] = [
        {**rates, "axis_index": 0, "dimension_name": "unit", "coordinate_resource": "core.units"},
        {
            **rates,
            "axis_index": 1,
            "dimension_name": "time_bin",
            "origin_value": 0.0,
            "step_value": 1.0,
            "coordinate_unit": "1",
        },
    ]
    rows["analysis.array_labels"] = [
        {**rates, "axis_index": 0, "depends_on_position_index": 0, "position_index": k, "label_id": unit}
        for k, unit in enumerate(contacts)
    ]
    return rows


def writer(
    rows: Mapping[str, list[dict[str, Any]]] | None = None,
    *,
    extensions: Mapping[str, Mapping[str, Any]] = EXTENSIONS,
    lineage: bool = True,
) -> PacketWriter:
    """A writer holding the example, ready to commit; `rows` and `lineage` let a test break it."""
    built = PacketWriter(REGISTRY, extensions=list(extensions.values()), packet_id=SESSION, session=SESSION)
    for resource_id, records in (tables() if rows is None else rows).items():
        built.add(resource_id, records)
    built.add_array(
        OWNED,
        StagedArray(
            values=np.arange(2 * CHANNELS * 10, dtype="int16").reshape(2, CHANNELS, 10),
            resource_id=OWNED,
            declaration_id="core.array_asset_instances",
            array_asset_id="waveform_mean",
            chunks=(1, CHANNELS, 10),
        ),
    )
    built.reference_array(
        EXTERNAL,
        ExternalArray(
            array_asset_id="probe0_lfp",
            declaration_id="core.array_asset_instances",
            uri="s3://example-bucket/s001/probe0_lfp.zarr",
            physical_profile="zarr_v2",
            codecs=("blosc",),
            size_bytes=402_053_057,
            verified_at="2026-08-20T16:00:00Z",
        ),
    )
    built.add_array(
        DERIVED,
        StagedArray(
            values=np.full((2, 30), 3.0, dtype="float32"),
            resource_id=DERIVED,
            declaration_id="analysis.array_asset_instances",
            array_asset_id="unit_rates",
            chunks=(2, 30),
        ),
    )
    if lineage:
        for resource_id in ("analysis.array_assets", "analysis.array_dimensions", "analysis.array_labels", DERIVED):
            built.derives(resource_id, LINEAGE)
    return built


#: Run at commit, so `analysis.spike_events` is derived from the staged core tables.
MATERIALIZE: tuple[Callable[[Any, PacketWriter], Any], ...] = (materialize_spike_events,)


def build(root: Path, **options: Any) -> Any:
    """Commit the example at `root` and return the validation report."""
    return writer(**options).commit(root, materialize=MATERIALIZE)


# -- Part 08 --------------------------------------------------------------------------------

#: Values that differ between two builds of the same rows, or with a library's version.
ELIDED = {"sha256", "value", "created_at", "validated_at"}


def _elide(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {k: _elide(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_elide(v) for v in value]
    return "…" if key in ELIDED else value


def _inline(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))


def excerpt(manifest: Mapping[str, Any]) -> str:
    """The manifest with one entry per resource kind, one member per line, volatile values elided."""
    shown = _elide(dict(manifest, resources=[e for e in manifest["resources"] if e["resource_id"] in EXCERPT]))
    lines = ["{"]
    members = list(shown.items())
    for position, (name, value) in enumerate(members):
        comma = "," if position < len(members) - 1 else ""
        if name == "registries":
            lines.append(f'  "{name}": {{')
            for index, (registry_id, descriptor) in enumerate(value.items()):
                lines.append(f'    "{registry_id}": {_inline(descriptor)}{"," if index < len(value) - 1 else ""}')
            lines.append(f"  }}{comma}")
        elif name == "resources":
            lines.append(f'  "{name}": [')
            for index, entry in enumerate(value):
                lines.append("    {")
                fields = list(entry.items())
                lines.extend(
                    f'      "{field}": {_inline(item)}{"," if at < len(fields) - 1 else ""}'
                    for at, (field, item) in enumerate(fields)
                )
                lines.append(f"    }}{',' if index < len(value) - 1 else ''}")
            lines.append(f"  ]{comma}")
        else:
            lines.append(f'  "{name}": {_inline(value)}{comma}')
    lines.append("}")
    return "\n".join(lines)


def _namespace_order(item: tuple[str, Any]) -> tuple[int, str]:
    """Core, then analysis, then the extensions by name."""
    return ({"core": 0, "analysis": 1}.get(item[0], 2), item[0])


def layout(manifest: Mapping[str, Any]) -> str:
    """The packet's directory tree, as the manifest places each resource."""
    registries = sorted(
        (
            (registry_id, descriptor["path"].rsplit("/", 1)[-1])
            for registry_id, descriptor in manifest["registries"].items()
        ),
        key=_namespace_order,
    )
    placed: dict[str, dict[str, list[str]]] = {}
    for entry in manifest["resources"]:
        if entry.get("external"):
            continue
        top, namespace, name = entry["uri"].split("/", 2)
        placed.setdefault(top, {}).setdefault(namespace, []).append(name.removesuffix(".parquet"))
    width = max(len(name) for name in [*dict(registries), *(n for top in placed.values() for n in top)]) + 2
    lines = ["packet_root/", "  packet.json", "  registries/"]
    lines += [f"    {f'{registry_id}/':{width}}{file}" for registry_id, file in registries]
    for top in ("tables", "arrays"):
        lines.append(f"  {top}/")
        for namespace, names in sorted(placed.get(top, {}).items(), key=_namespace_order):
            label, indent = f"    {f'{namespace}/':{width}}", " " * (4 + width)
            row: list[str] = []
            for name in names:
                shown = name + ("/" if top == "arrays" else "")
                if row and len(label) + len(", ".join([*row, shown])) > 96:
                    lines.append(label + ", ".join(row) + ",")
                    label, row = indent, []
                row.append(shown)
            lines.append(label + ", ".join(row))
    return "\n".join(lines)


def shown(manifest: Mapping[str, Any]) -> dict[str, str]:
    """The text Part 08 §§2–3 carry for this manifest, by section."""
    owned = sum(1 for entry in manifest["resources"] if not entry.get("external"))
    count = (
        f"The packet carries {len(manifest['resources'])} resources, {owned} of them packet-owned; "
        f"the excerpt shows one entry of each kind."
    )
    return {
        "§2's layout": f"```text\n{layout(manifest)}\n```",
        "§3's manifest excerpt": f"{count}\n\n```json\n{excerpt(manifest)}\n```",
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch) / SESSION
        # A packet that fails validation is refused at commit, so one that exists has passed.
        build(root)
        manifest = json.loads((root / "packet.json").read_text())
    text = PART.read_text()
    stale = {section: body for section, body in shown(manifest).items() if body not in text}
    for section, body in stale.items():
        print(f"Part 08 {section} differs from the packet the writer builds, which shows:\n{body}\n")
    if not stale:
        print("Part 08 shows the packet the writer builds")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
