"""Every exception this package raises on purpose; each derives from :exc:`WriterError`.

The codes an error or a reported problem carries are declared beside the classes:
:class:`RecipeFault`.

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

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from escapewheel_reader.errors import EscapewheelError, NotAligned

if TYPE_CHECKING:  # pragma: no cover
    from escapewheel_validator import Report


class WriterError(EscapewheelError):
    """Base class for every error raised by this package."""


class RecipeFault(StrEnum):
    """What is wrong with a recipe, as the code a :class:`~escapewheel_writer.recipe.Problem` carries.

    A fault reported from two places shares a member: a declaration that contributes what it does
    not produce, and a protocol outside the profile's group.
    """

    #: A source supplies a resource no loaded registry defines.
    UNDEFINED_RESOURCE = "undefined_resource"
    #: Several sources own one resource.
    SEVERAL_OWNERS = "several_owners"
    #: One source owns a resource another also supplies.
    OWNED_AND_SUPPLIED = "owned_and_supplied"
    #: A source kind is listed more than once.
    REPEATED_KIND = "repeated_kind"
    #: A preference names a source the recipe does not list.
    PREFERENCE_UNLISTED = "preference_unlisted"
    #: A preference names a source whose adapter cannot supply the resource.
    PREFERENCE_UNPRODUCED = "preference_unproduced"
    #: A preference names one source, and another declares the resource under owns or contributes.
    PREFERENCE_CONTRADICTED = "preference_contradicted"
    #: A preference names a resource fewer than two listed sources produce.
    PREFERENCE_IDLE = "preference_idle"
    #: An adapter contributes a resource its produces does not name.
    CONTRIBUTES_UNPRODUCED = "contributes_unproduced"
    #: One extension is listed in more than one entry.
    REPEATED_EXTENSION = "repeated_extension"
    #: An adapter declares no states, so a build cannot tell what facts it states.
    STATES_UNDECLARED = "states_undeclared"
    #: An adapter states a field through an attribute it does not expose.
    STATE_UNEXPOSED = "state_unexposed"
    #: An `[encoding]` entry names no declared column.
    ENCODING_UNDECLARED = "encoding_undeclared"
    #: An override names a field no listed source states, or the recipe declares no value for.
    OVERRIDE_IDLE = "override_idle"
    #: A declared field overrides the sources that state it.
    OVERRIDE_APPLIED = "override_applied"
    #: A declared field is also stated by a source, so the build compares the two.
    FACT_COMPARED = "fact_compared"
    #: A foreign key of a supplied table targets a table nothing supplies.
    DANGLING_REFERENCE = "dangling_reference"
    #: A listed source can produce a resource nothing in the recipe claims.
    UNCLAIMED = "unclaimed"
    #: Two `preferred_run` entries share an activity and scope.
    REPEATED_PREFERRED_RUN = "repeated_preferred_run"
    #: A `preferred_run` entry's `chosen_at` names no instant.
    CHOSEN_AT_NO_INSTANT = "chosen_at_no_instant"
    #: The recipe both replaces packets and amends one.
    REPLACES_AND_AMENDS = "replaces_and_amends"
    #: An amending recipe declares a member the packet's rows prevail over.
    AMENDING_DECLARES = "amending_declares"
    #: A storage option carries a credential.
    CREDENTIAL = "credential"
    #: A kind another distribution registered is neither delivered nor run in process.
    NO_ROUTE = "no_route"
    #: A source declares both a delivery and `in_process`.
    TWO_ROUTES = "two_routes"
    #: A delivery declares no command.
    NO_COMMAND = "no_command"
    #: A named declaration document cannot be read.
    DECLARATION_UNREADABLE = "declaration_unreadable"
    #: A delivered source names no declaration and the build cannot import its adapter.
    NO_DECLARATION = "no_declaration"
    #: An adapter released independently of the build declares no protocol.
    NO_PROTOCOL = "no_protocol"
    #: An adapter's declarations do not satisfy the declaration schema.
    DECLARATION_SHAPE = "declaration_shape"
    #: A protocol is in no group the profile names.
    PROTOCOL_UNKNOWN = "protocol_unknown"
    #: The recipe names a protocol the adapter does not declare.
    PROTOCOL_UNDECLARED = "protocol_undeclared"
    #: An adapter produces a resource no loaded registry declares.
    PRODUCES_UNDECLARED = "produces_undeclared"
    #: An adapter states a field that resolves to no column of a recipe block's table.
    STATES_UNRESOLVED = "states_unresolved"
    #: An adapter needs `source_cache`, which it may only accept.
    NEEDS_SOURCE_CACHE = "needs_source_cache"
    #: An adapter needs a term a protocol supplies.
    NEEDS_PROTOCOL_TERM = "needs_protocol_term"
    #: An adapter needs a name that is neither a term nor an option the entry sets.
    NEEDS_UNFILLED = "needs_unfilled"
    #: An adapter accepts a name that is a term.
    ACCEPTS_TERM = "accepts_term"
    #: An adapter accepts a name it also needs.
    ACCEPTS_NEEDED = "accepts_needed"
    #: An entry leaves unset an option its adapter requires.
    OPTION_UNSET = "option_unset"
    #: An entry sets a name that is a term the build fills.
    OPTION_IS_TERM = "option_is_term"
    #: An entry sets an option its adapter declares neither as needed nor as accepted.
    OPTION_UNREAD = "option_unread"
    #: A `[[materialize]]` entry names a resource nothing derives.
    NO_MATERIALIZER = "no_materializer"
    #: A `[[materialize]]` entry sets a parameter its materializer does not take.
    MATERIALIZE_PARAMETER = "materialize_parameter"
    #: A prefix holds characters a resource ID does not admit.
    PREFIX_CHARACTERS = "prefix_characters"
    #: Sources whose adapters take a prefix set different ones.
    PREFIX_DISAGREES = "prefix_disagrees"
    #: A clock is declared more than once.
    REPEATED_CLOCK = "repeated_clock"
    #: A declared clock has the name of one the amended packet holds.
    CLOCK_HELD = "clock_held"
    #: The session's reference clock is declared nowhere.
    REFERENCE_CLOCK_UNDECLARED = "reference_clock_undeclared"
    #: A clock names a parent that is declared nowhere.
    PARENT_CLOCK_UNDECLARED = "parent_clock_undeclared"


class RecipeError(WriterError):
    """A recipe cannot be built: a source kind is unknown, or its dependencies do not order."""


class ReplacementRefused(WriterError):
    """A recipe's `[packet].replaces` names what a build cannot replace (Part 05 §3.5)."""


