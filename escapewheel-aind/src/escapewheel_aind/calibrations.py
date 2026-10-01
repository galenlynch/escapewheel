"""The calibration tables, from what `rig.json` and a session's `ephys_modules` state.

- :func:`calibration_rows` -- `core.calibrations`.
- :func:`point_rows` -- `core.calibration_points`.
- :func:`device_rows` -- `core.calibration_devices`.
- :func:`stated_text` -- a stated string, or None where a document wrote its word for nothing.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any

from escapewheel_writer.adapter import SourceDefect

from .errors import AindFault


def calibration_rows(
    rig: Mapping[str, Any],
    modules: Sequence[Mapping[str, Any]],
    *,
    session_id: str,
    prefix: str,
    calibrated_at: Callable[[str | None, str], datetime | None],
) -> list[dict[str, Any]]:
    """`core.calibrations`: what was measured about an instrument so its numbers can be read.

    Two shapes, because a source states a calibration more than one way (R89 §1.3). A
    `rig.json` entry is a curve, and its type is the quantity its own output label names --
    the vocabulary is open (Part 02 §9.3), so the source's word for what it measured is a value
    rather than something to map onto a closed set. An `ephys_module` states a manipulator
    transform, one calibration cited by every module sharing its file and timestamp (R89
    §1.4), whose content is an array this adapter does not read: the row records that the
    calibration was in force and that the packet holds nothing further (Part 02 §12.3).

    `rig` is the `rig.json` document, `modules` every `ephys_module` the session states, and
    `calibrated_at` reads a stated date under the label it is reported by.
    """
    rows: list[dict[str, Any]] = []
    for entry in rig.get("calibrations", []) or []:
        name = stated_text(entry.get("device_name"))
        if name is None:
            continue
        output = _label(entry.get("output"))
        rows.append(
            {
                "calibration_id": prefix + name,
                "session_id": session_id,
                "calibration_name": prefix + name,
                "calibration_type": _quantity(output) or "unknown",
                "calibrated_at": calibrated_at(entry.get("calibration_date"), name),
                "description": stated_text(entry.get("description")),
                "input_unit": _unit(_label(entry.get("input"))),
                "output_unit": _unit(output),
                "array_asset_id": None,
                "detail_kind": None,
                # R89 §2.6: what the source said that no column above models. The note is not
                # `description`, which carries the source's own description field.
                "metadata": _bag(notes=stated_text(entry.get("notes"))),
            }
        )
    for transform, when in _transforms(modules).items():
        rows.append(
            {
                "calibration_id": prefix + transform,
                "session_id": session_id,
                "calibration_name": prefix + transform,
                "calibration_type": "manipulator_transform",
                "calibrated_at": calibrated_at(when, transform),
                "description": None,
                "input_unit": None,
                "output_unit": None,
                # R89 §2.4 wants the array asset; this adapter does not read the `.npy`, so the
                # content is unrecorded (Part 02 §12.3). The path is `calibration_name`, which is the
                # identifier the source used for it, so nothing repeats it in `metadata`.
                "array_asset_id": None,
                "detail_kind": None,
                "metadata": None,
            }
        )
    return rows


def point_rows(rig: Mapping[str, Any], *, session_id: str, prefix: str) -> list[dict[str, Any]]:
    """`core.calibration_points`: the paired series of each calibration that is a curve.

    `rig.json` holds two parallel JSON lists, which Part 02 §5.2 forbids as a column; a series of
    unequal lengths is a defect in the source rather than something to truncate.
    """
    rows: list[dict[str, Any]] = []
    for entry in rig.get("calibrations", []) or []:
        name = stated_text(entry.get("device_name"))
        if name is None:
            continue
        inputs, outputs = _series(entry.get("input")), _series(entry.get("output"))
        if len(inputs) != len(outputs):
            raise SourceDefect(
                f"calibration {name!r} states {len(inputs)} inputs against {len(outputs)} "
                "outputs; a point needs both sides (R89 §2.3)",
                code=AindFault.CALIBRATION_MISALIGNED,
                where=name,
            )
        rows.extend(
            {
                "session_id": session_id,
                "calibration_id": prefix + name,
                "point_index": index,
                "input_value": float(x),
                "output_value": float(y),
            }
            for index, (x, y) in enumerate(zip(inputs, outputs, strict=True))
        )
    return rows


def device_rows(modules: Sequence[Mapping[str, Any]], *, session_id: str, prefix: str) -> list[dict[str, Any]]:
    """`core.calibration_devices`: the devices each calibration covers.

    The assembly name is the device name the acquisition chain gives the same probe, and the
    writer numbers both from that name under one recipe prefix (Part 05 §4.3), so the reference
    resolves without this adapter seeing `core.devices`. A calibration covering a device the
    packet does not hold gets no row, which is a fact rather than a defect (R89 §2.2) -- which is
    why the lick spouts of a water calibration appear here only if some source built them.
    """
    rows = []
    for module in modules:
        transform = stated_text(module.get("coordinate_transform"))
        device = stated_text(module.get("assembly_name"))
        if transform is not None and device is not None:
            rows.append(
                {
                    "session_id": session_id,
                    "calibration_id": prefix + transform,
                    "device_id": prefix + device,
                }
            )
    return rows


def _transforms(modules: Sequence[Mapping[str, Any]]) -> dict[str, str | None]:
    """Each distinct `coordinate_transform` the modules cite, to the date they state for it."""
    found: dict[str, str | None] = {}
    for module in modules:
        transform = stated_text(module.get("coordinate_transform"))
        if transform is not None:
            found.setdefault(transform, stated_text(module.get("calibration_date")))
    return found


def stated_text(value: Any) -> str | None:
    """Return a stated string, or None where the source wrote nothing or its word for nothing.

    This schema writes the string `None` where a field is unset, so a truthiness test keeps it.
    """
    if value is None:
        return None
    text = str(value).strip()
    return None if text in {"", "None", "null"} else text


def _label(side: Any) -> str | None:
    """Return the single key naming one side of a calibration's series."""
    return next(iter(side), None) if isinstance(side, dict) and len(side) == 1 else None


def _series(side: Any) -> list[float]:
    """Return the values of one side of a calibration's series, in file order."""
    return list(next(iter(side.values()))) if isinstance(side, dict) and len(side) == 1 else []


def _unit(label: str | None) -> str | None:
    """Return the unit of measure a series label states in parentheses, as in `water volume (ul):`."""
    found = re.search(r"\(([^)]*)\)", label or "")
    return found.group(1).strip() or None if found else None


def _quantity(label: str | None) -> str | None:
    """Return a series label's quantity as a vocabulary value: `water volume (ul):` to `water_volume`.

    The vocabulary is open (Part 02 §9.3), so what the source called the quantity it measured is a value
    rather than something to map onto a closed set this specification does not have.
    """
    if label is None:
        return None
    bare = re.sub(r"\([^)]*\)", "", label).strip().strip(":").strip()
    return re.sub(r"[^a-z0-9]+", "_", bare.lower()).strip("_") or None


def _bag(**stated: str | None) -> str | None:
    """Return what the source stated that no column models, as JSON, or None where it stated none."""
    kept = {key: value for key, value in stated.items() if value is not None}
    return json.dumps(kept, sort_keys=True) if kept else None


__all__ = ["calibration_rows", "device_rows", "point_rows", "stated_text"]
