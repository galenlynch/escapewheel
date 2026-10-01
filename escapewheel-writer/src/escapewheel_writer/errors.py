"""Every exception this package raises on purpose; each derives from :exc:`WriterError`.

The codes an error or a reported problem carries are declared beside the classes:
:class:`RecipeFault`, :class:`AmendmentFault`, :class:`SourceFault`, :class:`PayloadFault` and
:class:`UsageFault`.

A recipe that cannot be built:

- :exc:`RecipeError` -- a recipe that cannot be built; each cause below is a subclass.
- :exc:`RecipeUnreadable` -- a file is not a recipe: not TOML, no packet ID, or off the schema.
- :exc:`RecipeUnsound` -- a build refuses a recipe, and carries each problem it found.
- :exc:`UnknownSourceKind` -- a source names a kind no adapter is registered for.
- :exc:`SourcesNotOrdered` -- what the sources consume gives them no order to run in.
- :exc:`TermUnfilled` -- a source needs a name the build cannot supply.
- :exc:`MaterializerNotFound` -- a `[[materialize]]` entry names a resource nothing derives.
- :exc:`NotesUnderStrict` -- a source reported a note in a build that admits none.
- :exc:`ReplacementRefused` -- a `[packet].replaces` entry names something a build cannot replace.
- :exc:`AmendmentRefused` -- the amendment would change a held row, or the packet cannot be amended.
- :exc:`ExtensionNotFound` -- an entry names neither a file nor an installed distribution.
- :exc:`DeclarationUnreadable` -- a file is no adapter declaration.

A source that cannot supply what a build asked of it:

- :exc:`SourceDefect` -- a source cannot supply what it was asked for, which stops the build.
- :exc:`UnsupportedEncoding` -- an array uses an encoding this package will not decode.
- :exc:`DeliveryFailed` -- an adapter run out of process did not deliver what was asked of it.
- :exc:`PayloadRefused` -- a delivery holds something a packet cannot own.

A call the writer will not carry out:

- :exc:`UsageError` -- a call asks for something the writer will not stage, write or amend.
- :exc:`UndeclaredResource` -- a call names a table no loaded registry defines.
- :exc:`UnknownCompensation` -- an adapter declares a compensation nothing registers.
- :exc:`CompensationsInvalid` -- a distribution registers something other than compensations.
- :exc:`FixedOffsetZone` -- a zone was given as a fixed offset.

Values a packet cannot hold:

- :exc:`OffGrid`, :exc:`NonFinite` -- seconds that land on no tick, and NaN or infinite seconds.
- :exc:`NaiveTimestamp` -- a wall-clock value carried no UTC offset.
- :exc:`CarriedNotAnInteger` -- a carried identifier arrived as something other than a number.
- :exc:`OutOfRange` -- a number does not fit the integer width its column declares.
- :exc:`TickOverflow` -- a tick falls outside the 64-bit range.
- :exc:`Collided` -- two spikes of one unit convert to the same reference tick.

A packet root that cannot be committed to, or read back:

- :exc:`PacketOccupied` -- a root already holds what a commit would write there.
- :exc:`CommitRefused` -- validation's verdict was not ``passed``, so nothing was committed.
- :exc:`NotCommitted` -- there is no committed packet at a root.
- :exc:`PromotionRecordUnreadable` -- a staging area holds a promotion record this writer cannot
  read.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from escapewheel_reader.errors import EscapewheelError, NotAligned

if TYPE_CHECKING:  # pragma: no cover
    from escapewheel_validator import Report

    from .recipe import Problem


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
    #: The file is not valid TOML.
    NOT_TOML = "not_toml"
    #: `[packet]` declares no ID.
    NO_PACKET_ID = "no_packet_id"
    #: The document does not satisfy the recipe schema.
    RECIPE_SHAPE = "recipe_shape"
    #: No published manifest can be read at a `[packet].replaces` entry.
    REPLACED_UNREADABLE = "replaced_unreadable"
    #: A replaced manifest's packet ID or version does not satisfy the manifest schema.
    REPLACED_NO_IDENTITY = "replaced_no_identity"
    #: Two `[packet].replaces` entries read one manifest.
    REPLACED_TWICE = "replaced_twice"
    #: The packet at the recipe's output cannot be amended, or the amendment would change it.
    AMENDMENT_REFUSED = "amendment_refused"
    #: The packet an amending recipe names has another packet ID.
    AMENDS_OTHER_PACKET = "amends_other_packet"
    #: The packet an amending recipe names is at another version.
    AMENDS_OTHER_VERSION = "amends_other_version"
    #: The packet an amending recipe names does not list the recipe's session.
    AMENDS_OTHER_SESSION = "amends_other_session"
    #: A registry's standard version differs from the amended packet's.
    AMENDS_OTHER_STANDARD = "amends_other_standard"
    #: A `preferred_run` entry names a run neither the packet holds nor the build records.
    PREFERRED_RUN_UNKNOWN = "preferred_run_unknown"
    #: A `preferred_run` entry's activity or scope differs from its run's.
    PREFERRED_RUN_DIFFERS = "preferred_run_differs"


class RecipeError(WriterError):
    """A recipe cannot be built. Each cause is a subclass."""


class RecipeUnreadable(RecipeError, ValueError):
    """A file is not a recipe: it is not TOML, declares no packet ID, or fails the recipe schema.

    Attributes
    ----------
    path : Path
        The file.
    problems : list of Problem
        What is wrong with it, each an error carrying its code.
    """

    def __init__(self, message: str, *, path: Path, problems: Sequence[Problem]) -> None:
        super().__init__(message)
        self.path = path
        self.problems = list(problems)


class RecipeUnsound(RecipeError):
    """A build refuses a recipe for what its check, or the packet it names, reports (Part 05 §3.5).

    Attributes
    ----------
    path : Path
        The recipe's file.
    problems : list of Problem
        Every problem that refuses it, each an error carrying its code.
    """

    def __init__(self, message: str, *, path: Path, problems: Sequence[Problem]) -> None:
        super().__init__(message)
        self.path = path
        self.problems = list(problems)


class UnknownSourceKind(RecipeError):
    """A source names a kind no adapter is registered for.

    Attributes
    ----------
    kind : str
        The kind the source names.
    known : tuple of str
        The kinds an adapter is registered for.
    """

    def __init__(self, message: str, *, kind: str, known: Sequence[str]) -> None:
        super().__init__(message)
        self.kind = kind
        self.known = tuple(known)


class SourcesNotOrdered(RecipeError):
    """What the sources consume gives them no order to run in.

    Attributes
    ----------
    kinds : tuple of str
        The sources that cannot be placed.
    missing : tuple of str
        The kinds they consume that the recipe does not declare; empty where they depend on each
        other.
    """

    def __init__(self, message: str, *, kinds: Sequence[str], missing: Sequence[str] = ()) -> None:
        super().__init__(message)
        self.kinds = tuple(kinds)
        self.missing = tuple(missing)


class TermUnfilled(RecipeError):
    """A source needs a name the build cannot supply (Part 12 §4).

    The name is a term the recipe cannot fill, or an option its entry does not set.

    Attributes
    ----------
    kind : str
        The source's kind.
    name : str
        The name its adapter declares it needs.
    """

    def __init__(self, message: str, *, kind: str, name: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.name = name


class MaterializerNotFound(RecipeError):
    """A `[[materialize]]` entry names a resource nothing derives.

    Attributes
    ----------
    resource : str
        The resource the entry names.
    known : tuple of str
        The resources this writer derives.
    """

    def __init__(self, message: str, *, resource: str, known: Sequence[str]) -> None:
        super().__init__(message)
        self.resource = resource
        self.known = tuple(known)


class NotesUnderStrict(RecipeError):
    """A source reported a note in a build that admits none.

    Attributes
    ----------
    kind : str
        The source's kind.
    notes : list of str
        The notes it reported since the build last looked.
    """

    def __init__(self, message: str, *, kind: str, notes: Sequence[str]) -> None:
        super().__init__(message)
        self.kind = kind
        self.notes = list(notes)


class ReplacementRefused(WriterError):
    """A recipe's `[packet].replaces` names what a build cannot replace (Part 05 §3.5).

    Attributes
    ----------
    problems : list of Problem
        One per entry refused, each an error carrying its code.
    """

    def __init__(self, message: str, *, problems: Sequence[Problem] = ()) -> None:
        super().__init__(message)
        self.problems = list(problems)


class AmendmentFault(StrEnum):
    """Why a packet cannot be amended, as the code an :exc:`AmendmentRefused` carries."""

    #: The root holds no published manifest, so there is no packet to amend.
    NO_PACKET = "no_packet"
    #: A held table carries an assigned identifier with no name beside it, or a null one.
    HELD_NAME_ABSENT = "held_name_absent"
    #: A held name or number already stands for something else of its kind.
    HELD_KEY_TAKEN = "held_key_taken"
    #: Delivered rows would change or grow a group of rows the packet holds.
    CHANGES_HELD = "changes_held"


class AmendmentRefused(WriterError, ValueError):
    """An amendment would change what Part 05 §15.2 forbids, or a build cannot amend this packet.

    Attributes
    ----------
    code : AmendmentFault
        Which refusal it is, whatever the names in the message.
    resource_id : str or None
        The table the refusal concerns; None where it concerns the packet.
    """

    def __init__(self, message: str, *, code: AmendmentFault, resource_id: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.resource_id = resource_id


class ExtensionNotFound(WriterError):
    """A recipe names an extension that is neither a file nor an installed distribution.

    Attributes
    ----------
    named : str
        The entry as the recipe names it.
    known : tuple of str
        The extensions installed distributions register.
    """

    def __init__(self, message: str, *, named: str, known: Sequence[str] = ()) -> None:
        super().__init__(message)
        self.named = named
        self.known = tuple(known)


class DeclarationUnreadable(WriterError, ValueError):
    """A file is no adapter declaration: absent, not JSON, or off the published schema."""


class SourceFault(StrEnum):
    """Why a source this package ships an adapter for cannot supply what a build asked of it."""

    #: The electrode table has no `group_name` column.
    NO_ELECTRODE_GROUPS = "no_electrode_groups"
    #: A series' contacts span several electrode groups, so it records no one probe.
    SERIES_SPANS_GROUPS = "series_spans_groups"
    #: Other than one clock belongs to a series' probe.
    NO_ONE_CLOCK = "no_one_clock"
    #: An array is not a Zarr v2 array.
    NOT_ZARR_V2 = "not_zarr_v2"
    #: An array has a rank its reader does not read.
    ARRAY_RANK = "array_rank"
    #: An array is pickled.
    PICKLED = "pickled"
    #: A chunk is absent and the fill value cannot stand in for it.
    FILL_VALUE = "fill_value"
    #: A strided read was asked of a reader that takes contiguous slabs.
    STRIDED_READ = "strided_read"
    #: A series' timestamps give no interval.
    NO_SAMPLE_INTERVAL = "no_sample_interval"
    #: A series' interval is not a whole number of its probe's ticks.
    NOT_A_DECIMATION = "not_a_decimation"
    #: A clock has no declared tick rate.
    NO_TICK_RATE = "no_tick_rate"
    #: The file states no session start time.
    NO_SESSION_START = "no_session_start"
    #: The recipe declares a signal the file does not hold with timestamps.
    SIGNAL_ABSENT = "signal_absent"
    #: The source was given no `interval_kind`.
    NO_INTERVAL_KIND = "no_interval_kind"
    #: The trials table lacks a column every trial needs.
    TRIAL_COLUMN_ABSENT = "trial_column_absent"
    #: A trial has no start or no stop.
    TRIAL_EDGE_MISSING = "trial_edge_missing"
    #: The root is not an NWB-Zarr directory and does not hold exactly one.
    NO_ONE_NWB = "no_one_nwb"
    #: A folder is not named as a curated stream is.
    STREAM_NAME = "stream_name"
    #: The root holds no curated directory.
    NO_CURATED_DIRECTORY = "no_curated_directory"
    #: No stream belongs to the experiment.
    NO_STREAM = "no_stream"
    #: A stream lacks a file the adapter reads.
    STREAM_FILE_ABSENT = "stream_file_absent"
    #: A `.npy` file has a format version this reader does not know.
    NPY_VERSION = "npy_version"
    #: A stream's unit IDs are not strictly increasing.
    UNIT_IDS_UNORDERED = "unit_ids_unordered"
    #: A sampling frequency is not a whole number of hertz.
    RATE_NOT_WHOLE = "rate_not_whole"
    #: A stream holds a different number of amplitudes and spikes.
    AMPLITUDES_MISALIGNED = "amplitudes_misaligned"
    #: A unit property holds a different number of values and units.
    PROPERTY_MISALIGNED = "property_misaligned"
    #: A sample index does not fit the packed sort key.
    SAMPLE_INDEX_OVERFLOW = "sample_index_overflow"
    #: The recording holds no TTL events.
    NO_TTL_EVENTS = "no_ttl_events"
    #: No stream carries HARP-aligned timestamps.
    NO_ALIGNED_STREAM = "no_aligned_stream"
    #: Two streams of one name disagree on samples both recorded.
    STREAMS_DISAGREE = "streams_disagree"
    #: Nothing gives a stream's first sample number.
    NO_FIRST_SAMPLE = "no_first_sample"
    #: The sync line has no rising edge.
    NO_RISING_EDGE = "no_rising_edge"
    #: Sync pulses do not increase on both clocks.
    PULSES_UNORDERED = "pulses_unordered"
    #: The root holds no Record Node directory.
    NO_RECORD_NODE = "no_record_node"
    #: The root holds no analyzer directory.
    NO_ANALYZER_DIRECTORY = "no_analyzer_directory"
    #: No analyzer belongs to the experiment.
    NO_ANALYZER = "no_analyzer"
    #: An analyzer states no channel list.
    NO_CHANNEL_LIST = "no_channel_list"
    #: An analyzer states no window or sampling rate for its templates.
    NO_TEMPLATE_WINDOW = "no_template_window"
    #: No unit the analyzer holds is in the packet's sorting.
    NO_UNIT_MATCHES = "no_unit_matches"
    #: The streams' templates span different windows.
    TEMPLATE_WINDOWS_DIFFER = "template_windows_differ"
    #: The streams' templates are in different units.
    TEMPLATE_UNITS_DIFFER = "template_units_differ"
    #: Every template is zero.
    TEMPLATES_ZERO = "templates_zero"
    #: Every deviation is zero over the mean's support.
    DEVIATIONS_ZERO = "deviations_zero"
    #: Deviations were asked for and the analyzer holds none.
    NO_DEVIATION = "no_deviation"
    #: An analyzer's unit IDs, mask rows and templates differ in number.
    TEMPLATES_MISALIGNED = "templates_misaligned"
    #: A unit has a template in more than one analyzer row.
    UNIT_REPEATED = "unit_repeated"
    #: A source states a fact the recipe declares otherwise, with no override.
    FACT_DIFFERS = "fact_differs"
    #: A source states a fact the amended packet holds otherwise.
    HELD_FACT_DIFFERS = "held_fact_differs"
    #: An acquisition window ends before it starts.
    WINDOW_REVERSED = "window_reversed"
    #: Preferring a source discarded a fact another stated.
    FACT_DISCARDED = "fact_discarded"
    #: A source stages a dense array and was supplied no `array_location`.
    NO_ARRAY_LOCATION = "no_array_location"
    #: No adapter is registered for the kind asked for.
    UNKNOWN_KIND = "unknown_kind"
    #: An adapter was supplied no root.
    NO_ROOT = "no_root"
    #: A protocol is in no group the profile names.
    PROTOCOL_UNKNOWN = "protocol_unknown"
    #: A delivery's command is not an argument list.
    COMMAND_NOT_A_LIST = "command_not_a_list"
    #: A delivery declares no command.
    NO_COMMAND = "no_command"
    #: A delivery failed; :exc:`DeliveryFailed` carries each failure.
    DELIVERY_FAILED = "delivery_failed"
    #: The adapter's command exited with a failure.
    COMMAND_EXITED = "command_exited"
    #: The adapter exited before it served anything.
    EXITED_BEFORE_SERVING = "exited_before_serving"
    #: A delivered file cannot be read.
    DELIVERED_FILE_UNREADABLE = "delivered_file_unreadable"
    #: A stream delivery did not end with the sentinel.
    NO_SENTINEL = "no_sentinel"
    #: A Flight delivery reported an error.
    FLIGHT_ERROR = "flight_error"
    #: The resource document is not JSON.
    DOCUMENT_NOT_JSON = "document_not_json"
    #: A resource document's entry declares itself packet-owned.
    ENTRY_NOT_EXTERNAL = "entry_not_external"
    #: A resource document's entry has a URI that is neither absolute nor a relative reference.
    ENTRY_URI = "entry_uri"
    #: The resource document does not satisfy its schema.
    DOCUMENT_SHAPE = "document_shape"
    #: A resource the build asked for never arrived.
    NEVER_ARRIVED = "never_arrived"
    #: A referenced resource binds no delivered catalog row.
    REFERENCE_UNBOUND = "reference_unbound"


class SourceDefect(WriterError, ValueError):
    """A source cannot supply what it was asked for, and the build cannot proceed past it.

    Carried as an exception rather than a note because it stops a build (Part 05 §4.4), where what
    an adapter worked around goes in the run's report (Part 12 §9).

    Attributes
    ----------
    code : str or None
        Which defect it is, whatever the names in the message: a :class:`SourceFault` from an
        adapter this package ships, and a code of its own from an adapter released separately.
        None where the adapter gave none.
    where : str or None
        The place the defect lies at, as the message names it: a path, a stream, a column or a
        resource.
    """

    def __init__(self, message: str, *, code: str | None = None, where: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.where = where


class UnsupportedEncoding(SourceDefect):
    """An array uses an encoding this package will not decode, such as ``pickle``."""


class DeliveryFailed(SourceDefect):
    """An adapter run out of process did not deliver what the build asked of it (Part 05 §4.4).

    Attributes
    ----------
    failures : list of SourceDefect
        Each failure, carrying its own code.
    """

    def __init__(self, message: str, *, failures: Sequence[SourceDefect], where: str | None = None) -> None:
        super().__init__(message, code=SourceFault.DELIVERY_FAILED, where=where)
        self.failures = list(failures)


class PayloadFault(StrEnum):
    """What a packet cannot own in a delivered payload, or why a payload binds no single resource."""

    #: An adapter hands over a payload and declares no `opaque_location`.
    NO_LOCATION = "no_location"
    #: A resource ID cannot name a resource directory.
    RESOURCE_ID_UNREPRESENTABLE = "resource_id_unrepresentable"
    #: A payload, or a member of one, has a name that is not representable.
    NAME_UNREPRESENTABLE = "name_unrepresentable"
    #: A handed-over payload is neither one file's bytes nor a directory's files.
    NOT_ONE_FORM = "not_one_form"
    #: A resource directory holds no payload, or more than one.
    NOT_ONE_PAYLOAD = "not_one_payload"
    #: An entry of the location is not a resource directory.
    NOT_A_RESOURCE_DIRECTORY = "not_a_resource_directory"
    #: A payload holds an empty directory.
    EMPTY_DIRECTORY = "empty_directory"
    #: A payload holds a member that is neither a regular file nor a directory.
    NOT_REGULAR = "not_regular"
    #: A payload names both a catalog row's resource and an opaque singleton.
    ROW_AND_SINGLETON = "row_and_singleton"
    #: A payload names a singleton the recipe does not leave its source owning.
    SINGLETON_NOT_OWNED = "singleton_not_owned"
    #: A payload names a resource several catalog rows carry.
    SEVERAL_ROWS = "several_rows"
    #: A payload names neither a catalog row's resource nor an opaque singleton.
    BINDS_NOTHING = "binds_nothing"
    #: One resource is delivered as a payload more than once.
    DELIVERED_TWICE = "delivered_twice"
    #: One resource is delivered as a payload and as a referenced resource.
    DELIVERED_AND_REFERENCED = "delivered_and_referenced"
    #: A catalog row of an opaque family carries no resource ID.
    ROW_UNNAMED = "row_unnamed"
    #: A catalog row of an opaque family is bound by no payload or referenced resource.
    ROW_UNBOUND = "row_unbound"


@dataclass(frozen=True)
class PayloadProblem:
    """One thing a :exc:`PayloadRefused` refuses.

    Attributes
    ----------
    code : PayloadFault
        Which fault it is, whatever the names in the message.
    message : str
        What is refused, naming the path or the resource.
    """

    code: PayloadFault
    message: str


class PayloadRefused(WriterError, ValueError):
    """A delivery holds something a packet cannot own, or a payload binds no single resource.

    Attributes
    ----------
    problems : list of PayloadProblem
        Each thing refused, carrying its code.
    source : str or None
        The source whose delivery is refused; None where the problems span sources.
    """

    def __init__(self, message: str, *, problems: Sequence[PayloadProblem] = (), source: str | None = None) -> None:
        super().__init__(message)
        self.problems = list(problems)
        self.source = source


class UsageFault(StrEnum):
    """What a call asked of the writer that it will not do, as the code a :exc:`UsageError` carries.

    A fault raised from two places shares a member.
    """

    #: A written table's footer names a compression or an encoding outside the writer floor.
    PARQUET_FLOOR = "parquet_floor"
    #: A record or a batch carries a column no loaded registry declares.
    UNDECLARED_COLUMN = "undeclared_column"
    #: A later batch carries an optional column the first batch lacked.
    COLUMN_AFTER_FIRST_BATCH = "column_after_first_batch"
    #: A reference names a source beside an absolute URI, which no source resolves.
    SOURCE_ON_ABSOLUTE_URI = "source_on_absolute_uri"
    #: A reference's URI is neither absolute nor a relative reference.
    URI_UNRESOLVABLE = "uri_unresolvable"
    #: Two registries were given for one extension.
    EXTENSION_TWICE = "extension_twice"
    #: An extension defines a resource outside its own namespace.
    EXTENSION_NAMESPACE = "extension_namespace"
    #: An extension redefines a core resource.
    EXTENSION_REDEFINES_CORE = "extension_redefines_core"
    #: An array or media names a declaration no loaded registry holds.
    UNKNOWN_DECLARATION = "unknown_declaration"
    #: A declaration is of another kind than the resource staged against it.
    DECLARATION_KIND = "declaration_kind"
    #: A declaration admits no family instances.
    NOT_A_FAMILY = "not_a_family"
    #: A resource ID lies outside the namespace that owns its declaration.
    INSTANCE_NAMESPACE = "instance_namespace"
    #: An array or media matches no one catalog row.
    CATALOG_ROW_UNBOUND = "catalog_row_unbound"
    #: The catalog row an array or media matches already names another resource.
    CATALOG_ROW_TAKEN = "catalog_row_taken"
    #: A resource was staged a second time.
    STAGED_TWICE = "staged_twice"
    #: Lineage was recorded for a resource the packet does not carry.
    LINEAGE_UNSTAGED = "lineage_unstaged"
    #: A staged array declares another resource ID than the one it was added under.
    RESOURCE_ID_DIFFERS = "resource_id_differs"
    #: The source resolution document would not satisfy its schema.
    SOURCES_DOCUMENT = "sources_document"
    #: A packet was committed with no session.
    NO_SESSION = "no_session"
    #: An amendment's packet version does not sort after the one it supersedes.
    VERSION_NOT_AFTER = "version_not_after"
    #: An amendment's packet version leaves the major version it supersedes.
    VERSION_MAJOR_CHANGED = "version_major_changed"
    #: A registry differs from the one the packet retains under the same ID and version.
    REGISTRY_DIGEST_DIFFERS = "registry_digest_differs"
    #: An array names a codec this writer does not emit.
    UNKNOWN_CODEC = "unknown_codec"
    #: A shard is not a whole number of chunks on every axis.
    SHARD_MISFIT = "shard_misfit"
    #: A clock's tick rate is not positive.
    TICK_RATE_NOT_POSITIVE = "tick_rate_not_positive"
    #: A wall-clock instant was asked of a clock that declares no `tick_zero_utc`.
    NO_TICK_ZERO = "no_tick_zero"
    #: A verification level is not one this writer records.
    UNKNOWN_LEVEL = "unknown_level"
    #: A source was asked to verify in a mode it does not have.
    UNKNOWN_VERIFY_MODE = "unknown_verify_mode"
    #: A source was handed a clock that belongs to another session.
    CLOCK_OTHER_SESSION = "clock_other_session"
    #: A name or a number already stands for something else of its kind.
    KEY_TAKEN = "key_taken"


class UsageError(WriterError, ValueError):
    """A call asks the writer for something it will not stage, write or amend as given.

    Attributes
    ----------
    code : UsageFault
        Which fault it is, whatever the names in the message.
    where : str or None
        The resource, clock, path or name the message is about, where it names one.
    """

    def __init__(self, message: str, *, code: UsageFault, where: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.where = where


class UndeclaredResource(WriterError, KeyError):
    """A call names a table no loaded registry defines.

    Attributes
    ----------
    resource_id : str
        The resource the call named.
    """

    def __init__(self, message: str, *, resource_id: str) -> None:
        super().__init__(message)
        self.resource_id = resource_id

    def __str__(self) -> str:
        """Return the message bare, where a `KeyError` would quote it."""
        return str(self.args[0])


class UnknownCompensation(WriterError, KeyError):
    """An adapter declares a compensation nothing registers.

    Attributes
    ----------
    identifier : str
        The compensation the adapter named.
    """

    def __init__(self, message: str, *, identifier: str) -> None:
        super().__init__(message)
        self.identifier = identifier

    def __str__(self) -> str:
        """Return the message bare, where a `KeyError` would quote it."""
        return str(self.args[0])


class CompensationsInvalid(WriterError, ValueError):
    """A distribution registers something other than a mapping of complete compensations."""


class FixedOffsetZone(WriterError, TypeError):
    """A zone was given as a fixed offset, which resolves daylight saving for no date."""


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

    Attributes
    ----------
    n_non_finite : int
        How many values were NaN or infinite.
    n_values : int
        How many values were given.
    """

    def __init__(self, message: str, *, n_non_finite: int, n_values: int) -> None:
        super().__init__(message)
        self.n_non_finite = n_non_finite
        self.n_values = n_values


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


