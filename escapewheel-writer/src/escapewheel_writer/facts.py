"""A recipe's declared facts against what its sources and the held packet state (Part 05 §3.6).

- :func:`compare_declared_facts`, :func:`compare_held_facts` -- what a source states against the
  recipe, and against the packet being amended.
- :func:`refuse_a_discarded_fact` -- the refusal of a preference that discards a stated value
  (Part 05 §3.4).
- :func:`stored_types`, :func:`as_stored` -- a fact in the type its column stores.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from escapewheel_reader.resource_ids import CORE_SESSIONS, CORE_SUBJECTS

from .errors import SourceDefect, SourceFault
from .notes import Note, NoteCode
from .protocols import Located, SourceAdapter
from .recipe import Recipe, SourceSpec
from .writer import PacketWriter

if TYPE_CHECKING:
    from .session import Context


#: Part 05 §3.6: facts whose difference refuses a build rather than being reported. A subject is not
#: scoped to a session (Part 02 §7.1), so a wrong one agrees with another packet's animal instead of
#: colliding with the true value, and nothing downstream can detect it.
REFUSES_ON_DIFFERENCE = frozenset({"subject.subject_id"})

#: Part 05 §3.6's third disposition: facts where the source's value is written and the recipe's is
#: reported. Both ends of a session are derived from the acquisition windows a source declares, so
#: a hand-typed one transcribes that derivation rather than competing with it -- where a subject is
#: a fact about the world that the recipe may legitimately correct.
SOURCE_WINS = frozenset({"session.session_start_time", "session.session_end_time"})

#: The recipe block each resource's fields are declared in, for Part 05 §3.6's comparison type.
FACT_BLOCKS = {"session": CORE_SESSIONS, "subject": CORE_SUBJECTS}


def stored_types(registry: Mapping[str, Any]) -> dict[str, str]:
    """`block.field` to the registry type the packet stores it as (Part 05 §3.6)."""
    return {
        f"{block}.{column['name']}": column["type"]
        for block, resource in FACT_BLOCKS.items()
        for column in registry["resources"].get(resource, {}).get("table", {}).get("columns", ())
    }


def as_stored(value: Any, declared_type: str | None) -> Any:
    """Return a stated value as the type the packet stores it as, not as the text it crossed as.

    `_normalized` reduces two spellings to one for comparison; this is the other direction, and
    it is needed because a value that crossed a process boundary is a string whatever it means.
    """
    if value is None or declared_type not in {"timestamp", "date"}:
        return value
    if isinstance(value, datetime):
        return value.date() if declared_type == "date" else value
    if isinstance(value, date):
        return value
    parsed = datetime.fromisoformat(str(value))
    return parsed.date() if declared_type == "date" else parsed


def _normalized(value: Any, declared_type: str | None) -> Any:
    """Reduce a value to the type the packet stores it as, so two spellings compare equal.

    A `session.json` may state a subject as a number where a recipe declares it as a string, and
    an NWB states a date of birth as a timestamp where the column is a calendar date.
    Comparing what was written would refuse both. A wall clock is the same problem
    with more spellings -- `Z` against `+00:00`, and a `T` against the space `str` puts there -- so
    it is compared as the instant it names rather than as the text either side wrote.
    """
    if value is None:
        return None
    if declared_type == "timestamp":
        return as_stored(value, "timestamp")
    if declared_type == "date":
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.fromisoformat(str(value)).date()
    return str(value)


def _named(source: SourceAdapter, spec: SourceSpec) -> str:
    """Name a source in a message about what it states: by its path where it has one, else by its kind."""
    return str(source.path) if isinstance(source, Located) else spec.kind


def compare_declared_facts(spec: SourceSpec, source: SourceAdapter, context: Context, recipe: Recipe) -> None:
    """Compare what the recipe declares against what this source states (Part 05 §3.6).

    Three dispositions, and which one applies is the fact's rather than the source's. A fact that
    identifies something a reader resolves across packets refuses the build, since nothing
    downstream can detect a wrong one. A fact the source derives and the recipe transcribes is
    written from the source. Everything else is the ordinary case, where a recipe correcting a
    source is legitimate and the difference is reported.

    A source that states a fact the recipe does not declare is not comparing anything, and its
    value is taken: which is how `core.sessions` gets both its ends from the windows a session
    source declares, whether that source ran here or delivered them from elsewhere.
    """
    declared, notes = recipe.declared_facts, source.notes
    if context.held_facts is not None:
        compare_held_facts(spec, source, context.held_facts, notes, context.fact_types)
        return
    for fact, attribute in sorted(source.STATES.items()):
        stated = getattr(source, attribute, None)
        block, _, field = fact.partition(".")
        if stated is not None and fact in SOURCE_WINS and block == "session":
            context.session_extra[field] = as_stored(stated, context.fact_types.get(fact))
        if fact not in declared:
            continue
        want = declared[fact]
        reason = recipe.field_overrides.get(fact)
        if stated is None:
            # Silence is a fact about the source, not a disagreement -- but it is
            # reported, so a build log tells a verified fact from an asserted one.
            notes.append(Note(f"{fact} {want!r} went unchecked; {spec.kind} states none", NoteCode.FACT_UNCHECKED))
            continue
        column = context.fact_types.get(fact)
        if _normalized(stated, column) == _normalized(want, column):
            if reason is not None:
                notes.append(
                    Note(
                        f"{fact} declares an override and {spec.kind} states the same value", NoteCode.OVERRIDE_UNNEEDED
                    )
                )
            continue
        if reason is not None:
            notes.append(Note(f"{fact} is {want!r} over {spec.kind}'s {stated!r}: {reason}", NoteCode.FACT_OVERRIDDEN))
        elif fact in REFUSES_ON_DIFFERENCE:
            raise SourceDefect(
                f"{fact} is {want!r} and {_named(source, spec)} states {stated!r}; "
                "a declared fact differs from the source that states it, with no override (Part 05 §3.6)",
                code=SourceFault.FACT_DIFFERS,
                where=fact,
            )
        elif fact in SOURCE_WINS:
            notes.append(
                Note(
                    f"{fact} is {want!r} and {spec.kind} derives {stated!r}; the source's value is used",
                    NoteCode.SOURCE_VALUE_USED,
                )
            )
        else:
            notes.append(
                Note(
                    f"{fact} is {want!r} and {spec.kind} states {stated!r}; the recipe's value is used",
                    NoteCode.RECIPE_VALUE_USED,
                )
            )


def compare_held_facts(
    spec: SourceSpec, source: SourceAdapter, held: Mapping[str, Any], notes: list[str], fact_types: Mapping[str, str]
) -> None:
    """Compare what a source states against the amended packet's row, which prevails (Part 05 §3.6)."""
    for fact, attribute in sorted(source.STATES.items()):
        stated = getattr(source, attribute, None)
        if stated is None:
            continue
        kept = held.get(fact)
        column = fact_types.get(fact)
        if kept is not None and _normalized(stated, column) == _normalized(kept, column):
            continue
        if fact in REFUSES_ON_DIFFERENCE:
            raise SourceDefect(
                f"{fact} is {kept!r} in the packet and {_named(source, spec)} states {stated!r}; "
                "an amendment keeps the packet's value (Part 05 §3.6)",
                code=SourceFault.HELD_FACT_DIFFERS,
                where=fact,
            )
        notes.append(
            Note(
                f"{fact} is {kept!r} in the packet and {spec.kind} states {stated!r}; the packet's value is kept",
                NoteCode.PACKET_VALUE_KEPT,
            )
        )


