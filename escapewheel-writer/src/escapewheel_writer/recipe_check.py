"""Everything wrong with a recipe that is knowable without reading a source (Part 05 §3).

:func:`check` is what `Recipe.check` runs. Each `_*_problems` function reports one concern as
faults and messages, which `check` gives a level.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from typing import Any, NamedTuple

from escapewheel_reader.registries import declared_tables
from escapewheel_validator import Level

from .errors import RecipeFault
from .kinds import builtin, importable, state_accessors
from .recipe import RECIPE_SUPPLIES, TERMS, Problem, Recipe, declared, normalized_chosen_at, payloads
from .secrets import carries_a_secret

#: What Part 04 §4.1 admits after a resource ID's dot, which a prefix begins.
_PREFIX = re.compile(r"[a-z0-9_.-]*")


#: Options a build reaches a source with rather than an adapter reading them, so no declaration
#: names them and none is refused. `storage_options` says how to open the root and is consumed
#: where the store is opened (Part 12 §4). A facility a build applies through an option the
#: *adapter* reads is not one of these: Part 12 §4 makes the adapter declare it, which is why
#: `sample` is `sorter`'s to accept and not a build's to inject silently.
_BUILD_OPTIONS = frozenset({"storage_options"})


class _Found(NamedTuple):
    """A fault and the message that reports it, before `Recipe.check` gives it a level."""

    code: RecipeFault
    message: str


def check(
    recipe: Recipe,
    registry: Mapping[str, Any],
    extensions: Sequence[Mapping[str, Any]] = (),
    *,
    held_tables: Collection[str] = (),
    held_clocks: Collection[str] = (),
) -> list[Problem]:
    """Return everything wrong with `recipe`, as `Recipe.check` documents it."""
    tables = declared_tables(registry, strict=True)
    for document in extensions or ():
        tables.update(declared_tables(document, strict=True))
    # A source may own an opaque singleton, whose payload it delivers under the declaration's ID
    # (Part 12 §5); catalog instances are bound by the rows of the table it owns instead.
    singletons = payloads(registry, extensions)
    owners, claimants = recipe.owners, recipe.claimants
    supplied = {**claimants, **{r: claimants.get(r, ["packet"]) for r in held_tables}}
    errors: list[_Found] = []
    warnings: list[_Found] = []

    for resource, kinds in sorted(claimants.items()):
        if resource not in tables and resource not in singletons:
            errors.append(
                _Found(
                    RecipeFault.UNDEFINED_RESOURCE,
                    f"{kinds[0]} supplies {resource}, which the registry does not define",
                )
            )
    for resource, kinds in sorted(owners.items()):
        if len(kinds) > 1:
            errors.append(
                _Found(
                    RecipeFault.SEVERAL_OWNERS,
                    f"{resource} is owned by {len(kinds)} sources ({', '.join(sorted(kinds))}); declare a "
                    f"[preference] naming the one that knows more, or contributes where each holds part",
                )
            )
        elif len(claimants.get(resource, ())) > 1:
            others = sorted(set(claimants[resource]) - set(kinds))
            errors.append(
                _Found(
                    RecipeFault.OWNED_AND_SUPPLIED,
                    f"{resource} is owned by {kinds[0]} but also supplied by {', '.join(others)}",
                )
            )

    errors.extend(_arbitration_problems(recipe))
    errors.extend(_extension_problems(recipe, extensions or ()))
    warnings.extend(_unclaimed(recipe))
    errors.extend(_dangling_references(recipe, tables, claimants, warnings, supplied))
    errors.extend(_clock_problems(recipe, held_clocks))
    errors.extend(_preferred_run_problems(recipe))
    errors.extend(_amending_problems(recipe))
    errors.extend(_option_problems(recipe))
    errors.extend(_materialize_problems(recipe))
    errors.extend(_prefix_problems(recipe))
    errors.extend(_storage_problems(recipe))
    errors.extend(_delivery_problems(recipe))
    errors.extend(_declaration_problems(recipe, tables, singletons))
    errors.extend(_states_problems(recipe))
    errors.extend(_Found(RecipeFault.ENCODING_UNDECLARED, message) for message in recipe.encoding_problems(tables))
    fact_errors, fact_warnings, notes = _declared_fact_problems(recipe)
    errors.extend(fact_errors)
    warnings.extend(fact_warnings)

    return [
        Problem(level, message, code)
        for level, found in ((Level.ERROR, errors), (Level.WARNING, warnings), (Level.INFO, notes))
        for message, code in sorted({(message, code) for code, message in found})
    ]


def _arbitration_problems(recipe: Recipe) -> list[_Found]:
    """Report a repeated kind, an unsound preference, and a class contributing what it cannot produce.

    A source is named by its kind throughout, so a kind listed twice leaves a preference and
    every report unable to say which entry they mean (Part 05 §3.1). A preference declares
    ownership (Part 05 §3.3), so one naming a source that is absent, cannot supply the resource,
    or contradicts another entry's own `owns` or `contributes` has no sound reading. A delivered
    adapter's `contributes` is refused with the rest of its document (Part 12 §7); an
    imported one's is refused here.
    """
    problems: list[_Found] = []
    kinds = [spec.kind for spec in recipe.sources]
    problems += [
        _Found(
            RecipeFault.REPEATED_KIND,
            f"source {kind} is listed {kinds.count(kind)} times; a recipe lists a kind once, since everything "
            "names a source by its kind (Part 05 §3.1)",
        )
        for kind in sorted({k for k in kinds if kinds.count(k) > 1})
    ]
    by_kind = {spec.kind: spec for spec in recipe.sources}
    for resource, kind in sorted(recipe.preferred.items()):
        chosen = by_kind.get(kind)
        if chosen is None:
            problems.append(
                _Found(
                    RecipeFault.PREFERENCE_UNLISTED,
                    f"[preference] {resource} names {kind}, which this recipe does not list",
                )
            )
            continue
        if resource not in declared(chosen)["produces"]:
            problems.append(
                _Found(
                    RecipeFault.PREFERENCE_UNPRODUCED,
                    f"[preference] {resource} names {kind}, whose adapter does not declare it can supply it",
                )
            )
        for entry in recipe.document.get("source", []):
            other = str(entry.get("kind"))
            if other != kind and resource in (*entry.get("owns", ()), *entry.get("contributes", ())):
                problems.append(
                    _Found(
                        RecipeFault.PREFERENCE_CONTRADICTED,
                        f"[preference] {resource} names {kind}, and source {other} declares it under owns or "
                        "contributes; a preference says one source knows more, so the other supplies none of it",
                    )
                )
        producers = sorted({spec.kind for spec in recipe.sources if resource in declared(spec)["produces"]})
        if len(producers) < 2:
            problems.append(
                _Found(
                    RecipeFault.PREFERENCE_IDLE,
                    f"[preference] {resource} arbitrates nothing: only {', '.join(producers) or 'no source'} in "
                    "this recipe produces it (Part 05 §3.3)",
                )
            )
    for spec in recipe.sources:
        if spec.delivery is not None:
            continue
        asked = declared(spec)
        problems += [
            _Found(
                RecipeFault.CONTRIBUTES_UNPRODUCED,
                f"{spec.kind} contributes {resource}, which its produces does not name",
            )
            for resource in sorted(asked["contributes"] - asked["produces"])
        ]
    return problems


def _extension_problems(recipe: Recipe, extensions: Sequence[Mapping[str, Any]]) -> list[_Found]:
    """Report one extension listed in more than one `extensions` entry (Part 05 §3.1).

    Compared by `extension_id`, which only a resolved document carries, so a path paired with
    an installed id, or paths to two versions, are caught as well as a repeated string. A
    packet binds one registry per extension, so otherwise the build keeps one silently.
    """
    entries = (
        recipe.extensions
        if len(recipe.extensions) == len(extensions)
        else tuple(f"document {position}" for position in range(1, len(extensions) + 1))
    )
    by_extension: dict[str, list[str]] = {}
    for entry, document in zip(entries, extensions, strict=True):
        by_extension.setdefault(str(document["extension_id"]), []).append(entry)
    return [
        _Found(
            RecipeFault.REPEATED_EXTENSION,
            f"extension {extension_id} is listed in {len(named)} entries ({', '.join(repr(e) for e in named)}); "
            "a recipe lists an extension once, since a packet binds one registry per extension (Part 05 §3.1)",
        )
        for extension_id, named in sorted(by_extension.items())
        if len(named) > 1
    ]


def _states_problems(recipe: Recipe) -> list[_Found]:
    """Adapters a build cannot ask which recipe fields they state (Part 05 §3.4).

    Refused rather than defaulted: an adapter that declares nothing would otherwise read as
    one that states nothing, which is the failure `PRODUCES` has.
    """
    problems: list[_Found] = []
    for spec in sorted(recipe.sources, key=lambda s: s.kind):
        if not declared(spec)["declares_states"]:
            problems.append(
                _Found(
                    RecipeFault.STATES_UNDECLARED,
                    f"source {spec.kind} declares no STATES, so a build cannot tell what facts it states",
                )
            )
        if spec.delivery is not None:
            # An adapter a build cannot import exposes its stated values in its report rather
            # than through an attribute, so there is nothing here to look for (Part 12 §9).
            continue
        for fact, attribute in sorted(state_accessors(spec.kind).items()):
            problems.append(
                _Found(
                    RecipeFault.STATE_UNEXPOSED,
                    f"source {spec.kind} states {fact} through {attribute!r}, which its adapter does not expose",
                )
            )
    return problems


def _declared_fact_problems(recipe: Recipe) -> tuple[list[_Found], list[_Found], list[_Found]]:
    """Errors, warnings and notes about declared facts and their overrides (Part 05 §3.6).

    An empty override reason never loads (Part 05 §3.1). A field a source states is a warning because
    agreement is the likely case and only the build can tell, and a stale override costs a
    line rather than a build because it leaves the packet correct.
    """
    declared, stated = recipe.declared_facts, recipe.stated_by()
    errors: list[_Found] = []
    warnings: list[_Found] = []
    notes: list[_Found] = []
    for fact, reason in sorted(recipe.overrides.items()):
        if fact not in stated:
            warnings.append(
                _Found(
                    RecipeFault.OVERRIDE_IDLE,
                    f"[overrides] {fact} overrides nothing; no source in this recipe states it",
                )
            )
        elif fact not in declared:
            warnings.append(
                _Found(
                    RecipeFault.OVERRIDE_IDLE,
                    f"[overrides] {fact} overrides nothing; the recipe declares no value for it",
                )
            )
    for fact, kinds in sorted(stated.items()):
        if fact not in declared:
            continue
        who = ", ".join(kinds)
        if fact in recipe.overrides:
            notes.append(_Found(RecipeFault.OVERRIDE_APPLIED, f"{fact} is declared and overrides {who}"))
        else:
            warnings.append(
                _Found(RecipeFault.FACT_COMPARED, f"{fact} is declared and {who} states it; the build compares them")
            )
    return errors, warnings, notes


def _dangling_references(
    recipe: Recipe,
    tables: Mapping[str, Any],
    claimed: Mapping[str, list[str]],
    warnings: list[_Found],
    supplied: Mapping[str, list[str]] | None = None,
) -> list[_Found]:
    """Foreign keys from an owned table into a table no source produces.

    Severity follows the column: a **required** foreign key into an absent table means
    every row dangles, so the packet cannot validate. A **nullable** one may be legitimately
    empty, so it is a warning -- and worth saying, because `generate(only=...)` silently
    skips a foreign-key check whose target is absent, which is the quiet version of the
    same problem. `supplied` adds, as targets only, the tables an amended packet holds.
    """
    supplied = claimed if supplied is None else supplied
    problems: list[_Found] = []
    for resource in sorted(claimed):
        spec = tables.get(resource)
        if spec is None:
            continue
        presence = {c["name"]: c["presence"] for c in spec["columns"]}
        for reference in spec.get("references", []):
            target = reference["resource"]
            if target in supplied:
                continue
            columns = ", ".join(reference["columns"])
            if any(presence.get(c) == "required" for c in reference["columns"]):
                problems.append(
                    _Found(
                        RecipeFault.DANGLING_REFERENCE,
                        f"{resource}.{columns} requires {target}, which no source owns",
                    )
                )
            else:
                warnings.append(
                    _Found(
                        RecipeFault.DANGLING_REFERENCE,
                        f"{resource}.{columns} references {target}, which no source owns",
                    )
                )
    return problems


def _unclaimed(recipe: Recipe) -> list[_Found]:
    """Resources a listed source can produce that nothing in this recipe claims (Part 05 §3.5).

    A warning and not an error: narrowing is legitimate, and only the recipe's author knows
    whether this one was meant. It is the first of the three ways a recipe loses a resource,
    reported before a byte is read.
    """
    claimed = {resource for spec in recipe.sources for resource in spec.claims}
    claimed.update(RECIPE_SUPPLIES)
    return [
        _Found(RecipeFault.UNCLAIMED, f"{spec.kind} can produce {resource}, which no source in this recipe claims")
        for spec in recipe.sources
        for resource in sorted(declared(spec)["produces"] - claimed)
    ]


def _preferred_run_problems(recipe: Recipe) -> list[_Found]:
    """Two `preferred_run` entries of one key, or a `chosen_at` naming no instant (Part 05 §3.5)."""
    problems: list[_Found] = []
    keys = [(str(e["activity_type"]), str(e["scope_kind"]), str(e["scope"])) for e in recipe.preferred_runs]
    problems += [
        _Found(
            RecipeFault.REPEATED_PREFERRED_RUN,
            f"[[preferred_run]] {activity} of {kind} {scope} is declared {keys.count(key)} times; a recipe "
            "prefers one run per activity and scope (Part 05 §12)",
        )
        for key in sorted(set(keys))
        if keys.count(key) > 1
        for activity, kind, scope in [key]
    ]
    problems += [
        _Found(
            RecipeFault.CHOSEN_AT_NO_INSTANT,
            f"[[preferred_run]] {entry['processing_run_name']} gives chosen_at {entry['chosen_at']!r}, which "
            "names no instant; give an offset date-time",
        )
        for entry in recipe.preferred_runs
        if "chosen_at" in entry and normalized_chosen_at(entry["chosen_at"]) is None
    ]
    return problems


def _amending_problems(recipe: Recipe) -> list[_Found]:
    """Report each member an amending recipe declares where the packet's rows prevail (Part 05 §3.5)."""
    if recipe.amends is None:
        return []
    problems: list[_Found] = []
    if recipe.replaces:
        problems.append(
            _Found(
                RecipeFault.REPLACES_AND_AMENDS,
                "[packet] gives both replaces and amends, and a build replaces packets or amends one",
            )
        )
    declares = [
        f"[session] {name} is declared, and an amending recipe declares only session_id"
        for name in sorted(recipe.session)
        if name != "session_id"
    ]
    declares += [
        f"[subject] {name} is declared, and an amending recipe declares none" for name in sorted(recipe.subject)
    ]
    declares += [
        f"[overrides] {name} is declared, and an amending recipe declares none" for name in sorted(recipe.overrides)
    ]
    return problems + [_Found(RecipeFault.AMENDING_DECLARES, message) for message in declares]


