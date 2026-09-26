"""Build the example packet, and refresh Part 08's layout and manifest excerpt from it.

The packet is the conformance corpus's valid session written by the writer rather than by hand,
with every shipped extension bound and one resource of each kind the corpus lacks: a
packet-owned array, an external array, a materialized analysis table, and a derived analysis
array. Part 08 shows this packet, so its layout and manifest cannot drift from what the writer
produces against the current registries.

    python example.py           # rewrite Part 08's generated regions
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
from escapewheel_writer import PacketWriter, materialize
from escapewheel_writer.writer import ExternalArray, StagedArray

ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "escapewheel_poc_docs_v0.2" / "08_example_packet.md"
REGISTRY = json.loads((ROOT / "registry" / "logical_schemas.json").read_text())
EXTENSIONS = {
    path.stem: json.loads(path.read_text()) for path in sorted((ROOT / "registry" / "extensions").glob("*.json"))
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
    rows["core.array_dimensions"] = [
        {"array_asset_id": asset, "axis_index": index, "dimension_name": name}
        for asset, axes in (("waveform_mean", ("unit", "channel", "sample")), ("probe0_lfp", ("time", "channel")))
        for index, name in enumerate(axes)
    ]
    rows["analysis.array_assets"] = [
        {
            "array_asset_id": "unit_rates",
            "array_asset_name": "firing rate per unit per bin",
            "semantic_type": "binned_rate",
            "unit": "Hz",
        },
    ]
    rows["analysis.array_dimensions"] = [
        {"array_asset_id": "unit_rates", "axis_index": index, "dimension_name": name}
        for index, name in enumerate(("unit", "time_bin"))
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
            values=np.arange(2 * 3 * 10, dtype="int16").reshape(2, 3, 10),
            resource_id=OWNED,
            declaration_id="core.array_asset_instances",
            array_asset_id="waveform_mean",
            chunks=(1, 3, 10),
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
        for resource_id in ("analysis.array_assets", "analysis.array_dimensions", DERIVED):
            built.derives(resource_id, LINEAGE)
    return built


#: Run at commit, so `analysis.spike_events` is derived from the staged core tables.
MATERIALIZE: tuple[Callable[[Any, PacketWriter], Any], ...] = (materialize.into,)


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


def _fill(text: str, region: str, body: str) -> str:
    begin = f"<!-- BEGIN GENERATED EXAMPLE PACKET: {region} -->"
    end = f"<!-- END GENERATED EXAMPLE PACKET: {region} -->"
    before, remainder = text.split(begin, 1)
    _, after = remainder.split(end, 1)
    return f"{before}{begin}\n{body}\n{end}{after}"


def render(manifest: Mapping[str, Any]) -> str:
    """Part 08 with its generated regions filled from this manifest."""
    owned = sum(1 for entry in manifest["resources"] if not entry.get("external"))
    count = (
        f"The packet carries {len(manifest['resources'])} resources, {owned} of them packet-owned; "
        f"the excerpt shows one entry of each kind."
    )
    text = _fill(PART.read_text(), "layout", f"```text\n{layout(manifest)}\n```")
    return _fill(text, "manifest", f"{count}\n\n```json\n{excerpt(manifest)}\n```")


def main() -> None:
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch) / SESSION
        # A packet that fails validation is refused at commit, so one that exists has passed.
        build(root)
        manifest = json.loads((root / "packet.json").read_text())
    PART.write_text(render(manifest))
    print(f"wrote {PART.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
