"""The values and names every adapter reading one NWB file takes the same way.

- :func:`electrode_name`, :func:`contact_ids`, :func:`contact_columns` -- the one rule naming a
  contact.
- :func:`ucum_code` -- the UCUM code for an NWB `unit` attribute.
- :data:`ABSENT` -- the spellings an NWB writes where a value is absent.
- :func:`clean`, :func:`one` -- a source value as a typed column takes it, and the single value of
  a scalar array.
- :func:`alike` -- whether two trial-column values are the same.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ...errors import SourceDefect, SourceFault
from ...notes import Note, NoteCode

#: NWB writes the literal string ``None`` where a value is absent -- in `laser_location`,
#: `auto_train_stage`, `was_generated_by`. Treated as null when mapped into a typed core
#: column; left verbatim inside metadata, which is a faithful copy of the source.
ABSENT = {"", "None", "none", "nan", "NaN"}


def one(values: NDArray[Any]) -> str | None:
    """Take the single value of a scalar NWB array, as text, or None if it is absent."""
    if values.size == 0:
        return None
    value = values[0]
    if isinstance(value, bytes):
        value = value.decode()
    text = str(value).strip()
    return None if text in ABSENT else text


def clean(value: Any) -> Any:
    """Map a source value into a typed core column, turning absence into null."""
    if isinstance(value, bytes):
        value = value.decode()
    if isinstance(value, str):
        return None if value.strip() in ABSENT else value
    if isinstance(value, float):
        return None if math.isnan(value) else value
    if isinstance(value, np.generic):
        return clean(value.item())
    return value


def alike(a: Any, b: Any) -> bool:
    """Whether two trial-column values are the same, with NaN equal to NaN.

    A float column of all-NaN is constant, not varying: `nan != nan` would otherwise make every
    absent parameter look like per-trial data and keep it on every row.
    """
    try:
        if isinstance(a, float) and isinstance(b, float) and np.isnan(a) and np.isnan(b):
            return True
    except TypeError:
        pass
    return bool(a == b)


def electrode_name(group: Any, channel: Any, prefix: str = "") -> str:
    """Compose a contact's packet-wide name, which no NWB column carries on its own.

    `electrode_name` repeats across the shanks of a quad-base probe and `channel_name` is
    per-probe, so the pair is what identifies a contact.

    Module-level because every adapter reading one NWB composes it: a writer numbers a name
    (Part 05 §4.3), so a second spelling of one contact mints a second electrode, and the packet then
    references a row that is not there.
    """
    return f"{prefix}{group}.{channel}"


#: Part 02 §8.4. NWB spells a unit as a word where a packet records its UCUM code. A spelling not
#: listed passes through unchanged, so validation rejects it rather than the writer guessing.
UCUM_CODES: Mapping[str, str] = {"volts": "V"}


def ucum_code(stated: str | None) -> str | None:
    """Return the UCUM code for an NWB `unit` attribute, or None where the file states none."""
    return UCUM_CODES.get(stated, stated) if stated else None


def contact_columns(store: Any, table: Path) -> dict[str, Any]:
    """Read the electrode columns a contact's name is composed from, whichever the file carries."""
    return {
        column: store.array(table / column)
        for column in ("group_name", "channel_name", "id")
        if (table / column).is_dir()
    }


def contact_ids(columns: Mapping[str, Any], prefix: str = "") -> tuple[list[str], Note | None]:
    """Name every contact in electrode-table row order, and say if the fallback was needed.

    Three adapters name the same contacts, and a writer numbers a name (Part 05 §4.3), so a second
    spelling of one contact mints a second electrode and the packet then references a row that is
    not there. The rule lives here once rather than in each of them.
    """
    if "group_name" not in columns:
        raise SourceDefect(
            "electrodes/group_name: absent, so no contact can be named",
            code=SourceFault.NO_ELECTRODE_GROUPS,
            where="electrodes/group_name",
        )
    group = columns["group_name"]
    if "channel_name" in columns:
        pairs = columns["channel_name"]
        note: Note | None = None
    else:
        # Every `DynamicTable` has an `id`, so a contact is always nameable; what the fallback
        # loses is the source's own spelling, which `local_channel_label` then cannot carry.
        pairs = columns["id"] if "id" in columns else np.arange(len(group))
        note = Note(
            "electrodes: no channel_name, so a contact is named by its group and row id", NoteCode.NO_CHANNEL_NAMES
        )
    return [electrode_name(one, other, prefix) for one, other in zip(group, pairs, strict=True)], note


__all__ = ["ABSENT", "alike", "clean", "contact_columns", "contact_ids", "electrode_name", "one", "ucum_code"]