def _storage_problems(recipe: Recipe) -> list[_Found]:
    """Storage options that carry a credential, which a recipe must not (Part 05 §3.1).

    Refused rather than redacted on the way in, because the recipe file is the author's and
    the value is in it: replacing it here would leave the packet clean and the file leaking,
    and the author would not learn. What a build records is redacted as well, since a recipe
    written before this check ran is already inside a packet.
    """
    return [
        _Found(
            RecipeFault.CREDENTIAL,
            f"[[source]] {spec.kind} sets storage_options.{name}, which is a credential; name a "
            f"profile or leave it to the environment, because the recipe is recorded in the packet "
            f"it builds",
        )
        for spec in recipe.sources
        for name, value in sorted(spec.storage_options.items())
        if carries_a_secret(str(name), value)
    ]


def _delivery_problems(recipe: Recipe) -> list[_Found]:
    """Report each source with no route to a build (Part 05 §3.9).

    There are three: a `[source.delivery]` block, which carries the command that runs the
    adapter out of process; `in_process`, which is the recipe author saying this machine
    installs the adapter beside the writer; and being an adapter this build ships, which runs
    in process unless its entry gives it a delivery, so a recipe need say nothing.

    What is left over is a kind another distribution registered and the recipe says nothing
    about. An adapter released independently of a build must declare a protocol (Part 12
    §3), and declaring one is not enough on its own: something still has to say what
    command runs it, and only the recipe knows.
    """
    problems: list[_Found] = []
    for spec in recipe.sources:
        if spec.in_process or spec.delivery is not None or builtin(spec.kind):
            continue
        problems.append(
            _Found(
                RecipeFault.NO_ROUTE,
                f"{spec.kind} is registered by another distribution and this recipe neither delivers it nor "
                f"runs it in process; give it a [source.delivery] command or set in_process",
            )
        )
    return problems


