"""The quality labels a curated sorting carries for its units, and their projection onto the closed set.

- :data:`PROJECTION` -- a mapping from a source's quality label to the closed set that
  `core.units.quality_label` takes, or to null where no member fits.
- :data:`LABEL_SOURCES` -- a mapping from each per-unit label file to the `source` of its labels.
- :data:`DESIGNATED` -- the label source that fills `core.units.quality_label`.
- :func:`automated_labels` -- one stream's `core.unit_quality_labels` rows from its label files.
- :func:`manual_labels` -- one stream's `core.unit_quality_labels` rows from its curation.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ..errors import SourceDefect, SourceFault
from ..notes import Note, NoteCode
from .analyzer import SortedStream

#: Part 02 §9.3: a source's own label is open, the projection onto the closed set is declared.
#: `non_soma` projects to null rather than being forced into `noise` -- bombcell means
#: "a real waveform recorded off-soma", which is not the same claim as "not a unit".
PROJECTION: dict[str, str | None] = {
    "good": "sua",
    "sua": "sua",
    "mua": "mua",
    "MUA": "mua",
    "noise": "noise",
    "non_soma": None,
}

#: `properties/<file>.npy` -> the `core.unit_quality_labels.source` it becomes.
LABEL_SOURCES = {
    "KSLabel": "kilosort",
    "bombcell_label": "bombcell",
    "decoder_label": "decoder",
    "unitrefine_label": "unitrefine",
}

#: `curation.json`'s label category that fills the same role the automated sources do. Any
#: other category becomes `manual:<category>`, since one source may emit one label per unit.
MANUAL_CATEGORY = "quality"

#: Sources that also report a probability, which becomes `confidence`.
CONFIDENCE = {"decoder": "decoder_probability", "unitrefine": "unitrefine_probability"}

#: Which source fills `core.units.quality_label`. The decoder emits `sua`/`mua`/`noise`
#: natively, which is the vocabulary R11 §3 closed the column to and the reason it chose
#: `sua` over the more common `good`.
DESIGNATED = "decoder"


def automated_labels(
    stream: SortedStream,
    ids: NDArray[np.int64],
    *,
    session_id: str,
    unit_id: Callable[[int], str],
    read: Callable[[str], NDArray[Any] | None],
    notes: list[str],
) -> list[dict[str, Any]]:
    """`core.unit_quality_labels` rows from one stream's per-unit label files, one per (unit, source).

    Parameters
    ----------
    stream : SortedStream
        The curated stream.
    ids : numpy.ndarray
        The stream's unit labels, in the order each label file follows.
    session_id : str
        The session the units belong to.
    unit_id : callable
        Composes a unit's name from its label.
    read : callable
        Returns one per-unit property array by name, or None where the sorting does not carry it.
    notes : list of str
        Receives a note for each label no projection is declared for.
    """
    rows = []
    for name, source in LABEL_SOURCES.items():
        labels = read(name)
        if labels is None:
            continue
        if labels.size != ids.size:
            raise SourceDefect(
                f"{stream.key}: {name} has {labels.size} values for {ids.size} units",
                code=SourceFault.PROPERTY_MISALIGNED,
                where=stream.key,
            )
        confidence = read(CONFIDENCE[source]) if source in CONFIDENCE else None
        unknown = {str(v) for v in np.unique(labels)} - set(PROJECTION)
        if unknown:
            notes.append(
                Note(
                    f"{stream.key}/{name}: {sorted(unknown)} have no declared projection; "
                    "kept verbatim with a null normalized_label",
                    NoteCode.LABEL_UNPROJECTED,
                )
            )
        for offset, label in enumerate(ids):
            raw = str(labels[offset])
            rows.append(
                {
                    "session_id": session_id,
                    "unit_id": unit_id(int(label)),
                    "source": source,
                    "label": raw,
                    "normalized_label": PROJECTION.get(raw),
                    "confidence": float(confidence[offset]) if confidence is not None else None,
                }
            )
    return rows


def manual_labels(
    stream: SortedStream,
    curation: dict[str, Any],
    ids: NDArray[np.int64],
    *,
    session_id: str,
    unit_id: Callable[[int], str],
    notes: list[str],
) -> list[dict[str, Any]]:
    """`core.unit_quality_labels` rows from a curation's own manual labels.

    The four automated sources live in `properties/`; these live in `curation.json` and
    are the only record of what a person decided. Without them a packet's removed units
    are indistinguishable from its kept ones.

    Removal is checked here rather than emitted. `curation.json` lists `removed` units
    separately, and where that list is exactly the manually labelled set the label makes
    removal queryable. That coincidence is a property of a pipeline and not a rule, so a
    stream where it breaks is reported: the packet would then be hiding a removal no label
    records, and Part 02 has no column to put one in.

    `curation` is the stream's `curation.json`; the other parameters are those of
    :func:`automated_labels`.
    """
    known = set(ids.tolist())
    removed = set(curation.get("removed") or [])
    labelled = {entry["unit_id"] for entry in curation.get("manual_labels") or []}
    if removed != labelled:
        notes.append(
            Note(
                f"{stream.key}: {len(removed - labelled)} units are removed by the curation and carry "
                f"no manual label, so the packet cannot say they were removed; 02 has no column for it",
                NoteCode.REMOVAL_UNRECORDED,
            )
        )
    if stray := labelled - known:
        notes.append(
            Note(
                f"{stream.key}: {len(stray)} manual labels name units the sorting does not have",
                NoteCode.LABEL_NAMES_NO_UNIT,
            )
        )

    rows = []
    for entry in curation.get("manual_labels") or []:
        label = entry["unit_id"]
        if label not in known:
            continue
        for category, values in (entry.get("labels") or {}).items():
            chosen = list(values) if isinstance(values, list) else [values]
            if len(chosen) != 1:
                notes.append(
                    Note(
                        f"{stream.key}/unit {label}: {len(chosen)} labels in category {category!r}; "
                        "kept verbatim and left unprojected, since the closed set holds one value",
                        NoteCode.SEVERAL_LABELS,
                    )
                )
            raw = "|".join(str(v) for v in chosen)
            rows.append(
                {
                    "session_id": session_id,
                    "unit_id": unit_id(int(label)),
                    "source": "manual" if category == MANUAL_CATEGORY else f"manual:{category}",
                    "label": raw,
                    "normalized_label": PROJECTION.get(raw) if len(chosen) == 1 else None,
                }
            )
    return rows


__all__ = ["DESIGNATED", "LABEL_SOURCES", "PROJECTION", "automated_labels", "manual_labels"]