def refuse_a_discarded_fact(writer: PacketWriter, context: Context, recipe: Recipe) -> None:
    """Refuse where preferring a source discarded a value another source stated (Part 05 §3.4).

    That section spends a preference to buy silence about a discarded row, on the premise that the
    loser's copy is redundant. A preference is declared before either source is opened, so nothing
    checked the premise: one naming a source that turns out to state less, or nothing at all, buys
    the same silence and loses the difference. A preferred source producing no rows while another
    does is the limiting case, every value being discarded.

    Rows are compared as staging fills them, so a `session_id` or owned name one source omits is
    not a loss, and correspond on equal non-null primary keys; a passed-over row with a null in its
    key corresponds to no row. Compared over declared columns. `metadata` is schemaless by design
    (Part 02 §8.6), so two sources filling it differently is not a difference this can weigh.

    A column override releases a null column that every corresponding preferred row leaves null,
    and nothing else: where some of a repeated key's rows state the value, keeping the preferred
    source's rows would be choosing among them. The preferred rows are staged as delivered either
    way, since a row composed from both would be a fact no source stated.
    """
    kinds = {spec.kind for spec in recipe.sources}
    overrides = recipe.column_overrides
    lost: list[str] = []
    released: dict[str, set[str]] = {}
    preferred = recipe.preferred
    for resource, by_kind in sorted(context.stated.items()):
        table = writer.spec(resource)
        if table is None or len(by_kind) < 2:
            continue
        # The preference names the winner. Reading it off whoever claims the resource is wrong for
        # a contributed one, where every claimant is a legitimate supplier of different rows.
        winner = preferred.get(resource)
        if winner not in kinds:
            continue
        kept = writer.filled(resource, by_kind.get(winner, []))
        key = list(table.get("primary_key") or [])
        columns = [c["name"] for c in table["columns"] if c["name"] != "metadata"]
        held = _by_key(kept, key)
        for kind, rows in sorted(by_kind.items()):
            if kind == winner or not rows:
                continue
            if not kept:
                lost.append(f"{resource}: {kind} stated {len(rows):,} row(s) and {winner or 'no source'} staged none")
                continue
            for row in writer.filled(resource, rows):
                matches = held.get(tuple(row.get(k) for k in key)) if key else None
                if not matches:
                    lost.append(f"{resource}: {kind} stated a row {winner} did not")
                    continue
                for name, stated, left in _left_null(resource, row, matches, columns):
                    if left == len(matches) and name in overrides:
                        released.setdefault(name, set()).add(kind)
                    elif left == len(matches):
                        lost.append(f"{name}: {kind} stated {stated!r} and {winner} left it null")
                    else:
                        lost.append(
                            f"{name}: {kind} stated {stated!r} and {winner} left it null in {left} of "
                            f"{len(matches)} rows with that key, which no column override releases"
                        )
    _report_releases(context, overrides, released)
    if lost:
        raise SourceDefect(
            "preferring a source discarded a fact another stated (Part 05 §3.4). Name a null column in "
            "[overrides] as resource.column with a reason, prefer the other source, or fix the one that "
            "states less:\n  " + "\n  ".join(sorted(set(lost))),
            code=SourceFault.FACT_DISCARDED,
        )