def _declaration_problems(recipe: Recipe, tables: Mapping[str, Any], singletons: Collection[str] = ()) -> list[_Found]:
    """Everything wrong with a source's declaration, knowable with nothing opened.

    Part 12 §7's checks for every source, whichever route it takes, plus what the recipe has
    to get right for a build to reach the adapter at all. A class is checked as the document it
    would generate, so the two forms are refused for the same defects. Each check fires on its
    own and names what is wrong, and none needs the adapter imported.
    """
    from . import declaration as document

    problems: list[_Found] = []
    for spec in recipe.sources:
        delivery = spec.delivery
        if delivery is not None:
            if spec.in_process:
                problems.append(
                    _Found(
                        RecipeFault.TWO_ROUTES,
                        f"{spec.kind} declares both a delivery and in_process; a source is reached one way or "
                        "the other (Part 05 §3.9)",
                    )
                )
            if not delivery.command:
                problems.append(
                    _Found(RecipeFault.NO_COMMAND, f"{spec.kind} declares a delivery and no command to run it with")
                )
            if delivery.declaration is not None and "unreadable" in delivery.declaration:
                problems.append(
                    _Found(RecipeFault.DECLARATION_UNREADABLE, f"{spec.kind}: {delivery.declaration['unreadable']}")
                )
                continue
        if (delivery is None or delivery.declaration is None) and not importable(spec.kind):
            if delivery is not None:
                problems.append(
                    _Found(
                        RecipeFault.NO_DECLARATION,
                        f"{spec.kind} names no declaration and this build cannot import it, so nothing says "
                        "what it produces",
                    )
                )
            continue
        asked = declared(spec)
        stated = {
            "kind": spec.kind,
            **({"protocols": list(asked["protocols"])} if asked["protocols"] else {}),
            "produces": sorted(asked["produces"]),
            "contributes": sorted(asked["contributes"]),
            "states": list(asked["states"]),
            "needs": list(asked["needs"]),
            "accepts": list(asked["accepts"]),
            "consumes": list(asked["consumes"]),
        }
        if delivery is None or delivery.declaration is None:
            # A document was shape-checked as it was read; a class is checked here, as one.
            shipped = builtin(spec.kind)
            if not shipped and not asked["protocols"]:
                problems.append(
                    _Found(
                        RecipeFault.NO_PROTOCOL,
                        f"{spec.kind} declares no protocol; an adapter released independently of a build "
                        f"declares at least one of {', '.join(document.PROTOCOLS)} (Part 12 §3)",
                    )
                )
            problems += [
                _Found(RecipeFault.DECLARATION_SHAPE, f"{spec.kind} declaration: {problem}")
                for problem in document.shape_problems(stated, shipped=True)
            ]
        problems += [
            _Found(code, f"{spec.kind} {refusal}")
            for code, refusal in document.refusals(
                stated, tables=tables, options=spec.options, terms=TERMS, payloads=singletons
            )
        ]
        named = delivery.protocol if delivery is not None else ""
        if named and asked["protocols"] and named not in asked["protocols"]:
            problems.append(
                _Found(
                    RecipeFault.PROTOCOL_UNDECLARED,
                    f"{spec.kind} names protocol {named!r}, which its adapter does not declare "
                    f"({', '.join(asked['protocols'])})",
                )
            )
        elif named and named not in document.PROTOCOLS:
            problems.append(
                _Found(
                    RecipeFault.PROTOCOL_UNKNOWN,
                    f"{spec.kind} names protocol {named!r}, which is in no group this profile names",
                )
            )
    return problems