class AmendmentRefused(WriterError, ValueError):
    """An amendment would change what Part 05 §15.2 forbids, or a build cannot amend this packet."""


class ExtensionNotFound(WriterError):
    """A recipe names an extension that is neither a file nor an installed distribution."""


class SourceDefect(WriterError, ValueError):
    """A source cannot supply what it was asked for, and the build cannot proceed past it.

    Carried as an exception rather than a note because it stops a build (Part 05 §4.4), where what
    an adapter worked around goes in the run's report (Part 12 §9).
    """


class UnsupportedEncoding(WriterError, ValueError):
    """An array uses an encoding this package will not decode, such as ``pickle``."""


class PayloadRefused(WriterError, ValueError):
    """A delivery holds something a packet cannot own, or a payload binds no single resource."""


class OffGrid(WriterError, ValueError):
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


class NonFinite(WriterError, ValueError):
    """A source timestamp was NaN or infinite.

    Placeholder streams do occur -- an NWB may carry a behaviour stream holding a single NaN --
    so a caller that expects them filters first and says so, rather than letting a NaN become
    an arbitrary integer.
    """


class NaiveTimestamp(WriterError, ValueError):
    """A wall-clock value carried no UTC offset.

    Part 03 requires wall-clock columns to be ``TIMESTAMP(MICROS, UTC)``, so a value without an
    offset is not merely inconvenient -- it is unlocatable, and assuming UTC would be a guess.
    Real source metadata gets this wrong: an aind-data-schema `session.json` may stamp `+00:00`
    on a local wall clock. Refusing naive values does not catch a wrong offset, but it does stop
    a writer inventing one.
    """


class CarriedNotAnInteger(WriterError, ValueError):
    """A carried identifier arrived as something other than the source's own number."""


class Collided(WriterError, NotAligned):
    """Two spikes of one unit convert to the same reference tick, so the table cannot be built.

    Part 06 §4. This table is keyed on the converted tick, and a conversion preserves distinctness
    only where it expands -- a reference clock slower than a probe's collapses spikes that were
    distinct on the probe. Refusing costs nothing usable: a histogram over collapsed spikes
    undercounts them, so a clock that coarse makes this table the wrong instrument rather than a
    broken one, and Part 06 §2 makes not building it an ordinary outcome.
    """


class CommitRefused(WriterError):
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


class NotCommitted(WriterError):
    """There is no committed packet at this root to amend."""


class PromotionRecordUnreadable(WriterError):
    """A staging area holds a promotion record this writer cannot read (Part 05 §6)."""