class OutOfRange(WriterError, ValueError):
    """A number does not fit the integer width its column declares."""


class TickOverflow(WriterError, OverflowError):
    """A tick falls outside the 64-bit range a tick column holds."""


class Collided(WriterError, NotAligned):
    """Two spikes of one unit convert to the same reference tick, so the table cannot be built.

    Part 06 §4. This table is keyed on the converted tick, and a conversion preserves distinctness
    only where it expands -- a reference clock slower than a probe's collapses spikes that were
    distinct on the probe. Refusing costs nothing usable: a histogram over collapsed spikes
    undercounts them, so a clock that coarse makes this table the wrong instrument rather than a
    broken one, and Part 06 §2 makes not building it an ordinary outcome.

    Attributes
    ----------
    unit_id : int
        The unit whose spikes collide.
    t_tick : int
        The reference tick two of them convert to.
    """

    def __init__(self, message: str, *, unit_id: int, t_tick: int) -> None:
        super().__init__(message)
        self.unit_id = unit_id
        self.t_tick = t_tick


class PacketOccupied(WriterError, FileExistsError):
    """A packet root already holds what a commit would write there.

    Attributes
    ----------
    root : Path
        The packet root.
    occupied : list of str
        The root-relative paths in the way.
    """

    def __init__(self, message: str, *, root: Path, occupied: Sequence[str]) -> None:
        super().__init__(message)
        self.root = root
        self.occupied = list(occupied)


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
    """A staging area holds a promotion record this writer cannot read (Part 05 §6).

    Attributes
    ----------
    path : Path
        The promotion record.
    """

    def __init__(self, message: str, *, path: Path) -> None:
        super().__init__(message)
        self.path = path


__all__ = [
    "AmendmentFault",
    "AmendmentRefused",
    "CarriedNotAnInteger",
    "Collided",
    "CommitRefused",
    "CompensationsInvalid",
    "DeclarationUnreadable",
    "DeliveryFailed",
    "ExtensionNotFound",
    "FixedOffsetZone",
    "MaterializerNotFound",
    "NaiveTimestamp",
    "NonFinite",
    "NotCommitted",
    "NotesUnderStrict",
    "OffGrid",
    "OutOfRange",
    "PacketOccupied",
    "PayloadFault",
    "PayloadProblem",
    "PayloadRefused",
    "PromotionRecordUnreadable",
    "RecipeError",
    "RecipeFault",
    "RecipeUnreadable",
    "RecipeUnsound",
    "ReplacementRefused",
    "SourceDefect",
    "SourceFault",
    "SourcesNotOrdered",
    "TermUnfilled",
    "TickOverflow",
    "UndeclaredResource",
    "UnknownCompensation",
    "UnknownSourceKind",
    "UnsupportedEncoding",
    "UsageError",
    "UsageFault",
    "WriterError",
]