def _option_problems(recipe: Recipe) -> list[_Found]:
    """Options a source kind requires and the recipe does not set, terms it sets, and unread options.

    All are refused before any source is opened (Part 12 §4). A term the build fills is not
    a recipe's business, so only the names that fall through to the recipe's options are
    reported here. An option the adapter names nowhere is the converse: the recipe states
    something about the packet that never reaches the source, and its author's next evidence
    would be its absence from the output.
    """
    problems: list[_Found] = [
        _Found(RecipeFault.OPTION_UNSET, f"source {spec.kind} requires {name!r}, which this entry does not set")
        for spec in recipe.sources
        for name in declared(spec)["needs"]
        if name not in TERMS and name not in spec.options
    ]
    problems += [
        _Found(
            RecipeFault.OPTION_IS_TERM,
            f"source {spec.kind} sets {name!r}, which is a term the build fills rather than an option",
        )
        for spec in recipe.sources
        for name in sorted(spec.options)
        if name in TERMS
    ]
    for spec in recipe.sources:
        known = set(declared(spec)["needs"]) | set(declared(spec)["accepts"])
        problems += [
            _Found(
                RecipeFault.OPTION_UNREAD,
                f"source {spec.kind} sets {name!r}, which it declares neither as needed nor as accepted",
            )
            for name in sorted(spec.options)
            if name not in known and name not in _BUILD_OPTIONS and name not in TERMS
        ]
    return problems


