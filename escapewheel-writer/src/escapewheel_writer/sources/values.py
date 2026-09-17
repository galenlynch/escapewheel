"""Values a source states, rendered the way a packet records them.

Neither of these belongs to a format. `sex` maps onto a closed core vocabulary and `utc_offset`
renders an offset for a compensation note, and both are read by the NWB adapter and by the one
reading AIND's session metadata -- which is why they are here rather than in either, where the
second had to import a private name from the first.
"""

from __future__ import annotations

from typing import Any

#: Part 02 §9.3. `core.subjects.sex` closes to `male`, `female`, `hermaphrodite` and `other`, and a
#: source writes `M`/`F`/`U`/`O`. `U` is unknown, which becomes null rather than `other`: recording
#: it as `other` asserts a sex the source never claimed, where a null column says it did not say.
SEX = {
    "m": "male",
    "male": "male",
    "f": "female",
    "female": "female",
    "h": "hermaphrodite",
    "hermaphrodite": "hermaphrodite",
    "o": "other",
    "other": "other",
}


def sex(stated: str | None) -> str | None:
    """Map a source's spelling onto Part 02 §9.3's four values, or None where it states none."""
    return SEX.get(stated.strip().lower()) if stated else None


def utc_offset(delta: Any) -> str:
    """Render a UTC offset the way a timestamp writes it, not the way a timedelta prints."""
    if delta is None:
        return "none"
    minutes = round(delta.total_seconds() / 60)
    return f"{'-' if minutes < 0 else '+'}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d}"


__all__ = ["SEX", "sex", "utc_offset"]
