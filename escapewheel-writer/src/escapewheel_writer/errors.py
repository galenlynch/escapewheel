"""Every exception this package raises on purpose.

A recipe that cannot be built:

- :exc:`RecipeError` -- a recipe that cannot be built.
- :exc:`ReplacementRefused` -- a `[packet].replaces` entry names something a build cannot replace.
- :exc:`AmendmentRefused` -- the amendment would change a held row, or the packet cannot be amended.
- :exc:`ExtensionNotFound` -- an entry names neither a file nor an installed distribution.

A source that cannot supply what a build asked of it:

- :exc:`SourceDefect` -- a source cannot supply what it was asked for, which stops the build.
- :exc:`UnsupportedEncoding` -- an array uses an encoding this package will not decode.
- :exc:`PayloadRefused` -- a delivery holds something a packet cannot own.

Values a packet cannot hold:

- :exc:`OffGrid`, :exc:`NonFinite` -- seconds that land on no tick, and NaN or infinite seconds.
- :exc:`NaiveTimestamp` -- a wall-clock value carried no UTC offset.
- :exc:`CarriedNotAnInteger` -- a carried identifier arrived as something other than a number.
- :exc:`Collided` -- two spikes of one unit convert to the same reference tick.

A packet root that cannot be committed to, or read back:

- :exc:`CommitRefused` -- validation's verdict was not ``passed``, so nothing was committed.
- :exc:`NotCommitted` -- there is no committed packet at a root.
- :exc:`PromotionRecordUnreadable` -- a staging area holds a promotion record this writer cannot
  read.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from escapewheel_reader.errors import NotAligned

if TYPE_CHECKING:  # pragma: no cover
    from escapewheel_validator import Report


class RecipeError(Exception):
    """A recipe cannot be built: a source kind is unknown, or its dependencies do not order."""


class ReplacementRefused(Exception):
    """A recipe's `[packet].replaces` names what a build cannot replace (Part 05 §3.5)."""


class AmendmentRefused(ValueError):
    """An amendment would change what Part 05 §15.2 forbids, or a build cannot amend this packet."""


class ExtensionNotFound(Exception):
    """A recipe names an extension that is neither a file nor an installed distribution."""


class SourceDefect(ValueError):
    """A source cannot supply what it was asked for, and the build cannot proceed past it.

    Carried as an exception rather than a note because it stops a build (Part 05 §4.4), where what
    an adapter worked around goes in the run's report (Part 12 §9).
    """


class UnsupportedEncoding(ValueError):
    """An array uses an encoding this package will not decode, such as ``pickle``."""


class PayloadRefused(ValueError):
    """A delivery holds something a packet cannot own, or a payload binds no single resource."""


class OffGrid(ValueError):
    """Source seconds do not lie on this clock's tick grid, so no exact tick exists.

    Recovering ticks from such values means fitting a rate and an offset, which is an
    estimate this package will not silently produce. The message reports how many values
    missed and by how much, in ticks.

    Attributes
    ----------
    n_off : int
        How many values missed the grid.
    worst : float
        The largest miss, as a fraction of one tick.
    """

    def __init__(self, message: str, *, n_off: int, worst: float) -> None:
        super().__init__(message)
        self.n_off = n_off
        self.worst = worst


class NonFinite(ValueError):
    """A source timestamp was NaN or infinite.

    Placeholder streams do occur -- an NWB may carry a behaviour stream holding a single NaN --
    so a caller that expects them filters first and says so, rather than letting a NaN become
    an arbitrary integer.
    """


class NaiveTimestamp(ValueError):
    """A wall-clock value carried no UTC offset.

    Part 03 requires wall-clock columns to be ``TIMESTAMP(MICROS, UTC)``, so a value without an
    offset is not merely inconvenient -- it is unlocatable, and assuming UTC would be a guess.
    Real source metadata gets this wrong: an aind-data-schema `session.json` may stamp `+00:00`
    on a local wall clock. Refusing naive values does not catch a wrong offset, but it does stop
    a writer inventing one.
    """


class CarriedNotAnInteger(ValueError):
    """A carried identifier arrived as something other than the source's own number."""


class Collided(NotAligned):
    """Two spikes of one unit convert to the same reference tick, so the table cannot be built.

    Part 06 §4. This table is keyed on the converted tick, and a conversion preserves distinctness
    only where it expands -- a reference clock slower than a probe's collapses spikes that were
    distinct on the probe. Refusing costs nothing usable: a histogram over collapsed spikes
    undercounts them, so a clock that coarse makes this table the wrong instrument rather than a
    broken one, and Part 06 §2 makes not building it an ordinary outcome.
    """


class CommitRefused(Exception):
    """The packet's verdict was not ``passed``, so nothing was committed (Part 05 §9.2).

    Attributes
    ----------
    report : Report
        The findings. The staging directory is left in place for inspection.
    """

    def __init__(self, report: Report, staging: Path) -> None:
        super().__init__(f"packet {report.verdict()}, {report.errors} error(s); staged resources left at {staging}")
        self.report = report
        self.staging = staging


class NotCommitted(Exception):
    """There is no committed packet at this root to amend."""


class PromotionRecordUnreadable(Exception):
    """A staging area holds a promotion record this writer cannot read (Part 05 §6)."""
