"""A recipe's `[session]` and `[subject]` facts, read from the raw asset's DocDB v2 record.

- :func:`session_facts` -- the session's name, subject and extent, each time in UTC.
- :func:`subject_facts` -- the subject's species, sex, genotype and date of birth.

Each returns the notes a reader of the recipe needs: where a stored value was replaced, and why.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

#: Core's closed vocabulary for `core.subjects.sex`, which AIND's capitalized values map onto.
SEXES = frozenset({"male", "female", "hermaphrodite", "other"})


def _stamp(raw: Any) -> datetime:
    return datetime.fromisoformat(str(raw))


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _stream_instants(acquisition: Mapping[str, Any]) -> set[datetime]:
    """Every stream boundary whose stamp carries a non-zero offset, which this schema gets right."""
    instants: set[datetime] = set()
    for stream in acquisition.get("data_streams") or []:
        for key in ("stream_start_time", "stream_end_time"):
            if stream.get(key) is not None and (value := _stamp(stream[key])).utcoffset() not in (None, timedelta(0)):
                instants.add(value)
    return instants


def instant(raw: Any, zone: ZoneInfo, corroborating: set[datetime], label: str, notes: list[str]) -> datetime:
    """Read one acquisition time.

    The acquisition pipeline stamps `+00:00` on some Pacific wall-clock readings and the true
    offset on others. A stamp with a non-zero offset is kept. A `+00:00` stamp is kept where a
    stream boundary with a non-zero offset states the same instant, and is otherwise read as
    local time in `zone`.
    """
    value = _stamp(raw)
    if value.tzinfo is None:
        localized = value.replace(tzinfo=zone)
        notes.append(f"{label}: {raw} has no offset, read as {zone.key} local time")
        return localized
    if value.utcoffset() != timedelta(0) or value in corroborating:
        return value
    localized = value.replace(tzinfo=zone)
    notes.append(
        f"{label}: {raw} is wall-clock time in {zone.key} stamped UTC, so it is read as {localized.isoformat()}"
    )
    return localized


def session_facts(record: Mapping[str, Any], session_name: str, zone: ZoneInfo) -> tuple[dict[str, str], list[str]]:
    """Return the `[session]` facts from the raw asset's record, and the notes on how each was read."""
    acquisition = record.get("acquisition") or {}
    notes: list[str] = []
    corroborating = _stream_instants(acquisition)
    facts = {"session_id": session_name, "reference_clock_id": "harp"}
    start = instant(acquisition["acquisition_start_time"], zone, corroborating, "acquisition_start_time", notes)
    facts["session_start_time"] = _utc(start)
    if acquisition.get("acquisition_end_time") is not None:
        end = instant(acquisition["acquisition_end_time"], zone, corroborating, "acquisition_end_time", notes)
        if end < start:
            notes.append("acquisition_end_time precedes the start once read, so session_end_time is left out")
        else:
            facts["session_end_time"] = _utc(end)
    subject_id = acquisition.get("subject_id") or (record.get("subject") or {}).get("subject_id")
    if subject_id is not None:
        facts["subject_id"] = str(subject_id)
    return facts, notes


def subject_facts(record: Mapping[str, Any]) -> tuple[dict[str, str], list[str]]:
    """Return the `[subject]` facts from the raw asset's record, and the notes on what it leaves unstated."""
    subject = record.get("subject") or {}
    details = subject.get("subject_details") or {}
    notes: list[str] = []
    facts: dict[str, str] = {}
    if subject.get("subject_id") is not None:
        facts["subject_id"] = str(subject["subject_id"])
    species = (details.get("species") or {}).get("name")
    if species:
        facts["species"] = str(species)
    if details.get("sex"):
        if (sex := str(details["sex"]).lower()) in SEXES:
            facts["sex"] = sex
        else:
            notes.append(f"sex: {details['sex']!r} is none of core's {', '.join(sorted(SEXES))}, so it is left out")
    if details.get("genotype"):
        facts["genotype"] = str(details["genotype"])
    if details.get("date_of_birth"):
        facts["date_of_birth"] = str(details["date_of_birth"])
    strain = details.get("background_strain")
    if isinstance(strain, Mapping) and strain.get("name"):
        facts["strain"] = str(strain["name"])
    notes += [f"subject record states no {key}" for key in ("species", "date_of_birth") if key not in facts]
    return facts, notes


__all__ = ["SEXES", "instant", "session_facts", "subject_facts"]