def _by_key(rows: list[dict[str, Any]], key: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    """Group preferred rows by primary key, leaving out a row with a null in its key, which matches none."""
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        if key and all(row.get(k) is not None for k in key):
            grouped.setdefault(tuple(row[k] for k in key), []).append(row)
    return grouped


def _left_null(
    resource: str, row: Mapping[str, Any], matches: list[dict[str, Any]], columns: list[str]
) -> list[tuple[str, Any, int]]:
    """Each `resource.column` a passed-over row states, its value, and how many matches leave it null."""
    found = []
    for column in columns:
        if row.get(column) is None:
            continue
        if left := sum(match.get(column) is None for match in matches):
            found.append((f"{resource}.{column}", row[column], left))
    return found


def _report_releases(context: Context, overrides: Mapping[str, str], released: Mapping[str, set[str]]) -> None:
    """Report each column override's release as information, and an idle one as a warning (Part 05 §3.6)."""
    for name, reason in sorted(overrides.items()):
        if name in released:
            context.notes.append(
                Note(
                    f"[overrides] {name} released the value {', '.join(sorted(released[name]))} stated: {reason}",
                    NoteCode.VALUE_RELEASED,
                )
            )
        else:
            context.notes.append(
                Note(f"warning: [overrides] {name} released no value in this build", NoteCode.COLUMN_OVERRIDE_IDLE)
            )


__all__ = ["as_stored", "compare_declared_facts", "compare_held_facts", "refuse_a_discarded_fact", "stored_types"]