def _materialize_problems(recipe: Recipe) -> list[_Found]:
    """Refuse a `[[materialize]]` resource nothing derives, or a parameter its materializer lacks.

    Materialization runs at commit, after every source has been read, so either would
    otherwise surface only once the build's whole cost had been paid.
    """
    import inspect

    from . import materialize
    from .session import MATERIALIZERS

    taken = {
        name
        for name, parameter in inspect.signature(materialize.materialize_spike_events).parameters.items()
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
    }
    problems: list[_Found] = []
    for spec in recipe.materialize:
        if spec.resource not in MATERIALIZERS:
            known = ", ".join(sorted(MATERIALIZERS)) or "nothing"
            problems.append(
                _Found(RecipeFault.NO_MATERIALIZER, f"no materializer for {spec.resource}; this writer derives {known}")
            )
            continue
        problems += [
            _Found(
                RecipeFault.MATERIALIZE_PARAMETER,
                f"[[materialize]] {spec.resource} sets {name!r}, which its materializer does not take",
            )
            for name in sorted(spec.options)
            if name not in taken
        ]
    return problems


def _prefix_problems(recipe: Recipe) -> list[_Found]:
    """Refuse a prefix no resource ID admits, or sources that would spell one identifier two ways.

    A prefix begins the name an adapter mints a resource ID from, so it holds only what Part 04
    §4.1 admits after the ID's dot. Adapters that read `prefix` compose shared identifiers from
    it -- `nwb`, `lfp` and `waveforms` each name a contact through `nwb.contact_ids` -- and a
    writer numbers a name (Part 05 §4.3), so a prefix on one and not another mints a second row
    for one entity. An unset prefix counts as a value, since a delivered adapter's default is
    not declared.
    """
    problems: list[_Found] = [
        _Found(
            RecipeFault.PREFIX_CHARACTERS,
            f"source {spec.kind!r}: prefix {spec.options['prefix']!r} holds characters outside [a-z0-9_.-], "
            "which a resource ID does not admit (Part 04 §4.1)",
        )
        for spec in recipe.sources
        if "prefix" in spec.options
        and not (isinstance(spec.options["prefix"], str) and _PREFIX.fullmatch(spec.options["prefix"]))
    ]
    taking = sorted(
        (spec for spec in recipe.sources if "prefix" in {*declared(spec)["needs"], *declared(spec)["accepts"]}),
        key=lambda spec: spec.kind,
    )
    values = {spec.kind: spec.options.get("prefix") for spec in taking}
    # By repr, since an option may be a TOML table, which is unhashable.
    if len({repr(value) for value in values.values()}) <= 1:
        return problems
    named = ", ".join(f"{kind} {'unset' if value is None else repr(value)}" for kind, value in values.items())
    return [
        *problems,
        _Found(
            RecipeFault.PREFIX_DISAGREES,
            f"sources disagree on prefix ({named}); every source whose adapter accepts prefix sets the same "
            "one, or one entity gets two identifiers",
        ),
    ]


def _clock_problems(recipe: Recipe, held: Collection[str] = ()) -> list[_Found]:
    """Clock IDs that are declared twice, referenced but absent, or parented to nothing.

    A clock an amended packet holds counts as declared, and declaring it again is refused, since
    its held row would then meet a second (Part 05 §3.5).
    """
    declared = [c.clock_id for c in recipe.clocks]
    known = set(declared) | set(held)
    problems: list[_Found] = [
        _Found(RecipeFault.REPEATED_CLOCK, f"clock {c} is declared more than once")
        for c in sorted({c for c in declared if declared.count(c) > 1})
    ]
    problems += [
        _Found(
            RecipeFault.CLOCK_HELD,
            f"clock {c} is declared, and the packet this recipe amends holds a clock of that name",
        )
        for c in sorted(set(declared) & set(held))
    ]
    reference = recipe.session.get("reference_clock_id")
    if reference and reference not in known:
        problems.append(
            _Found(
                RecipeFault.REFERENCE_CLOCK_UNDECLARED,
                f"session.reference_clock_id is {reference!r}, which no [[clock]] declares",
            )
        )
    for clock in recipe.clocks:
        if clock.parent_clock_id and clock.parent_clock_id not in known:
            problems.append(
                _Found(
                    RecipeFault.PARENT_CLOCK_UNDECLARED,
                    f"clock {clock.clock_id} names parent {clock.parent_clock_id!r}, which is not declared",
                )
            )
    return problems


__all__ = ["check"]
